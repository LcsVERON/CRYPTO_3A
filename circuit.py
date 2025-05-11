import networkx as nx

#fonction qui génère le circuit logique de la fonction max_n
def generate_max_min_circuit(n):
    G = nx.DiGraph()
    labels = {}

    #entrées
    in_a = [f"IN_A_{i}" for i in range(n)]
    in_b = [f"IN_B_{i}" for i in range(n)]

    for node in in_a:
        labels[node] = "IN_A"
    for node in in_b:
        labels[node] = "IN_B"

    equal = None #verifie A == B
    a_greater = None #verifie A > B

    for i in reversed(range(n)):
        a_bit = in_a[i]
        b_bit = in_b[i]

        #NOT B
        not_b = f"NOT_B_{i}"
        labels[not_b] = "NOT"
        G.add_edge(b_bit, not_b)

        #A > B pour ce bit seul
        a_greater_b = f"A_GREATER_B_{i}"
        labels[a_greater_b] = "AND"
        G.add_edge(a_bit, a_greater_b)
        G.add_edge(not_b, a_greater_b)

        #A == B pour ce bit seul
        a_xor_b = f"A_XOR_B_{i}"
        labels[a_xor_b] = "XOR"
        G.add_edge(a_bit, a_xor_b)
        G.add_edge(b_bit, a_xor_b)

        not_a_xor_b = f"NOT_A_XOR_B_{i}"
        labels[not_a_xor_b] = "NOT"
        G.add_edge(a_xor_b, not_a_xor_b)

        if equal is None:
            #initialisation
            a_greater = a_greater_b
            equal = not_a_xor_b
        else:
            #nouveau a_greater = (equal AND a_greater_b) XOR a_greater
            and_node = f"AND_EQUAL_GREATER_{i}"
            labels[and_node] = "AND"
            G.add_edge(equal, and_node)
            G.add_edge(a_greater_b, and_node)

            or_node = f"OR_GREATER_{i}"
            labels[or_node] = "XOR"
            G.add_edge(a_greater, or_node)
            G.add_edge(and_node, or_node)

            a_greater = or_node

            #nouveau equal = (equal AND (A_i == B_i))
            new_equal = f"AND_EQUAL_{i}"
            labels[new_equal] = "AND"
            G.add_edge(equal, new_equal)
            G.add_edge(not_a_xor_b, new_equal)

            equal = new_equal

    #a_greater = 1 si A > B, sinon 0
    #sélection des bits pour OUT_A et OUT_B
    for i in range(n):
        a_bit = in_a[i]
        b_bit = in_b[i]

        # pour OUT_A (le maximum)
        not_a_greater = f"NOT_A_GREATER_SELECT_{i}"
        labels[not_a_greater] = "NOT"
        G.add_edge(a_greater, not_a_greater)

        a_and = f"A_AND_SELECT_{i}"
        labels[a_and] = "AND"
        G.add_edge(a_greater, a_and)
        G.add_edge(a_bit, a_and)

        b_and = f"B_AND_SELECT_{i}"
        labels[b_and] = "AND"
        G.add_edge(not_a_greater, b_and)
        G.add_edge(b_bit, b_and)

        xor_out_a = f"XOR_OUT_A_{i}"
        labels[xor_out_a] = "XOR"
        G.add_edge(a_and, xor_out_a)
        G.add_edge(b_and, xor_out_a)

        # Sortie vers OUT_A (Alice)
        out_a = f"OUT_A_{i}"
        labels[out_a] = "OUT_A"
        G.add_edge(xor_out_a, out_a)

        # Sortie vers OUT_B (Bob) - identique à OUT_A
        out_b = f"OUT_B_{i}"
        labels[out_b] = "OUT_B"
        G.add_edge(xor_out_a, out_b)



    return G, labels

#fonction qui évalue le circuit logique
def evaluate_circuit(G, labels, inputs):
    values = inputs.copy()
    order = list(nx.topological_sort(G))

    for node in order:
        preds = list(G.predecessors(node))
        
        if node in values:
            continue
        label = labels[node]
        
        if label == "NOT":
            values[node] = 1 - values[preds[0]]
        elif label == "AND":
            values[node] = values[preds[0]] & values[preds[1]]
        elif label == "XOR":
            values[node] = values[preds[0]] ^ values[preds[1]]
        elif label.startswith("OUT"):
            values[node] = values[preds[0]]

    outputs = {node: values[node] for node in labels if labels[node] in {"OUT_A", "OUT_B"}}
    return outputs

#fonctions de conversion entre int et bits
def int_to_bits(x, n):
    return [(x >> i) & 1 for i in range(n)]

def bits_to_int(bits):
    return sum(bit << i for i, bit in enumerate(bits))

#Test exhaustif pour n=8
n = 8
G, labels = generate_max_min_circuit(n)

for a in range(2**n):
    for b in range(2**n):
        inputs = {f"IN_A_{i}": (a >> i) & 1 for i in range(n)}
        inputs.update({f"IN_B_{i}": (b >> i) & 1 for i in range(n)})

        outputs = evaluate_circuit(G, labels, inputs)

        out_a = bits_to_int([outputs[f"OUT_A_{i}"] for i in range(n)])
        out_b = bits_to_int([outputs[f"OUT_B_{i}"] for i in range(n)])

        assert out_a == max(a, b), f"erreur max: a={a} b={b} => out_a={out_a}, attendu={max(a, b)}"
        assert out_b == max(a, b), f"erreur max: a={a} b={b} => out_a={out_a}, attendu={max(a, b)}"

print("tous les tests sont passés avec succès sur 8 bits.")
