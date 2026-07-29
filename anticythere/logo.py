"""
Logo du programme : la grande roue à quatre bras et la spirale du Saros.

Program logo: the four-spoked great wheel and the Saros spiral.

Dessiné en courbes, comme les cadrans, donc net à toute taille. Le module
produit le SVG, les PNG et le fichier .ico multi-résolutions utilisé par
l'exécutable Windows :

    python -m anticythere.logo --out docs
"""

from __future__ import annotations

import argparse
import math
import os
import struct

from PyQt6 import QtCore, QtGui

# palette : bronze chaud sur bleu de nuit
NIGHT_0 = QtGui.QColor(28, 42, 66)
NIGHT_1 = QtGui.QColor(12, 20, 34)
GOLD = QtGui.QColor(226, 180, 92)
GOLD_LIGHT = QtGui.QColor(247, 216, 150)
GOLD_DEEP = QtGui.QColor(168, 124, 48)
SILVER = QtGui.QColor(214, 222, 235)


def paint_logo(p: QtGui.QPainter, size: float, with_background: bool = True,
               teeth: int = 48) -> None:
    """Dessine le logo dans un carré de côté `size`, origine en haut à gauche."""
    c = size / 2.0
    R = size * 0.455                     # rayon de tête de la roue
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

    # --- fond : disque de nuit
    if with_background:
        g = QtGui.QRadialGradient(c, c * 0.82, size * 0.62)
        g.setColorAt(0.0, NIGHT_0)
        g.setColorAt(1.0, NIGHT_1)
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QBrush(g))
        p.drawEllipse(QtCore.QPointF(c, c), size * 0.5, size * 0.5)

    # --- couronne dentée
    rf = R * 0.885
    poly = QtGui.QPolygonF()
    for i in range(teeth):
        a0 = 2.0 * math.pi * i / teeth
        a1 = 2.0 * math.pi * (i + 0.46) / teeth
        poly.append(QtCore.QPointF(c + rf * math.cos(a0), c + rf * math.sin(a0)))
        poly.append(QtCore.QPointF(c + R * math.cos(a1), c + R * math.sin(a1)))
    ring = QtGui.QPainterPath()
    ring.addPolygon(poly)
    ring.closeSubpath()
    hole = QtGui.QPainterPath()
    hole.addEllipse(QtCore.QPointF(c, c), R * 0.775, R * 0.775)
    grad = QtGui.QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, GOLD_LIGHT)
    grad.setColorAt(0.5, GOLD)
    grad.setColorAt(1.0, GOLD_DEEP)
    p.setBrush(QtGui.QBrush(grad))
    p.setPen(QtGui.QPen(GOLD_DEEP, size * 0.006))
    p.drawPath(ring.subtracted(hole))

    # --- quatre bras, comme la roue b1
    arms = QtGui.QPainterPath()
    for k in range(4):
        a = math.pi / 4.0 + k * math.pi / 2.0
        t = QtGui.QTransform()
        t.translate(c, c)
        t.rotateRadians(a)
        arms.addPolygon(t.map(QtGui.QPolygonF([
            QtCore.QPointF(size * 0.045, -size * 0.030),
            QtCore.QPointF(R * 0.80, -size * 0.021),
            QtCore.QPointF(R * 0.80, size * 0.021),
            QtCore.QPointF(size * 0.045, size * 0.030)])))
    p.setBrush(QtGui.QBrush(grad))
    p.setPen(QtGui.QPen(GOLD_DEEP, size * 0.004))
    p.drawPath(arms)

    # --- spirale du Saros, au centre : quatre tours
    path = QtGui.QPainterPath()
    n = 420
    r0, r1 = size * 0.045, size * 0.255
    for i in range(n + 1):
        t = 4.0 * 2.0 * math.pi * i / n
        r = r0 + (r1 - r0) * i / n
        pt = QtCore.QPointF(c + r * math.cos(t - math.pi / 2.0),
                            c - r * math.sin(t - math.pi / 2.0))
        path.moveTo(pt) if i == 0 else path.lineTo(pt)
    p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
    p.setPen(QtGui.QPen(SILVER, size * 0.011,
                        QtCore.Qt.PenStyle.SolidLine,
                        QtCore.Qt.PenCapStyle.RoundCap))
    p.drawPath(path)

    # --- aiguille et moyeu
    p.setPen(QtGui.QPen(GOLD_LIGHT, size * 0.018,
                        QtCore.Qt.PenStyle.SolidLine,
                        QtCore.Qt.PenCapStyle.RoundCap))
    p.drawLine(QtCore.QPointF(c, c),
               QtCore.QPointF(c + r1 * 0.98 * math.cos(math.radians(-62.0)),
                              c + r1 * 0.98 * math.sin(math.radians(-62.0))))
    p.setPen(QtGui.QPen(GOLD_DEEP, size * 0.006))
    p.setBrush(QtGui.QBrush(GOLD_LIGHT))
    p.drawEllipse(QtCore.QPointF(c, c), size * 0.038, size * 0.038)


