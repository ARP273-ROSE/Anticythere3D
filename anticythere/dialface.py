"""
Cadrans gravés : les vraies inscriptions de la machine, sur les deux faces.

Engraved dials: the mechanism's actual inscriptions, on both faces.

Chaque cadran est décrit **une seule fois**, par une fonction ``paint_*`` qui
dessine sur n'importe quel ``QPainter``. Elle sert deux fois :

* pour fabriquer une **texture** appliquée sur la façade en 3D ;
* directement dans le **rendu vectoriel**, où les gravures restent donc nettes
  à tout zoom et s'exportent en SVG et en PDF sans devenir des pixels.

Sources des inscriptions
------------------------
* **Zodiaque** — les douze noms grecs sont attestés sur l'anneau du zodiaque,
  gravés avec des lettres-index renvoyant au parapegma. Noter ΧΗΛΑΙ (« les
  pinces » du Scorpion) là où nous disons Balance : c'est le nom grec ancien.
* **Calendrier** — l'anneau extérieur porte les mois égyptiens écrits en
  caractères grecs. Seuls quelques noms subsistent sur les fragments ; les
  douze sont restitués d'après les formes grecques usuelles d'Égypte.
* **Réserve honnête** — le nombre de divisions de l'anneau calendaire est
  discuté : la lecture traditionnelle donne 365 jours, une étude de 2024
  fondée sur la répartition des trous de fixation défend 354, soit une année
  **lunaire**. Le programme affiche 365 par défaut et sait faire les deux,
  sans trancher le débat.
* **Cadran des Jeux** — quatre secteurs, d'après Freeth *et al.* (2008).
"""

from __future__ import annotations

import math

from PyQt6 import QtCore, QtGui

# --------------------------------------------------------------- inscriptions
#: les douze signes, en grec, à partir du point vernal
ZODIAC_GREEK = [
    ("ΚΡΙΟΣ", "Bélier", "Aries"),
    ("ΤΑΥΡΟΣ", "Taureau", "Taurus"),
    ("ΔΙΔΥΜΟΙ", "Gémeaux", "Gemini"),
    ("ΚΑΡΚΙΝΟΣ", "Cancer", "Cancer"),
    ("ΛΕΩΝ", "Lion", "Leo"),
    ("ΠΑΡΘΕΝΟΣ", "Vierge", "Virgo"),
    ("ΧΗΛΑΙ", "Balance", "Libra"),
    ("ΣΚΟΡΠΙΟΣ", "Scorpion", "Scorpio"),
    ("ΤΟΞΟΤΗΣ", "Sagittaire", "Sagittarius"),
    ("ΑΙΓΟΚΕΡΩΣ", "Capricorne", "Capricorn"),
    ("ΥΔΡΟΧΟΟΣ", "Verseau", "Aquarius"),
    ("ΙΧΘΥΕΣ", "Poissons", "Pisces"),
]

#: mois égyptiens en caractères grecs, tels qu'écrits dans l'Égypte hellénistique
EGYPTIAN_GREEK = ["ΘΩΘ", "ΦΑΩΦΙ", "ΑΘΥΡ", "ΧΟΙΑΚ", "ΤΥΒΙ", "ΜΕΧΕΙΡ",
                  "ΦΑΜΕΝΩΘ", "ΦΑΡΜΟΥΘΙ", "ΠΑΧΩΝ", "ΠΑΥΝΙ", "ΕΠΙΦΙ", "ΜΕΣΟΡΗ"]

#: lettres-index du parapegma, gravées sur l'anneau du zodiaque
PARAPEGMA_LETTERS = "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"

#: jeux panhelléniques du cadran des Jeux
GAMES_GREEK = ["ΙΣΘΜΙΑ", "ΟΛΥΜΠΙΑ", "ΝΕΜΕΑ", "ΠΥΘΙΑ"]

