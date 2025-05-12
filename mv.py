import random
import networkx as nx
import circuit
import re

# === MACHINE VIRTUELLE SIMULANT UN PROTOCOLE DE CALCUL SÉCURISÉ ENTRE ALICE ET BOB ===
class VirtualMachine:
    def __init__(self, alice_code, bob_code):
        # Instructions pour Alice et Bob
        self.alice_code = alice_code
        self.bob_code = bob_code

        # Variables privées pour Alice et Bob
        self.alice_vars = {}
        self.bob_vars = {}

        # Buffers pour la communication entre Alice et Bob
        self.buffer_ab = None
        self.buffer_ba = None

        # Compteurs de programme (instruction courante)
        self.alice_pc = 0
        self.bob_pc = 0

        # États d’attente
        self.alice_waiting = False
        self.bob_waiting = False
        self.finished = False

    # Évalue une expression binaire ou un appel rnd()
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

    # Lance l'exécution jusqu'à ce que tous les programmes soient terminés
    def run(self):
        max_cycles = 10000  # Pour éviter les boucles infinies
        cycle = 0
        while not self.finished and cycle < max_cycles:
            cycle += 1
            self.finished = True
            self.alice_waiting = False
            self.bob_waiting = False

            # Bob exécute une instruction s’il n’a pas fini
            if self.bob_pc < len(self.bob_code):
                self.step_bob()
                self.finished = False

            # Alice exécute une instruction s’il n’a pas fini
            if self.alice_pc < len(self.alice_code):
                self.step_alice()
                self.finished = False

            # Si les deux parties attendent un message, alors deadlock
            if self.alice_waiting and self.bob_waiting:
                print("Deadlock détecté : les deux attendent.")
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

    # Exécution d’une commande
    def execute_command(self, cmd, vars, side="bob"):
        op = cmd["op"]
        if op == "assign":
            vars[cmd["dest"]] = self.eval_expr(cmd["expr"], vars)

        elif op == "push":
            buffer = "buffer_ab" if side == "alice" else "buffer_ba"
            if getattr(self, buffer) is not None:
                setattr(self, f"{side}_waiting", True)
                return
            val = self.eval_expr(cmd["value"], vars)
            setattr(self, buffer, val)

        elif op == "pop":
            buffer = "buffer_ba" if side == "alice" else "buffer_ab"
            buf_val = getattr(self, buffer)
            if buf_val is None:
                setattr(self, f"{side}_waiting", True)
                return
            vars[cmd["dest"]] = buf_val
            setattr(self, buffer, None)

        elif op == "push4":
            buffer = "buffer_ab" if side == "alice" else "buffer_ba"
            if getattr(self, buffer) is not None:
                setattr(self, f"{side}_waiting", True)
                return
            values = [self.eval_expr(v, vars) for v in cmd["values"]]
            setattr(self, buffer, tuple(values))

        elif op == "pop4":
            buffer = "buffer_ba" if side == "alice" else "buffer_ab"
            recv_buf = getattr(self, buffer)
            if not isinstance(recv_buf, tuple) or len(recv_buf) != 4:
                setattr(self, f"{side}_waiting", True)
                return
            x1, x2, x3, x4 = recv_buf
            y1 = self.eval_expr(cmd["y1"], vars)
            y2 = self.eval_expr(cmd["y2"], vars)
            result = (y1 * x2 + (1 + y1) * x1 + y2 * x4 + (1 + y2) * x3) & 1
            vars[cmd["dest"]] = result
            setattr(self, buffer, None)

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


