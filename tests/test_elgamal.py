"""Tests for ElGamal encryption (crypto3a.elgamal)."""

import pytest

from crypto3a.elgamal import elgamal_decrypt, elgamal_encrypt, elgamal_keygen


@pytest.mark.parametrize("message", [1, 42, 123456, 987654321])
def test_elgamal_encryption_decryption(message):
    (p, g, y), x = elgamal_keygen()
    c1, c2 = elgamal_encrypt(p, g, y, message)
    assert elgamal_decrypt(p, x, c1, c2) == message


def test_elgamal_message_out_of_range():
    (p, g, y), _ = elgamal_keygen(64)
    for message in (0, p, p + 1):
        with pytest.raises(ValueError):
            elgamal_encrypt(p, g, y, message)
