## Question 5:
Nous avons choisi de représenter le circuit sous forme de graphe, avec n entrées et n sorties pour Alice et Bob, et donnant pour chaque sortie le bit du maximum entre les deux entiers comparés.
Les détails de la construction du graphe se trouvent dans la fonction generate_max_min_circuit(n) au sein du fichier circuit.py, accompagnée de commentaires détaillés.
Les test et exemples se trouvent au sein du dossier test, dans le fichier test_max.py .

## Question 6:
Le fichier test_circuit.py contient le test exhaustif. Les détails du code sont dans le fichier circuit.py .

## Question 7:
Les détails de la strcuture de la machine virtuelle se trouvent dans le fichier mv.py . Il en est de même pour la fonction de compilation.
Concernant les test, malheureusement nous ne sommes pas parvenus à une version concluante. Les test ne passent pas car il y a sûrement une erreur dans la compréhension du sujet, ce qui provoque des calculs de variables faussés, qui donnent une sortie erronée.