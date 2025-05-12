import random
import networkx as nx
from aes import dechiffrement  
from circuit import generate_max_min_circuit
from prepa_Alice import alice_prepare_circuit
from collections import defaultdict

from Crypto.Cipher import AES
from Crypto.Util import Counter
from Crypto.Util.number import bytes_to_long

def bob_evalue_circuit(G, keys, garbled_tables):

    outputs = {}

    order = list(nx.topological_sort(G))

    for node in order :
        label = G.nodes[node].get("label") 

        preds = list(G.predecessors(node))

        if label in {"IN_B", "IN_A"}:
            continue

        if label in {"OUT_A", "OUT_B"}:
            preds = list(G.predecessors(node))
            pred = preds[0]
            
            keys[node] = keys[pred]
            
        else :
        
            preds = list(G.predecessors(node))
            found = False
            for gar_bebou in garbled_tables[node]:
                  
                res = gar_bebou

                # Étape 1 : Déchiffrement avec la clé correspondant au second prédécesseur (ordre inverse du chiffrement)
                if label in {"AND", "XOR"}:
                    res = dechiffrement(gar_bebou, keys[preds[1]])
                
                
                # Étape 2 : Déchiffrement du résultat intermédiaire avec la clé du premier prédécesseur
                res = dechiffrement(res, keys[preds[0]])

                if not res.startswith(b'MSG:'):
                    # Si le déchiffrement échoue, on passe à la combinaison suivante
                    continue

                found = True  # Une combinaison valide a été trouvée
                break
                

            # Si aucune combinaison n'a permis de déchiffrer correctement, on signale une erreur
            if not found:
                raise ValueError(f"Déchiffrement échoué pour la table brouillée du nœud {node}")

            # On ajoute la clé de sortie à la liste des clés
            keys[node] = res

    # On récupère les clés de sortie
    outputs_a_list = [int.from_bytes(keys[node][4:], byteorder="big") for node in G.nodes if G.nodes[node].get("label") == "OUT_A"]
    outputs_b_list = [int.from_bytes(keys[node][4:], byteorder="big") for node in G.nodes if G.nodes[node].get("label") == "OUT_B"]

    # On convertit les listes de bits en entiers binaires (avec inversion pour poids fort à gauche)
    outputs_a = sum([1 << i for i, bit in enumerate(reversed(outputs_a_list)) if bit == 1])
    outputs_b = sum([1 << i for i, bit in enumerate(reversed(outputs_b_list)) if bit == 1])

    print("Résultats de BOB:", outputs_a, outputs_b)
    return outputs_a, outputs_b

        
if __name__ == "__main__":
    
    G, labels = generate_max_min_circuit(2) 

    # Entrée de Alice pour A
    inputs_a = [0, 1]  # Alice choisit

    # Entrée de Bob pour B
    inputs_b = [1, 1]  # Bob choisit 
    
    keys_a, keys_b, garbled_tables = alice_prepare_circuit(G, labels, inputs_b)

    keys = {}
    compter_a = 0
    compter_b = 0
    
    for node in G.nodes:
        label = labels[node]

        # Ne pas envoyer les clés pour les entrées de Bob
        if label == "IN_A":
            keys[node] = keys_a[(node, inputs_a[compter_a])]
            compter_a += 1

        # PROTOCOLE OT
        elif label == "IN_B":
            keys[node] = keys_b[(node, inputs_b[0])]
            compter_b += 1

    # Bob évalue le circuit
    result = bob_evalue_circuit(G, keys, garbled_tables)
