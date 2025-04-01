from Crypto.Util.number import getPrime, inverse
import random

# -----------------------
# 1. Génération des clés
# -----------------------
def elgamal_keygen(bits=256):
    """
    Génère une paire de clés pour El Gamal
    - bits : taille du nombre premier p
    Retourne : (clé publique (p, g, y), clé privée x)
    """
    p = getPrime(bits)                      # Grand nombre premier p
    g = random.randint(2, p - 2)            # Générateur g
    x = random.randint(1, p - 2)            # Clé privée x
    y = pow(g, x, p)                        # Clé publique y = g^x mod p
    return (p, g, y), x

# -----------------------
# 2. Chiffrement
# -----------------------
def elgamal_encrypt(p, g, y, m):
    """
    Chiffre un message m avec la clé publique (p, g, y)
    - m : message (entier < p)
    Retourne : tuple (c1, c2)
    """
    r = random.randint(1, p - 2)            # Choix de l’aléa r
    c1 = pow(g, r, p)                       # c1 = g^r mod p
    s = pow(y, r, p)                        # s = y^r mod p
    c2 = (m * s) % p                        # c2 = m * s mod p
    return c1, c2

# -----------------------
# 3. Déchiffrement
# -----------------------
def elgamal_decrypt(p, x, c1, c2):
    """
    Déchiffre le couple (c1, c2) avec la clé privée x
    Retourne : le message m
    """
    s = pow(c1, x, p)                       # s = c1^x = g^{xr}
    s_inv = inverse(s, p)                   # Calcul de s^{-1} mod p
    m = (c2 * s_inv) % p                    # m = c2 / s mod p
    return m

# -----------------------
# 4. Test du système
# -----------------------
if __name__ == "__main__":
    # Génération des clés
    public_key, private_key = elgamal_keygen()
    p, g, y = public_key
    x = private_key

    # Message à chiffrer
    message = 123456
    print("Message original :", message)

    # Chiffrement
    c1, c2 = elgamal_encrypt(p, g, y, message)
    print("Chiffrement : c1 =", c1, ", c2 =", c2)

    # Déchiffrement
    decrypted = elgamal_decrypt(p, x, c1, c2)
    print("Message déchiffré :", decrypted)
    
  
