import pytest
import networkx as nx
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from prepa_Alice import alice_prepare_circuit
from Crypto.Util.number import long_to_bytes

def test_alice_prepare_simple_AND():
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

    inputs_b = [1]  # ou 0

    key_map, garbled_tables = alice_prepare_circuit(G, labels, inputs_b)

    # === Tests sur key_map ===
    assert ("A", 0) in key_map
    assert ("A", 1) in key_map
    assert ("AND1", 0) in key_map
    assert ("AND1", 1) in key_map

    # Bob a deux bits pour B, donc deux entrées
    assert ("B", 0) in key_map or ("B", 1) in key_map

    # === Tests sur garbled_tables ===
    assert "AND1" in garbled_tables
    table = garbled_tables["AND1"]
    assert len(table) == 4  # 2 entrées => 4 combinaisons possibles
    assert all(isinstance(x, bytes) for x in table)

def test_alice_prepare_NOT_gate():
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

    inputs_b = []  # pas d'entrée Bob ici

    key_map, garbled_tables = alice_prepare_circuit(G, labels, inputs_b)

    # Vérifie les clés
    assert ("A", 0) in key_map
    assert ("A", 1) in key_map
    assert ("NOT1", 0) in key_map
    assert ("NOT1", 1) in key_map

    # Vérifie la table NOT
    assert "NOT1" in garbled_tables
    assert len(garbled_tables["NOT1"]) == 2
    assert all(isinstance(x, bytes) for x in garbled_tables["NOT1"])
