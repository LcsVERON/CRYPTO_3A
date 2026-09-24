"""Examples of computing the maximum with the plaintext circuit (Question 5)."""

import pytest

from crypto3a.circuit import (decode_output, encode_inputs, evaluate_circuit,
                              generate_max_circuit)


@pytest.mark.parametrize("a, b, expected", [
    (57, 132, 132),   # A < B
    (200, 100, 200),  # A > B
    (123, 123, 123),  # A == B
    (0, 255, 255),    # 8-bit min and max
    (255, 0, 255),
])
def test_max_circuit(a, b, expected):
    n = 8
    G, labels = generate_max_circuit(n)
    outputs = evaluate_circuit(G, labels, encode_inputs(a, b, n))

    assert decode_output(outputs, "A", n) == expected, f"max({a}, {b}) should be {expected}"
    assert decode_output(outputs, "B", n) == expected