#: les douze mois du calendrier corinthien, gravés case par case dans la
#: spirale métonique. Attestés sur les fragments (Freeth *et al.*, Nature 454,
#: 2008). La forme abrégée sert seule au rendu : une case du tour extérieur
#: fait 6,7 mm de large, un nom complet n'y tient pas — sur l'original les
#: lettres font 1,5 mm de haut, illisibles à l'écran.
CORINTHIAN_MONTHS = [
    ("ΦΟΙΝΙΚΑΙΟΣ", "ΦΟΙΝ"), ("ΚΡΑΝΕΙΟΣ", "ΚΡΑΝ"), ("ΛΑΝΟΤΡΟΠΙΟΣ", "ΛΑΝΟ"),
    ("ΜΑΧΑΝΕΥΣ", "ΜΑΧΑ"), ("ΔΩΔΕΚΑΤΕΥΣ", "ΔΩΔΕ"), ("ΕΥΚΛΕΙΟΣ", "ΕΥΚΛ"),
    ("ΑΡΤΕΜΙΣΙΟΣ", "ΑΡΤΕ"), ("ΨΥΔΡΕΥΣ", "ΨΥΔΡ"), ("ΓΑΜΕΙΛΙΟΣ", "ΓΑΜΕ"),
    ("ΑΓΡΙΑΝΙΟΣ", "ΑΓΡΙ"), ("ΠΑΝΑΜΟΣ", "ΠΑΝΑ"), ("ΑΠΕΛΛΑΙΟΣ", "ΑΠΕΛ"),
]

#: chiffres grecs 1 à 19, pour numéroter les années du cycle métonique
GREEK_NUMERALS = ["Α", "Β", "Γ", "Δ", "Ε", "Ϛ", "Ζ", "Η", "Θ", "Ι",
                  "ΙΑ", "ΙΒ", "ΙΓ", "ΙΔ", "ΙΕ", "ΙϚ", "ΙΖ", "ΙΗ", "ΙΘ"]

#: années embolismiques du cycle métonique (13 mois au lieu de 12). Le cycle
#: en compte exactement 7 : 235 = 19 × 12 + 7. Critère (12k) mod 19 < 7,
#: vérifié dans `anticythere_cadrans2.sage` — la somme retombe sur 235 pile.
EMBOLISMIC_YEARS = {2, 5, 8, 10, 13, 16, 19}


def metonic_year_starts() -> list[int]:
    """Numéro de mois (0-234) où commence chacune des 19 années."""
    out, mois = [], 0
    for k in range(1, 20):
        out.append(mois)
        mois += 13 if k in EMBOLISMIC_YEARS else 12
    assert mois == 235, mois
    return out


#: cases du Saros portant un glyphe d'éclipse — Η pour le Soleil (Ἥλιος),
#: Σ pour la Lune (Σελήνη), comme sur la plaque.
#:
#: ⚠️ **Reconstitué, pas copié.** Le motif de la plaque originale n'est connu
#: que par fragments. Celui-ci est *calculé* par le module `astro` du
#: programme — syzygie proche d'un nœud, exactement le critère que la machine
#: mécanise — sur les 223 mois d'un cycle de Saros à partir de janvier 2000.
#: Il donne 48 cases solaires et 32 lunaires, un peu plus que les glyphes
#: gravés : les limites retenues incluent des éclipses rasantes que le graveur
#: n'a pas notées.
SAROS_SOLAR = {0, 1, 6, 7, 12, 18, 24, 30, 36, 42, 47, 48, 53, 54, 59, 65,
               71, 77, 83, 88, 89, 95, 100, 106, 107, 112, 118, 124, 129,
               130, 136, 141, 147, 148, 153, 159, 165, 171, 177, 182, 183,
               188, 189, 194, 200, 206, 212, 218}
SAROS_LUNAR = {0, 6, 12, 18, 30, 35, 41, 47, 53, 59, 71, 76, 82, 88, 94,
               100, 106, 112, 123, 129, 135, 141, 147, 153, 159, 164, 176,
               182, 188, 194, 200, 217}

#: corrections de l'exeligmos : 0, 8 et 16 heures, en chiffres grecs
EXELIGMOS_LABELS = ["0", "Η", "ΙϚ"]

