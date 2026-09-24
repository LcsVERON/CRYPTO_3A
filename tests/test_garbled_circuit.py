"""Tests for Yao's garbled circuit (crypto3a.garbled_circuit, Questions 8 and 9)."""

import itertools

import pytest

from crypto3a.circuit import generate_max_circuit, input_node
from crypto3a.garbled_circuit import (TAG, alice_garble_circuit, alice_input_keys,
                                      bob_evaluate_circuit, bob_obtain_input_keys,
                                      secure_max)

# Smaller primes to speed up the oblivious transfer in tests
# (keys are 128 bits long, so the prime must exceed 2^128).
OT_BITS = 160


def test_alice_garble_output_structure():
    G, labels = generate_max_circuit(2)
    key_map, garbled_tables = alice_garble_circuit(G, labels)

    for node, label in labels.items():
        if label in {"AND", "XOR", "NOT"}:
            table = garbled_tables[node]
            assert len(table) == (2 if label == "NOT" else 4)
            assert all(isinstance(entry, bytes) for entry in table)
        if label in {"IN_A", "IN_B"}:
            k0, k1 = key_map[(node, 0)], key_map[(node, 1)]
            assert k0 != k1 and len(k0) == len(k1) == 16
            assert k0.startswith(TAG) and k1.startswith(TAG)


def test_alice_sends_a_single_key_per_bit():
    n = 3
    G, labels = generate_max_circuit(n)
    key_map, _ = alice_garble_circuit(G, labels)
    keys = alice_input_keys(key_map, 0b101, n)
    assert keys == {
        input_node("A", 0): key_map[(input_node("A", 0), 1)],
        input_node("A", 1): key_map[(input_node("A", 1), 0)],
        input_node("A", 2): key_map[(input_node("A", 2), 1)],
    }


def test_bob_gets_his_keys_through_ot():
    n = 2
    G, labels = generate_max_circuit(n)
    key_map, _ = alice_garble_circuit(G, labels)
    keys = bob_obtain_input_keys(key_map, 0b10, n, bits=OT_BITS)
    assert keys[input_node("B", 0)] == key_map[(input_node("B", 0), 0)]
    assert keys[input_node("B", 1)] == key_map[(input_node("B", 1), 1)]


@pytest.mark.parametrize("a, b", list(itertools.product(range(4), repeat=2)))
def test_secure_max_exhaustive_2_bits(a, b):
    assert secure_max(a, b, 2, bits=OT_BITS) == (max(a, b), max(a, b))


@pytest.mark.parametrize("a, b", [(0, 0), (9, 12), (12, 9), (15, 15), (0, 15), (8, 7)])
def test_secure_max_4_bits(a, b):
    assert secure_max(a, b, 4, bits=OT_BITS) == (max(a, b), max(a, b))


def test_secure_max_bit_order():
    # Regression: most and least significant bits used to be swapped (max(2, 1) returned 1).
    assert secure_max(2, 1, 2, bits=OT_BITS) == (2, 2)


def test_wrong_keys_detected():
    G, labels = generate_max_circuit(1)
    key_map, tables = alice_garble_circuit(G, labels)
    keys = {input_node("A", 0): b"MSG:" + bytes(12), input_node("B", 0): b"MSG:" + bytes(12)}
    with pytest.raises(ValueError):
        bob_evaluate_circuit(G, labels, keys, tables)


def test_input_out_of_range():
    with pytest.raises(ValueError):
        secure_max(4, 1, 2)
