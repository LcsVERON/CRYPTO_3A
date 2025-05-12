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
    
    grand_pas = h
    for k in range(t):
        if grand_pas in petits_pas:
            return k * t + petits_pas[grand_pas]
        grand_pas = (grand_pas * g_t_inv) % p
    return None

# ------------------------- TESTS -------------------------

# Test 1 : cas classique
p = 13291  # p est premier
if est_premier(p):
    g = trouve_generateurs(p)[0]  # premier générateur trouvé
    h = 5
    x = baby_step_giant_step(g, h, p)
    print(f"[Test 1] Log_g({h}) mod {p} = {x}")
else:
    print("[Test 1] p n'est pas premier")

# Test 2 : petit corps fini
p = 17  # petit nombre premier
if est_premier(p):
    generateurs = trouve_generateurs(p)
    print(f"[Test 2] Générateurs de F_{p}* : {generateurs}")
    g = generateurs[0]
    h = 9
    x = baby_step_giant_step(g, h, p)
    print(f"[Test 2] Log_g({h}) mod {p} = {x}")
else:
    print("[Test 2] p n'est pas premier")

# Test 3 : cas limite, p n'est pas premier
p = 15
if est_premier(p):
    g = trouve_generateurs(p)[0]
    h = 4
    x = baby_step_giant_step(g, h, p)
    print(f"[Test 3] Log_g({h}) mod {p} = {x}")
else:
    print("[Test 3] ERREUR : p n'est pas premier, algorithme invalide.")

# Test 4 : h = 1 (log_g(1) = 0 toujours si g^0 ≡ 1)
p = 101
g = trouve_generateurs(p)[0]
h = 1
x = baby_step_giant_step(g, h, p)
print(f"[Test 4] Log_g(1) mod {p} = {x} (doit être 0)")

# Test 5 : h = g (log_g(g) = 1)
h = g
x = baby_step_giant_step(g, h, p)
print(f"[Test 5] Log_g(g) mod {p} = {x} (doit être 1)")

# Test 6 : h non dans le sous-groupe généré
# Ici, on va volontairement prendre un g qui **n'est pas générateur** et tenter de résoudre log_g(h)
p = 101
g = 10  # pas un générateur en général
if est_generateur(g, p):
    h = 5
    x = baby_step_giant_step(g, h, p)
    print(f"[Test 6] Log_{g}({h}) mod {p} = {x}")
else:
    print(f"[Test 6] {g} n'est pas un générateur de F_{p}*, donc le log peut ne pas exister ou être incomplet.")

# Test 7 : grand nombre premier (vérification performance sur taille raisonnable)
p = 104729  # 10000ème nombre premier
if est_premier(p):
    g = trouve_generateurs(p)[0]
    h = 67890
    x = baby_step_giant_step(g, h, p)
    print(f"[Test 7] Log_g({h}) mod {p} = {x}")
else:
    print("[Test 7] p n'est pas premier")