# ------------------------------------------------------------------ couleurs
BRONZE_LIGHT = QtGui.QColor(226, 200, 140)      # bronze poli, clair
BRONZE_MID = QtGui.QColor(198, 168, 106)
BRONZE_PALE = QtGui.QColor(236, 214, 160)
ENGRAVE = QtGui.QColor(74, 58, 30)              # trait gravé
ENGRAVE_SOFT = QtGui.QColor(116, 96, 56)
PATINA = QtGui.QColor(150, 170, 140, 24)        # patine verte, très discrète


def _ring_text(p: QtGui.QPainter, cx, cy, radius, angle_deg, text,
               font_px, color):
    """Écrit un texte le long d'un rayon, tourné pour suivre le cercle."""
    p.save()
    p.translate(cx, cy)
    # un texte est tête-bêche quand sa ROTATION EFFECTIVE (90 - angle)
    # dépasse ±90° — pas quand son angle polaire est dans la moitié basse :
    # ce raccourci retournait à tort tout le quadrant haut-gauche
    rot = (90.0 - angle_deg) % 360.0
    flipped = 90.0 < rot < 270.0
    p.rotate(-angle_deg + 90.0 + (180.0 if flipped else 0.0))
    f = p.font()
    f.setPixelSize(max(1, int(font_px)))
    f.setBold(True)
    p.setFont(f)
    p.setPen(color)
    fm = QtGui.QFontMetricsF(f)
    w = fm.horizontalAdvance(text)
    y = radius + font_px * 0.8 if flipped else -radius
    p.drawText(QtCore.QPointF(-w / 2.0, y), text)
    p.restore()


