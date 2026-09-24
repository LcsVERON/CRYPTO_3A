"""Tests for the Baby-step Giant-step discrete logarithm (crypto3a.discrete_log, Question 3)."""

import random
import time

import pytest

from crypto3a.discrete_log import (baby_step_giant_step, find_generator, find_generators,
                                   is_generator, is_prime, next_prime, prime_factors)


def test_is_prime():
    primes = [2, 3, 5, 7, 11, 13, 7919, 10007, 13291]
    non_primes = [-7, 0, 1, 4, 9, 15, 7917, 10005]
    assert all(is_prime(n) for n in primes)
    assert not any(is_prime(n) for n in non_primes)


def test_prime_factors():
    assert prime_factors(360) == [2, 3, 5]
    assert prime_factors(13290) == [2, 3, 5, 443]
    assert prime_factors(97) == [97]


def test_generators():
    # The generators of (Z/7Z)* are 3 and 5.
    assert find_generators(7) == [3, 5]
    assert find_generator(7) == 3
    assert is_generator(3, 7) and not is_generator(2, 7)


@pytest.mark.parametrize("p, h", [
    (13291, 5),
    (10007, 123),
    (7919, 4567),
])
def test_baby_step_giant_step(p, h):
    assert is_prime(p), f"{p} is not prime"
    g = find_generator(p)

    x = baby_step_giant_step(g, h, p)

    assert x is not None, f"No solution found for log_{g}({h}) mod {p}"
    assert pow(g, x, p) == h, f"Wrong result: g^x = {pow(g, x, p)} ≠ {h} mod {p}"


def test_baby_step_giant_step_no_solution():
    # 2 generates a subgroup of order 3 in (Z/7Z)* = {1, 2, 4}: 3 is not in it.
    assert baby_step_giant_step(2, 3, 7) is None


@pytest.mark.parametrize("bits", [16, 20, 24, 28, 32])
def test_baby_step_giant_step_efficiency(bits):
    max_time_seconds = 30  # time limit per case
    p = next_prime(2 ** bits)
    g = find_generator(p)
    expected_x = random.randrange(1, p - 1)
    h = pow(g, expected_x, p)

    start = time.perf_counter()
    x = baby_step_giant_step(g, h, p)
    elapsed = time.perf_counter() - start

    assert x == expected_x, f"Failure for bits={bits}"
    assert elapsed < max_time_seconds, f"Too slow for {bits} bits: {elapsed:.2f} s"
