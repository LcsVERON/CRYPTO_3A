import random
import networkx as nx
import time
import circuit
import re

# Définir la machine virtuelle comme un objet
class VirtualMachine:
    def __init__(self, alice_code, bob_code):
        self.alice_code = alice_code
        self.bob_code = bob_code
        self.alice_vars = {}
        self.bob_vars = {}
        self.buffer_ab = None  # Tampon d'Alice vers Bob
        self.buffer_ba = None  # Tampon de Bob vers Alice
        self.alice_pc = 0
        self.bob_pc = 0
        self.alice_waiting = False
        self.bob_waiting = False
        self.finished = False

    def eval_expr(self, expr, context):
        if isinstance(expr, str):
            if expr.strip() == 'rnd()':
                return random.randint(0, 1)
            return context.get(expr.strip(), 0)
        elif isinstance(expr, tuple):
            op = expr[0]
            if op == '+':
                return (self.eval_expr(expr[1], context) ^ self.eval_expr(expr[2], context)) & 1
            elif op == '+1':
                return (self.eval_expr(expr[1], context) ^ 1) & 1
            elif op == '*':
                return (self.eval_expr(expr[1], context) & self.eval_expr(expr[2], context)) & 1
        return expr

    def run(self):
        max_cycles = 10000
        cycle = 0
        #print(self.alice_code)
        while not self.finished and cycle < max_cycles:
            print("Variables d'Alice :", self.alice_vars)
            print("Variables de Bob :", self.bob_vars)
            print("Tampon d'Alice vers Bob ")
            print(self.buffer_ab)
            print("Tampon de Bob vers Alice ")
            print(self.buffer_ba)
            print("commande en cours d'Alice :", self.alice_code[self.alice_pc] if self.alice_pc < len(self.alice_code) else "Fin")
            print("commande en cours de Bob :", self.bob_code[self.bob_pc] if self.bob_pc < len(self.bob_code) else "Fin")

            cycle += 1
            self.finished = True
            self.alice_waiting = False
            self.bob_waiting = False
            
            if self.bob_pc < len(self.bob_code):
                self.step_bob()
                self.finished = False
                            
            if self.alice_pc < len(self.alice_code):
                self.step_alice()
                self.finished = False

            if self.alice_waiting and self.bob_waiting:
                print("Deadlock possible: les deux parties attendent.")
                break

    def step_alice(self):
        if self.alice_pc >= len(self.alice_code):
            return
        cmd = self.alice_code[self.alice_pc]
        self.execute_command(cmd, self.alice_vars, side="alice")
        if not self.alice_waiting:
            self.alice_pc += 1

    def step_bob(self):
        if self.bob_pc >= len(self.bob_code):
            return
        cmd = self.bob_code[self.bob_pc]
        self.execute_command(cmd, self.bob_vars, side="bob")
        if not self.bob_waiting:
            self.bob_pc += 1

    def execute_command(self, cmd, vars, side="bob"):
        op = cmd["op"]

        if op == "assign":
            vars[cmd["dest"]] = self.eval_expr(cmd["expr"], vars)

        elif op == "push":
            buffer_name = "buffer_ab" if side == "alice" else "buffer_ba"
            if getattr(self, buffer_name) is not None:
                if side == "alice": self.alice_waiting = True
                else: self.bob_waiting = True
                return
            val = self.eval_expr(cmd["value"], vars)
            setattr(self, buffer_name, val)
            print(f"[{side.upper()}] PUSH:", val)


        elif op == "pop":
            buffer_name = "buffer_ba" if side == "alice" else "buffer_ab"
            buf_val = getattr(self, buffer_name)
            if buf_val is None:
                if side == "alice": self.alice_waiting = True
                else: self.bob_waiting = True
                return
            vars[cmd["dest"]] = buf_val
            print(f"[{side.upper()}] POP → {cmd['dest']}:", buf_val)
            setattr(self, buffer_name, None)



        elif op == "push4":
            buffer_name = "buffer_ab" if side == "alice" else "buffer_ba"
            if getattr(self, buffer_name) is not None:
                if side == "alice": self.alice_waiting = True
                else: self.bob_waiting = True
                return
            values = [self.eval_expr(v, vars) for v in cmd["values"]]
            setattr(self, buffer_name, tuple(values))
            print(f"[{side.upper()}] PUSH4:", values)


        elif op == "pop4":
            buffer_name = "buffer_ba" if side == "alice" else "buffer_ab"
            recv_buf = getattr(self, buffer_name)
            if not isinstance(recv_buf, tuple) or len(recv_buf) != 4:
                if side == "alice": self.alice_waiting = True
                else: self.bob_waiting = True
                return
            x1, x2, x3, x4 = recv_buf
            y1 = self.eval_expr(cmd["y1"], vars)
            y2 = self.eval_expr(cmd["y2"], vars)
            result = (y1 * x2 + (1 - y1) * x1 + y2 * x4 + (1 - y2) * x3) & 1
            vars[cmd["dest"]] = result
            print(f"[{side.upper()}] POP4 → {cmd['dest']}:", {
                "received": recv_buf,
                "y1": y1,
                "y2": y2,
                "result": result
            })
            setattr(self, buffer_name, None)


    def set_variable(self, side, var_name, value):
        if side == "A":
            self.alice_vars[var_name] = value
        elif side == "B":
            self.bob_vars[var_name] = value

    def get_variable(self, side, var_name):
        if side == "A":
            return self.alice_vars.get(var_name, 0)
        elif side == "B":
            return self.bob_vars.get(var_name, 0)        


