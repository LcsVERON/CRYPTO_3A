"""
Virtual machine and compiler for secret-sharing based secure computation (Question 7).

Principle (GMW-style protocol)
------------------------------
Each wire ``w`` of the circuit is *shared* between Alice and Bob: Alice
holds ``xA_w`` and Bob holds ``xB_w`` with ``w = xA_w ⊕ xB_w``. Neither of
them knows the value of the wire on their own.

- **Alice's input** ``a``: Alice draws a random ``r``, sends ``r ⊕ a`` to
  Bob and keeps ``r``. Symmetric for one of Bob's inputs.
- **XOR**: each party XORs its shares locally.
- **NOT**: Bob flips his share, Alice does nothing.
- **AND** ``z = x·y``: ``x·y = xA·yA ⊕ xB·yB ⊕ xA·yB ⊕ xB·yA``. The first
  two terms are computed locally; the cross terms are obtained through an
  oblivious transfer ``push(x1, x2, x3, x4)`` / ``pop(y1, y2)``: Bob draws
  ``r1, r2`` and sends ``(r1, r1 ⊕ xB, r2, r2 ⊕ yB)``; Alice selects with
  ``(yA, xA)`` and gets ``r1 ⊕ r2 ⊕ yA·xB ⊕ xA·yB``. Bob keeps ``r1 ⊕ r2``.
- **Output for Alice**: Bob sends her his share and Alice rebuilds the
  value (and conversely for one of Bob's outputs).

Machine language
----------------
Each party runs a list of instructions operating on bits:

====================================  ==============================================
Instruction                           Effect
====================================  ==============================================
``x = rnd()``                         ``x`` gets a random bit
``x = e``                             assignment, ``e`` ∈ {``y``, ``0``, ``1``,
                                      ``y + z`` (XOR), ``y * z`` (AND)}
``push(e)``                           send a bit to the other party
``x = pop()``                         receive a bit from the other party
``push(e1, e2, e3, e4)``              oblivious transfer sender
``x = pop(y1, y2)``                   receiver: ``x = (y1 ? e2 : e1) ⊕ (y2 ? e4 : e3)``
====================================  ==============================================

Each communication direction has a single-message buffer: a ``push``
blocks until the previous message has been read, a ``pop`` blocks until a
message is available.
"""

from __future__ import annotations

import re
import secrets

import networkx as nx

from .circuit import (AND, IN_A, IN_B, NOT, OUT_A, OUT_B, XOR, bits_to_int,
                      generate_max_circuit, input_node, int_to_bits, output_node)

ALICE, BOB = "A", "B"
_IDENT = r"[A-Za-z_]\w*"


def _other(side: str) -> str:
    return BOB if side == ALICE else ALICE


# ==========================================================================
# Parsing: text -> instructions
# ==========================================================================

def parse_operand(text: str):
    """Parse a variable or a constant (``0``/``1``)."""
    text = text.strip()
    if text in ("0", "1"):
        return ("const", int(text))
    if re.fullmatch(_IDENT, text):
        return ("var", text)
    raise ValueError(f"Invalid operand: {text!r}")


def parse_expr(text: str):
    """Parse an expression and return its tree as a tuple.

    Possible forms: ``("rnd",)``, ``("const", v)``, ``("var", name)``,
    ``("+", left, right)`` (XOR) and ``("*", left, right)`` (AND).
    """
    text = text.strip()
    if text == "rnd()":
        return ("rnd",)
    for op in ("+", "*"):
        if op in text:
            left, right = text.split(op, 1)
            return (op, parse_operand(left), parse_operand(right))
    return parse_operand(text)


def parse_line(line: str) -> dict:
    """Translate a line of code into an executable instruction (dictionary)."""
    line = line.strip().rstrip(";")

    m = re.fullmatch(r"push\((.*)\)", line)
    if m:
        args = [parse_expr(e) for e in m.group(1).split(",")]
        if len(args) == 1:
            return {"op": "push", "value": args[0]}
        if len(args) == 4:
            return {"op": "push4", "values": args}
        raise ValueError(f"push expects 1 or 4 arguments: {line}")

    m = re.fullmatch(rf"({_IDENT})\s*=\s*pop\(\s*\)", line)
    if m:
        return {"op": "pop", "dest": m.group(1)}

    m = re.fullmatch(rf"({_IDENT})\s*=\s*pop\(([^,]+),([^,]+)\)", line)
    if m:
        return {"op": "pop4", "dest": m.group(1),
                "y1": parse_expr(m.group(2)), "y2": parse_expr(m.group(3))}

    m = re.fullmatch(rf"({_IDENT})\s*=\s*(.+)", line)
    if m:
        return {"op": "assign", "dest": m.group(1), "expr": parse_expr(m.group(2))}

    raise ValueError(f"Unrecognised instruction: {line}")


