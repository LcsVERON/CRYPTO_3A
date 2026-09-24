"""Tests for AES counter-mode symmetric encryption (crypto3a.aes)."""

import os

import pytest

from crypto3a.aes import BLOCK_SIZE, decrypt, encrypt, xor_bytes


@pytest.mark.parametrize("length", [0, 1, 15, 16, 17, 32, 100])
def test_encrypt_decrypt(length):
    key = os.urandom(16)
    message = os.urandom(length)
    ciphertext = encrypt(message, key)

    # 16-byte nonce + body of the same length as the message (no padding)
    assert len(ciphertext) == BLOCK_SIZE + length
    assert decrypt(ciphertext, key) == message


def test_trailing_zero_bytes_preserved():
    # Regression: trailing zero bytes of the message used to be stripped.
    key = os.urandom(16)
    message = b"MSG:" + b"\x01" * 11 + b"\x00"
    assert decrypt(encrypt(message, key), key) == message


def test_encryption_is_probabilistic():
    key = os.urandom(16)
    message = b"same message"
    assert encrypt(message, key) != encrypt(message, key)


def test_wrong_key():
    message = b"MSG:" + os.urandom(12)
    ciphertext = encrypt(message, os.urandom(16))
    assert decrypt(ciphertext, os.urandom(16)) != message


@pytest.mark.parametrize("key", [b"", b"too short", os.urandom(32)])
def test_invalid_key(key):
    with pytest.raises(ValueError):
        encrypt(b"message", key)


def test_ciphertext_too_short():
    with pytest.raises(ValueError):
        decrypt(b"short", os.urandom(16))


def test_xor_bytes():
    assert xor_bytes(b"\x0f\xf0", b"\xff\xff") == b"\xf0\x0f"
    with pytest.raises(ValueError):
        xor_bytes(b"a", b"ab")
