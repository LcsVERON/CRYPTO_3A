# Architecture

This document describes the role of each module in `crypto3a/`, the
shared conventions and how the two secure computation protocols work.

## Shared conventions

- **Bits**: an integer `x` on `n` bits is split least significant bit
  first (`int_to_bits(6, 4) == [0, 1, 1, 0]`). The index `i` of a node
  (`IN_A_i`, `OUT_B_i`…) always denotes the bit of weight `2^i`.
- **Circuit**: a pair `(G, labels)` where `G` is an acyclic
  `networkx.DiGraph` and `labels[node]` is the node type (`IN_A`, `IN_B`,
  `AND`, `XOR`, `NOT`, `OUT_A`, `OUT_B`). The predecessors of a gate are
  in edge insertion order, which is the same for Alice and Bob since they
  share `G`.
- **Randomness**: every draw with a cryptographic role uses `secrets` /
  `os.urandom`, never `random`.

## Modules

| Module | Role | Main functions |
|---|---|---|
| `aes.py` | AES-128 encryption in counter mode: `E(m, k) = r ‖ AES_k(r+1) ⊕ m_1 ‖ …` | `encrypt`, `decrypt` |
| `elgamal.py` | ElGamal encryption | `elgamal_keygen`, `elgamal_encrypt`, `elgamal_decrypt` |
| `oblivious_transfer.py` | 1-out-of-2 oblivious transfer | `alice_setup`, `bob_choose`, `alice_send`, `bob_receive`, `oblivious_transfer` |
| `discrete_log.py` | Discrete logarithm (Baby-step Giant-step), primality, generators | `baby_step_giant_step`, `find_generator`, `is_prime` |
| `circuit.py` | Construction and plaintext evaluation of the maximum circuit | `generate_max_circuit`, `evaluate_circuit`, `encode_inputs`, `decode_output` |
| `garbled_circuit.py` | Yao's protocol | `alice_garble_circuit`, `alice_input_keys`, `bob_obtain_input_keys`, `bob_evaluate_circuit`, `secure_max` |
| `virtual_machine.py` | Virtual machine, language and compiler (secret sharing) | `VirtualMachine`, `parse_line`, `compile_to_source`, `compiler`, `run_secure_max` |

## Maximum circuit

For each bit `i`, from most to least significant:

```
gt_i        = a_i ∧ ¬b_i
a_greater   = a_greater ⊕ (equal ∧ gt_i)       (XOR = OR since the terms are exclusive)
equal       = equal ∧ ¬(a_i ⊕ b_i)             (useless on the last bit, not computed)
```

then for each bit: `max_i = (a_greater ∧ a_i) ⊕ (¬a_greater ∧ b_i)`,
connected to `OUT_A_i` and to `OUT_B_i`.

## Protocol 1: Yao garbled circuit

```
        Alice (a)                                        Bob (b)
        ─────────                                        ───────
 1. keys K(w,0), K(w,1) for every wire
    shuffled garbled tables
                     ── garbled tables ─────────────────▶
 2.                  ── K(IN_A_i, a_i) for every i ─────▶
 3. oblivious transfer for each bit b_i:
                     ◀─ (A0, A1) ───────────────────────   (Bob knows the private key of A_(b_i))
                     ── Enc_A0(K(IN_B_i,0)), Enc_A1(K(IN_B_i,1)) ─▶
                                                         Bob decrypts K(IN_B_i, b_i)
 4.                                                      gate-by-gate evaluation
 5.                                                      reads the public output keys
                     ◀─ OUT_A output ───────────────────
```

**Garbled table** of a gate `g` with inputs `u`, `v` and output `w`: for
each `(x, y)`, the row `E(E(K(w, g(x, y)), K(u, x)), K(v, y))`. Bob removes
the layers in reverse order (key of `v`, then key of `u`); only the right
row yields a plaintext starting with `MSG:`.

**Keys**: 16 bytes = `MSG:` + 12 random bytes. Wires connected to the
outputs use the public keys `MSG:` + `0…00` and `MSG:` + `0…01`, which lets
Bob read the result. Alice checks that such a wire does not feed any other
gate, otherwise an intermediate value would be revealed.

**Known limitations** (acceptable for this project):

- recognising the right row by its prefix has an error probability of
  2^-32 per row; a real implementation would use the *point-and-permute*
  technique;
- the security model is "honest but curious": nothing prevents Alice from
  garbling a different circuit.

## Protocol 2: secret-sharing virtual machine

Each wire `w` is shared: Alice holds `xA_w`, Bob holds `xB_w`, with
`w = xA_w ⊕ xB_w`. The compiler walks the circuit in topological order and
emits, for each node, instructions for each party:

| Node | Alice | Bob |
|---|---|---|
| `IN_A` | `r = rnd()`, `push(r + a)`, `xA = r` | `xB = pop()` |
| `IN_B` | `xA = pop()` | `r = rnd()`, `push(r + b)`, `xB = r` |
| `XOR`  | `xA = xA_u + xA_v` | `xB = xB_u + xB_v` |
| `NOT`  | `xA = xA_u` | `xB = xB_u + 1` |
| `AND`  | `c = pop(xA_v, xA_u)`, `xA = xA_u * xA_v + c` | `r1, r2 = rnd()`, `push(r1, r1 + xB_u, r2, r2 + xB_v)`, `xB = xB_u * xB_v + r1 + r2` |
| `OUT_A`| `c = pop()`, `xA = xA_u + c` | `push(xB_u)` |
| `OUT_B`| `push(xA_u)` | `c = pop()`, `xB = xB_u + c` |

(simplified: the generated programs use temporary variables `t1`, `t2`…
and a single operation per instruction.)

For the AND gate, `pop(y1, y2)` returns `(y1 ? x2 : x1) ⊕ (y2 ? x4 : x3)`,
i.e. here `r1 ⊕ r2 ⊕ xA_v·xB_u ⊕ xA_u·xB_v`: the two cross terms of the
product `(xA_u ⊕ xB_u)·(xA_v ⊕ xB_v)`. Adding the local terms `xA_u·xA_v`
and `xB_u·xB_v` gives a valid sharing of `u ∧ v`.

**Scheduling**: on each cycle Bob then Alice execute one instruction,
unless they are blocked (`push` on a full buffer, `pop` on an empty
buffer). Since both programs follow the same topological order, messages
are consumed in the order they are produced. If neither party makes
progress during a cycle, the machine raises `DeadlockError`.
