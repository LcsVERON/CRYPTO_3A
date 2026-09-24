"""
Secure two-party computation with Yao's garbled circuit (Questions 8 and 9).

Alice (the *garbler*) encrypts the circuit, Bob (the *evaluator*)
evaluates it without learning the intermediate values.

Protocol (:func:`secure_max`):

1. **Alice garbles the circuit** (:func:`alice_garble_circuit`): for each
   wire ``w`` she draws two AES keys ``K(w, 0)`` and ``K(w, 1)`` (one per
   boolean value), then builds a *garbled table* for each gate: for each
   input combination ``(x, y)`` she encrypts the output key
   ``K(out, g(x, y))`` under ``K(in0, x)`` then ``K(in1, y)``. The rows of
   each table are shuffled randomly.
2. **Alice sends her input keys** (:func:`alice_input_keys`): for each of
   her bits she only sends the key matching its value; since keys are
   random, Bob learns nothing about the bit.
3. **Bob obtains his input keys through oblivious transfer**
   (:func:`bob_obtain_input_keys`): for each of his bits ``b_i`` he gets
   ``K(IN_B_i, b_i)`` without Alice learning ``b_i`` and without learning
   the other key.
4. **Bob evaluates the circuit** (:func:`bob_evaluate_circuit`): for each
   gate he tries to decrypt every row of the table with the keys he holds;
   only one row yields a valid plaintext (``MSG:`` prefix), which is the
   key of the output wire.
5. **Decoding**: the wires connected to the outputs use public keys
   ``MSG:0…00`` / ``MSG:0…01`` (:func:`output_key`), which lets Bob read
   the result. He then sends Alice her ``OUT_A`` output.

Exchanged data format:

- ``garbled_tables``: ``{node: [ciphertext, ...]}`` (4 rows for AND/XOR,
  2 for NOT), each ciphertext produced by :func:`crypto3a.aes.encrypt`;
- input keys: ``{input node: 16-byte key}``.

Recognising a valid decryption: keys start with the 32-bit prefix ``MSG:``.
A row decrypted with the wrong keys yields a pseudo-random result that
starts with this prefix only with probability 2^-32 (negligible for this
project; a real implementation would use the *point-and-permute*
technique).
"""

from __future__ import annotations

import os
import secrets

import networkx as nx

from .aes import KEY_SIZE, decrypt, encrypt
from .circuit import (AND, INPUTS, NOT, OUTPUTS, XOR, decode_output,
                      generate_max_circuit, input_node, int_to_bits)
from .oblivious_transfer import alice_send, alice_setup, bob_choose, bob_receive

#: Prefix letting Bob recognise a correctly decrypted key.
TAG = b"MSG:"

#: Boolean function computed by each two-input gate.
GATE_FUNCTIONS = {
    AND: lambda x, y: x & y,
    XOR: lambda x, y: x ^ y,
}


# --- Keys -----------------------------------------------------------------

def generate_random_key() -> bytes:
    """Generate a random 16-byte wire key: ``MSG:`` + 12 random bytes."""
    return TAG + os.urandom(KEY_SIZE - len(TAG))


def output_key(bit: int) -> bytes:
    """Public key of an output wire carrying ``bit`` (``MSG:`` + bit on 12 bytes)."""
    return TAG + bit.to_bytes(KEY_SIZE - len(TAG), "big")


def _feeds_output(G, labels, node) -> bool:
    return any(labels[s] in OUTPUTS for s in G.successors(node))


# --- 1. Alice: garbling the circuit ---------------------------------------

def alice_garble_circuit(G, labels):
    """Generate the keys of every wire and the garbled tables of the gates.

    :return: ``(key_map, garbled_tables)`` where ``key_map[(node, bit)]`` is
             the key of wire ``node`` for value ``bit``. ``key_map`` is
             **secret** and stays with Alice; ``garbled_tables`` is sent to Bob.
    """
    key_map: dict[tuple[str, int], bytes] = {}

    # Step 1: two keys per wire (output nodes copy the key of their predecessor)
    for node in G.nodes:
        if labels[node] in OUTPUTS:
            continue
        if _feeds_output(G, labels, node):
            # Public keys so that Bob can decode the result. Such a wire must
            # not feed any gate, otherwise its value would be revealed.
            if any(labels[s] not in OUTPUTS for s in G.successors(node)):
                raise ValueError(f"Node {node} feeds both an output and a gate")
            key_map[(node, 0)], key_map[(node, 1)] = output_key(0), output_key(1)
        else:
            key_map[(node, 0)], key_map[(node, 1)] = generate_random_key(), generate_random_key()

    # Step 2: one garbled table per gate
    garbled_tables: dict[str, list[bytes]] = {}
    for node in G.nodes:
        label = labels[node]
        preds = list(G.predecessors(node))

        if label in GATE_FUNCTIONS:
            table = []
            for x in (0, 1):
                for y in (0, 1):
                    k_out = key_map[(node, GATE_FUNCTIONS[label](x, y))]
                    # Double encryption: first under the key of input 1, then input 2.
                    first_layer = encrypt(k_out, key_map[(preds[0], x)])
                    table.append(encrypt(first_layer, key_map[(preds[1], y)]))
        elif label == NOT:
            table = [encrypt(key_map[(node, 1 - x)], key_map[(preds[0], x)]) for x in (0, 1)]
        else:
            continue

        # Cryptographic shuffle: the row order must not reveal anything.
        secrets.SystemRandom().shuffle(table)
        garbled_tables[node] = table

    return key_map, garbled_tables


