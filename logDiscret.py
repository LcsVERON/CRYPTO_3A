import math

def trouve_diviseurs(n):
    # Retourne les diviseurs propres de n (différents de 1 et n)
    return [d for d in range(2, n) if n % d == 0]

def est_generateur(g, p):
    # Vérifie si g est un générateur du groupe multiplicatif de F_p
    ordre = p - 1
    for d in trouve_diviseurs(ordre):
        if pow(g, ordre // d, p) == 1:
            return False
    return True

def trouve_generateurs(p):
    # Retourne tous les générateurs du groupe multiplicatif de F_p
    return [g for g in range(2, p) if est_generateur(g, p)]

def est_premier(n):
    # Test naïf de primalité basé sur l'absence de diviseurs propres
    return len(trouve_diviseurs(n)) == 0

def baby_step_giant_step(g, h, p):
    # Algorithme de Baby-step Giant-step pour résoudre g^x ≡ h mod p
    t = math.isqrt(p) + 1
    petits_pas = {pow(g, i, p): i for i in range(t)}
    g_t_inv = pow(g, -t, p)
    
    grand_pas = h #initialisation du grand pas à h
    for k in range (t):
        
        if grand_pas in petits_pas: #si grand pas est dans petit pas, alors on retourne k*t + i (h*g^-kt = g^i => x = kt+i)
            i = petits_pas[grand_pas]
            return k*t+i
        
        grand_pas = (grand_pas * g_t_inv) % p #sinon, on actualise grand pas en le multipliant par g^-t
        
    return None  #si aucune solution trouvée
