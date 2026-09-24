"""
Demo: ``python -m crypto3a A B [N]``.

Computes ``max(A, B)`` on ``N`` bits (8 by default) in three ways: in the
clear with the circuit, with a garbled circuit (Yao) and with the virtual
machine (secret sharing).
"""

import argparse

from .circuit import decode_output, encode_inputs, evaluate_circuit, generate_max_circuit
from .garbled_circuit import secure_max
from .virtual_machine import run_secure_max


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="python -m crypto3a", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("a", type=int, help="Alice's input")
    parser.add_argument("b", type=int, help="Bob's input")
    parser.add_argument("n", type=int, nargs="?", default=8, help="number of bits (default: 8)")
    args = parser.parse_args(argv)

    if not (0 <= args.a < 2 ** args.n and 0 <= args.b < 2 ** args.n):
        parser.error(f"a and b must be between 0 and {2 ** args.n - 1}")

    G, labels = generate_max_circuit(args.n)
    plain = decode_output(evaluate_circuit(G, labels, encode_inputs(args.a, args.b, args.n)), "A", args.n)
    print(f"max({args.a}, {args.b}) on {args.n} bits")
    print(f"  plaintext circuit     : {plain}")
    print("  garbled circuit (Yao) : Alice = {}, Bob = {}".format(*secure_max(args.a, args.b, args.n)))
    print("  virtual machine       : Alice = {}, Bob = {}".format(*run_secure_max(args.a, args.b, args.n)))


if __name__ == "__main__":
    main()
