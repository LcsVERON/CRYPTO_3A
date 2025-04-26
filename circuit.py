import networkx as nx

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
