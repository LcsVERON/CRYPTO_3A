import pytest
from logDiscret import est_premier, trouve_generateurs,baby_step_giant_step

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
