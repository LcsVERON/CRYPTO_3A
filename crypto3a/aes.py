"""
Symmetric encryption built on AES-128 (counter mode).

The scheme is the one given in the assignment:

    E(m_1 ... m_l, k) = [r, AES_k(r + 1) ⊕ m_1, ..., AES_k(r + l) ⊕ m_l]
    D(r · c_1 ... c_l, k) = c_1 ⊕ AES_k(r + 1) ... c_l ⊕ AES_k(r + l)

where ``r`` is a random 128-bit nonce and ``m_i`` are 128-bit blocks.
This is a stream cipher: the last block may be shorter, in which case the
keystream is simply truncated to the right length. No padding is needed,
so decryption returns exactly the original message, trailing zero bytes
included.

This module is the building block of the garbled circuit
(:mod:`crypto3a.garbled_circuit`).
"""

from __future__ import annotations

import os

from Crypto.Cipher import AES

#: Size of an AES block and of an AES-128 key, in bytes.
BLOCK_SIZE = 16
KEY_SIZE = 16


def xor_bytes(a: bytes, b: bytes) -> bytes:
    """Return the byte-wise XOR of two strings of equal length."""
    if len(a) != len(b):
        raise ValueError("Both byte strings must have the same length")
    return bytes(x ^ y for x, y in zip(a, b))


def aes_encrypt_block(key: bytes, block: bytes) -> bytes:
    """Encrypt a single 128-bit block with AES-128 (raw primitive, ECB mode)."""
    return AES.new(key, AES.MODE_ECB).encrypt(block)


def _counter_block(r: bytes, i: int) -> bytes:
    """Compute the block ``r + i`` (addition modulo 2^128)."""
    value = (int.from_bytes(r, "big") + i) % (1 << (8 * BLOCK_SIZE))
    return value.to_bytes(BLOCK_SIZE, "big")


def _keystream_xor(key: bytes, r: bytes, data: bytes) -> bytes:
    """XOR ``data`` with the keystream AES_k(r + 1) || AES_k(r + 2) || ...

    Encryption and decryption are the same operation.
    """
    cipher = AES.new(key, AES.MODE_ECB)
    output = bytearray()
    for index, start in enumerate(range(0, len(data), BLOCK_SIZE), start=1):
        block = data[start:start + BLOCK_SIZE]
        keystream = cipher.encrypt(_counter_block(r, index))
        # The last block may be shorter: truncate the keystream.
        output += xor_bytes(block, keystream[:len(block)])
    return bytes(output)


def _check_key(key: bytes) -> None:
    if len(key) != KEY_SIZE:
        raise ValueError("The key must be 16 bytes long (AES-128)")


def encrypt(m: bytes, key: bytes) -> bytes:
    """Encrypt the message ``m`` with ``key``.

    :param m: message to encrypt (any length).
    :param key: 16-byte AES-128 key.
    :return: ``r || c`` where ``r`` is the nonce (16 bytes) and ``len(c) == len(m)``.
    """
    _check_key(key)
    r = os.urandom(BLOCK_SIZE)  # random 128-bit nonce
    return r + _keystream_xor(key, r, m)


def decrypt(ciphertext: bytes, key: bytes) -> bytes:
    """Decrypt a ciphertext produced by :func:`encrypt`.

    Note: this scheme is not authenticated. Decrypting with the wrong key
    does not raise an error but yields pseudo-random bytes; it is up to the
    caller to recognise a valid plaintext (see the ``MSG:`` prefix used by
    the garbled circuit).

    :raises ValueError: if the key is invalid or the ciphertext too short.
    """
    _check_key(key)
    if len(ciphertext) < BLOCK_SIZE:
        raise ValueError("Ciphertext is too short")
    r, body = ciphertext[:BLOCK_SIZE], ciphertext[BLOCK_SIZE:]
    return _keystream_xor(key, r, body)


if __name__ == "__main__":
    key = os.urandom(KEY_SIZE)
    message = b"Hello, this is a test message!"
    print("Plaintext  :", message.decode())

    ciphertext = encrypt(message, key)
    print("Ciphertext :", ciphertext.hex())

    plaintext = decrypt(ciphertext, key)
    print("Decrypted  :", plaintext.decode())
