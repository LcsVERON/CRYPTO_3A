from Crypto.Util.number import getPrime, inverse
import random
import AlGamal

# genere le groupe 
def Alice_prepare(bits=256):
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

# Alice a les 2 clés publique (avec la "fausse" comprise)     
def elgamal_encrypt(p,g,A0,A1,m0,m1):
    # On converti de bytes en int si nécéssaire
    if isinstance(m0, bytes):
        m0 = int.from_bytes(m0, byteorder='big')
    if isinstance(m1, bytes):
        m1 = int.from_bytes(m1, byteorder='big')
    b0 = random.randint(1,p-2)
    B0=pow(g,b0,p)
    c0=(m0*pow(A0,b0,p))%p
    
    b1=random.randint(1,p-2)
    B1=pow(g,b1,p)
    c1 = (m1 * pow(A1, b1, p)) % p

    return (B0, c0), (B1, c1)

# Bob déchiffre avec a qui est la clé privé, B utile dans les calculs pour retrouver m, c est le texte chiffré
def elgamal_decrypt(p,a,B,c, as_bytes=False, byte_length=16):
    s=pow(B,a,p)
    m=(c*inverse(s,p))%p
    if as_bytes:
        return m.to_bytes(byte_length, byteorder='big')
    else:
        return m

    
