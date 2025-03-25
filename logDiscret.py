import math
import bisect

def trouve_diviseurs(n): #fonction retournant la liste des diviseurs de n différents de 1 et n
    diviseurs=[d for d in range(2,n) if n%d==0] #liste des diviseurs de p
    return diviseurs

def est_generateur(g, p): #fonction vérifiant si g génère le groupe multiplicatif du corps F_p
    ordre = p - 1  #ordre du groupe multiplicatif
    for d in trouve_diviseurs(ordre):
        if pow(g, ordre // d, p) == 1:
            return False #si l'odre de g est inférieur à p-1, g n'est pas générateur
    return True

def trouve_generateurs(p): #fonction retournant la liste des générateurs du groupe multiplicatif de F_p
    generateurs = [g for g in range(2, p) if est_generateur(g, p)]
    return generateurs

def est_premier(n): #fonction vérifiant si n est premier
    return len(trouve_diviseurs(n))==0


def baby_step_giant_step(g, h, p):
    t = math.isqrt(p) + 1  #taille des petits pas
    
    petits_pas = {pow(g, i, p): i for i in range (t)} #on place dans une liste les puissances i de 0 à t de g avec leur indice
    
    g_t_inv = pow (g, -t, p) #on calcule l'inverse de g^t
    
    grand_pas = h
    for k in range (t):
        
        if grand_pas in petits_pas:
            i = petits_pas[grand_pas]
            return k*t+i
        
        grand_pas = (grand_pas * g_t_inv) % p
        
    return None  #si aucune solution trouvée

#tests sur le logarithme discret
p = 13291 #cardinal du corps fini
g = trouve_generateurs(p)[0] #générateur (base)
h = 5 #élément dont on cherche le log discret base g mod p

x = baby_step_giant_step(g, h, p)

if (est_premier(p)):
    print(f"Logarithme discret de {h} en base {g} modulo {p} est: {x}")

else:
    print("p n'est pas premier")
