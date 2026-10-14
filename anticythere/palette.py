"""
Science des couleurs, sans dépendance : écart CIEDE2000, contraste WCAG et
simulation des daltonismes (Machado, Oliveira & Fernandes 2009, sévérité 1).

Colour science with no dependency: CIEDE2000 difference, WCAG contrast and
colour-vision-deficiency simulation (Machado et al. 2009, full severity).

Sert à choisir puis à vérifier la palette des sous-ensembles (`layout.COLORS`) :
deux trains voisins doivent rester distincts pour tout le monde, y compris
pour les ~8 % d'hommes qui confondent le rouge et le vert.
"""

from __future__ import annotations

import math

# Matrices de Machado et al. (2009), sévérité 1,0, appliquées en sRGB LINÉAIRE.
CVD = {
    "protan": ((0.152286, 1.052583, -0.204868),
               (0.114503, 0.786281, 0.099216),
               (-0.003882, -0.048116, 1.051998)),
    "deutan": ((0.367322, 0.860646, -0.227968),
               (0.280085, 0.672501, 0.047413),
               (-0.011820, 0.042940, 0.968881)),
    "tritan": ((1.255528, -0.076749, -0.178779),
               (-0.078411, 0.930809, 0.147602),
               (0.004733, 0.691367, 0.303900)),
}


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c: float) -> float:
    c = min(1.0, max(0.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def hex_to_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def rgb_to_hex(rgb) -> str:
    return "#" + "".join(f"{round(min(1, max(0, c)) * 255):02X}" for c in rgb[:3])


def simulate(rgb, kind: str):
    """Couleur perçue par un dichromate (`protan`, `deutan`, `tritan`)."""
    m = CVD[kind]
    lin = [_lin(c) for c in rgb[:3]]
    return tuple(_gam(sum(m[i][j] * lin[j] for j in range(3))) for i in range(3))


def rgb_to_lab(rgb):
    r, g, b = (_lin(c) for c in rgb[:3])
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = (0.2126729 * r + 0.7151522 * g + 0.0721750 * b)
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > (6 / 29) ** 3 else t / (3 * (6 / 29) ** 2) + 4 / 29
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def ciede2000(lab1, lab2) -> float:
    """Écart de couleur CIEDE2000 (Sharma, Wu & Dalal 2005)."""
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dLp = L2 - L1
    dCp = C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    else:
        dhp = h2p - h1p
        if dhp > 180:
            dhp -= 360
        elif dhp < -180:
            dhp += 360
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2))
    Lpm = (L1 + L2) / 2
    Cpm = (C1p + C2p) / 2
    if C1p * C2p == 0:
        hpm = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hpm = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        hpm = (h1p + h2p + 360) / 2
    else:
        hpm = (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hpm - 30))
         + 0.24 * math.cos(math.radians(2 * hpm))
         + 0.32 * math.cos(math.radians(3 * hpm + 6))
         - 0.20 * math.cos(math.radians(4 * hpm - 63)))
    dtheta = 30 * math.exp(-(((hpm - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cpm ** 7 / (Cpm ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lpm - 50) ** 2 / math.sqrt(20 + (Lpm - 50) ** 2)
    Sc = 1 + 0.045 * Cpm
    Sh = 1 + 0.015 * Cpm * T
    Rt = -math.sin(math.radians(2 * dtheta)) * Rc
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2
                     + Rt * (dCp / Sc) * (dHp / Sh))


def delta_e(rgb1, rgb2, vision: str = "normal") -> float:
    """ΔE00 entre deux couleurs sRGB (0..1), telles que les voit `vision`."""
    if vision != "normal":
        rgb1, rgb2 = simulate(rgb1, vision), simulate(rgb2, vision)
    return ciede2000(rgb_to_lab(rgb1), rgb_to_lab(rgb2))


def luminance(rgb) -> float:
    r, g, b = (_lin(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(rgb1, rgb2) -> float:
    """Rapport de contraste WCAG 2 (1 à 21)."""
    l1, l2 = sorted((luminance(rgb1), luminance(rgb2)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)
