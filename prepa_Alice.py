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
    return b'MSG:' + os.urandom(16)[4:]  # On ajoute MSG: pour identifier le message
    
def alice_prepare_circuit(G, labels, inputs_b): 
    key_map = {}         
    garbled_tables = {}  

    # Initialisation des labels pour chaque nœud dans le graphe
    for node, label in labels.items():
        G.nodes[node]['label'] = label

    cpt = 0

    # === Étape 0 : Génération des paramètres du groupe ===
    p, g, C = Alice_prepare() 

    # === Étape 1 : Génération des clés ===
    for node in G.nodes:
        label = labels[node]
        # pas générer de clés pour les sorties de Bob (il les récupère lui-même)
        if label in {"OUT_B"}:
            continue
        # pas générer de clés pour les entrées (Alice et Bob les reçoivent à part)
        if label not in {"OUT_A", "OUT_B"}:
            
            if label == "IN_B":

                K0 = generate_random_key()
                K1 = generate_random_key()
                
                a, A0, A1 = Bob_prepare(p, g, C, inputs_b[cpt]) 

                # Alice chiffre les deux messages (les clés) avec A0 et A1
                c0, c1 = elgamal_encrypt(p, g, A0, A1, K0, K1)

                # Bob reçoit la clé qu'il a choisie à partir de OT
                c_b = c0 if inputs_b[cpt] == 0 else c1
                B, c = c_b
                key_map[(node, inputs_b[cpt])] = elgamal_decrypt(p, a, B, c, as_bytes=True, byte_length=16)

                # on stocke toutes les clés dans key_map pour que Alice puisse construire la table
                key_map[(node, 0)] = K0
                key_map[(node, 1)] = K1

                cpt+=1

            elif any(labels[child] == "OUT_B" for child in G.successors(node)):
                key_map[(node, 0)] = b'MSG:' + bytes([0]*12)  # 16 octets pile : 'MSG:' + 12x0
                key_map[(node, 1)] = b'MSG:' + bytes([0]*11) + b'\x01'  # 'MSG:' + 11x0 + 1

            
            else:
                # les autres noeuds, Alice génère simplement des clés
                key_map[(node, 0)] = generate_random_key()
                key_map[(node, 1)] = generate_random_key()
                

    # === Étape 2 : Construction des tables brouillées ===
    for node in G.nodes:
        label = labels[node]

        if label in {"AND", "XOR"}:
            preds = list(G.predecessors(node))

            pk0 = key_map[(preds[0], 0)]
            pk1 = key_map[(preds[0], 1)]
            qk0 = key_map[(preds[1], 0)]
            qk1 = key_map[(preds[1], 1)]

            table = [] # table qui contiendra les valeurs de la table brouillée pour ce noeud

            for x in [0, 1]:
                for y in [0, 1]:
                    out = x & y if label == "AND" else x ^ y

                    # Récupère la clé associée au resultat 
                    k_out = key_map[(node, out)]

                    first_layer = chiffrement(k_out, pk0 if x == 0 else pk1)
                    double_layer = chiffrement(first_layer, qk0 if y == 0 else qk1)

                    table.append(double_layer)

            # on melange
            random.shuffle(table)

            garbled_tables[node] = table

        elif label == "NOT":
            preds = list(G.predecessors(node))

            pk0 = key_map[(preds[0], 0)]
            pk1 = key_map[(preds[0], 1)]

            k0 = key_map[(node, 0)]
            k1 = key_map[(node, 1)]

            c0 = chiffrement(k1, pk0)  # Chiffrement pour la sortie 0
            c1 = chiffrement(k0, pk1)  # Chiffrement pour la sortie 1

            table = [c0, c1]

            random.shuffle(table)

            garbled_tables[node] = table

    # === Étape 3 : Envoi des clés d'entrées et des tables à Bob ===

    keys_a = {}  # Liste pour stocker les clés d'entrée d'Alice
    keys_b = {}  # Liste pour stocker les clés d'entrée de Bob

    for node in G.nodes:
        label = labels[node]

        # on envoie pas les clés pour les entrées de Bob
        if label == "IN_A":
            keys_a[(node, 0)] = key_map[(node, 0)] 
            keys_a[(node, 1)] = key_map[(node, 1)]
        elif label == "IN_B":
            keys_b[(node, 0)] = key_map[(node, 0)]
            keys_b[(node, 1)] = key_map[(node, 1)]

    return keys_a, keys_b, garbled_tables