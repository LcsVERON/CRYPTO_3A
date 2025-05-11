import random
import networkx as nx
from aes import dechiffrement  
from AlGamal_OT import Bob_prepare, elgamal_encrypt, elgamal_decrypt, Alice_prepare
from collections import defaultdict

from Crypto.Cipher import AES
from Crypto.Util import Counter
from Crypto.Util.number import bytes_to_long

def bob_evalue_circuit(G, key_map, garbled_tables):

    outputs = {}
    order = list(nx.topological_sort(G))

    for node in order :
        label = G.nodes[node].get("label")  # Correction importante : accéder au label depuis les attributs du graphe

        preds = list(G.predecessors(node))

        if label in {"IN_B", "IN_A"}:
            continue

        if label in {"OUT_A", "OUT_B"}:
            preds = list(G.predecessors(node))
            pred = preds[0]
            
            # Récupère la clé reçue à ce niveau
            received_key = key_map.get((pred, 0))

            if received_key == key_map.get((node, 0)):
                outputs[node] = 0
            elif received_key == key_map.get((node, 1)):
                outputs[node] = 1
            else:
                raise ValueError(f"Impossible de déterminer la sortie du nœud {node}")
            
        if label in {"AND", "XOR"}:
            preds = list(G.predecessors(node))

            for gar_bebou in garbled_tables[node]:
                found = False  # Ce drapeau indique si une combinaison (x, y) a permis un déchiffrement valide

                # On teste toutes les combinaisons possibles des bits d'entrée (x, y) ∈ {0,1} × {0,1}
                for x in [0, 1]:
                    for y in [0, 1]:
                        try:
                            # Étape 1 : Déchiffrement avec la clé correspondant au second prédécesseur (ordre inverse du chiffrement)
                            inter = dechiffrement(gar_bebou, key_map[(preds[1], y)])

                            # Étape 2 : Déchiffrement du résultat intermédiaire avec la clé du premier prédécesseur
                            res = dechiffrement(inter, key_map[(preds[0], x)])

                            # Vérifie si le résultat du double déchiffrement correspond à une des clés attendues en sortie
                            if res in [key_map[(node, 0)], key_map[(node, 1)]]:
                                # Calcule la sortie logique de la porte avec les entrées x et y
                                out = x & y if label == "AND" else x ^ y

                                # Enregistre la clé sortie dans key_map pour une utilisation future
                                key_map[(node, out)] = res
                                found = True
                                break  # Sort de la boucle interne sur y
                        except Exception:
                            continue  # Ignore les erreurs de déchiffrement (mauvaises clés)

                    if found:
                        break  # Sort de la boucle externe sur x si on a trouvé une bonne combinaison

                # Si aucune combinaison n'a permis de déchiffrer correctement, on signale une erreur
                if not found:
                    raise ValueError(f"Déchiffrement échoué pour la table brouillée du nœud {node}")


        elif label == "NOT":
            # Une porte NOT n'a qu'un seul prédécesseur
            pred = list(G.predecessors(node))[0]

            found = False  # Drapeau indiquant si un déchiffrement valide a été trouvé

            for x in [0, 1]:  # On teste les deux valeurs possibles de l’entrée
                try:
                    # On tente de déchiffrer chaque entrée de la table avec la clé associée à la valeur x du prédécesseur
                    for garbled_entry in garbled_tables[node]:
                        res = dechiffrement(garbled_entry, key_map[(pred, x)])

                        # Si le résultat correspond à une des clés de sortie, on a trouvé
                        if res in [key_map[(node, 0)], key_map[(node, 1)]]:
                            # La sortie logique d’un NOT est simplement l’inverse de l’entrée
                            out = 1 - x
                            key_map[(node, out)] = res
                            found = True
                            break  # Sort de la boucle sur garbled_entry
                    if found:
                        break  # Sort de la boucle sur x
                except Exception:
                    continue  # Ignore les erreurs de déchiffrement (mauvaises clés)

            if not found:
                raise ValueError(f"Déchiffrement échoué pour la porte NOT au nœud {node}")

        