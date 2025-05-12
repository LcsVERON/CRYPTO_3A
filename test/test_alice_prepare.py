import pytest
import networkx as nx
from circuit import generate_max_min_circuit
from prepa_Alice import alice_prepare_circuit

def test_alice_prepare_output_structure():
    # Génère un petit circuit de test
    G, labels = generate_max_min_circuit(2)

    # Donne des entrées à Bob (valeurs arbitraires valides)
    inputs_b = [0, 1]

    # Exécute la préparation d’Alice
    keys_a, keys_b, garbled_tables = alice_prepare_circuit(G, labels, inputs_b)

    # === Vérifications ===

    # Vérifie que les tables brouillées sont bien créées pour chaque porte logique
    for node in G.nodes:
        label = labels[node]
        if label in {"AND", "XOR", "NOT"}:
            assert node in garbled_tables, f"Table brouillée manquante pour le nœud {node} ({label})"
            assert isinstance(garbled_tables[node], list), "La table brouillée doit être une liste"
            assert all(isinstance(entry, bytes) for entry in garbled_tables[node]), "Les entrées doivent être des bytes"

    # Vérifie que les clés d'entrée d'Alice sont bien présentes
    for node in G.nodes:
        if labels[node] == "IN_A":
            assert (node, 0) in keys_a and (node, 1) in keys_a
            assert isinstance(keys_a[(node, 0)], bytes)
            assert isinstance(keys_a[(node, 1)], bytes)

    # Vérifie que les clés d'entrée de Bob sont bien présentes
    for node in G.nodes:
        if labels[node] == "IN_B":
            assert (node, 0) in keys_b and (node, 1) in keys_b
            assert isinstance(keys_b[(node, 0)], bytes)
            assert isinstance(keys_b[(node, 1)], bytes)