# ==========================================================================
# Virtual machine
# ==========================================================================

class DeadlockError(RuntimeError):
    """Raised when neither party can make progress any more."""


class ProtocolError(RuntimeError):
    """Raised when a received message does not match the receiving instruction."""


class VirtualMachine:
    """Run Alice's and Bob's programs side by side.

    On each cycle, Bob then Alice each execute one instruction unless they
    are blocked on a communication.
    """

    def __init__(self, alice_code, bob_code, rng=None):
        self.code = {ALICE: list(alice_code), BOB: list(bob_code)}
        self.vars = {ALICE: {}, BOB: {}}   # private variables of each party
        self.pc = {ALICE: 0, BOB: 0}       # program counters
        # buffers[s]: message sent by s and not yet read by the other party
        self.buffers = {ALICE: None, BOB: None}
        self.rng = rng or secrets.SystemRandom()
        self.cycles = 0

    # --- Variable access ---

    def set_variable(self, side: str, name: str, value: int) -> None:
        self.vars[side][name] = value

    def get_variable(self, side: str, name: str) -> int:
        return self.vars[side][name]

    # --- Execution ---

    def finished(self, side: str | None = None) -> bool:
        """Tell whether ``side`` (or both parties if ``None``) has finished."""
        sides = (side,) if side else (ALICE, BOB)
        return all(self.pc[s] >= len(self.code[s]) for s in sides)

    def run(self) -> None:
        """Run both programs to completion.

        :raises DeadlockError: if neither party can make progress.
        """
        while not self.finished():
            self.cycles += 1
            bob_progressed = self.step(BOB)
            alice_progressed = self.step(ALICE)
            if not (bob_progressed or alice_progressed):
                raise DeadlockError(
                    f"Deadlock: Alice at instruction {self.pc[ALICE]}, "
                    f"Bob at instruction {self.pc[BOB]}")

    def step(self, side: str) -> bool:
        """Execute one instruction of ``side``; return ``False`` if blocked or finished."""
        if self.finished(side):
            return False
        if self.execute(side, self.code[side][self.pc[side]]):
            self.pc[side] += 1
            return True
        return False

    def eval_expr(self, expr, variables) -> int:
        """Evaluate an expression (see :func:`parse_expr`) in the ``variables`` context."""
        kind = expr[0]
        if kind == "rnd":
            return self.rng.randint(0, 1)
        if kind == "const":
            return expr[1]
        if kind == "var":
            try:
                return variables[expr[1]]
            except KeyError:
                raise NameError(f"Undefined variable: {expr[1]}") from None
        left, right = self.eval_expr(expr[1], variables), self.eval_expr(expr[2], variables)
        if kind == "+":
            return left ^ right
        if kind == "*":
            return left & right
        raise ValueError(f"Unknown expression: {expr}")

    def execute(self, side: str, instr: dict) -> bool:
        """Execute ``instr`` for ``side``; return ``False`` if the instruction blocks."""
        variables = self.vars[side]
        op = instr["op"]

        if op == "assign":
            variables[instr["dest"]] = self.eval_expr(instr["expr"], variables)
            return True

        if op in ("push", "push4"):
            if self.buffers[side] is not None:
                return False  # the other party has not read the previous message yet
            if op == "push":
                self.buffers[side] = ("bit", self.eval_expr(instr["value"], variables))
            else:
                self.buffers[side] = ("ot", tuple(self.eval_expr(v, variables) for v in instr["values"]))
            return True

        if op in ("pop", "pop4"):
            message = self.buffers[_other(side)]
            if message is None:
                return False  # nothing to read yet
            kind, payload = message
            expected = "bit" if op == "pop" else "ot"
            if kind != expected:
                raise ProtocolError(f"{side} expects a {expected!r} message but got {kind!r}")
            if op == "pop":
                variables[instr["dest"]] = payload
            else:
                x1, x2, x3, x4 = payload
                y1 = self.eval_expr(instr["y1"], variables)
                y2 = self.eval_expr(instr["y2"], variables)
                variables[instr["dest"]] = (x2 if y1 else x1) ^ (x4 if y2 else x3)
            self.buffers[_other(side)] = None
            return True

        raise ValueError(f"Unknown operation: {op}")


# ==========================================================================
# Compiler: circuit -> Alice's and Bob's programs
# ==========================================================================

def share(side: str, node: str) -> str:
    """Name of the variable holding ``side``'s share of wire ``node``."""
    return f"x{side}_{node}"


