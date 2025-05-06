import random
import circuit

def calcul_biparti(x, n, G):
    #on tire aléatoirement n bits
    y = random.getrandbits(n)
    x_a = y
    x_b = x ^ y #ce que alice envoie a bob TODO: gérer cela bit par bit
    #TODO: Bob procède de façon symétrique
    
    outputs_a = circuit.evaluer_circuit(G, x_a, x_b) #TODO: evaluer le cicruit avec leur part des valeurs
    outputs_b = circuit.evaluer_circuit(G, x_a, x_b) #TODO: evaluer le cicruit avec leur part des valeurs
    
    
    
    
    