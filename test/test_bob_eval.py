import pytest
import networkx as nx
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from prepa_Alice import alice_prepare_circuit
from execution_Bob import bob_evalue_circuit

def test_bob_evalue_simple_AND():
    # === Étape 1 : Construction du circuit A AND B => OUT
    G = nx.DiGraph()
    G.add_edges_from([
        ("A", "AND1"),
        ("B", "AND1"),
        ("AND1", "OUT_A")
    ])

    # Ajout des labels comme attributs des nœuds pour qu'ils soient disponibles dans bob_eval
    labels = {
        "A": "IN_A",
        "B": "IN_B",
        "AND1": "AND",
        "OUT_A": "OUT_A",
    }

    for node, label in labels.items():
        G.nodes[node]["label"] = label

    # === Étape 2 : Choix de l'entrée de Bob
    inputs_b = [1]  # Bob fournit 1 en entrée

    # === Étape 3 : Appel à la fonction de préparation d’Alice
    key_map, garbled_tables = alice_prepare_circuit(G, labels, inputs_b)

    # === Étape 4 : Évaluation par Bob
    outputs = bob_evalue_circuit(G, key_map, garbled_tables)

    # === Étape 5 : Résultat attendu selon les entrées (A inconnue pour l'instant, testons 0 et 1)
    # On suppose que Alice a mis A = 1 (clé (A,1) présente dans key_map)

    # Pour forcer une clé d'entrée pour A (Alice) à 1 :
    for val in [0, 1]:
        if (("A", val) in key_map):
            input_a_val = val
            break

    expected_output = inputs_b[0] & input_a_val
    assert outputs["OUT_A"] == expected_output, f"Expected OUT_A = {expected_output}, got {outputs['OUT_A']}"

def test_bob_evalue_simple_AND_zero():
    # Même circuit mais avec Bob = 0
    G = nx.DiGraph()
    G.add_edges_from([
        ("A", "AND1"),
        ("B", "AND1"),
        ("AND1", "OUT_A")
    ])

    labels = {
        "A": "IN_A",
        "B": "IN_B",
        "AND1": "AND",
        "OUT_A": "OUT_A",
    }

    for node, label in labels.items():
        G.nodes[node]["label"] = label

    inputs_b = [0]  # Bob fournit 0

    key_map, garbled_tables = alice_prepare_circuit(G, labels, inputs_b)

    outputs = bob_evalue_circuit(G, key_map, garbled_tables)

    for val in [0, 1]:
        if (("A", val) in key_map):
            input_a_val = val
            break

    expected_output = inputs_b[0] & input_a_val
    assert outputs["OUT_A"] == expected_output, f"Expected OUT_A = {expected_output}, got {outputs['OUT_A']}"
