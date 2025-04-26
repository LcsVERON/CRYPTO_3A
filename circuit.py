import networkx as nx

#fonction qui permet de générer le circuit logique de la fonction max_n
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

    #comparaison bit par bit
    greater_bits = []
    equal_bits = []

    for i in reversed(range(n)):
        a_bit = in_a[i]
        b_bit = in_b[i]

        not_b = f"NOT_B_{i}"
        labels[not_b] = "NOT"
        G.add_edge(b_bit, not_b)

        a_gt_b = f"A_GREATER_B_{i}"
        labels[a_gt_b] = "AND"
        G.add_edge(a_bit, a_gt_b)
        G.add_edge(not_b, a_gt_b)

        a_xor_b = f"A_XOR_B_{i}"
        labels[a_xor_b] = "XOR"
        G.add_edge(a_bit, a_xor_b)
        G.add_edge(b_bit, a_xor_b)

        not_a_xor_b = f"NOT_A_XOR_B_{i}"
        labels[not_a_xor_b] = "NOT"
        G.add_edge(a_xor_b, not_a_xor_b)

        greater_bits.append(a_gt_b)
        equal_bits.append(not_a_xor_b)

    #comparaison finale
    greater = greater_bits[0] #variable vérifiant si A>B
    for i in range(1, n):
        temp_and = f"TEMP_AND_{i}" #vérifie si A>B et si les bits précédents étaient égaux
        labels[temp_and] = "AND"
        G.add_edge(equal_bits[i-1], temp_and)
        G.add_edge(greater_bits[i], temp_and)

        #on crée GREATER OR TEMP_AND avec NOT(NOT(GREATER) AND NOT(TEMP_AND))
        not_greater = f"NOT_{greater}"
        not_temp_and = f"NOT_{temp_and}"

        labels[not_greater] = "NOT"
        labels[not_temp_and] = "NOT"
        G.add_edge(greater, not_greater)
        G.add_edge(temp_and, not_temp_and)

        new_greater = f"GREATER_{i}"
        labels[new_greater] = "AND"
        G.add_edge(not_greater, new_greater)
        G.add_edge(not_temp_and, new_greater)

        greater = new_greater

    #greater contient NOT(NOT(res)) : il est inversé, il faut le ré-inverser pour obtenir le résultat final
    greater_final = f"NOT_{greater}"
    labels[greater_final] = "NOT"
    G.add_edge(greater, greater_final)

    #sélection des bits de sortie
    for i in range(n):
        a_bit = in_a[i]
        b_bit = in_b[i]

        #pour OUT_A (max)
        a_selected_a = f"A_SELECTED_A_{i}"
        labels[a_selected_a] = "AND"
        G.add_edge(greater_final, a_selected_a)
        G.add_edge(a_bit, a_selected_a)

        not_greater_final = f"NOT_GREATER_FINAL"
        labels[not_greater_final] = "NOT"
        if not_greater_final not in labels:  #on le crée une seule fois
            G.add_edge(greater_final, not_greater_final)

        b_selected_a = f"B_SELECTED_A_{i}"
        labels[b_selected_a] = "AND"
        G.add_edge(not_greater_final, b_selected_a)
        G.add_edge(b_bit, b_selected_a)

        out_bit_a = f"OUT_A_{i}"
        labels[out_bit_a] = "XOR"
        G.add_edge(a_selected_a, out_bit_a)
        G.add_edge(b_selected_a, out_bit_a)
        labels[out_bit_a] = "OUT_A"
        #si A>B, on sélectionne les bits de A, sinon ceux de B

        #pour OUT_B (min)
        a_selected_b = f"A_SELECTED_B_{i}"
        labels[a_selected_b] = "AND"
        G.add_edge(not_greater_final, a_selected_b)
        G.add_edge(a_bit, a_selected_b)

        b_selected_b = f"B_SELECTED_B_{i}"
        labels[b_selected_b] = "AND"
        G.add_edge(greater_final, b_selected_b)
        G.add_edge(b_bit, b_selected_b)

        out_bit_b = f"OUT_B_{i}"
        labels[out_bit_b] = "XOR"
        G.add_edge(a_selected_b, out_bit_b)
        G.add_edge(b_selected_b, out_bit_b)
        labels[out_bit_b] = "OUT_B"
        #si A>B, on sélectionne les bits de B, sinon ceux de A

    return G, labels #on retourne le circuit final et les labels associés


#fonction qui permet d'évaluer un circuit logique
def evaluate_circuit(G, labels, inputs):
    values = inputs.copy()
    order = list(nx.topological_sort(G))

    for node in order:
        if node in values:
            continue
        label = labels[node]
        preds = list(G.predecessors(node))
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

#test pour n = 8
n = 8
G, labels = generate_max_min_circuit(n)

#test exhaustif
for a in range(2**n):
    for b in range(2**n):
        inputs = {f"IN_A_{i}": (a >> i) & 1 for i in range(n)}
        inputs.update({f"IN_B_{i}": (b >> i) & 1 for i in range(n)})

        outputs = evaluate_circuit(G, labels, inputs)

        #reconstruction des valeurs
        out_a = sum(outputs[f"OUT_A_{i}"] << i for i in range(n))
        out_b = sum(outputs[f"OUT_B_{i}"] << i for i in range(n))

        assert out_a == max(a, b), f"erreur max : a={a} b={b} out_a={out_a}"
        assert out_b == min(a, b), f"erreur min : a={a} b={b} out_b={out_b}"

print("tous les tests passés pour n =", n)