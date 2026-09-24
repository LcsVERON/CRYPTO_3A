"""
Discrete logarithm with the *Baby-step Giant-step* algorithm (Question 3).

Given a prime ``p``, a generator ``g`` of (Z/pZ)* and an element ``h``, we
look for ``x`` such that ``g^x ≡ h (mod p)``.

Shanks' algorithm runs in O(√p) time and memory: this is the bound used to
assess the security of the oblivious transfer
(:mod:`crypto3a.oblivious_transfer`), which relies on the hardness of this
problem.

The module also provides the arithmetic tools needed by the tests
(primality, generator search). They are deliberately simple (trial
division) and suited to primes of a few dozen bits only.
"""

from __future__ import annotations

import math


def is_prime(n: int) -> bool:
    """Primality test by trial division up to √n."""
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    return all(n % d != 0 for d in range(3, math.isqrt(n) + 1, 2))


def next_prime(n: int) -> int:
    """Return the smallest prime strictly greater than ``n``."""
    candidate = n + 1
    while not is_prime(candidate):
        candidate += 1
    return candidate


def prime_factors(n: int) -> list[int]:
    """Return the sorted list of the distinct prime factors of ``n``."""
    factors = []
    d = 2
    while d * d <= n:
        if n % d == 0:
            factors.append(d)
            while n % d == 0:
                n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors


def is_generator(g: int, p: int, factors: list[int] | None = None) -> bool:
    """Tell whether ``g`` generates the multiplicative group (Z/pZ)*.

    ``g`` is a generator if and only if ``g^((p-1)/q) ≠ 1`` for every prime
    factor ``q`` of ``p - 1``.

    :param factors: prime factors of ``p - 1`` if already known
                    (avoids factoring again on every call).
    """
    if not 1 <= g < p:
        return False
    order = p - 1
    if factors is None:
        factors = prime_factors(order)
    return all(pow(g, order // q, p) != 1 for q in factors)


def find_generator(p: int) -> int:
    """Return the smallest generator of (Z/pZ)*."""
    factors = prime_factors(p - 1)
    for g in range(1, p):
        if is_generator(g, p, factors):
            return g
    raise ValueError(f"No generator found: is {p} prime?")


def find_generators(p: int) -> list[int]:
    """Return every generator of (Z/pZ)* (O(p) cost, for small p only)."""
    factors = prime_factors(p - 1)
    return [g for g in range(1, p) if is_generator(g, p, factors)]


def baby_step_giant_step(g: int, h: int, p: int) -> int | None:
    """Solve ``g^x ≡ h (mod p)`` with the Baby-step Giant-step algorithm.

    Write ``x = k·t + i`` with ``t = ⌈√p⌉`` and ``0 ≤ i, k < t``:

    - *baby steps*: store ``g^i`` for every ``i < t``;
    - *giant steps*: compute ``h · g^(-k·t)`` for ``k = 0, 1, ...`` until
      it matches a stored value ``g^i``, hence ``x = k·t + i``.

    :return: the smallest ``x`` found, or ``None`` if there is none.
    """
    h %= p
    t = math.isqrt(p) + 1
    baby_steps = {}
    value = 1
    for i in range(t):
        # setdefault keeps the smallest exponent i for a given value.
        baby_steps.setdefault(value, i)
        value = (value * g) % p

    g_minus_t = pow(g, -t, p)   # g^(-t) mod p
    giant_step = h              # h · g^(-k·t) for k = 0
    for k in range(t):
        if giant_step in baby_steps:
            return k * t + baby_steps[giant_step]
        giant_step = (giant_step * g_minus_t) % p
    return None


if __name__ == "__main__":
    p = next_prime(2 ** 30)
    g = find_generator(p)
    h = pow(g, 123456789, p)
    x = baby_step_giant_step(g, h, p)
    print(f"p = {p}, g = {g}, h = {h}")
    print(f"log_g(h) = {x}  (check: g^x mod p = {pow(g, x, p)})")
