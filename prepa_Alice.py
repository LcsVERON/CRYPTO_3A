import os
import random
from aes import chiffrement  
from AlGamal_OT import Bob_prepare, elgamal_encrypt, elgamal_decrypt, Alice_prepare
from collections import defaultdict

from Crypto.Cipher import AES
from Crypto.Util import Counter
from Crypto.Util.number import bytes_to_long

# Description du format des données envoyées par Alice à Bob : 
# 
# key_map : Clés AES associées à chaque nœud et valeur booléenne.
# garbled_tables : Tables de vérité brouillées pour chaque porte logique, mélangées pour garantir la confidentialité. 

# Génère une clé AES aléatoire de 128 bits (16 octets)
def generate_random_key():
    return os.urandom(16)

# Fonction principale : Alice prépare le circuit logique sous forme brouillée
# Supposons que l'OT est déjà implémenté comme tu l'as montré

def alice_prepare_circuit(G, labels, inputs_b): # le b c'est l'entrée de Bob 
    key_map = {}         
    garbled_tables = {}  

    cpt = 0

    # === Étape 0 : Génération des paramètres du groupe ===
    p, g, C = Alice_prepare()  # Alice génère les paramètres du groupe

    # === Étape 1 : Génération des clés ===
    for node in G.nodes:
        label = labels[node]
        # Ne pas générer de clés pour les sorties de Bob (il les récupère lui-même)
        if label in {"OUT_B"}:
            continue
        # Ne pas générer de clés pour les entrées (Alice et Bob les reçoivent à part)
        if label not in {"OUT_A", "OUT_B"}:
            # Pour chaque entrée de Bob (λ(i) = IN B), on engage un OT
            if label == "IN_B":

                # Alice prépare deux clés K0 et K1 pour chaque entrée de Bob
                K0 = generate_random_key()
                K1 = generate_random_key()

                # Alice engage un protocole OT pour chaque entrée de Bob
                a, A0, A1 = Bob_prepare(p, g, C, inputs_b[cpt])  # Bob choisit b

                # Alice chiffre les deux messages (les clés) avec A0 et A1
                c0, c1 = elgamal_encrypt(p, g, A0, A1, K0, K1)

                # Bob reçoit la clé qu'il a choisie à partir de OT
                c_b = c0 if inputs_b[cpt] == 0 else c1
                B, c = c_b
                key_map[(node, inputs_b[cpt])] = elgamal_decrypt(p, a, B, c, as_bytes=True, byte_length=16)

                # Stocker toutes les clés dans key_map pour que Alice puisse construire la table
                key_map[(node, 0)] = K0
                key_map[(node, 1)] = K1

                cpt+=1
            else:
                # Pour les autres nœuds, Alice génère simplement des clés
                key_map[(node, 0)] = generate_random_key()
                key_map[(node, 1)] = generate_random_key()

    # === Étape 2 : Construction des tables brouillées ===
    # Parcourt chaque nœud du circuit
    for node in G.nodes:
        label = labels[node]

        if label in {"AND", "XOR"}:
            preds = list(G.predecessors(node))

            # Vérifie si l'un des successeurs du nœud est une sortie Bob ("OUT_B")
            # Si oui, on passe au nœud suivant (cette étape évite de générer la table pour ce nœud)
            if any(labels[child] == "OUT_B" for child in G.successors(node)):
                continue

            # Récupère les clés des prédécesseurs pour les entrées x et y de la porte
            pk0 = key_map[(preds[0], 0)]
            pk1 = key_map[(preds[0], 1)]
            qk0 = key_map[(preds[1], 0)]
            qk1 = key_map[(preds[1], 1)]

            # Initialise la liste qui contiendra les valeurs de la table brouillée pour ce nœud
            table = []

            # Parcourt toutes les combinaisons possibles des entrées x et y
            for x in [0, 1]:
                for y in [0, 1]:
                    # Calcule la sortie attendue pour la porte logique (AND ou XOR)
                    out = x & y if label == "AND" else x ^ y

                    # Récupère la clé associée au resultat 
                    k_out = key_map[(node, out)]

                    # Effectue un double chiffrement : d'abord avec la clé pk0 ou pk1 pour x, puis avec qk0 ou qk1 pour y
                    first_layer = chiffrement(k_out, pk0 if x == 0 else pk1)
                    double_layer = chiffrement(first_layer, qk0 if y == 0 else qk1)

                    # Ajoute le résultat du double chiffrement à la table
                    table.append(double_layer)

            # Mélange les entrées de la table 
            random.shuffle(table)

            # Enregistre la table brouillée pour le nœud actuel dans le dictionnaire des tables 
            garbled_tables[node] = table

        elif label == "NOT":
            preds = list(G.predecessors(node))

            # Vérifie si l'un des successeurs du nœud est une sortie Bob ("OUT_B")
            # Si oui, on passe au nœud suivant (cette étape évite de générer la table pour ce nœud)
            if any(labels[child] == "OUT_B" for child in G.successors(node)):
                continue

            # Récupère les clés des prédécesseurs pour l'entrée x de la porte NOT
            pk0 = key_map[(preds[0], 0)]
            pk1 = key_map[(preds[0], 1)]

            # Récupère les clés associées à la sortie de la porte NOT
            k0 = key_map[(node, 0)]
            k1 = key_map[(node, 1)]

            # chiffrement avec les clés appropriées pour la porte NOT
            c0 = chiffrement(k1, pk0)  # Chiffrement pour la sortie 0
            c1 = chiffrement(k0, pk1)  # Chiffrement pour la sortie 1

            # Crée la table contenant les deux résultats possibles de la porte NOT
            table = [c0, c1]

            random.shuffle(table)

            # Enregistre la table brouillée pour le nœud actuel dans le dictionnaire des tables
            garbled_tables[node] = table

    return key_map, garbled_tables