# === COMPILATEUR QUI TRADUIT UN CIRCUIT LOGIQUE EN INSTRUCTIONS POUR LA VM ===
def compiler(circuit, labels):
    alice_code = []
    bob_code = []
    var_counter = 0

    # Génère un nom de variable temporaire unique
    def new_var(prefix):
        nonlocal var_counter
        var_name = f"{prefix}{var_counter}"
        var_counter += 1
        return var_name

    # Parcours topologique du DAG représentant le circuit
    for node_id in nx.topological_sort(circuit):
        label = labels[node_id]
        preds = list(circuit.predecessors(node_id))

        # Entrée d’Alice
        if label.startswith("IN_A"):
            rnd = new_var("t")
            masked = new_var("t")
            alice_code += [
                f"{rnd} = rnd()",
                f"{masked} = {rnd} + xA{node_id}",
                f"push({masked})"
            ]
            bob_code += [f"xB{node_id} = pop()"]

        # Entrée de Bob
        elif label.startswith("IN_B"):
            rnd = new_var("t")
            masked = new_var("t")
            bob_code += [
                f"{rnd} = rnd()",
                f"{masked} = {rnd} + xB{node_id}",
                f"push({masked})"
            ]
            alice_code += [f"xA{node_id} = pop()"]

        # Porte AND (avec protocole d’évaluation sécurisé)
        elif label.startswith("AND"):
            t1 = new_var("t")
            t2 = new_var("t")
            t3 = new_var("t")
            t4 = new_var("t")
            bob_code += [
                f"{t1} = rnd()",
                f"{t2} = rnd()",
                f"{t3} = {t1} + xB{preds[0]}",
                f"{t4} = {t2} + xB{preds[1]}",
                f"push({t1}, {t3}, {t2}, {t4})",
                f"{t1} = {t1} + {t2}",
                f"xB{node_id} = xB{preds[0]} * xB{preds[1]}",
                f"xB{node_id} = xB{node_id} + {t1}"
            ]
            alice_code += [
                f"xA{node_id} = pop(xA{preds[0]}, xA{preds[1]})",
                f"{t1} = xA{preds[0]} * xA{preds[1]}",
                f"xA{node_id} = {t1} + xA{node_id}"
            ]

        # Porte NOT (inversion uniquement chez Bob)
        elif label.startswith("NOT"):
            bob_code += [f"xB{node_id} = xB{preds[0]} + 1"]
            alice_code += [f"xA{node_id} = xA{preds[0]}"]

        # Porte XOR
        elif label.startswith("XOR"):
            alice_code += [f"xA{node_id} = xA{preds[0]} + xA{preds[1]}"]
            bob_code += [f"xB{node_id} = xB{preds[0]} + xB{preds[1]}"]

        # Sortie pour Alice
        elif label.startswith("OUT_A"):
            alice_code += [
                f"xA{node_id} = pop()",
                f"xA{node_id} = xA{preds[0]} + xA{node_id}"
            ]
            bob_code += [
                f"push(xB{preds[0]})",
                f"xB{node_id} = xB{preds[0]}"
            ]

        # Sortie pour Bob
        elif label.startswith("OUT_B"):
            bob_code += [
                f"xB{node_id} = pop()",
                f"xB{node_id} = xB{preds[0]} + xB{node_id}"
            ]
            alice_code += [
                f"push(xA{preds[0]})",
                f"xA{node_id} = xA{preds[0]}"
            ]

    # On parse chaque ligne vers des instructions exécutables
    return [parse_line(line) for line in alice_code], [parse_line(line) for line in bob_code]


# === FONCTIONS DE PARSING DE CHAÎNES EN INSTRUCTIONS ===
def parse_expr(expr):
    expr = expr.strip()
    if expr == 'rnd()':
        return 'rnd()'
    if '+' in expr:
        parts = expr.split('+')
        if len(parts) == 2:
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
        return {"op": "pop4", "dest": m.group(1).strip(),
                "y1": parse_expr(m.group(2)), "y2": parse_expr(m.group(3))}
    if '=' in line:
        dest, expr = line.split('=')
        return {"op": "assign", "dest": dest.strip(), "expr": parse_expr(expr)}
    raise ValueError(f"Unsupported line: {line}")


# === EXEMPLE DE LANCEMENT D'UNE SIMULATION ===
n = 1
G, labels = circuit.generate_max_min_circuit(n)
a = 0
b = 1
a_bits = circuit.int_to_bits(a, n)
b_bits = circuit.int_to_bits(b, n)

# Compilation du circuit en instructions Alice/Bob
alice_code, bob_code = compiler(G, labels)
vm = VirtualMachine(alice_code, bob_code)

# Injection des bits d’entrée dans la VM
for node_id in nx.topological_sort(G):
    label = labels[node_id]
    if label.startswith("IN_A"):
        vm.set_variable("A", f"xA{node_id}", a_bits.pop(0))
    elif label.startswith("IN_B"):
        vm.set_variable("B", f"xB{node_id}", b_bits.pop(0))

# Exécution du protocole
vm.run()

# Récupération des bits de sortie
out_a_bits, out_b_bits = [], []
for node_id in nx.topological_sort(G):
    label = labels[node_id]
    if label.startswith("OUT_A"):
        out_a_bits.append(vm.get_variable("A", f"xA{node_id}"))
    elif label.startswith("OUT_B"):
        out_b_bits.append(vm.get_variable("B", f"xB{node_id}"))

# Conversion des bits en entier
out_a = circuit.bits_to_int(out_a_bits)
out_b = circuit.bits_to_int(out_b_bits)

# Affichage du résultat
print(f"Entrées : A = {a}, B = {b}")
print(f"Résultat MAX d'Alice (OUT_A) : {out_a}")
print(f"Résultat MAX de Bob (OUT_B) : {out_b}")
print("Succès" if out_a == max(a, b) and out_b == max(a, b) else "Erreur")
