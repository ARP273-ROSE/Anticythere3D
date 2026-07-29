"""
Implantation physique de la machine : position de chaque arbre dans le plan,
étage (hauteur) de chaque roue, épaisseurs, couleurs.

Physical layout: position of every arbor, level (height) of every gear.

Les coordonnées des 15 arbres ne sont pas dessinées à la main : elles sont le
résultat d'une **optimisation sous contraintes** (SageMath + scipy), qui impose
simultanément :

* les 17 entraxes exacts  a = m (N1 + N2) / 2  — obtenus à 0,1 µm près ;
* la fermeture des deux boucles cinématiques (b-c-d-e et b-l-m-e) ;
* qu'aucun arbre ne traverse une roue pleine, en tenant compte du fait que
  b1, e3 et e4 sont des roues **à bras** (donc évidées) et qu'un arbre
  n'occupe que la plage de hauteurs de ses propres roues ;
* qu'aucune paire de roues d'un même étage ne se recouvre.

Script : ``anticythere_implantation.sage``.
"""

from __future__ import annotations

MODULE = 1.0                 # mm — module retenu (b1 = 223 mm de diamètre)
GEAR_THICKNESS = 2.6         # mm
LEVEL_PITCH = 3.4            # mm entre deux étages (roue + jeu)
ARBOR_RADIUS = 2.0           # mm

#: position (x, y) de chaque arbre, en mm — résultat de l'optimisation, AVEC
#: la contrainte mécanique des cadrans : l'aiguille métonique est portée par
#: l'arbre n et celle du Saros par g, donc n et g sont GELÉS aux centres des
#: deux spirales (80, ±52), alignés verticalement comme sur l'original.
#: Entraxes exacts à 0,4 µm, aucune collision (implantation7.out).
ARBORS = {
    "K": (8.795, -30.198),      # second axe du tenon-fente (décalé de eps)
    "a": (135.500, 0.000),      # manivelle
    "b": (0.000, 0.000),        # grande roue motrice
    "c": (33.423, -38.521),
    "d": (12.022, -67.469),
    "e": (-31.976, -1.254),     # 6 roues, 3 vitesses -> tubes coaxiaux
    "f": (88.145, -10.797),
    "g": (80.000, -52.000),     # PORTE L'AIGUILLE DU SAROS
    "h": (46.569, -30.036),
    "i": (15.326, -9.297),
    "k": (10.007, -28.410),
    "l": (21.528, 46.234),
    "m": (91.220, 19.905),
    "n": (80.000, 52.000),      # PORTE L'AIGUILLE MÉTONIQUE
    "o": (17.938, 12.624),
    "p": (48.444, 31.740),
}

#: étage de chaque roue. Deux roues d'un même étage sont dans le même plan
#: et s'engrènent ; deux roues d'un même arbre sont à des hauteurs différentes.
LEVELS = {
    "a1": 1, "b1": 1,
    "b2": 2, "c1": 2, "l1": 2,
    "c2": 3, "d1": 3,
    "d2": 4, "e2": 4,
    "e5": 5, "k1": 5,
    "e6": 6, "k2": 6,
    "b3": 7, "e1": 7,
    "l2": 8, "m1": 8,
    "m2": 9, "n1": 9,
    "n2": 10, "p1": 10,
    "o1": 11, "p2": 11,
    "e3": 12, "m3": 12,
    "e4": 13, "f1": 13,
    "f2": 14, "g1": 14,
    "g2": 15, "h1": 15,
    "h2": 16, "i1": 16,
}

N_LEVELS = 16

#: roues à bras (évidées) — b1 est attestée avec 4 bras
SPOKED = {"b1": 4, "e3": 4, "e4": 4}

#: arbre porteur de chaque roue
ARBOR_OF = {
    "a1": "a", "b1": "b", "b2": "b", "b3": "b",
    "c1": "c", "c2": "c", "d1": "d", "d2": "d",
    "e1": "e", "e2": "e", "e3": "e", "e4": "e", "e5": "e", "e6": "e",
    "f1": "f", "f2": "f", "g1": "g", "g2": "g",
    "h1": "h", "h2": "h", "i1": "i",
    "k1": "k", "k2": "K",
    "l1": "l", "l2": "l", "m1": "m", "m2": "m", "m3": "m",
    "n1": "n", "n2": "n", "o1": "o", "p1": "p", "p2": "p",
}

