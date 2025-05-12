import pytest
from AlGamal import elgamal_keygen, elgamal_encrypt, elgamal_decrypt

@pytest.mark.parametrize("message", [42, 123456, 987654321])
def test_elgamal_encryption_decryption(message):
    public_key, private_key = elgamal_keygen()
    p, g, y = public_key
    x = private_key

    # Vérifie que le message est dans le bon domaine
    assert message < p, f"Le message doit être < p (p = {p}, message = {message})"

    # Chiffrement
    c1, c2 = elgamal_encrypt(p, g, y, message)

    # Déchiffrement
    decrypted = elgamal_decrypt(p, x, c1, c2)

    assert decrypted == message, f"Erreur de déchiffrement : attendu {message}, obtenu {decrypted}"