# ============================================================== FACE AVANT
def paint_front_dial(p: QtGui.QPainter, cx: float, cy: float, R: float,
                     calendar_days: int = 365, lang: str = "fr") -> None:
    """Anneau du zodiaque (360 divisions, 12 noms grecs) et anneau calendaire."""
    s = R / 0.485                        # échelle de référence du tracé
    r_cal_out, r_cal_in = R, R * 0.845
    r_zod_out, r_zod_in = R * 0.825, R * 0.63
    r_face = R * 0.61

    grad = QtGui.QRadialGradient(cx, cy - R * 0.2, R * 1.3)
    grad.setColorAt(0.0, QtGui.QColor(242, 222, 172))
    grad.setColorAt(0.65, BRONZE_LIGHT)
    grad.setColorAt(1.0, BRONZE_MID)
    p.setBrush(QtGui.QBrush(grad))
    p.setPen(QtGui.QPen(ENGRAVE_SOFT, s * 0.004))
    p.drawEllipse(QtCore.QPointF(cx, cy), R, R)

    # --- anneau calendaire : un trait par jour, douze mois nommés
    p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
    for r in (r_cal_in, r_cal_out):
        p.setPen(QtGui.QPen(ENGRAVE, s * 0.0035))
        p.drawEllipse(QtCore.QPointF(cx, cy), r, r)
    for i in range(calendar_days):
        a = math.radians(90.0 - 360.0 * i / calendar_days)
        long_tick = (i % 30 == 0)
        r0 = r_cal_in if long_tick else r_cal_out - (r_cal_out - r_cal_in) * 0.42
        p.setPen(QtGui.QPen(ENGRAVE if long_tick else ENGRAVE_SOFT,
                            s * (0.0022 if long_tick else 0.0011)))
        p.drawLine(QtCore.QPointF(cx + r0 * math.cos(a), cy - r0 * math.sin(a)),
                   QtCore.QPointF(cx + r_cal_out * math.cos(a),
                                  cy - r_cal_out * math.sin(a)))
    months = 12 if calendar_days >= 354 else max(1, calendar_days // 30)
    for i in range(months):
        a = 90.0 - 360.0 * (i + 0.5) * (calendar_days / 12.0) / calendar_days
        _ring_text(p, cx, cy, (r_cal_in + r_cal_out) / 2.0 - s * 0.006, a,
                   EGYPTIAN_GREEK[i], s * 0.0195, ENGRAVE)

    # --- anneau du zodiaque : 360 divisions, 12 secteurs, lettres-index
    for r in (r_zod_in, r_zod_out):
        p.setPen(QtGui.QPen(ENGRAVE, s * 0.0035))
        p.drawEllipse(QtCore.QPointF(cx, cy), r, r)
    for d in range(360):
        a = math.radians(90.0 - d)
        if d % 30 == 0:
            r0, wdt, col = r_zod_in, 0.0026, ENGRAVE
        elif d % 5 == 0:
            r0, wdt, col = r_zod_out - (r_zod_out - r_zod_in) * 0.38, 0.0014, ENGRAVE
        else:
            r0, wdt, col = r_zod_out - (r_zod_out - r_zod_in) * 0.20, 0.0008, ENGRAVE_SOFT
        p.setPen(QtGui.QPen(col, s * wdt))
        p.drawLine(QtCore.QPointF(cx + r0 * math.cos(a), cy - r0 * math.sin(a)),
                   QtCore.QPointF(cx + r_zod_out * math.cos(a),
                                  cy - r_zod_out * math.sin(a)))
    for i, (grec, fr, en) in enumerate(ZODIAC_GREEK):
        a = 90.0 - 30.0 * (i + 0.5)
        _ring_text(p, cx, cy, (r_zod_in + r_zod_out) / 2.0 + s * 0.010, a,
                   grec, s * 0.0170, ENGRAVE)
        _ring_text(p, cx, cy, (r_zod_in + r_zod_out) / 2.0 - s * 0.016, a,
                   fr if lang == "fr" else en, s * 0.0110, ENGRAVE_SOFT)
        _ring_text(p, cx, cy, r_zod_in + s * 0.012, 90.0 - 30.0 * i - 2.0,
                   PARAPEGMA_LETTERS[i % len(PARAPEGMA_LETTERS)],
                   s * 0.0120, ENGRAVE_SOFT)

    # --- plage centrale
    p.setPen(QtGui.QPen(ENGRAVE_SOFT, s * 0.0022))
    p.setBrush(QtGui.QBrush(BRONZE_PALE))
    p.drawEllipse(QtCore.QPointF(cx, cy), r_face, r_face)
    p.setBrush(QtGui.QBrush(PATINA))
    p.setPen(QtCore.Qt.PenStyle.NoPen)
    for dx, dy, rr in ((-0.26, -0.34, 0.10), (0.30, 0.20, 0.06),
                       (-0.40, 0.38, 0.045)):
        p.drawEllipse(QtCore.QPointF(cx + s * dx, cy + s * dy),
                      s * rr, s * rr * 0.8)


# ============================================================= FACE ARRIÈRE
def _spiral(p, cx, cy, s, turns, cells, r0, r1, label,
            cell_text=None, strong=(), title_below=False):
    """Une spirale d'Archimède graduée en `cells` cases.

    `cell_text(k)` renvoie l'inscription à graver dans la case k (ou None) ;
    `strong` est l'ensemble des cases dont le trait de séparation est
    renforcé — sur la métonique, les débuts d'année. Sans inscriptions, une
    spirale n'est qu'un décor : la machine grave chaque case.
    """
    path = QtGui.QPainterPath()
    n = 1400
    for i in range(n + 1):
        t = turns * 2.0 * math.pi * i / n
        r = r0 + (r1 - r0) * i / n
        pt = QtCore.QPointF(cx + r * math.cos(t - math.pi / 2),
                            cy - r * math.sin(t - math.pi / 2))
        path.moveTo(pt) if i == 0 else path.lineTo(pt)
    p.setPen(QtGui.QPen(ENGRAVE, s * 0.0032))
    p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
    p.drawPath(path)

    # largeur du couloir de la spirale : c'est l'écart radial entre deux
    # tours, donc la hauteur utile d'une case
    lane = (r1 - r0) / turns
    w = lane * 0.42                # demi-trait : en deçà de 0,5, les traits
    dtheta = turns * 2.0 * math.pi / cells        # angle d'une case
    for k in range(cells):
        t = dtheta * k
        r = r0 + (r1 - r0) * k / cells
        a = t - math.pi / 2
        fort = k in strong
        p.setPen(QtGui.QPen(ENGRAVE if fort else ENGRAVE_SOFT,
                            s * (0.0020 if fort else 0.0009)))
        p.drawLine(QtCore.QPointF(cx + (r - w) * math.cos(a),
                                  cy - (r - w) * math.sin(a)),
                   QtCore.QPointF(cx + (r + w) * math.cos(a),
                                  cy - (r + w) * math.sin(a)))

    # Inscriptions : chaque case reçoit son texte, écrit tangentiellement et
    # tourné pour suivre la spirale, comme sur la plaque. La taille est
    # imposée par la **largeur d'arc réelle** de la case (r·dθ) : une police
    # choisie sur la seule largeur du couloir déborde sur les cases voisines.
    if cell_text is not None:
        p.setPen(ENGRAVE)
        f = p.font()
        for k in range(cells):
            got = cell_text(k)
            if not got:
                continue
            txt, bold = got
            t = dtheta * (k + 0.5)
            # La ligne gravée passe au MILIEU du couloir : écrire au rayon
            # exact de la spirale, c'est écrire sur le trait. On décale
            # l'inscription vers l'extérieur du couloir.
            r = r0 + (r1 - r0) * (k + 0.5) / cells + lane * 0.27
            arc = r * dtheta
            px = min(lane * 0.42, arc / len(txt) * 1.45)
            if px < 2.0:                    # sous 2 px, ce n'est plus lisible
                continue
            f.setPixelSize(int(px)); f.setBold(bold); p.setFont(f)
            a = t - math.pi / 2
            p.save()
            p.translate(cx + r * math.cos(a), cy - r * math.sin(a))
            # le texte suit la tangente, et reste lisible tête en haut
            deg = -math.degrees(a) - 90.0
            if 90.0 < (deg % 360.0) < 270.0:
                deg += 180.0
            p.rotate(deg)
            p.drawText(QtCore.QRectF(-arc / 2.0, -lane * 0.3, arc, lane * 0.6),
                       QtCore.Qt.AlignmentFlag.AlignCenter, txt)
            p.restore()

    # titre hors de la spirale : au centre, il serait caché par le moyeu et
    # l'aiguille. `title_below` évite qu'il tombe sur la spirale voisine.
    f = p.font(); f.setPixelSize(max(1, int(s * 0.016))); f.setBold(True)
    p.setFont(f); p.setPen(ENGRAVE)
    dy = (r1 + s * 0.006) if title_below else (-r1 - s * 0.030)
    p.drawText(QtCore.QRectF(cx - s * 0.2, cy + dy, s * 0.4, s * 0.026),
               QtCore.Qt.AlignmentFlag.AlignCenter, label)


def _small_dial(p, cx, cy, s, rad, sectors, labels, title,
                title_above=False):
    p.setPen(QtGui.QPen(ENGRAVE, s * 0.0026))
    p.setBrush(QtGui.QBrush(BRONZE_PALE))
    p.drawEllipse(QtCore.QPointF(cx, cy), rad, rad)
    for k in range(sectors):
        a = math.radians(90.0 - 360.0 * k / sectors)
        p.setPen(QtGui.QPen(ENGRAVE_SOFT, s * 0.0014))
        p.drawLine(QtCore.QPointF(cx, cy),
                   QtCore.QPointF(cx + rad * math.cos(a),
                                  cy - rad * math.sin(a)))
    f = p.font(); f.setPixelSize(max(1, int(rad * 0.155))); f.setBold(True)
    p.setFont(f); p.setPen(ENGRAVE)
    for k, txt in enumerate(labels):
        a = math.radians(90.0 - 360.0 * (k + 0.5) / sectors)
        rr = rad * 0.58
        p.drawText(QtCore.QRectF(cx + rr * math.cos(a) - rad * 0.5,
                                 cy - rr * math.sin(a) - rad * 0.14,
                                 rad, rad * 0.28),
                   QtCore.Qt.AlignmentFlag.AlignCenter, txt)
    # le titre va sous le cadran, sauf quand le cadran du dessous est trop
    # proche : les deux légendes se marcheraient dessus
    f.setPixelSize(max(1, int(rad * 0.17))); p.setFont(f)
    ty = (cy - rad * 1.58) if title_above else (cy + rad * 1.08)
    p.drawText(QtCore.QRectF(cx - rad * 1.6, ty, rad * 3.2, rad * 0.5),
               QtCore.Qt.AlignmentFlag.AlignCenter, title)


def paint_back_dial(p: QtGui.QPainter, cx: float, cy: float, R: float,
                    lang: str = "fr", with_background: bool = True,
                    mirrored: bool = True) -> None:
    """Spirale métonique (5 tours, 235 cases), spirale du Saros (4 tours,
    223 cases) et les petits cadrans — chacun DESSINÉ SUR SON ARBRE.

    Les positions viennent de l'implantation (layout.ARBORS) : l'aiguille
    métonique est portée par l'arbre n, celle du Saros par g, le callippique
    par o, l'exeligmos par i. Le cadran n'est plus un décor posé n'importe
    où : il est l'extrémité visible du train qui l'entraîne.

    `mirrored` : cette face se regarde **par derrière**, donc en texture 3D
    ses x sont inversés. La vue vectorielle, elle, ne retourne pas la scène —
    elle doit passer ``mirrored=False``, sinon les cadrans partent du côté
    opposé aux aiguilles qui les entraînent.
    """
    from . import layout as lay

    s = R / 0.485
    x0, y0 = cx - s / 2.0, cy - s / 2.0
    ppm = s / lay.BACK_DIAL_SPAN                   # pixels par millimètre
    sx = -1.0 if mirrored else 1.0

    def at_mm(mx, my):
        """Position dessin d'un point (x, y) du plan de la machine, en mm.
        y écran vers le haut, y texture vers le bas : toujours inversé."""
        return (cx + sx * (mx - lay.CASE_CX) * ppm,
                cy - (my - lay.CASE_CY) * ppm)

    def at(arbor):
        return at_mm(*lay.ARBORS[arbor])

    if with_background:
        # le fond épouse le boîtier réel (W × H mm), pas le carré de la
        # texture : sinon la plaque de bronze déborde du coffret
        bw, bh = lay.CASE_WIDTH * ppm, lay.CASE_HEIGHT * ppm
        grad = QtGui.QRadialGradient(cx, cy - R * 0.2, R * 1.35)
        grad.setColorAt(0.0, QtGui.QColor(240, 220, 168))
        grad.setColorAt(1.0, BRONZE_MID)
        p.setBrush(QtGui.QBrush(grad))
        p.setPen(QtGui.QPen(ENGRAVE_SOFT, s * 0.004))
        p.drawRect(QtCore.QRectF(cx - bw / 2.0, cy - bh / 2.0, bw, bh))

    # --- spirale métonique : les mois corinthiens, année par année --------
    starts = metonic_year_starts()
    year_of = {}
    for yr, first in enumerate(starts):
        last = starts[yr + 1] if yr + 1 < len(starts) else 235
        for mois in range(first, last):
            year_of[mois] = (yr, mois - first)

    def metonic_cell(k):
        """(inscription, gras) de la case k, ou None."""
        yr, rank = year_of[k]
        if rank == 0:                      # début d'année : son numéro, en gras
            return GREEK_NUMERALS[yr], True
        if k >= starts[15]:                # tour extérieur : place pour un nom
            return CORINTHIAN_MONTHS[rank % 12][1], False
        return None

    def saros_cell(k):
        # Η = Ἥλιος (Soleil), Σ = Σελήνη (Lune) ; les deux si le mois porte
        # une éclipse de chaque sorte
        sol, lun = k in SAROS_SOLAR, k in SAROS_LUNAR
        if sol and lun:
            return "ΗΣ", True
        if sol:
            return "Η", True
        if lun:
            return "Σ", True
        return None

    nx, ny = at("n")
    gx, gy = at("g")
    _spiral(p, nx, ny, s, 5, 235, lay.METONIC_RADIUS * 0.275 * ppm,
            lay.METONIC_RADIUS * ppm, "ΜΕΤΩΝ · 235",
            cell_text=metonic_cell, strong=set(starts))
    # titre du Saros SOUS sa spirale : au-dessus, il tomberait dans la
    # métonique — il ne reste que 7,75 mm entre les deux
    _spiral(p, gx, gy, s, 4, 223, lay.SAROS_RADIUS * 0.27 * ppm,
            lay.SAROS_RADIUS * ppm, "ΣΑΡΟΣ · 223",
            cell_text=saros_cell, strong={0, 56, 112, 168},
            title_below=True)

    # --- petits cadrans ---------------------------------------------------
    # Rayons contraints : les arbres o et i ne sont distants que de 22,08 mm,
    # et les deux cadrans se chevauchaient de 2,92 mm. Les rayons viennent de
    # `anticythere_cadrans2.sage` (3 mm de jeu conservés).
    ox, oy = at("o")
    ix, iy = at("i")
    _small_dial(p, ox, oy, s, lay.CALLIPPIC_RADIUS * ppm, 4,
                ["Α", "Β", "Γ", "Δ"], "ΚΑΛΛΙΠΠΟΣ", title_above=True)
    _small_dial(p, ix, iy, s, lay.EXELIGMOS_RADIUS * ppm, 3,
                EXELIGMOS_LABELS, "ΕΞΕΛΙΓΜΟΣ")
    # Le cadran des Jeux n'a pas d'arbre modélisé : il est libre. Il était
    # posé sur la spirale du Saros (0,67 mm de chevauchement) ; il rejoint la
    # zone réellement vide de la plaque, côté grande roue.
    jx, jy = at_mm(*lay.GAMES_CENTER)
    _small_dial(p, jx, jy, s, 13.0 * ppm, 4, GAMES_GREEK, "ΑΓΩΝΕΣ")


# ================================================================ textures
def _render(painter_fn, size: int) -> QtGui.QImage:
    img = QtGui.QImage(size, size, QtGui.QImage.Format.Format_ARGB32)
    img.fill(QtCore.Qt.GlobalColor.transparent)
    p = QtGui.QPainter(img)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)
    painter_fn(p, size / 2.0, size / 2.0, size * 0.485)
    p.end()
    return img