def compiler(circuit, labels):
    alice_code = []
    bob_code = []
    var_counter = 0
    
    def new_var(prefix):
        nonlocal var_counter
        var_name = f"{prefix}{var_counter}"
        var_counter += 1
        return var_name
    
    def in_idx(node_id, x_type):
        # On parcourt les prédécesseurs du nœud jusqu'à trouver un noeud avec le label "IN_X"
        for pred in reversed(list(circuit.predecessors(node_id))):
            if labels[pred] == f"IN_{x_type}":
                return pred
        return None  # Si aucun prédécesseur avec le label "IN_X" n'est trouvé avant node_id
        
        

    for node_id in nx.topological_sort(circuit):
        label = labels[node_id]
        predecessors = list(circuit.predecessors(node_id))  #on récupère les prédécesseurs du noeud

        #on écupère l'ID des noeuds prédécesseurs
        predecessor_ids = [pred for pred in predecessors]
    
        if label.startswith("IN_A"):
            rnd = new_var("t")
            masked = new_var("t")
            alice_code += [
                f"{rnd} = rnd()",
                f"{masked} = {rnd} + xA{node_id}",
                f"push({masked})",
                f"xA{node_id} = {rnd}"
            ]
            bob_code += [
                f"xB{node_id} = pop()"
            ]

        elif label.startswith("IN_B"):
            rnd = new_var("t")
            masked = new_var("t")
            bob_code += [
                f"{rnd} = rnd()",
                f"{masked} = {rnd} + xB{node_id}",
                f"push({masked})",
                f"xB{node_id} = {rnd}"
            ]
            alice_code += [
                f"xA{node_id} = pop()"
            ]
            
        elif label.startswith("AND"):
            
            t1 = new_var("t")
            t2 = new_var("t")
            t3 = new_var("t")
            t4 = new_var("t")
            t5 = new_var("t")
            bob_code += [
                f"{t1} = rnd()",
                f"{t2} = rnd()",
                f"{t3} = {t1} + xB{predecessor_ids[1]}",
                f"{t4} = {t2} + xB{in_idx(node_id, "B")}",
                f"push({t1}, {t3}, {t2}, {t4})",
                f"{t1} = {t1} + {t2}",
                f"xB{node_id} = xB{predecessor_ids[1]} * xB{in_idx(node_id, "B")}",
                f"xB{node_id} = xB{node_id} * {t1}"
            ]
            alice_code += [
                f"xA{node_id} = pop({t5}, xA{predecessor_ids[0]})",
                f"{t1} = {t5} * xA{predecessor_ids[0]}",
                f"xA{node_id} = {t1} + xA{node_id}",
            ]

        elif label.startswith("NOT"):
            bob_code += [
                f"xB{node_id} = xB{predecessor_ids[0]} + 1"
            ]
            alice_code += [
                f"xA{node_id} = xA{predecessor_ids[0]}"
            ]

        elif label.startswith("XOR"):
            alice_code += [
                f"xA{node_id} = xA{predecessor_ids[0]} + xA{predecessor_ids[1]}",
            ]
            bob_code += [
                f"xB{node_id} = xB{predecessor_ids[0]} + xB{predecessor_ids[1]}",
            ]


        elif label.startswith("OUT_A"):
            alice_code += [
                f"xA{node_id} = pop()",
                f"xA{node_id} = xA{predecessor_ids[0]} + xA{node_id}"
            ]
            bob_code += [
                f"push(xB{predecessor_ids[0]})",
                f"xB{node_id} = xB{predecessor_ids[0]}"
            ]

        elif label.startswith("OUT_B"):
            bob_code += [
                f"xB{node_id} = pop()",
                f"xB{node_id} = xB{predecessor_ids[0]} + xB{node_id}"
            ]
            alice_code += [
                f"push(xA{predecessor_ids[0]})",
                f"xA{node_id} = xA{predecessor_ids[0]}"
            ]

    alice_structured = [parse_line(line) for line in alice_code]
    bob_structured = [parse_line(line) for line in bob_code]
    return alice_structured, bob_structured


