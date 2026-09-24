"""
ElGamal encryption over the multiplicative group (Z/pZ)*.

- Private key: random ``x``.
- Public key: ``(p, g, y = g^x mod p)``.
- Encryption of ``m``: ``(c1, c2) = (g^r, m · y^r)`` with random ``r``.
- Decryption: ``m = c2 · (c1^x)^-1``.

Randomness comes from :mod:`secrets` (a cryptographic generator) rather
than :mod:`random`, which is predictable.
"""

from __future__ import annotations

import secrets

from Crypto.Util.number import getPrime


def random_int(a: int, b: int) -> int:
    """Draw a uniform integer in ``[a, b]`` using a cryptographic generator."""
    return a + secrets.randbelow(b - a + 1)


def elgamal_keygen(bits: int = 256):
    """Generate an ElGamal key pair.

    :param bits: bit size of the prime ``p``.
    :return: ``((p, g, y), x)`` — public key, then private key.
    """
    p = getPrime(bits)
    g = random_int(2, p - 2)
    x = random_int(1, p - 2)
    y = pow(g, x, p)
    return (p, g, y), x


def elgamal_encrypt(p: int, g: int, y: int, m: int):
    """Encrypt the integer ``m`` (``0 < m < p``) with the public key ``(p, g, y)``.

    :return: the pair ``(c1, c2)``.
    """
    if not 0 < m < p:
        raise ValueError("The message must satisfy 0 < m < p")
    r = random_int(1, p - 2)
    c1 = pow(g, r, p)       # c1 = g^r
    s = pow(y, r, p)        # shared secret s = y^r = g^(xr)
    c2 = (m * s) % p        # c2 = m · s
    return c1, c2


def elgamal_decrypt(p: int, x: int, c1: int, c2: int) -> int:
    """Decrypt ``(c1, c2)`` with the private key ``x`` and return ``m``."""
    s = pow(c1, x, p)           # s = c1^x = g^(xr)
    s_inv = pow(s, -1, p)       # modular inverse of s
    return (c2 * s_inv) % p     # m = c2 / s


if __name__ == "__main__":
    (p, g, y), x = elgamal_keygen()
    message = 123456789
    c1, c2 = elgamal_encrypt(p, g, y, message)
    print("Message    :", message)
    print("Ciphertext :", (c1, c2))
    print("Decrypted  :", elgamal_decrypt(p, x, c1, c2))