# --- 2. Alice: sending her input keys -------------------------------------

def alice_input_keys(key_map, a: int, n: int) -> dict[str, bytes]:
    """Keys sent by Alice to Bob for her own input bits (a single key per bit)."""
    return {
        input_node("A", i): key_map[(input_node("A", i), bit)]
        for i, bit in enumerate(int_to_bits(a, n))
    }


# --- 3. Oblivious transfer of Bob's input keys ----------------------------

def bob_obtain_input_keys(key_map, b: int, n: int, bits: int = 256) -> dict[str, bytes]:
    """Simulate, for each of Bob's bits, an oblivious transfer of his input key.

    Alice provides both keys ``K(IN_B_i, 0)`` and ``K(IN_B_i, 1)``; Bob only
    gets ``K(IN_B_i, b_i)``. The group parameters are generated once and
    reused for every bit.
    """
    p, g, c = alice_setup(bits)                                        # Alice
    keys = {}
    for i, bit in enumerate(int_to_bits(b, n)):
        node = input_node("B", i)
        a_priv, A0, A1 = bob_choose(p, g, c, bit)                      # Bob
        c0, c1 = alice_send(p, g, c, A0, A1,                           # Alice
                            key_map[(node, 0)], key_map[(node, 1)])
        B, ciphertext = c0 if bit == 0 else c1                         # Bob
        keys[node] = bob_receive(p, a_priv, B, ciphertext, as_bytes=True, byte_length=KEY_SIZE)
    return keys


# --- 4. Bob: evaluating the garbled circuit -------------------------------

def _open_table(table, input_keys) -> bytes:
    """Return the single row of ``table`` that ``input_keys`` can decrypt.

    Encryption layers are removed in the reverse order of their application
    (last input first).
    """
    for row in table:
        plaintext = row
        for key in reversed(input_keys):
            plaintext = decrypt(plaintext, key)
        if plaintext.startswith(TAG):
            return plaintext
    raise ValueError("No row of the garbled table decrypts correctly")


def bob_evaluate_circuit(G, labels, input_keys, garbled_tables) -> dict[str, int]:
    """Evaluate the garbled circuit.

    :param input_keys: one key per input node (Alice's keys and those
                       obtained through oblivious transfer).
    :return: ``{output node: bit}`` dictionary.
    """
    keys = dict(input_keys)
    for node in nx.topological_sort(G):
        label = labels[node]
        preds = list(G.predecessors(node))

        if label in INPUTS:
            if node not in keys:
                raise KeyError(f"Missing key for input {node}")
        elif label in OUTPUTS:
            keys[node] = keys[preds[0]]
        else:
            try:
                keys[node] = _open_table(garbled_tables[node], [keys[p] for p in preds])
            except ValueError as err:
                raise ValueError(f"Decryption failed for the garbled table of node {node}") from err

    outputs = {}
    for node in G.nodes:
        if labels[node] in OUTPUTS:
            key = keys[node]
            if key not in (output_key(0), output_key(1)):
                raise ValueError(f"Invalid output key for {node}")
            outputs[node] = int(key == output_key(1))
    return outputs


# --- Full protocol --------------------------------------------------------

def secure_max(a: int, b: int, n: int, bits: int = 256) -> tuple[int, int]:
    """Compute ``max(a, b)`` with a garbled circuit.

    :param a: Alice's input (``0 <= a < 2^n``).
    :param b: Bob's input (``0 <= b < 2^n``).
    :param bits: size of the prime used for the oblivious transfer.
    :return: ``(Alice's output, Bob's output)``, both equal to ``max(a, b)``.
    """
    for x in (a, b):
        if not 0 <= x < 2 ** n:
            raise ValueError(f"{x} does not fit in {n} bits")

    G, labels = generate_max_circuit(n)                         # public circuit

    key_map, garbled_tables = alice_garble_circuit(G, labels)   # Alice
    input_keys = alice_input_keys(key_map, a, n)                # Alice -> Bob
    input_keys.update(bob_obtain_input_keys(key_map, b, n, bits))  # OT

    outputs = bob_evaluate_circuit(G, labels, input_keys, garbled_tables)  # Bob
    return decode_output(outputs, "A", n), decode_output(outputs, "B", n)


if __name__ == "__main__":
    n, a, b = 4, 9, 12
    out_a, out_b = secure_max(a, b, n)
    print(f"Inputs: a = {a} (Alice), b = {b} (Bob), on {n} bits")
    print(f"Alice's output: {out_a}, Bob's output: {out_b}")