def parse_expr(expr):
    expr = expr.strip()
    if expr == 'rnd()':
        return 'rnd()'
    if '+' in expr:
        parts = expr.split('+')
        left = parts[0].strip()
        right = parts[1].strip()
        if right == '1':
            return ('+1', left)
        return ('+', left, right)
    if '*' in expr:
        parts = expr.split('*')
        return ('*', parts[0].strip(), parts[1].strip())
    return expr

def parse_line(line):
    line = line.strip().rstrip(';')
    if line.startswith("push("):
        inner = line[5:-1].strip()
        if ',' in inner:
            values = [parse_expr(e.strip()) for e in inner.split(',')]
            return {"op": "push4", "values": values}
        else:
            return {"op": "push", "value": parse_expr(inner)}
    if re.match(r'^\w+\s*=\s*pop\(\)$', line):
        dest = line.split('=')[0].strip()
        return {"op": "pop", "dest": dest}
    m = re.match(r'^(\w+)\s*=\s*pop\(([^,]+),\s*([^)]+)\)$', line)
    if m:
        dest = m.group(1).strip()
        y1 = parse_expr(m.group(2).strip())
        y2 = parse_expr(m.group(3).strip())
        return {"op": "pop4", "dest": dest, "y1": y1, "y2": y2}
    if '=' in line:
        dest, expr = line.split('=')
        return {"op": "assign", "dest": dest.strip(), "expr": parse_expr(expr)}
    raise ValueError(f"Unsupported line: {line}")


# Exemple d'utilisation avec les circuits
n=1
G, labels = circuit.generate_max_min_circuit(n)
print("Labels du circuit :")
for node, label in labels.items():
    print(f"{node}: {label}")

a = 1 
b = 0

a_bits = circuit.int_to_bits(a, n)
b_bits = circuit.int_to_bits(b, n)

alice_code, bob_code = compiler(G, labels)


vm = VirtualMachine(alice_code, bob_code)

for node_id in nx.topological_sort(G):
    label = labels[node_id]
    if label.startswith("IN_A"):
        vm.set_variable("A", f"xA{node_id}", a_bits.pop(0))
    elif label.startswith("IN_B"):
        vm.set_variable("B", f"xB{node_id}", b_bits.pop(0))


# Exécution du programme
vm.run()

print("Variables d'Alice :")
print(vm.alice_vars)
print("Variables de Bob :")
print(vm.bob_vars)

out_a_bits = []
out_b_bits = []

for node_id in nx.topological_sort(G):
    label = labels[node_id]
    if label.startswith("OUT_A"):
        out_a_bits.append(vm.get_variable("A", f"xA{node_id}"))
        print(vm.get_variable("A", f"xA{node_id}"))
    elif label.startswith("OUT_B"):
        out_b_bits.append(vm.get_variable("B", f"xB{node_id}"))


out_a = circuit.bits_to_int(out_a_bits)
out_b = circuit.bits_to_int(out_b_bits)

print(f"Entrées : A = {a}, B = {b}")
print(f"Résultat MAX d'Alice (OUT_A) : {out_a}")
print(f"Résultat MAX de Bob (OUT_B) : {out_b}")
print("Succès" if out_a == max(a, b) and out_b == max(a, b) else "Erreur")
