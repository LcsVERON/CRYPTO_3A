"""Tests for the ElGamal-based oblivious transfer (crypto3a.oblivious_transfer)."""

import os

import pytest

from crypto3a.oblivious_transfer import (alice_send, alice_setup, bob_choose, bob_receive,
                                         oblivious_transfer)


@pytest.mark.parametrize("b", [0, 1])
def test_elgamal_ot_correctness(b):
    m0, m1 = 4321, 9876

    p, g, c = alice_setup()                            # Alice
    a, A0, A1 = bob_choose(p, g, c, b)                 # Bob
    c0, c1 = alice_send(p, g, c, A0, A1, m0, m1)       # Alice
    B, ciphertext = c0 if b == 0 else c1               # Bob
    received = bob_receive(p, a, B, ciphertext)

    assert received == (m0 if b == 0 else m1), "Bob did not receive the right message"


@pytest.mark.parametrize("b", [0, 1])
def test_ot_bytes_messages(b):
    m0, m1 = os.urandom(16), os.urandom(16)
    assert oblivious_transfer(m0, m1, b, as_bytes=True) == (m0, m1)[b]


@pytest.mark.parametrize("b", [0, 1])
def test_bob_cannot_decrypt_the_other_message(b):
    m0, m1 = 4321, 9876
    p, g, c = alice_setup()
    a, A0, A1 = bob_choose(p, g, c, b)
    c0, c1 = alice_send(p, g, c, A0, A1, m0, m1)
    B, ciphertext = c1 if b == 0 else c0  # the message that was not chosen
    assert bob_receive(p, a, B, ciphertext) != (m1 if b == 0 else m0)


def test_alice_rejects_cheating_keys():
    # Bob tries to know both private keys: A0 · A1 ≠ c
    p, g, c = alice_setup(64)
    A0, A1 = pow(g, 3, p), pow(g, 5, p)
    with pytest.raises(ValueError):
        alice_send(p, g, c, A0, A1, 1, 2)


def test_invalid_choice_bit():
    p, g, c = alice_setup(64)
    with pytest.raises(ValueError):
        bob_choose(p, g, c, 2)
