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

import math

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
    # o PORTE L'AIGUILLE CALLIPPIQUE. Il était en (17,938 ; 12,624), à
    # 22,08 mm de i : prolongé jusqu'au cadran, il traversait i1 (60 dents,
    # rayon de tête 31 mm). o est une feuille du train (il n'engrène que p2) :
    # on l'a fait tourner sur son cercle d'entraxe autour de p (36 mm, exact)
    # jusqu'à 165°, du côté de la spirale métonique, comme sur l'original où
    # le cadran callippique est dans la moitié haute et celui de l'exeligmos
    # dans la moitié basse (côté Saros). Il est désormais à 50,4 mm de i.
    "o": (13.6707, 41.0575),
    "p": (48.444, 31.740),
}

#: étage de chaque roue. Deux roues d'un même étage sont dans le même plan
#: et s'engrènent ; deux roues d'un même arbre sont à des hauteurs différentes.
LEVELS = {
    "a1": 1, "b1": 1,
    "b2": 2, "c1": 2, "l1": 2,
    "c2": 3, "d1": 3,
    "d2": 4, "e2": 4,
    "b3": 5, "e1": 5,
    "l2": 6, "m1": 6,
    "m2": 7, "n1": 7,
    # Le tenon-fente : k1/k2 tournent AVEC le porte-satellite e3, sur un
    # cercle de 50 mm autour de e. Aux étages 5 et 6 (jusqu'en v1.3.0) ils
    # balayaient les arbres b (étages 1 à 7) et l (2 à 8) — le test ne
    # regardait que la position de départ du porte-satellite. Ils passent
    # juste devant e3, qui les porte (arbres k et K prolongés jusqu'à lui,
    # cf. CARRIED_BY). e6 devant e5 : le tube e1-e6 (étages 5 à 8) s'emboîte
    # dans le tube e2-e5 (4 à 9), et e3-e4 (10-11) vient derrière.
    "e6": 8, "k2": 8,
    "e5": 9, "k1": 9,
    "e3": 10, "m3": 10,
    "e4": 11, "f1": 11,
    # Train callippique derrière e3/e4 : l'arbre o, prolongé jusqu'à son
    # cadran, ne traverse plus le porte-satellite (roue à bras qui TOURNE).
    "n2": 12, "p1": 12,
    "o1": 13, "p2": 13,
    "f2": 14, "g1": 14,
    "g2": 15, "h1": 15,
    "h2": 16, "i1": 16,
}

N_LEVELS = 16

#: roues à bras (évidées) — b1 est attestée avec 4 bras. Une roue à bras
#: TOURNE : ses bras balaieraient un arbre fixe qui la traverserait. Aucun
#: arbre ne passe donc par une roue à bras, sauf ceux qu'elle porte.
SPOKED = {"b1": 4, "e3": 4, "e4": 4}

#: arbres portés par une roue (et non par la platine) : ils tournent avec
#: elle. k et K (tenon-fente) sont montés sur le porte-satellite e3.
CARRIED_BY = {"k": "e3", "K": "e3"}
#: arbres prolongés jusqu'à la roue qui les porte. k (k1, étage 9) touche
#: e3 (étage 10). K (k2, étage 8), décalé de 2,2 mm seulement, ne peut pas
#: traverser k1 : il est tenu par une petite potence sur e3, non dessinée.
MOUNTED_ON = {"k": "e3"}

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

