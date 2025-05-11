import pytest
import networkx as nx
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from prepa_Alice import alice_prepare_circuit
from execution_Bob import bob_evalue_circuit
from Crypto.Util.number import long_to_bytes

def test_bob_evaluation_simple_AND():
    # === Construire un petit circuit logique : A AND B => OUT_A
    G = nx.DiGraph()
    G.add_edges_from([
        ("A", "AND1"),
        ("B", "AND1"),
        ("AND1", "OUT_A"),
    ])

    labels = {
        "A": "IN_A",
        "B": "IN_B",
        "AND1": "AND",
        "OUT_A": "OUT_A",
    }

    # Entrée de Bob pour B
    inputs_b = [1]  # Bob choisit B = 1

    key_map, garbled_tables = alice_prepare_circuit(G, labels, inputs_b)

    # Bob évalue le circuit
    result = bob_evalue_circuit(G, key_map, garbled_tables)

    # Ajout de débogage pour vérifier si OUT_A est présent dans les résultats
    print("Résultats de Bob:", result)
    assert "OUT_A" in result, "La sortie 'OUT_A' est manquante dans le résultat de l'évaluation."

    # Vérification du résultat attendu pour A=0 et B=1 (AND => 0)
    assert result["OUT_A"] == 0, "Le résultat attendu pour OUT_A est 0."

    # Le résultat attendu pour A=0 et B=1 (AND => 0)
    assert result["OUT_A"] == 0  # Résultat attendu

def test_bob_evaluation_NOT_gate():
    # === Circuit : A → NOT → OUT_A
    G = nx.DiGraph()
    G.add_edges_from([
        ("A", "NOT1"),
        ("NOT1", "OUT_A"),
    ])

    labels = {
        "A": "IN_A",
        "NOT1": "NOT",
        "OUT_A": "OUT_A",
    }

    # Entrée de Bob pour A
    inputs_b = [1]  # Bob choisit A = 1

    key_map, garbled_tables = alice_prepare_circuit(G, labels, inputs_b)

    # Bob évalue le circuit
    result = bob_evalue_circuit(G, key_map, garbled_tables)

    # Ajout de débogage pour vérifier si OUT_A est présent dans les résultats
    print("Résultats de Bob:", result)
    assert "OUT_A" in result, "La sortie 'OUT_A' est manquante dans le résultat de l'évaluation."

    # Vérification du résultat attendu pour A=0 et B=1 (AND => 0)
    assert result["OUT_A"] == 0, "Le résultat attendu pour OUT_A est 0."

    # Le résultat attendu pour A=1 (NOT => 0)
    assert result["OUT_A"] == 0  # Résultat attendu
