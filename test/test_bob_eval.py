import pytest
import networkx as nx
from circuit import generate_max_min_circuit
from prepa_Alice import alice_prepare_circuit
from execution_Bob import bob_evalue_circuit

def test_bob_and_gate_evaluation():
    G, labels = generate_max_min_circuit(2)

    # Entrées pour A et B
    inputs_a = [0, 1]  # Alice
    inputs_b = [1, 1]  # Bob

    # Préparation du circuit par Alice
    keys_a, keys_b, garbled_tables = alice_prepare_circuit(G, labels, inputs_b)

    keys = {}
    compter_a = 0
    compter_b = 0

    for node in G.nodes:
        label = labels[node]
        if label == "IN_A":
            keys[node] = keys_a[(node, inputs_a[compter_a])]
            compter_a += 1
        elif label == "IN_B":
            keys[node] = keys_b[(node, inputs_b[compter_b])]
            compter_b += 1

    # Bob évalue le circuit
    output_a, output_b = bob_evalue_circuit(G, keys, garbled_tables)

    assert output_a == 3
    assert output_b == 3