#: Palette des sous-ensembles, pour fond CLAIR (parchemin) et rendu vectoriel.
#:
#: Choisie par le calcul (`anticythere/palette.py`), pas à l'œil : l'ancienne
#: palette (bronze, argent bleuté, bleu, vert, prune, bleu-violet…) faisait
#: se confondre le métonique, l'exeligmos et le Saros, et devenait illisible
#: pour un daltonien. Contraintes vérifiées par `tests/test_mechanism.py` :
#:
#: * écart CIEDE2000 ≥ 20 entre TOUS les sous-ensembles (vision normale) ;
#: * en deutéranopie et en protanopie simulées (Machado 2009), ≥ 15 entre
#:   sous-ensembles qui s'engrènent, ≥ 10 entre tous ;
#: * contraste WCAG ≥ 3 sur le fond parchemin, pour que le trait se lise.
COLORS = {
    "input":     (0.871, 0.412, 0.063, 1.0),   # #DE6910 orange — entrée
    "moon":      (0.051, 0.349, 0.757, 1.0),   # #0D59C1 bleu — Lune
    "anomaly":   (0.557, 0.090, 0.000, 1.0),   # #8E1700 rouge sang — tenon-fente
    "metonic":   (0.114, 0.584, 0.580, 1.0),   # #1D9594 bleu-vert — métonique
    "callippic": (0.471, 0.435, 0.298, 1.0),   # #786F4C kaki — callippique
    "saros":     (0.518, 0.098, 0.349, 1.0),   # #841959 framboise — Saros
    "exeligmos": (0.714, 0.424, 0.804, 1.0),   # #B66CCD lilas — exeligmos
    "arbor":     (0.28, 0.28, 0.30, 1.0),
    "plate":     (0.55, 0.45, 0.28, 0.30),
    "case":      (0.45, 0.34, 0.20, 0.30),
    "pointer":   (0.55, 0.16, 0.10, 1.0),
    "dial":      (0.66, 0.58, 0.36, 0.90),
}

#: paires de sous-ensembles qui s'engrènent ou partagent un arbre : ce sont
#: elles qu'il faut distinguer d'abord, puisqu'elles se touchent à l'écran
NEIGHBOURS = [("input", "moon"), ("input", "metonic"), ("moon", "anomaly"),
              ("anomaly", "saros"), ("metonic", "saros"),
              ("metonic", "callippic"), ("saros", "exeligmos"),
              ("moon", "saros")]

#: fond clair « parchemin » de la scène 3D et du rendu vectoriel
BACKGROUND = (0.961, 0.941, 0.902)          # #F5F0E6
INK = (0.16, 0.16, 0.18)                    # trait d'encre

SUBSYSTEM_OF = {g: s for s, gears in SUBSYSTEMS.items() for g in gears}


#: écart SUPPLÉMENTAIRE entre deux étages consécutifs à éclatement 100 %, en mm
EXPLODE_GAP = 12.0


def level_pitch(explode: float = 0.0) -> float:
    """Pas entre deux étages : 3,4 mm machine montée, jusqu'à 15,4 mm éclatée."""
    return LEVEL_PITCH + max(0.0, min(1.0, explode)) * EXPLODE_GAP


def level_z(level: int, explode: float = 0.0) -> float:
    """Hauteur (mm) du plan d'un étage. L'étage 1 (b1) est à l'avant.

    L'éclatement ne fait qu'ÉTIRER la pile le long des arbres : le fond
    (étage 16) reste en place, chaque étage s'éloigne de son voisin d'autant,
    et l'ordre des étages ne change jamais. L'ancienne formule ajoutait un
    décalage de sens contraire au pas des étages : vers 57 % les 16 plans se
    retrouvaient confondus, puis s'inversaient — les roues se rentraient
    dedans.
    """
    return (N_LEVELS - level) * level_pitch(explode)


def front_shift(explode: float = 0.0) -> float:
    """De combien la façade avance quand on éclate la machine (mm)."""
    return level_z(1, explode) - level_z(1, 0.0)


def gear_position(name: str, explode: float = 0.0) -> tuple[float, float, float]:
    x, y = ARBORS[ARBOR_OF[name]]
    return x, y, level_z(LEVELS[name], explode)


def orbit(x: float, y: float, carrier_turns: float) -> tuple[float, float]:
    """Position d'un point porté par le porte-satellite e3 (axes k et K)."""
    ex, ey = ARBORS["e"]
    a = 2.0 * math.pi * carrier_turns
    dx, dy = x - ex, y - ey
    c, s = math.cos(a), math.sin(a)
    return ex + c * dx - s * dy, ey + s * dx + c * dy


