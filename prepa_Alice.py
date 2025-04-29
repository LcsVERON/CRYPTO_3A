import os
import random
from aes import chiffrement
from collections import defaultdict

from Crypto.Cipher import AES
from Crypto.Util import Counter

def generate_random_key():
    return os.urandom(16)  # 128-bit key

def alice_prepare_circuit(G, labels):
    key_map = {}  # maps (node, bit) -> key
    garbled_tables = {}  # maps node -> list of ciphertexts

    # Étape 1 : Génération des clés
    for node in G.nodes:
        label = labels[node]
        # Ne pas générer de clés pour OUT_B
        if label in {"OUT_B"}:
            continue
        if label not in {"IN_A", "IN_B", "OUT_A"}:
            key_map[(node, 0)] = generate_random_key()
            key_map[(node, 1)] = generate_random_key()

    # Étape 2 : Construction des tables brouillées
    for node in G.nodes:
        label = labels[node]

        if label in {"AND", "XOR"}:
            preds = list(G.predecessors(node))
            if any(labels[child] == "OUT_B" for child in G.successors(node)):
                continue  # cas spécial traité plus tard

            k0, k1 = key_map[(node, 0)], key_map[(node, 1)]
            pk0 = key_map[(preds[0], 0)]
            pk1 = key_map[(preds[0], 1)]
            qk0 = key_map[(preds[1], 0)]
            qk1 = key_map[(preds[1], 1)]

            table = []

            for x in [0, 1]:
                for y in [0, 1]:
                    out = x & y if label == "AND" else x ^ y
                    k_out = key_map[(node, out)]
                    first_layer = chiffrement(key=pk0 if x == 0 else pk1, plaintext=k_out)
                    double_layer = chiffrement(key=qk0 if y == 0 else qk1, plaintext=first_layer)
                    table.append(double_layer)

            random.shuffle(table)
            garbled_tables[node] = table

        elif label == "NOT":
            preds = list(G.predecessors(node))
            if any(labels[child] == "OUT_B" for child in G.successors(node)):
                continue  # cas spécial traité plus tard

            pk0 = key_map[(preds[0], 0)]
            pk1 = key_map[(preds[0], 1)]
            k0 = key_map[(node, 0)]
            k1 = key_map[(node, 1)]

            c0 = chiffrement(pk0, k1)  # NOT(0) = 1
            c1 = chiffrement(pk1, k0)  # NOT(1) = 0

            table = [c0, c1]
            random.shuffle(table)
            garbled_tables[node] = table

    return key_map, garbled_tables
