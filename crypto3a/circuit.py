"""
Boolean circuit computing the maximum of two ``n``-bit integers (Questions 5 and 6).

Representation
--------------
A circuit is a directed acyclic graph ``networkx.DiGraph`` together with a
``labels`` dictionary mapping each node to its type:

=========  ====================================================
Type       Meaning
=========  ====================================================
``IN_A``   Alice's input bit (``IN_A_i`` = i-th bit of ``a``)
``IN_B``   Bob's input bit (``IN_B_i`` = i-th bit of ``b``)
``AND``    two-input AND gate
``XOR``    two-input XOR gate
``NOT``    one-input NOT gate
``OUT_A``  output bit revealed to Alice (``OUT_A_i``)
``OUT_B``  output bit revealed to Bob (``OUT_B_i``)
=========  ====================================================

Edges go from the inputs of a gate to the gate. The order of a node's
predecessors is the order in which the edges were added; it is the same
for every module sharing the graph (Alice and Bob).

Bit convention: index ``i`` is the bit of weight ``2^i`` (least
significant bit first), see :func:`int_to_bits`.
"""

from __future__ import annotations

import networkx as nx

# Node types
IN_A, IN_B = "IN_A", "IN_B"
OUT_A, OUT_B = "OUT_A", "OUT_B"
AND, XOR, NOT = "AND", "XOR", "NOT"

INPUTS = {IN_A, IN_B}
OUTPUTS = {OUT_A, OUT_B}
GATES = {AND, XOR, NOT}


# --- Node names and conversions -------------------------------------------

def input_node(party: str, i: int) -> str:
    """Name of the node carrying the i-th input bit of ``party`` (``"A"`` or ``"B"``)."""
    return f"IN_{party}_{i}"


def output_node(party: str, i: int) -> str:
    """Name of the node carrying the i-th output bit of ``party`` (``"A"`` or ``"B"``)."""
    return f"OUT_{party}_{i}"


def int_to_bits(x: int, n: int) -> list[int]:
    """Split ``x`` into ``n`` bits, least significant bit first."""
    return [(x >> i) & 1 for i in range(n)]


def bits_to_int(bits) -> int:
    """Rebuild an integer from its bits (least significant bit first)."""
    return sum(bit << i for i, bit in enumerate(bits))


def encode_inputs(a: int, b: int, n: int) -> dict[str, int]:
    """Build the ``{input node: bit}`` dictionary for the integers ``a`` and ``b``."""
    inputs = {input_node("A", i): bit for i, bit in enumerate(int_to_bits(a, n))}
    inputs.update({input_node("B", i): bit for i, bit in enumerate(int_to_bits(b, n))})
    return inputs


def decode_output(values: dict[str, int], party: str, n: int) -> int:
    """Read the integer carried by the nodes ``OUT_<party>_0 ... OUT_<party>_(n-1)``."""
    return bits_to_int(values[output_node(party, i)] for i in range(n))


# --- Circuit construction -------------------------------------------------

