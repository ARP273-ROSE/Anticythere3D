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
def _spiral(p, cx, cy, s, turns, cells, r0, r1, label):
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
    for k in range(cells):
        t = turns * 2.0 * math.pi * k / cells
        r = r0 + (r1 - r0) * k / cells
        a = t - math.pi / 2
        w = (r1 - r0) / turns * 0.5
        p.setPen(QtGui.QPen(ENGRAVE_SOFT, s * 0.0009))
        p.drawLine(QtCore.QPointF(cx + (r - w) * math.cos(a),
                                  cy - (r - w) * math.sin(a)),
                   QtCore.QPointF(cx + (r + w) * math.cos(a),
                                  cy - (r + w) * math.sin(a)))
    # titre AU-DESSUS de la spirale : au centre, il serait caché par le
    # moyeu et l'aiguille
    f = p.font(); f.setPixelSize(max(1, int(s * 0.016))); f.setBold(True)
    p.setFont(f); p.setPen(ENGRAVE)
    p.drawText(QtCore.QRectF(cx - s * 0.2, cy - r1 - s * 0.030,
                             s * 0.4, s * 0.026),
               QtCore.Qt.AlignmentFlag.AlignCenter, label)


def _small_dial(p, cx, cy, s, rad, sectors, labels, title):
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
    f.setPixelSize(max(1, int(rad * 0.17))); p.setFont(f)
    p.drawText(QtCore.QRectF(cx - rad * 1.6, cy + rad * 1.08, rad * 3.2, rad * 0.5),
               QtCore.Qt.AlignmentFlag.AlignCenter, title)


def paint_back_dial(p: QtGui.QPainter, cx: float, cy: float, R: float,
                    lang: str = "fr", with_background: bool = True) -> None:
    """Spirale métonique (5 tours, 235 cases), spirale du Saros (4 tours,
    223 cases) et les petits cadrans — chacun DESSINÉ SUR SON ARBRE.

    Les positions viennent de l'implantation (layout.ARBORS) : l'aiguille
    métonique est portée par l'arbre n, celle du Saros par g, le callippique
    par o, l'exeligmos par i. Le cadran n'est plus un décor posé n'importe
    où : il est l'extrémité visible du train qui l'entraîne.
    """
    from . import layout as lay

    s = R / 0.485
    x0, y0 = cx - s / 2.0, cy - s / 2.0
    ppm = s / lay.BACK_DIAL_SPAN                   # pixels par millimètre

    def at(arbor):
        """Position texture d'un arbre. La texture est affichée en miroir
        (on regarde le dos) : x est inversé ; y écran vers le haut, y texture
        vers le bas : inversé aussi."""
        ax, ay = lay.ARBORS[arbor]
        return (cx - (ax - lay.CASE_CX) * ppm,
                cy - (ay - lay.CASE_CY) * ppm)

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

    nx, ny = at("n")
    gx, gy = at("g")
    _spiral(p, nx, ny, s, 5, 235, lay.METONIC_RADIUS * 0.275 * ppm,
            lay.METONIC_RADIUS * ppm, "ΜΕΤΩΝ · 235")
    _spiral(p, gx, gy, s, 4, 223, lay.SAROS_RADIUS * 0.27 * ppm,
            lay.SAROS_RADIUS * ppm, "ΣΑΡΟΣ · 223")
    ox, oy = at("o")
    ix, iy = at("i")
    _small_dial(p, ox, oy, s, 13.0 * ppm, 4, ["1", "2", "3", "4"], "ΚΑΛΛΙΠΠΟΣ")
    _small_dial(p, ix, iy, s, 12.0 * ppm, 3, EXELIGMOS_LABELS, "ΕΞΕΛΙΓΜΟΣ")
    # le cadran des Jeux n'a pas d'arbre modélisé : il reste gravé, dans le
    # coin libre en haut à gauche de la plaque, comme un médaillon
    _small_dial(p, cx - 95.0 * ppm, cy + 95.0 * ppm, s, 13.0 * ppm, 4,
                GAMES_GREEK, "ΑΓΩΝΕΣ")


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