def compile_to_source(G, labels) -> tuple[list[str], list[str]]:
    """Translate the circuit into two text programs (Alice, Bob).

    Nodes are visited in the same topological order for both parties,
    which guarantees that messages are sent and received in the same order
    (no deadlock).
    """
    alice, bob = [], []
    counter = 0

    def tmp() -> str:
        nonlocal counter
        counter += 1
        return f"t{counter}"

    for node in nx.topological_sort(G):
        label = labels[node]
        preds = list(G.predecessors(node))
        a, b = share(ALICE, node), share(BOB, node)

        if label == IN_A:
            # Alice masks her bit with r and sends a ⊕ r; she keeps r as her share.
            r, masked = tmp(), tmp()
            alice += [f"{r} = rnd()", f"{masked} = {r} + {a}", f"push({masked})", f"{a} = {r}"]
            bob += [f"{b} = pop()"]

        elif label == IN_B:
            r, masked = tmp(), tmp()
            bob += [f"{r} = rnd()", f"{masked} = {r} + {b}", f"push({masked})", f"{b} = {r}"]
            alice += [f"{a} = pop()"]

        elif label == XOR:
            p, q = preds
            alice += [f"{a} = {share(ALICE, p)} + {share(ALICE, q)}"]
            bob += [f"{b} = {share(BOB, p)} + {share(BOB, q)}"]

        elif label == NOT:
            (p,) = preds
            alice += [f"{a} = {share(ALICE, p)}"]
            bob += [f"{b} = {share(BOB, p)} + 1"]

        elif label == AND:
            p, q = preds
            xa, ya = share(ALICE, p), share(ALICE, q)
            xb, yb = share(BOB, p), share(BOB, q)
            r1, r2, s1, s2, r, t = tmp(), tmp(), tmp(), tmp(), tmp(), tmp()
            bob += [
                f"{r1} = rnd()",
                f"{r2} = rnd()",
                f"{s1} = {r1} + {xb}",
                f"{s2} = {r2} + {yb}",
                f"push({r1}, {s1}, {r2}, {s2})",
                f"{r} = {r1} + {r2}",
                f"{b} = {xb} * {yb}",
                f"{b} = {b} + {r}",          # zB = xB·yB ⊕ r1 ⊕ r2
            ]
            alice += [
                # (yA ? r1⊕xB : r1) ⊕ (xA ? r2⊕yB : r2) = r1 ⊕ r2 ⊕ yA·xB ⊕ xA·yB
                f"{a} = pop({ya}, {xa})",
                f"{t} = {xa} * {ya}",
                f"{a} = {t} + {a}",          # zA = xA·yA ⊕ cross terms ⊕ r1 ⊕ r2
            ]

        elif label == OUT_A:
            (p,) = preds
            bob += [f"push({share(BOB, p)})"]
            alice += [f"{a} = pop()", f"{a} = {share(ALICE, p)} + {a}"]

        elif label == OUT_B:
            (p,) = preds
            alice += [f"push({share(ALICE, p)})"]
            bob += [f"{b} = pop()", f"{b} = {share(BOB, p)} + {b}"]

        else:
            raise ValueError(f"Unknown node type: {label}")

    return alice, bob


def compiler(G, labels):
    """Compile the circuit into executable instructions ``(alice_code, bob_code)``."""
    alice_src, bob_src = compile_to_source(G, labels)
    return [parse_line(line) for line in alice_src], [parse_line(line) for line in bob_src]


# ==========================================================================
# Full run
# ==========================================================================

def run_secure_max(a: int, b: int, n: int, rng=None) -> tuple[int, int]:
    """Compute ``max(a, b)`` with the virtual machine.

    :return: ``(Alice's output, Bob's output)``.
    """
    G, labels = generate_max_circuit(n)
    alice_code, bob_code = compiler(G, labels)
    vm = VirtualMachine(alice_code, bob_code, rng=rng)

    # Each party only receives its own input bits.
    for i, bit in enumerate(int_to_bits(a, n)):
        vm.set_variable(ALICE, share(ALICE, input_node(ALICE, i)), bit)
    for i, bit in enumerate(int_to_bits(b, n)):
        vm.set_variable(BOB, share(BOB, input_node(BOB, i)), bit)

    vm.run()

    out_a = bits_to_int(vm.get_variable(ALICE, share(ALICE, output_node(ALICE, i))) for i in range(n))
    out_b = bits_to_int(vm.get_variable(BOB, share(BOB, output_node(BOB, i))) for i in range(n))
    return out_a, out_b


if __name__ == "__main__":
    n = 3
    G, labels = generate_max_circuit(n)
    alice_src, bob_src = compile_to_source(G, labels)
    print(f"{n}-bit max circuit: {len(alice_src)} instructions for Alice, "
          f"{len(bob_src)} for Bob")

    for a, b in [(0, 1), (5, 3), (2, 6), (7, 7)]:
        out_a, out_b = run_secure_max(a, b, n)
        status = "OK" if out_a == out_b == max(a, b) else "ERROR"
        print(f"A = {a}, B = {b} -> Alice: {out_a}, Bob: {out_b}  [{status}]")