#: sous-ensemble fonctionnel -> couleur RGBA (rendu 3D)
SUBSYSTEMS = {
    "input":     ("b1", "b2", "a1"),
    "moon":      ("c1", "c2", "d1", "d2", "e2", "e5", "e6", "e1", "b3"),
    "anomaly":   ("k1", "k2", "e3", "e4"),
    "metonic":   ("l1", "l2", "m1", "m2", "n1"),
    "callippic": ("n2", "p1", "p2", "o1"),
    "saros":     ("m3", "f1", "f2", "g1"),
    "exeligmos": ("g2", "h1", "h2", "i1"),
}

#: palette pour fond CLAIR (parchemin) — teintes soutenues, lisibles sur ivoire
COLORS = {
    "input":     (0.72, 0.53, 0.04, 1.0),   # bronze doré
    "moon":      (0.42, 0.48, 0.56, 1.0),   # argent bleuté
    "anomaly":   (0.69, 0.23, 0.18, 1.0),   # rouge brique
    "metonic":   (0.12, 0.38, 0.55, 1.0),   # bleu
    "callippic": (0.10, 0.44, 0.24, 1.0),   # vert
    "saros":     (0.49, 0.24, 0.60, 1.0),   # prune
    "exeligmos": (0.29, 0.34, 0.62, 1.0),   # bleu-violet
    "arbor":     (0.28, 0.28, 0.30, 1.0),
    "plate":     (0.55, 0.45, 0.28, 0.30),
    "case":      (0.45, 0.34, 0.20, 0.30),
    "pointer":   (0.55, 0.16, 0.10, 1.0),
    "dial":      (0.66, 0.58, 0.36, 0.90),
}

#: fond clair « parchemin » de la scène 3D et du rendu vectoriel
BACKGROUND = (0.961, 0.941, 0.902)          # #F5F0E6
INK = (0.16, 0.16, 0.18)                    # trait d'encre

SUBSYSTEM_OF = {g: s for s, gears in SUBSYSTEMS.items() for g in gears}


def level_z(level: int) -> float:
    """Hauteur (mm) du plan d'un étage. L'étage 1 (b1) est à l'avant."""
    return (N_LEVELS - level) * LEVEL_PITCH


def gear_position(name: str) -> tuple[float, float, float]:
    x, y = ARBORS[ARBOR_OF[name]]
    return x, y, level_z(LEVELS[name])


def arbor_extent(arbor: str) -> tuple[float, float]:
    """Plage de hauteurs (z_min, z_max) occupée par un arbre."""
    zs = [level_z(LEVELS[g]) for g, a in ARBOR_OF.items() if a == arbor]
    return min(zs) - 3.0, max(zs) + GEAR_THICKNESS + 3.0


#: rayons extérieurs des deux spirales du dos, en mm (définis avant
#: l'emprise : les cadrans en font partie)
METONIC_RADIUS = 50.0
SAROS_RADIUS = 46.25


def mechanism_extent(margin: float = 14.0) -> tuple[float, float, float, float]:
    """Emprise réelle du mécanisme : (x_min, x_max, y_min, y_max).

    Mesurée sur les rayons de tête de toutes les roues, plus la manivelle.
    Le boîtier en découle — le calculer à la main, c'est se retrouver avec
    une grande roue qui dépasse.
    """
    from .kinematics import TEETH

    xs, ys = [], []
    for gear in LEVELS:
        x, y = ARBORS[ARBOR_OF[gear]]
        r = MODULE * (TEETH[gear] / 2.0 + 1.0)
        xs += [x - r, x + r]
        ys += [y - r, y + r]
    ax, ay = ARBORS["a"]                       # la manivelle sort du flanc
    xs += [ax + 30.0]
    ys += [ay - 20.0, ay + 20.0]
    # les spirales des cadrans arrière, centrées sur leurs arbres n et g
    for arbor, rad in (("n", METONIC_RADIUS), ("g", SAROS_RADIUS)):
        x, y = ARBORS[arbor]
        xs += [x - rad, x + rad]
        ys += [y - rad, y + rad]
    return (min(xs) - margin, max(xs) + margin,
            min(ys) - margin, max(ys) + margin)


