from Crypto.Util.number import getPrime, inverse
import random
import AlGamal

def generate_group(bits=256):
    p=getPrime(bits)
    g= random.randint(2,p-2)
    c=random.randint(2,p-2)
    return p,g,c

def Bob_prepare(p,g,c,b):
    a = random.randint(1, p - 2)         
    Ab = pow(g, a, p)                     
    A1b = (c * inverse(Ab, p)) % p        
    if b == 0:
        return a, Ab, A1b                
    else:
        return a, A1b, Ab
    

if __name__ == "__main__":
    # Alice choisit les paramètres du groupe
    p, g, C = generate_group()

    # Alice choisit ses deux messages
    m0 = 4321
    m1 = 9876

    # Bob choisit un bit b (0 ou 1)
    b = 0  # il veut recevoir m1

    # Bob prépare les clés à envoyer à Alice
    a, A0, A1 = Bob_prepare(p, g, C, b)

    # Alice chiffre les deux messages avec A0 et A1
    c0, c1 = AlGamal.elgamal_encrypt(p, g, A0, A1, m0, m1)

    # Bob déchiffre seulement le message qu’il a choisi
    c_b = c0 if b == 0 else c1
    recu = AlGamal.elgamal_decrypt(p, a, c_b)

    print(f"Bob a choisi b = {b}")
    print(f"Message reçu par Bob : {recu}")
    print(f"Message attendu : {m0 if b == 0 else m1}")
    print("Succès" if recu == (m0 if b == 0 else m1) else "Erreur")
    
    
    
