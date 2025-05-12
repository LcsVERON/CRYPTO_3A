import pytest
from Crypto.Util.number import getPrime
from AlGamal_OT import Alice_prepare, Bob_prepare, elgamal_encrypt, elgamal_decrypt

@pytest.mark.parametrize("b", [0, 1]) # permet d’exécuter le même test plusieurs fois, avec des valeurs différentes pour une ou plusieurs variables
def test_elgamal_ot_correctness(b):
    # Alice choisit les paramètres du groupe
    p, g, C = Alice_prepare()

    # Alice choisit ses deux messages (entiers)
    m0 = 4321
    m1 = 9876

    # Bob prépare ses clés publiques
    a, A0, A1 = Bob_prepare(p, g, C, b)

    # Alice chiffre les deux messages
    c0, c1 = elgamal_encrypt(p, g, A0, A1, m0, m1)

    # Bob déchiffre le message correspondant à son choix b
    c_b = c0 if b == 0 else c1
    recu = elgamal_decrypt(p, a, c_b[0], c_b[1])

    # Vérifie que Bob reçoit bien le message qu'il voulait
    assert recu == (m0 if b == 0 else m1), "Bob n'a pas reçu le bon message"
