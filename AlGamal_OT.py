from Crypto.Util.number import getPrime, inverse
import random

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
    
def elgamal_encrypt(p,g,A0,A1,m0,m1):
    r0 = random.randint(1,p-2)
    c0_1=pow(g,r0,p)
    c0_2=(m0*pow(A0,r0,p))%p
    
    r1=random.randint(1,p-2)
    c1_1=pow(g,r1,p)
    c1_2 = (m1 * pow(A1, r1, p)) % p

    return (c0_1, c0_2), (c1_1, c1_2)
    
def elgamal_decrypt(p,a,c):
    c1,c2 = c
    s=pow(c1,a,p)
    m=(c2*inverse(s,p))%p
    return m

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
    c0, c1 = elgamal_encrypt(p, g, A0, A1, m0, m1)

    # Bob déchiffre seulement le message qu’il a choisi
    c_b = c0 if b == 0 else c1
    recu = elgamal_decrypt(p, a, c_b)

    print(f"Bob a choisi b = {b}")
    print(f"Message reçu par Bob : {recu}")
    print(f"Message attendu : {m0 if b == 0 else m1}")
    print("✅ Succès" if recu == (m0 if b == 0 else m1) else "❌ Erreur")
    
    
    
