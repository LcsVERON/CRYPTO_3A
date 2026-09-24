# crypto_3A — Secure computation of the maximum of two integers

Alice holds an integer `a` and Bob holds an integer `b`. They want to
compute `max(a, b)` **without revealing their input to each other**. The
project implements two secure two-party computation solutions:

1. a **Yao garbled circuit**, where Bob's inputs are transmitted through
   **oblivious transfer** based on **ElGamal**;
2. a **virtual machine** running a **secret-sharing** protocol (GMW-style),
   produced by a circuit **compiler**.

Both rely on the same boolean circuit computing the maximum.

## Project history

This project started as a group assignment in the 3rd year of engineering
school. In 2026 I took it over on my own to finish it: fixing the remaining
bugs (notably the Question 7 virtual machine and the bit order of the
garbled circuit), reorganising the code into a package, extending the tests
and writing the documentation.

I used an AI assistant throughout this work, to track down bugs, rewrite
and clean up the code, write tests, comments and documentation. I reviewed
every change and checked it against the tests.

## Installation

Python 3.9 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

Run all the tests:

```bash
python -m pytest
```

Full demo (plaintext circuit, garbled circuit, virtual machine):

```bash
python -m crypto3a 200 100        # max(200, 100) on 8 bits
python -m crypto3a 5 3 4          # max(5, 3) on 4 bits
```

Each module also has its own demo:

```bash
python -m crypto3a.aes
python -m crypto3a.oblivious_transfer
python -m crypto3a.discrete_log
python -m crypto3a.garbled_circuit
python -m crypto3a.virtual_machine
```

From Python:

```python
from crypto3a.garbled_circuit import secure_max
from crypto3a.virtual_machine import run_secure_max

secure_max(9, 12, n=4)        # -> (12, 12): Alice's and Bob's outputs
run_secure_max(9, 12, n=4)    # -> (12, 12)
```

## Repository layout

```
crypto3a/                    Source code (Python package)
├── aes.py                   AES-128 symmetric encryption in counter mode
├── elgamal.py               ElGamal public-key encryption
├── oblivious_transfer.py    1-out-of-2 oblivious transfer based on ElGamal
├── discrete_log.py          Baby-step Giant-step attack (Question 3)
├── circuit.py               Boolean maximum circuit (Questions 5 and 6)
├── virtual_machine.py       Virtual machine + compiler (Question 7)
├── garbled_circuit.py       Yao garbled circuit (Questions 8 and 9)
└── __main__.py              Command-line demo
tests/                       pytest tests (one file per module)
docs/
└── ARCHITECTURE.md          Detailed architecture and protocol walkthrough
```

Module dependencies:

- `garbled_circuit` uses `aes`, `oblivious_transfer` (itself based on `elgamal`) and `circuit`;
- `virtual_machine` uses `circuit`;
- `discrete_log` is standalone (it assesses the security of the oblivious transfer).

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details on the
protocols and the format of the exchanged data.

## Answers to the questions

### Question 3 — Discrete logarithm

The Baby-step Giant-step algorithm is in `crypto3a/discrete_log.py`, the
functional and efficiency tests in `tests/test_discrete_log.py`.

The algorithm needs O(√p) operations **and** O(√p) memory. Indicative
measurements (Python 3.11, random exponent):

| Size of p | Time   | Memory |
|-----------|--------|--------|
| 32 bits   | 0.02 s | 15 MB  |
| 36 bits   | 0.16 s | 40 MB  |
| 40 bits   | 1.1 s  | 140 MB |
| 44 bits   | 5 s    | 480 MB |

Each extra bit multiplies time and memory by √2: 30 seconds and several
gigabytes of memory are exceeded around 48–50 bits. The oblivious transfer
uses a 256-bit prime `p`, i.e. about 2^128 operations for this attack: it
is out of reach.

### Question 5 — Maximum circuit

The circuit is represented as a directed acyclic graph (`networkx`) with
`n` inputs and `n` outputs for Alice and for Bob; each output gives one bit
of the maximum of the two integers. It is built by `generate_max_circuit(n)`
in `crypto3a/circuit.py`:

1. **comparison** from the most significant bit to the least significant
   one, maintaining `equal` (the bits seen so far are equal) and
   `a_greater` (`a > b` on the bits seen so far);
2. **selection** of each bit of the result:
   `(a_greater ∧ a_i) ⊕ (¬a_greater ∧ b_i)`.

The examples are in `tests/test_max.py`. On 8 bits the circuit has 37 AND,
22 XOR and 16 NOT gates.

### Question 6 — Exhaustive test

`tests/test_circuit.py` checks the circuit on every pair `(a, b)` for
`n = 1, 2, 3` and `8` bits (65,536 pairs), as well as its structure
(acyclic graph, gate arity, no useless gate).

### Question 7 — Virtual machine and compiler

`crypto3a/virtual_machine.py` contains:

- the parser of the machine language (`parse_line`);
- the virtual machine (`VirtualMachine`), which runs Alice's and Bob's
  programs side by side, communicating through single-message buffers;
- the compiler (`compile_to_source` / `compiler`), which translates the
  circuit into two programs;
- `run_secure_max(a, b, n)`, which chains everything together.

Each wire of the circuit is shared: Alice holds `xA`, Bob holds `xB`, and
value = `xA ⊕ xB`. XOR and NOT gates are computed locally; AND gates use
the oblivious transfer instruction `push(x1, x2, x3, x4)` / `pop(y1, y2)`
to compute the cross terms.

The tests (`tests/test_virtual_machine.py`) now pass, including an
exhaustive test on 1, 2 and 3 bits. The previous version failed because
of two compiler errors: inputs were not shared correctly, and AND gates
computed the wrong cross term.

### Questions 8 and 9 — Yao garbled circuit

`crypto3a/garbled_circuit.py` implements:

- **Alice** (`alice_garble_circuit`): two AES keys per wire, one shuffled
  garbled table per gate (4 rows for AND/XOR, 2 for NOT), each row being
  the output key encrypted twice;
- Alice sending only the keys matching her bits (`alice_input_keys`);
- the **oblivious transfer** of Bob's input keys (`bob_obtain_input_keys`);
- **Bob** (`bob_evaluate_circuit`): gate-by-gate evaluation; the right row
  is recognised thanks to the `MSG:` prefix of the keys, and output wires
  use public keys so that the result can be read;
- `secure_max(a, b, n)`, which runs the full protocol.

The tests are in `tests/test_garbled_circuit.py` (including an exhaustive
test on 2 bits).
