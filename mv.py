import random
import circuit

def trouver_max(G, labels, a, b, n):
    for a in range(2**n):
        for b in range(2**n):
            inputs = {f"IN_A_{i}": (a >> i) & 1 for i in range(n)}
            inputs.update({f"IN_B_{i}": (b >> i) & 1 for i in range(n)})

            outputs = circuit.evaluate_circuit(G, labels, inputs)

            out_a = circuit.bits_to_int([outputs[f"OUT_A_{i}"] for i in range(n)])
    return out_a

def calcul_biparti(x, y, n):
    #on tire aléatoirement n bits
    t = random.getrandbits(n)
    z = random.getrandbits(n)
    z_a = z
    z_b = x ^ z #ce que alice envoie a bob 
    x_b = t
    x_a = y ^ t #ce que bob envoie a alice
    
    G, labels = circuit.generate_max_min_circuit(n) 
    output_a = trouver_max(G, x_a, z_a) #TODO: evaluer le cicruit avec leur part des valeurs
    output_b = trouver_max(G, z_b, x_b) #TODO: evaluer le cicruit avec leur part des valeurs
    
    
    
    
    