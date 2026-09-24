"""
1-out-of-2 Oblivious Transfer based on ElGamal.

Alice holds two messages ``m0`` and ``m1``; Bob holds a choice bit ``b``.
At the end of the protocol Bob knows ``m_b`` and nothing about
``m_(1-b)``, while Alice learns nothing about ``b``.

Protocol:

1. **Alice** (:func:`alice_setup`) picks a group ``(p, g)`` and a random
   element ``c`` whose discrete logarithm nobody knows.
2. **Bob** (:func:`bob_choose`) draws a private key ``a`` and sets
   ``A_b = g^a`` then ``A_(1-b) = c / A_b``. He only knows the private key
   of ``A_b``: knowing that of ``A_(1-b)`` would mean computing the
   discrete logarithm of ``c``. He sends ``(A0, A1)``.
3. **Alice** (:func:`alice_send`) checks that ``A0 · A1 = c`` and then
   encrypts ``m0`` under ``A0`` and ``m1`` under ``A1`` (ElGamal).
4. **Bob** (:func:`bob_receive`) can only decrypt ``m_b``.

Security relies on the hardness of the discrete logarithm
(see :mod:`crypto3a.discrete_log`).
"""

from __future__ import annotations

from Crypto.Util.number import getPrime

from .elgamal import random_int


def _to_int(m) -> int:
    """Convert a ``bytes`` message to an integer (big-endian) if needed."""
    if isinstance(m, bytes):
        return int.from_bytes(m, byteorder="big")
    return m


# --- Step 1: Alice --------------------------------------------------------

def alice_setup(bits: int = 256):
    """Generate the public parameters ``(p, g, c)`` of the transfer."""
    p = getPrime(bits)
    g = random_int(2, p - 2)
    c = random_int(2, p - 2)
    return p, g, c


# --- Step 2: Bob ----------------------------------------------------------

def bob_choose(p: int, g: int, c: int, b: int):
    """Build Bob's two public keys according to his choice bit ``b``.

    :return: ``(a, A0, A1)`` where ``a`` is the private key (kept by Bob)
             matching ``A_b``, and ``(A0, A1)`` are the keys sent to Alice.
    """
    if b not in (0, 1):
        raise ValueError("The choice bit must be 0 or 1")
    a = random_int(1, p - 2)
    known_key = pow(g, a, p)                          # A_b = g^a
    unknown_key = (c * pow(known_key, -1, p)) % p     # A_(1-b) = c / A_b
    if b == 0:
        return a, known_key, unknown_key
    return a, unknown_key, known_key


# --- Step 3: Alice --------------------------------------------------------

def alice_send(p: int, g: int, c: int, A0: int, A1: int, m0, m1):
    """Encrypt ``m0`` under ``A0`` and ``m1`` under ``A1``.

    Messages may be integers or ``bytes``; once converted to integers they
    must be strictly smaller than ``p``.

    :raises ValueError: if ``A0 · A1 ≠ c`` (Bob would be cheating by knowing
                        both private keys) or if a message is too large.
    :return: ``((B0, c0), (B1, c1))``, the two ElGamal ciphertexts.
    """
    if (A0 * A1) % p != c % p:
        raise ValueError("Invalid keys from Bob: A0 · A1 ≠ c")

    ciphertexts = []
    for A, m in ((A0, m0), (A1, m1)):
        m = _to_int(m)
        if not 0 <= m < p:
            raise ValueError("The message must be strictly smaller than p")
        r = random_int(1, p - 2)
        ciphertexts.append((pow(g, r, p), (m * pow(A, r, p)) % p))
    return ciphertexts[0], ciphertexts[1]


# --- Step 4: Bob ----------------------------------------------------------

def bob_receive(p: int, a: int, B: int, c: int, as_bytes: bool = False, byte_length: int = 16):
    """Decrypt the chosen ciphertext ``(B, c)`` with the private key ``a``.

    :param as_bytes: if true, return the message as ``bytes`` of length
                     ``byte_length`` instead of an integer.
    """
    s = pow(B, a, p)
    m = (c * pow(s, -1, p)) % p
    if as_bytes:
        return m.to_bytes(byte_length, byteorder="big")
    return m


# --- Full protocol (local simulation) -------------------------------------

def oblivious_transfer(m0, m1, b: int, bits: int = 256, as_bytes: bool = False, byte_length: int = 16):
    """Simulate a complete oblivious transfer and return the message ``m_b`` received by Bob."""
    p, g, c = alice_setup(bits)                                    # Alice
    a, A0, A1 = bob_choose(p, g, c, b)                             # Bob -> Alice: (A0, A1)
    ciphertext0, ciphertext1 = alice_send(p, g, c, A0, A1, m0, m1)  # Alice -> Bob: ciphertexts
    B, ciphertext = ciphertext0 if b == 0 else ciphertext1          # Bob
    return bob_receive(p, a, B, ciphertext, as_bytes=as_bytes, byte_length=byte_length)


if __name__ == "__main__":
    for choice in (0, 1):
        received = oblivious_transfer(4321, 9876, choice)
        print(f"Bob chooses b = {choice} and receives: {received}")
