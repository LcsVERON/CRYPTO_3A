import cryptography
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


def xor_bytes(a: bytes, b: bytes) -> bytes:
    
    if len(a) != len(b):
        raise ValueError("Les deux chaînes doivent avoir la même longueur")
    
    return bytes(x ^ y for x, y in zip(a, b))

def aes_chiffrement_block(key: bytes, block: bytes) -> bytes:
    """
    Chiffre un bloc de 128 bits avec AES-128 en mode ECB.
    """
    cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
    encryptor = cipher.encryptor() 
    return encryptor.update(block) + encryptor.finalize()


def chiffrement(m: bytes, key: bytes,) -> bytes:
    """
    Chiffre un message m avec la clé key selon la fonction :
    E(m1 · · · ml, k) = [r, AES_k(r + 1) ⊕ m1, ..., AES_k(r + l) ⊕ ml]
    """
    if len(key) != 16:
        raise ValueError("La clé doit être de 16 octets (AES-128)")
    
    # 1. Générer un nonce `r` de 128 bits
    r = os.urandom(16)
    
    # 2. Diviser `m` en blocs de 16 octets
    n = len(m) // 16
    message_blocks = [m[i * 16 : (i+1) * 16] for i in range(n)]
    
    # Ajouter le padding si nécessaire
    if len(m) % 16 != 0:
        message_blocks.append(m[n * 16:] + b'\x00' * (16 - len(m) % 16))  # Padding nul
    
    # 3. Appliquer AES_k(r + i) et XOR
    encrypted_blocks = []
    for i, block in enumerate(message_blocks):
        r_i = (int.from_bytes(r, "big") + i + 1).to_bytes(16, "big")  # r + i
        aes_output = aes_chiffrement_block(key, r_i)  # AES_k(r + i)
        encrypted_blocks.append(xor_bytes(aes_output, block))  # XOR avec m_i
    
    # 4. Retourner r || blocs chiffrés
    return r + b''.join(encrypted_blocks)

def dechiffrement(ciphertext: bytes, key: bytes) -> bytes:
    """
    Déchiffre un texte chiffré selon :
    D(r · c1 · · · cl, k) = c1 ⊕ AES_k(r + 1) · · · cl ⊕ AES_k(r + l)
    """
    if len(key) != 16:
        raise ValueError("La clé doit être de 16 octets (AES-128)")
    
    if len(ciphertext) < 16:
        raise ValueError("Le texte chiffré est trop court !")
    
    # 1. Extraire `r`
    r = ciphertext[:16]
    encrypted_blocks = [ciphertext[i:i+16] for i in range(16, len(ciphertext), 16)]
    
    # 2. Déchiffrer chaque bloc
    decrypted_blocks = []
    for i, block in enumerate(encrypted_blocks):
        r_i = (int.from_bytes(r, "big") + i + 1).to_bytes(16, "big")  # r + i
        aes_output = aes_chiffrement_block(key, r_i)  # AES_k(r + i)
        decrypted_blocks.append(xor_bytes(aes_output, block))  # XOR avec c_i
    
    # 3. Retirer le padding si nécessaire
    plaintext = b''.join(decrypted_blocks).rstrip(b'\x00')

    if not plaintext.startswith(b'MSG:'):
        raise ValueError("Le texte déchiffré semble invalide (entête manquante)")

    return plaintext


# Exemple d'utilisation
key = os.urandom(16)  # Clé secrète de 16 octets
message_b = b"Hello, this is a test message!" # b pour preciser en bytes

message = "Hello, this is a test message!"
print("Texte de base :", message)

ciphertext = chiffrement(message_b, key)
print("Texte chiffré :", ciphertext.hex())

plaintext = dechiffrement(ciphertext, key)
print("Texte déchiffré :", plaintext.decode())

    