_X0, _X1, _Y0, _Y1 = mechanism_extent()
CASE_WIDTH = _X1 - _X0
CASE_HEIGHT = _Y1 - _Y0
CASE_CX = (_X0 + _X1) / 2.0
CASE_CY = (_Y0 + _Y1) / 2.0
CASE_DEPTH = (N_LEVELS + 1) * LEVEL_PITCH

#: centre géométrique, pour recentrer la caméra
CENTER = (CASE_CX, CASE_CY, CASE_DEPTH / 2.0)

# --- cadrans : géométrie calculée, pas ajustée à l'œil ---------------------
# Tout ce bloc sort de `anticythere_cadrans.sage`, qui vérifie que chaque
# anneau, chaque spirale et chaque aiguille tombe au bon endroit et que rien
# ne déborde du boîtier.

#: le cadran avant est centré sur l'arbre b, en (0, 0), alors que le boîtier
#: est centré ailleurs : son rayon est donc limité par le bord le plus proche
FRONT_DIAL_SPAN = 244.0
#: rayons des anneaux, en fraction du rayon du cadran (cf. dialface)
_ZOD_IN_F, _ZOD_OUT_F = 0.63, 0.825
#: l'aiguille du Soleil doit pointer DANS l'anneau du zodiaque, pas au-delà
SUN_HAND = FRONT_DIAL_SPAN / 2.0 * _ZOD_OUT_F - 3.0          # 97,7 mm
MOON_HAND = FRONT_DIAL_SPAN / 2.0 * (_ZOD_IN_F + _ZOD_OUT_F) / 2.0   # 88,8 mm

#: Côté de la texture du dos, en mm. Elle est carrée et doit couvrir tout le
#: boîtier : à 300 mm elle était plus étroite que les 338 mm de la plaque, qui
#: se trouvait donc rognée à gauche et à droite. On la cale sur la plus grande
#: dimension du boîtier, plus une marge.
BACK_DIAL_SPAN = max(CASE_WIDTH, CASE_HEIGHT) + 12.0

#: rayons des deux petits cadrans arrière, en mm. Ils sont portés par les
#: arbres o et i, distants de seulement 22,08 mm : à 13 et 12 mm ils se
#: chevauchaient de 2,92 mm. Calcul dans `anticythere_cadrans2.sage`, 3 mm de
#: jeu conservés entre les deux.
CALLIPPIC_RADIUS = 9.9
EXELIGMOS_RADIUS = 9.2

#: Le cadran des Jeux n'est porté par aucun arbre modélisé : sa position est
#: libre. Il était posé sur la spirale du Saros ; il rejoint la zone vraiment
#: vide de la plaque, du côté de la grande roue b1.
GAMES_CENTER = (-70.0, 0.0)

#: anneaux du Cosmos de la face avant (modèle Freeth 2021 : les planètes en
#: anneaux concentriques marqués d'une petite sphère). Rayon en mm ; ils
#: doivent rester sous l'anneau du zodiaque (r intérieur 77).
COSMOS_RINGS = [
    ("moon", 26.0, (0.75, 0.78, 0.84, 1.0)),
    ("mercury", 34.0, (0.55, 0.48, 0.42, 1.0)),
    ("venus", 42.0, (0.90, 0.83, 0.62, 1.0)),
    ("sun", 50.0, (1.00, 0.80, 0.25, 1.0)),
    ("mars", 58.0, (0.78, 0.32, 0.20, 1.0)),
    ("jupiter", 65.0, (0.85, 0.76, 0.62, 1.0)),
    ("saturn", 72.0, (0.72, 0.62, 0.38, 1.0)),
]

# Les centres des cadrans arrière SONT les arbres qui portent leurs
# aiguilles : c'est la contrainte imposée à l'implantation. Plus aucune
# position de cadran n'est indépendante de la mécanique.
METONIC_CENTER = ARBORS["n"]
SAROS_CENTER = ARBORS["g"]
