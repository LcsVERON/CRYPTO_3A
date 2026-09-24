"""Exhaustive test of the maximum circuit (Question 6)."""

import networkx as nx
import pytest

from crypto3a.circuit import (AND, NOT, OUTPUTS, XOR, bits_to_int, decode_output,
                              encode_inputs, evaluate_circuit, generate_max_circuit,
                              int_to_bits)


@pytest.mark.parametrize("n", [1, 2, 3, 8])
def test_max_circuit_exhaustive(n):
    G, labels = generate_max_circuit(n)

    for a in range(2 ** n):
        for b in range(2 ** n):
            outputs = evaluate_circuit(G, labels, encode_inputs(a, b, n))
            out_a = decode_output(outputs, "A", n)
            out_b = decode_output(outputs, "B", n)
            assert out_a == max(a, b), f"Wrong max: a={a}, b={b} => OUT_A={out_a}"
            assert out_b == max(a, b), f"Wrong max: a={a}, b={b} => OUT_B={out_b}"


@pytest.mark.parametrize("n", [1, 4, 8])
def test_circuit_structure(n):
    G, labels = generate_max_circuit(n)
    assert nx.is_directed_acyclic_graph(G)
    assert set(labels) == set(G.nodes)

    arity = {AND: 2, XOR: 2, NOT: 1}
    for node, label in labels.items():
        if label in arity:
            assert G.in_degree(node) == arity[label], node
        if label in OUTPUTS:
            assert G.in_degree(node) == 1 and G.out_degree(node) == 0
        # no useless gate: every gate feeds at least one other node
        if label in arity:
            assert G.out_degree(node) > 0, f"useless gate: {node}"


def test_bit_conversions():
    assert int_to_bits(6, 4) == [0, 1, 1, 0]  # least significant bit first
    assert bits_to_int([0, 1, 1, 0]) == 6
    assert all(bits_to_int(int_to_bits(x, 8)) == x for x in range(256))


def test_missing_input():
    G, labels = generate_max_circuit(2)
    with pytest.raises(KeyError):
        evaluate_circuit(G, labels, {"IN_A_0": 1})


def test_invalid_size():
    with pytest.raises(ValueError):
        generate_max_circuit(0)