def gear_placement(name: str, explode: float = 0.0,
                   carrier_turns: float = 0.0) -> tuple[float, float, float]:
    """Où se trouve une roue : (x, y) dans son plan, z le long des arbres.

    (x, y) ne dépend QUE du porte-satellite, jamais de l'éclatement : c'est
    l'invariant que vérifie le test d'éclatement.
    """
    x, y, z = gear_position(name, explode)
    if ARBOR_OF[name] in ("k", "K"):
        x, y = orbit(x, y, carrier_turns)
    return x, y, z


def arbor_position(arbor: str, carrier_turns: float = 0.0) -> tuple[float, float]:
    """Position (x, y) d'un arbre ; k et K suivent le porte-satellite."""
    x, y = ARBORS[arbor]
    if arbor in CARRIED_BY:
        x, y = orbit(x, y, carrier_turns)
    return x, y


def arbor_extent(arbor: str, explode: float = 0.0) -> tuple[float, float]:
    """Plage de hauteurs (z_min, z_max) occupée par un arbre."""
    zs = [level_z(LEVELS[g], explode) for g, a in ARBOR_OF.items() if a == arbor]
    stub = arbor_stub(explode)
    return min(zs) - stub, max(zs) + GEAR_THICKNESS + stub


def arbor_stub(explode: float = 0.0) -> float:
    """Dépassement d'un arbre au-delà de ses roues extrêmes, en mm.

    Il doit rester inférieur au jeu entre deux étages (0,8 mm machine
    montée) : à 3 mm, le bout d'arbre entrait dans la roue de l'étage voisin
    (c dans d2, n dans m1). Il croît avec l'éclatement, moins vite que le jeu.
    """
    e = max(0.0, min(1.0, explode))
    return 0.6 + 0.4 * e * EXPLODE_GAP


#: arbres qui traversent jusqu'à un cadran : ils portent les aiguilles
BACK_DIAL_ARBORS = ("n", "g", "o", "i")
FRONT_DIAL_ARBORS = ("b",)


def arbor_span(arbor: str, explode: float = 0.0) -> tuple[float, float]:
    """Longueur DESSINÉE d'un arbre : ses roues, plus le prolongement jusqu'à
    son cadran pour ceux qui portent une aiguille (fin de la lévitation).

    Le dos (étage 16) ne bouge pas à l'éclatement ; la façade avance avec
    l'étage 1, et l'arbre b, qui porte les aiguilles de devant, s'allonge
    d'autant.
    """
    z0, z1 = arbor_extent(arbor, explode)
    if arbor in MOUNTED_ON:                 # rejoint la roue qui le porte
        zc = level_z(LEVELS[MOUNTED_ON[arbor]], explode)
        z0, z1 = min(z0, zc), max(z1, zc + GEAR_THICKNESS)
    if arbor in BACK_DIAL_ARBORS:
        z0 = level_z(N_LEVELS) - 8.0 - 12.0
    if arbor in FRONT_DIAL_ARBORS:
        z1 = level_z(1, explode) + 8.0 + 9.0
    return z0, z1


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


def center(explode: float = 0.0) -> tuple[float, float, float]:
    """Centre de la scène : il recule avec la façade quand on éclate."""
    return CASE_CX, CASE_CY, CASE_DEPTH / 2.0 + front_shift(explode) / 2.0


# --- manivelle ---------------------------------------------------------------
#: géométrie de la manivelle (cf. geometry.crank_mesh) : arbre, bras, poignée
CRANK_SHAFT = 34.0
CRANK_ARM = 26.0
CRANK_HANDLE = 20.0
#: rayon de la poignée autour de l'axe de a1
CRANK_RADIUS = CRANK_ARM - 4.0
#: tours de manivelle (roue a1) par tour de b1 = 223/48, de sens contraire
CRANK_PER_TURN = -223.0 / 48.0

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
#: arbres o et i, alors distants de seulement 22,08 mm : à 13 et 12 mm ils se
#: chevauchaient de 2,92 mm (depuis la v1.3.1, o est à 50,4 mm de i). Calcul dans `anticythere_cadrans2.sage`, 3 mm de
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
