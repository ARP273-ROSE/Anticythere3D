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

#: position (x, y) de chaque arbre, en mm — résultat de l'optimisation
ARBORS = {
    "K": (48.170, -8.712),      # second axe du tenon-fente (décalé de eps)
    "a": (135.500, 0.000),      # manivelle
    "b": (0.000, 0.000),        # grande roue motrice
    "c": (50.116, -9.455),
    "d": (82.947, -24.224),
    "e": (3.806, -31.773),      # 6 roues, 3 vitesses -> tubes coaxiaux
    "f": (111.192, 22.893),
    "g": (70.371, 13.014),
    "h": (55.649, -24.178),
    "i": (68.257, 11.138),
    "k": (47.133, -6.817),
    "l": (40.978, 30.361),
    "m": (115.270, 24.802),
    "n": (83.558, 12.540),
    "o": (59.384, 13.179),
    "p": (68.277, -21.706),
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

# --- cadran arrière : où sont réellement les centres des deux spirales -----
#: côté de la texture du dos, en mm
BACK_DIAL_SPAN = 250.0
#: positions dans la texture, en fraction de son côté (cf. dialface)
_METONIC_FY, _SAROS_FY = 0.30, 0.72
#: rayons extérieurs des deux spirales, en fraction du côté
_METONIC_FR, _SAROS_FR = 0.20, 0.185

#: y de l'image va vers le bas, y de la scène vers le haut : d'où le signe.
METONIC_CENTER = (CASE_CX, CASE_CY + BACK_DIAL_SPAN * (0.5 - _METONIC_FY))
SAROS_CENTER = (CASE_CX, CASE_CY + BACK_DIAL_SPAN * (0.5 - _SAROS_FY))
METONIC_RADIUS = BACK_DIAL_SPAN * _METONIC_FR
SAROS_RADIUS = BACK_DIAL_SPAN * _SAROS_FR
