import os
import random
from aes import chiffrement  # Fonction personnalisée de chiffrement AES (probablement en mode CTR)
from collections import defaultdict

from Crypto.Cipher import AES
from Crypto.Util import Counter

# Génère une clé AES aléatoire de 128 bits (16 octets)
def generate_random_key():
    return os.urandom(16)

# Fonction principale : Alice prépare le circuit logique sous forme brouillée
def alice_prepare_circuit(G, labels):
    key_map = {}         # Dictionnaire pour stocker les clés associées à chaque (noeud, bit)
    garbled_tables = {}  # Dictionnaire pour stocker la table brouillée de chaque porte

    # === Étape 1 : Génération des clés ===
    for node in G.nodes:
        label = labels[node]
        # Ne pas générer de clés pour les sorties de Bob (il les récupère lui-même)
        if label in {"OUT_B"}:
            continue
        # Ne pas générer de clés pour les entrées (Alice et Bob les reçoivent à part)
        if label not in {"IN_A", "IN_B", "OUT_A"}:
            # Génère deux clés : une pour la valeur 0 et une pour la valeur 1
            key_map[(node, 0)] = generate_random_key()
            key_map[(node, 1)] = generate_random_key()

    # === Étape 2 : Construction des tables brouillées ===
    for node in G.nodes:
        label = labels[node]

        # Cas des portes AND et XOR (2 entrées)
        if label in {"AND", "XOR"}:
            preds = list(G.predecessors(node))  # Récupère les deux parents du nœud
            # Si la sortie est OUT_B, on la traite séparément (probablement pour l'envoi à Bob)
            if any(labels[child] == "OUT_B" for child in G.successors(node)):
                continue

            # Récupère les clés de sortie de la porte
            k0, k1 = key_map[(node, 0)], key_map[(node, 1)]
            # Récupère les clés des bits 0 et 1 des deux entrées
            pk0 = key_map[(preds[0], 0)]
            pk1 = key_map[(preds[0], 1)]
            qk0 = key_map[(preds[1], 0)]
            qk1 = key_map[(preds[1], 1)]

            table = []

            # Pour chaque combinaison (x, y) d'entrées binaires possibles
            for x in [0, 1]:
                for y in [0, 1]:
                    # Calcule la sortie attendue de la porte
                    out = x & y if label == "AND" else x ^ y
                    k_out = key_map[(node, out)]  # Clé associée à la sortie

                    # Double chiffrement : d'abord avec clé d'entrée x, puis avec clé d'entrée y
                    first_layer = chiffrement(key=pk0 if x == 0 else pk1, plaintext=k_out)
                    double_layer = chiffrement(key=qk0 if y == 0 else qk1, plaintext=first_layer)

                    table.append(double_layer)  # Ajoute à la table

            random.shuffle(table)  # Mélange l'ordre des lignes pour cacher la structure
            garbled_tables[node] = table  # Enregistre la table pour ce nœud

        # Cas des portes NOT (1 seule entrée)
        elif label == "NOT":
            preds = list(G.predecessors(node))
            if any(labels[child] == "OUT_B" for child in G.successors(node)):
                continue  # Cas spécial traité plus tard

            # Clés d'entrée
            pk0 = key_map[(preds[0], 0)]
            pk1 = key_map[(preds[0], 1)]

            # Clés de sortie
            k0 = key_map[(node, 0)]
            k1 = key_map[(node, 1)]

            # Chiffre la sortie inversée (NOT)
            c0 = chiffrement(pk0, k1)  # NOT(0) = 1 → chiffré avec clé d'entrée 0
            c1 = chiffrement(pk1, k0)  # NOT(1) = 0 → chiffré avec clé d'entrée 1

            table = [c0, c1]
            random.shuffle(table)  # Mélange la table
            garbled_tables[node] = table  # Enregistre la table

    # Retourne le dictionnaire des clés et les tables brouillées prêtes à être envoyées
    return key_map, garbled_tables
