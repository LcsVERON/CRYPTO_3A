import random
import networkx as nx
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
            if expr == 'rnd()':
                return random.randint(0, 1)
            return context.get(expr, 0)
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
        while not self.finished:
            self.finished = True
            if not self.alice_waiting and self.alice_pc < len(self.alice_code):
                self.step_alice()
                self.finished = False
            if not self.bob_waiting and self.bob_pc < len(self.bob_code):
                self.step_bob()
                self.finished = False

    def step_alice(self):
        if self.alice_pc >= len(self.alice_code):
            return
        cmd = self.alice_code[self.alice_pc]
        self.execute_command(cmd, self.alice_vars, self.buffer_ab, self.buffer_ba, side="alice")
        self.alice_pc += 1

    def step_bob(self):
        if self.bob_pc >= len(self.bob_code):
            return
        cmd = self.bob_code[self.bob_pc]
        self.execute_command(cmd, self.bob_vars, self.buffer_ba, self.buffer_ab, side="bob")
        self.bob_pc += 1

    def execute_command(self, cmd, vars, send_buf, recv_buf, side="alice"):
        op = cmd["op"]
        if op == "assign":
            vars[cmd["dest"]] = self.eval_expr(cmd["expr"], vars)
        elif op == "push":
            if send_buf is not None:
                if side == "alice":
                    self.alice_waiting = True
                else:
                    self.bob_waiting = True
                return
            send_buf = cmd["value"]
            if side == "alice":
                self.buffer_ab = send_buf
            else:
                self.buffer_ba = send_buf
        elif op == "pop":
            if recv_buf is None:
                if side == "alice":
                    self.alice_waiting = True
                else:
                    self.bob_waiting = True
                return
            vars[cmd["dest"]] = recv_buf
            if side == "alice":
                self.buffer_ba = None
            else:
                self.buffer_ab = None
        elif op == "push4":
            if send_buf is not None:
                if side == "alice":
                    self.alice_waiting = True
                else:
                    self.bob_waiting = True
                return
            send_buf = tuple(self.eval_expr(e, vars) for e in cmd["values"])
            if side == "alice":
                self.buffer_ab = send_buf
            else:
                self.buffer_ba = send_buf
        elif op == "pop4":
            if recv_buf is None:
                if side == "alice":
                    self.alice_waiting = True
                else:
                    self.bob_waiting = True
                return
            (x1, x2, x3, x4) = recv_buf
            y1 = self.eval_expr(cmd["y1"], vars)
            y2 = self.eval_expr(cmd["y2"], vars)
            result = (y1 * x2 + (1 - y1) * x1 + y2 * x4 + (1 - y2) * x3) & 1
            vars[cmd["dest"]] = result
            if side == "alice":
                self.buffer_ba = None
            else:
                self.buffer_ab = None

        if side == "alice":
            self.alice_waiting = False
        else:
            self.bob_waiting = False

    # Méthodes ajoutées pour gérer les variables
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