def generate_max_circuit(n: int):
    """Build the circuit computing ``max(a, b)`` for ``n``-bit ``a`` and ``b``.

    Principle:

    1. **Comparison** — bits are scanned from most to least significant
       while maintaining two wires:

       - ``equal``     = 1 if the bits of ``a`` and ``b`` seen so far are equal;
       - ``a_greater`` = 1 if ``a > b`` on the bits seen so far.

       For bit ``i``: ``a_greater ← a_greater ⊕ (equal ∧ a_i ∧ ¬b_i)``.
       The XOR acts as an OR here because both terms can never be 1 at the
       same time (if ``a_greater = 1`` then ``equal = 0``), and
       ``equal ← equal ∧ ¬(a_i ⊕ b_i)``.

    2. **Selection** — each bit of the result is
       ``(a_greater ∧ a_i) ⊕ (¬a_greater ∧ b_i)``.

    The result is sent both to ``OUT_A_i`` (Alice) and ``OUT_B_i`` (Bob).

    :return: ``(G, labels)``, see the module documentation.
    """
    if n < 1:
        raise ValueError("The circuit needs at least one input bit")

    G = nx.DiGraph()
    labels: dict[str, str] = {}

    def gate(name: str, kind: str, *inputs: str) -> str:
        """Add node ``name`` of type ``kind`` fed by ``inputs`` (in that order)."""
        labels[name] = kind
        G.add_node(name)
        for source in inputs:
            G.add_edge(source, name)
        return name

    in_a = [gate(input_node("A", i), IN_A) for i in range(n)]
    in_b = [gate(input_node("B", i), IN_B) for i in range(n)]

    # 1. Comparison, from the most significant bit (i = n-1) to the least (i = 0)
    equal = None      # higher bits equal? (None until a bit has been seen)
    a_greater = None  # a > b on the higher bits?
    for i in reversed(range(n)):
        not_b = gate(f"NOT_B_{i}", NOT, in_b[i])
        a_greater_b = gate(f"A_GREATER_B_{i}", AND, in_a[i], not_b)  # a_i ∧ ¬b_i

        if a_greater is None:
            a_greater = a_greater_b
        else:
            and_node = gate(f"AND_EQUAL_GREATER_{i}", AND, equal, a_greater_b)
            a_greater = gate(f"OR_GREATER_{i}", XOR, a_greater, and_node)

        # Equality is only useful if less significant bits remain:
        # skip it on the last round (avoids useless gates).
        if i > 0:
            a_xor_b = gate(f"A_XOR_B_{i}", XOR, in_a[i], in_b[i])
            a_eq_b = gate(f"NOT_A_XOR_B_{i}", NOT, a_xor_b)          # a_i == b_i
            equal = a_eq_b if equal is None else gate(f"AND_EQUAL_{i}", AND, equal, a_eq_b)

    # 2. Bit-by-bit selection of max(a, b)
    not_a_greater = gate("NOT_A_GREATER", NOT, a_greater)
    for i in range(n):
        a_and = gate(f"A_AND_SELECT_{i}", AND, a_greater, in_a[i])
        b_and = gate(f"B_AND_SELECT_{i}", AND, not_a_greater, in_b[i])
        max_bit = gate(f"XOR_OUT_{i}", XOR, a_and, b_and)

        gate(output_node("A", i), OUT_A, max_bit)
        gate(output_node("B", i), OUT_B, max_bit)

    return G, labels


# --- Plaintext evaluation -------------------------------------------------

def evaluate_circuit(G, labels, inputs: dict[str, int]) -> dict[str, int]:
    """Evaluate the circuit in the clear.

    :param inputs: value (0 or 1) of every input node.
    :return: ``{output node: bit}`` dictionary.
    """
    values = dict(inputs)
    for node in nx.topological_sort(G):
        label = labels[node]
        preds = list(G.predecessors(node))

        if label in INPUTS:
            if node not in values:
                raise KeyError(f"Missing value for input {node}")
        elif label == NOT:
            values[node] = 1 - values[preds[0]]
        elif label == AND:
            values[node] = values[preds[0]] & values[preds[1]]
        elif label == XOR:
            values[node] = values[preds[0]] ^ values[preds[1]]
        elif label in OUTPUTS:
            values[node] = values[preds[0]]
        else:
            raise ValueError(f"Unknown node type: {label}")

    return {node: values[node] for node in G.nodes if labels[node] in OUTPUTS}


if __name__ == "__main__":
    n, a, b = 8, 57, 132
    G, labels = generate_max_circuit(n)
    outputs = evaluate_circuit(G, labels, encode_inputs(a, b, n))
    gate_counts = {kind: sum(1 for k in labels.values() if k == kind) for kind in (AND, XOR, NOT)}
    print(f"{n}-bit max circuit: {gate_counts}")
    print(f"max({a}, {b}) = {decode_output(outputs, 'A', n)}")
