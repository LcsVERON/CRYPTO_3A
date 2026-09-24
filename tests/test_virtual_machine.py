"""Tests for the virtual machine and the compiler (crypto3a.virtual_machine, Question 7)."""

import itertools
import random

import pytest

from crypto3a.circuit import generate_max_circuit
from crypto3a.virtual_machine import (ALICE, BOB, DeadlockError, ProtocolError,
                                      VirtualMachine, compile_to_source, parse_line,
                                      run_secure_max)


def program(*lines):
    return [parse_line(line) for line in lines]


# --- Parsing ---

def test_parse_line():
    assert parse_line("x = rnd()") == {"op": "assign", "dest": "x", "expr": ("rnd",)}
    assert parse_line("x = y + 1") == {"op": "assign", "dest": "x",
                                       "expr": ("+", ("var", "y"), ("const", 1))}
    assert parse_line("x = y * z") == {"op": "assign", "dest": "x",
                                       "expr": ("*", ("var", "y"), ("var", "z"))}
    assert parse_line("push(x)") == {"op": "push", "value": ("var", "x")}
    assert parse_line("x = pop()") == {"op": "pop", "dest": "x"}
    assert parse_line("push(a, b, c, d)")["op"] == "push4"
    assert parse_line("x = pop(a, b)") == {"op": "pop4", "dest": "x",
                                           "y1": ("var", "a"), "y2": ("var", "b")}


@pytest.mark.parametrize("line", ["push(a, b)", "x == y", "x = y - z", "nothing"])
def test_parse_line_invalid(line):
    with pytest.raises(ValueError):
        parse_line(line)


# --- Virtual machine ---

def test_communication():
    vm = VirtualMachine(program("x = 1", "push(x)", "y = pop()"),
                        program("z = pop()", "z = z + 1", "push(z)"))
    vm.run()
    assert vm.get_variable(BOB, "z") == 0
    assert vm.get_variable(ALICE, "y") == 0


@pytest.mark.parametrize("y1, y2", list(itertools.product((0, 1), repeat=2)))
def test_oblivious_transfer(y1, y2):
    x = (0, 1, 1, 0)
    vm = VirtualMachine(program(f"y1 = {y1}", f"y2 = {y2}", "r = pop(y1, y2)"),
                        program("a = 0", "b = 1", "push(a, b, b, a)"))
    vm.run()
    assert vm.get_variable(ALICE, "r") == (x[1] if y1 else x[0]) ^ (x[3] if y2 else x[2])


def test_deadlock_detected():
    vm = VirtualMachine(program("x = pop()"), program("y = pop()"))
    with pytest.raises(DeadlockError):
        vm.run()


def test_mismatched_message():
    vm = VirtualMachine(program("x = 1", "push(x)"), program("y = pop(x, x)"))
    with pytest.raises(ProtocolError):
        vm.run()


def test_undefined_variable():
    vm = VirtualMachine(program("x = y + 1"), [])
    with pytest.raises(NameError):
        vm.run()


# --- Compiler and full protocol ---

@pytest.mark.parametrize("n", [1, 2, 3])
def test_run_secure_max_exhaustive(n):
    for a in range(2 ** n):
        for b in range(2 ** n):
            assert run_secure_max(a, b, n) == (max(a, b), max(a, b)), f"a={a}, b={b}"


def test_run_secure_max_8_bits():
    rng = random.Random(0)
    for _ in range(20):
        a, b = rng.randrange(256), rng.randrange(256)
        assert run_secure_max(a, b, 8) == (max(a, b), max(a, b))


def test_result_independent_of_randomness():
    # The result must not depend on the random masks that were drawn.
    for seed in range(10):
        assert run_secure_max(5, 3, 3, rng=random.Random(seed)) == (5, 5)


def test_compiled_parties_are_separate():
    # Alice only handles her xA_* shares, Bob only his xB_* shares.
    G, labels = generate_max_circuit(2)
    alice, bob = compile_to_source(G, labels)
    assert not any("xB_" in line for line in alice)
    assert not any("xA_" in line for line in bob)
