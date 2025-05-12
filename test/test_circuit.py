import pytest
from circuit import generate_max_min_circuit, evaluate_circuit, bits_to_int

@pytest.mark.parametrize("n", [8])
def test_max_min_circuit(n):
    G, labels = generate_max_min_circuit(n)

    for a in range(2**n):
        for b in range(2**n):
            inputs = {f"IN_A_{i}": (a >> i) & 1 for i in range(n)}
            inputs.update({f"IN_B_{i}": (b >> i) & 1 for i in range(n)})

            outputs = evaluate_circuit(G, labels, inputs)

            out_a = bits_to_int([outputs[f"OUT_A_{i}"] for i in range(n)])
            out_b = bits_to_int([outputs[f"OUT_B_{i}"] for i in range(n)])

            assert out_a == max(a, b), f"Erreur max: a={a}, b={b} => OUT_A={out_a}, attendu={max(a, b)}"
            assert out_b == max(a, b), f"Erreur max: a={a}, b={b} => OUT_B={out_b}, attendu={max(a, b)}"
