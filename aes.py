import cryptography

def decoupe (m):
    n=len(m)//128
    message =  [m[i * 128 : (i+1) * 128] for i in range (n)]
    if n%128 == 0:
        message [n] = int_to_bytes(pow(2, 128))

def enchiffre (m):
    