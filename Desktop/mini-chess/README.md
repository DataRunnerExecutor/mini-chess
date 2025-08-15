# ♟️ Mini Jeu d'Échecs (console, Python) - Joueur ( équipe blanche ) VS Joueur ( équipe noire ). Pas de Bot.

Un jeu d’échecs minimaliste en ligne de commande, écrit en Python, avec gestion des coups spéciaux et sauvegarde de partie.
Coups légaux, détection d'échec/échec et mat/pat.
**promotion automatique en dame**, **roque** et **prise en passant**.

---

## 🎯 Objectif

Le but est de mater le roi adverse (le mettre en **échec et mat**) en respectant les règles officielles des échecs.

---

### Déplacements des pièces

K = ♔  (roi blanc) : 1 case dans toutes les directions.
k = ♚  (roi noir)
Q = ♕  (dame blanche) : lignes + colonnes + diagonales.
q = ♛  (dame noire)
R = ♖  (tour blanche) : se déplace sur lignes ou colonnes.
r = ♜  (tour noire)
B = ♗  (fou blanc) : se déplace sur diagonales.
b = ♝  (fou noir)
N = ♘  (cavalier blanc) : mouvement en “L”, peut sauter les pièces.
n = ♞  (cavalier noir)
P = ♙  (pion blanc) : avance d’1 case (ou 2 depuis la case initiale), capture en diagonale.
p = ♟  (pion noir)

---

## ⌨️ Commandes

- `e2e4` : jouer un coup (notation type “deux coordonnées”)
- `moves e2` : afficher les coups légaux depuis e2
- `save [fichier]` : sauvegarder la partie (par défaut `game.json`)
- `load [fichier]` : charger une partie (par défaut `game.json`)
- `help` : rappel des commandes
- `quit` : quitter le jeu

---

### Roque

- **Blancs** : petit roque `e1g1`, grand roque `e1c1`
- **Noirs** : petit roque `e8g8`, grand roque `e8c8`
- **Conditions** :
  - Ni le roi ni la tour concernée n’ont déjà bougé.
  - Les cases entre eux sont libres.
  - Le roi ne passe pas et n’arrive pas sur une case attaquée.

---

### Prise en passant

Après un double pas d’un pion adverse atterrissant à côté du vôtre, vous pouvez capturer comme s’il n’avait avancé que d’1 case.

---

### Promotion

Quand un pion atteint la dernière rangée, le jeu demande : Promotion (q=♛, r=♜, b=♝, n=♞) [q]
Entrée seule = Dame par défaut.

---

### 🏁 Fins de partie

- **Échec et mat** : le roi est attaqué et aucun coup ne le sauve.
- **Pat** : aucun coup légal, pas d’échec → partie nulle.
- **Règle des 50 coups** : nulle automatique après 100 demi-coups sans capture ni coup de pion.
- **Trois répétitions** : nulle automatique à la 3e occurrence d’une même position (mêmes pièces, emplacements, droits de roque et en passant identiques).

---

## 📦 Installation

Cloner le dépôt :
```bash
git clone https://github.com/<ton-utilisateur>/mini-chess.git
cd mini-chess
