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

            if self.alice_pc < len(self.alice_code):
                self.step_alice()
                self.finished = False

            if self.bob_pc < len(self.bob_code):
                self.step_bob()
                self.finished = False

            if self.alice_waiting and self.bob_waiting:
                print("Deadlock possible: les deux parties attendent.")
                break

    def step_alice(self):
        #print(self.alice_pc)
        #print(len(self.alice_code))
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

    def execute_command(self, cmd, vars, side="alice"):
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

def compiler(circuit):
    alice_code = []
    bob_code = []
    temp_id = 0

    def fresh():
        nonlocal temp_id
        temp_id += 1
        return f"t{temp_id}"

    for node_id in circuit:
        node = circuit[node_id]
        label = node["label"]
        inputs = node["in"]

        if label.startswith("IN_A"):
            rnd = fresh()
            masked = fresh()
            alice_code.extend([
                f"{rnd} = rnd()",
                f"{masked} = {rnd} + xA{node_id}",
                f"push({masked})",
                f"xA{node_id} = {rnd}"
            ])
            bob_code.append(f"xB{node_id} = pop()")

        elif label.startswith("IN_B"):
            rnd = fresh()
            masked = fresh()
            bob_code.extend([
                f"{rnd} = rnd()",
                f"{masked} = {rnd} + xB{node_id}",
                f"push({masked})",
                f"xB{node_id} = {rnd}"
            ])
            alice_code.append(f"xA{node_id} = pop()")

        elif label.startswith ("NOT"):
            alice_code.append(f"xA{node_id} = xA{inputs[0]} + 1")
            bob_code.append(f"xB{node_id} = xB{inputs[0]}")

        elif label.startswith ("XOR"):
            alice_code.append(f"xA{node_id} = xA{inputs[0]} + xA{inputs[1]}")
            bob_code.append(f"xB{node_id} = xB{inputs[0]} + xB{inputs[1]}")

        elif label.startswith ("AND"):
            xA, yA = f"xA{inputs[0]}", f"xA{inputs[1]}"
            xB, yB = f"xB{inputs[0]}", f"xB{inputs[1]}"
            r1, r2 = fresh(), fresh()
            m1, m2 = fresh(), fresh()
            alice_code.extend([
                f"{r1} = rnd()",
                f"{r2} = rnd()",
                f"{m1} = {r1} + {xA}",
                f"{m2} = {r2} + {yA}",
                f"push({r1}, {m1}, {r2}, {m2})",
                f"xA{node_id} = {xA} * {yA} + {r1} + {r2}"
            ])
            bob_code.extend([
                f"xB{node_id} = pop({xB}, {yB})",
                f"xB{node_id} = {xB} * {yB} + xB{node_id}"
            ])

        elif label.startswith("OUT_A"):
            alice_code.append(f"xA{node_id} = pop()")
            bob_code.append(f"push(xB{inputs[0]})")

        elif label.startswith("OUT_B"):
            bob_code.append(f"xB{node_id} = pop()")
            alice_code.append(f"push(xA{inputs[0]})")

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

def extract_circuit(G, labels):
    circuit = {}
    for i, node in enumerate(nx.topological_sort(G)):
        label = labels[node]
        preds = list(G.predecessors(node))
        circuit[i] = {"label": label, "in": preds}
    return circuit

# Exemple d'utilisation avec les circuits
n=1
G, labels = circuit.generate_max_min_circuit(n)
print("Labels du circuit :")
for node, label in labels.items():
    print(f"{node}: {label}")

circuit_test = extract_circuit(G, labels)

alice_code, bob_code = compiler(circuit_test)

a = 1 
b = 0

a_bits = circuit.int_to_bits(a, n)
b_bits = circuit.int_to_bits(b, n)

vm = VirtualMachine(bob_code, alice_code)

# Initialisation des variables pour Alice et Bob
alice_input_nodes = [i for i, data in circuit_test.items() if data["label"] == "IN_A"]
bob_input_nodes = [i for i, data in circuit_test.items() if data["label"] == "IN_B"]

# Associer les bits aux bons indices de nœuds d'entrée
for idx, node in enumerate(alice_input_nodes):
    vm.set_variable("A", f"xA{node}", a_bits[idx])  # On associe le bit avec le bon nœud d'entrée pour Alice

for idx, node in enumerate(bob_input_nodes):
    vm.set_variable("B", f"xB{node}", b_bits[idx])  # On associe le bit avec le bon nœud d'entrée pour Bob


# Exécution du programme
vm.run()

print("Variables d'Alice :")
print(vm.alice_vars)
print("Variables de Bob :")
print(vm.bob_vars)

out_a_nodes = [i for i, data in circuit_test.items() if data["label"] == "OUT_A"]
out_b_nodes = [i for i, data in circuit_test.items() if data["label"] == "OUT_B"]

out_a_bits = [vm.get_variable("A", f"xA{i}") for i in out_a_nodes]
out_b_bits = [vm.get_variable("B", f"xB{i}") for i in out_b_nodes]


out_a = circuit.bits_to_int(out_a_bits)
out_b = circuit.bits_to_int(out_b_bits)

print(f"Entrées : A = {a}, B = {b}")
print(f"Résultat MAX d'Alice (OUT_A) : {out_a}")
print(f"Résultat MAX de Bob (OUT_B) : {out_b}")
print("Succès" if out_a == max(a, b) and out_b == max(a, b) else "Erreur")