def render(size: int, background: bool = True) -> QtGui.QImage:
    img = QtGui.QImage(size, size, QtGui.QImage.Format.Format_ARGB32)
    img.fill(QtCore.Qt.GlobalColor.transparent)
    p = QtGui.QPainter(img)
    paint_logo(p, float(size), background)
    p.end()
    return img


def write_svg(path: str, size: int = 512) -> bool:
    try:
        from PyQt6 import QtSvg
    except ImportError:
        return False
    gen = QtSvg.QSvgGenerator()
    gen.setFileName(path)
    gen.setSize(QtCore.QSize(size, size))
    gen.setViewBox(QtCore.QRectF(0, 0, size, size))
    gen.setTitle("Anticythere3D")
    p = QtGui.QPainter()
    if not p.begin(gen):
        return False
    paint_logo(p, float(size))
    p.end()
    return True


def write_ico(path: str, sizes=(16, 24, 32, 48, 64, 128, 256)) -> None:
    """Écrit un .ico multi-résolutions, chaque image étant un PNG embarqué.

    Qt ne sait pas écrire l'ICO ; le format l'autorise depuis Vista, et il est
    assez simple pour être assemblé à la main.
    """
    pngs = []
    for s in sizes:
        buf = QtCore.QBuffer()
        buf.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
        render(s).save(buf, "PNG")
        pngs.append((s, bytes(buf.data())))
        buf.close()

    n = len(pngs)
    header = struct.pack("<HHH", 0, 1, n)
    offset = 6 + 16 * n
    entries, blobs = b"", b""
    for s, data in pngs:
        dim = 0 if s >= 256 else s
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32,
                               len(data), offset)
        offset += len(data)
        blobs += data
    with open(path, "wb") as fh:
        fh.write(header + entries + blobs)


def app_icon() -> QtGui.QIcon:
    """Icône de fenêtre, en plusieurs tailles."""
    icon = QtGui.QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(QtGui.QPixmap.fromImage(render(s)))
    return icon


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Génère le logo du programme")
    ap.add_argument("--out", default="docs")
    args = ap.parse_args(argv)
    from PyQt6 import QtWidgets
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    os.makedirs(args.out, exist_ok=True)
    for s in (64, 128, 256, 512):
        render(s).save(os.path.join(args.out, f"logo_{s}.png"))
    render(512, background=False).save(
        os.path.join(args.out, "logo_transparent.png"))
    ok_svg = write_svg(os.path.join(args.out, "logo.svg"))
    write_ico(os.path.join(args.out, "logo.ico"))
    print(f"logo écrit dans {args.out}/ : PNG (64→512), "
          f"SVG {'oui' if ok_svg else 'non'}, ICO multi-résolutions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