def render_front_dial(size: int = 2048, calendar_days: int = 365,
                      lang: str = "fr") -> QtGui.QImage:
    return _render(lambda p, x, y, r: paint_front_dial(p, x, y, r,
                                                       calendar_days, lang), size)


def render_back_dial(size: int = 2048, lang: str = "fr",
                     mirror: bool = False) -> QtGui.QImage:
    """Face arrière. `mirror` dessine l'image en miroir horizontal : c'est ce
    qu'il faut pour la texture 3D, puisqu'on regarde cette face par derrière.
    Les deux spirales étant centrées, leurs centres ne bougent pas."""
    def draw(p, x, y, r):
        if mirror:
            p.translate(2.0 * x, 0.0)
            p.scale(-1.0, 1.0)
        paint_back_dial(p, x, y, r, lang)
    return _render(draw, size)


def image_to_array(img: QtGui.QImage):
    """QImage → tableau numpy RGBA, pour la texture OpenGL."""
    import numpy as np
    img = img.convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
    w, h = img.width(), img.height()
    ptr = img.constBits()
    ptr.setsize(h * img.bytesPerLine())
    arr = np.frombuffer(ptr, dtype=np.uint8).reshape(h, img.bytesPerLine() // 4, 4)
    return np.ascontiguousarray(arr[:, :w]).copy()