# Fonction qui permet de "formater" la série d'exécutions de commandes qu'auront à effectuer Alice et Bob
def compiler(circuit):
    alice_code = []
    bob_code = []
    
    for node_id in circuit:
        node = circuit[node_id]
        label = node["label"]

        if label == "IN_A":
            # Alice choisit un bit aléatoire pour masquer sa donnée et l'envoie à Bob
            alice_code.append(f"xA{node_id + 7} = rnd()")
            alice_code.append(f"xA{node_id + 8} = xA{node_id + 7} + xA{node_id}")
            alice_code.append("push(xA{});".format(node_id + 8))
            alice_code.append(f"xA{node_id} = xA{node_id + 7}")
            bob_code.append("xB{} = pop()".format(node_id))

        elif label == "IN_B":
            # Bob masque sa donnée et l'envoie à Alice
            bob_code.append(f"xB{node_id + 6} = rnd()")
            bob_code.append(f"xB{node_id + 7} = xB{node_id + 6} + xB{node_id}")
            bob_code.append("push(xB{});".format(node_id + 7))
            bob_code.append(f"xB{node_id} = xB{node_id + 6}")
            alice_code.append("xA{} = pop()".format(node_id))

        elif label == "NOT":
            # NOT est x + 1
            alice_code.append(f"xA{node_id} = xA{node['in'][0]} + 1")
            bob_code.append(f"xB{node_id} = xB{node['in'][0]}")

        elif label == "XOR":
            # XOR = somme bit à bit
            alice_code.append(f"xA{node_id} = xA{node['in'][0]} + xA{node['in'][1]}")
            bob_code.append(f"xB{node_id} = xB{node['in'][0]} + xB{node['in'][1]}")

        elif label == "AND":
            # Conjonction : protocole OT avec push/pop
            # Variables temporaires
            a, b = node['in']
            alice_code += [
                f"xA{node_id + 8} = rnd()",
                f"xA{node_id + 9} = rnd()",
                f"xA{node_id + 10} = xA{node_id + 8} + xA{a}",
                f"xA{node_id + 11} = xA{node_id + 9} + xA{b}",
                "push(xA{}, xA{}, xA{}, xA{})".format(
                    node_id + 8, node_id + 10, node_id + 9, node_id + 11
                ),
                f"xA{node_id + 8} = xA{node_id + 8} + xA{node_id + 9}",
                f"xA{node_id} = xA{a} xA{b}",
                f"xA{node_id} = xA{node_id} + xA{node_id + 8}"
            ]
            bob_code += [
                f"xB{node_id} = pop(xB{b}, xB{a})",
                f"xB{node_id + 8} = xB{a} xB{b}",
                f"xB{node_id} = xB{node_id} + xB{node_id + 8}"
            ]

        elif label == "OUT_A":
            # Alice récupère la sortie
            alice_code.append("xA{} = pop()".format(node['in'][0]))
            alice_code.append(f"xA{node_id} = xA{node['in'][0]} + xA{node_id}")
            bob_code.append("push(xB{})".format(node['in'][0]))
            bob_code.append(f"xB{node_id} = xB{node['in'][0]}")

        elif label == "OUT_B":
            # Bob récupère la sortie
            alice_code.append("push(xA{})".format(node['in'][0]))
            alice_code.append(f"xA{node_id} = xA{node['in'][0]}")
            bob_code.append("xB{} = pop()".format(node['in'][0]))
            bob_code.append(f"xB{node_id} = xB{node['in'][0]}")

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
    return expr  # Just a variable


def parse_line(line):
    line = line.strip().rstrip(';')
    
    # push(x)
    if line.startswith("push("):
        inner = line[5:-1].strip()
        if ',' in inner:  # push(x1, x2, x3, x4)
            values = [parse_expr(e.strip()) for e in inner.split(',')]
            return {"op": "push4", "values": values}
        else:
            return {"op": "push", "value": parse_expr(inner)}
    
    # x = pop()
    if re.match(r'^\w+\s*=\s*pop\(\)$', line):
        dest = line.split('=')[0].strip()
        return {"op": "pop", "dest": dest}
    
    # x = pop(x1, x2)
    m = re.match(r'^(\w+)\s*=\s*pop\(([^,]+),\s*([^)]+)\)$', line)
    if m:
        dest = m.group(1).strip()
        y1 = parse_expr(m.group(2).strip())
        y2 = parse_expr(m.group(3).strip())
        return {"op": "pop4", "dest": dest, "y1": y1, "y2": y2}
    
    # x = e (assign)
    if '=' in line:
        dest, expr = line.split('=')
        return {"op": "assign", "dest": dest.strip(), "expr": parse_expr(expr)}
    
    raise ValueError(f"Unsupported line: {line}")

def extract_circuit(G, labels):
    circuit = {}
    for node in nx.topological_sort(G):
        label = labels[node]
        preds = list(G.predecessors(node))
        circuit_id = hash(node) % (10**6)  # ou un simple compteur, ou juste node si c’est un int
        circuit[circuit_id] = {
            "label": label,
            "in": preds  # les identifiants des nœuds d'entrée
        }
    return circuit


# Exemple d'utilisation avec les circuits
G, labels = circuit.generate_max_min_circuit(8)
circuit_test = extract_circuit(G, labels)

alice_code, bob_code = compiler(circuit_test)

a = 42  # première valeur
b = 100 # deuxième valeur

a_bits = circuit.int_to_bits(a, 8)
b_bits = circuit.int_to_bits(b, 8)

vm = VirtualMachine(alice_code, bob_code)

# Initialisation des variables A et B dans la machine virtuelle
for i in range(8):
    vm.set_variable("A", f"xA{i}", a_bits[i])
    vm.set_variable("B", f"xB{i}", b_bits[i])

vm.run()

out_a_bits = [vm.get_variable("A", f"xA{i}") for i in range(8)]
out_b_bits = [vm.get_variable("B", f"xB{i}") for i in range(8)]

out_a = circuit.bits_to_int(out_a_bits)
out_b = circuit.bits_to_int(out_b_bits)

print(f"Entrées : A = {a}, B = {b}")
print(f"Résultat MAX d'Alice (OUT_A) : {out_a}")
print(f"Résultat MAX de Bob (OUT_B) : {out_b}")
print("Succès" if out_a == max(a, b) and out_b == max(a, b) else "Erreur")