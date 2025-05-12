import pytest
from logDiscret import est_premier, trouve_generateurs,baby_step_giant_step
import time
import sympy

@pytest.mark.parametrize("p, h", [
    (13291, 5),
    (10007, 123),
    (7919, 4567)
])
def test_baby_step_giant_step(p, h):
    assert est_premier(p), f"{p} n'est pas premier"

    generateurs = trouve_generateurs(p)
    assert len(generateurs) > 0, f"Aucun générateur trouvé pour p = {p}"

    g = generateurs[0]  # on prend simplement le premier générateur

    x = baby_step_giant_step(g, h, p)

    assert x is not None, f"Aucune solution trouvée pour log_{g}({h}) mod {p}"
    # vérification que g^x ≡ h mod p
    assert pow(g, x, p) == h, f"Résultat incorrect: g^x = {pow(g, x, p)} ≠ {h} mod {p}"
    

def test_baby_step_giant_step_efficiency():
    bit_lengths = [16, 20, 24, 26, 28]
    max_time_seconds = 30  # temps limite par cas

    for bits in bit_lengths:
        p = int(sympy.nextprime(2**bits))
        g = trouve_generateurs(p)[0]
        x_expected = 12345
        h = pow(g, x_expected, p)

        start = time.time()
        x = baby_step_giant_step(g, h, p)
        elapsed = time.time() - start

        assert x is not None, f"Aucune solution trouvée pour bits={bits}, p={p}"
        assert pow(g, x, p) == h, f"Échec pour bits={bits}, g^x mod p ≠ h"
        assert elapsed < max_time_seconds, f"Temps trop long pour {bits} bits: {elapsed:.2f} s"
