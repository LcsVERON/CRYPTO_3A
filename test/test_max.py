import pytest
from circuit import generate_max_min_circuit, evaluate_circuit, bits_to_int, int_to_bits

@pytest.mark.parametrize("a, b, expected", [
    (57, 132, 132),   # A < B
    (200, 100, 200),  # A > B
    (123, 123, 123),  # A == B
    (0, 255, 255),    # min et max sur 8 bits
    (255, 0, 255),
])
def test_max_min_circuit(a, b, expected):
    n = 8
    G, labels = generate_max_min_circuit(n)

    # Convertit a et b en bits (LSB en premier)
    in_a_bits = int_to_bits(a, n)
    in_b_bits = int_to_bits(b, n)

    # Prépare les entrées du circuit
    inputs = {f"IN_A_{i}": bit for i, bit in enumerate(in_a_bits)}
    inputs.update({f"IN_B_{i}": bit for i, bit in enumerate(in_b_bits)})

    # Évalue le circuit
    outputs = evaluate_circuit(G, labels, inputs)

    # Récupère les bits de sortie OUT_A (max)
    out_bits = [outputs[f"OUT_A_{i}"] for i in range(n)]
    result = bits_to_int(out_bits)

    assert result == expected, f"max({a}, {b}) devrait être {expected}, mais retourne {result}"
