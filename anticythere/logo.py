"""
Logo du programme : la grande roue à quatre bras et la spirale du Saros.

Program logo: the four-spoked great wheel and the Saros spiral.

UNE seule source : `docs/logo.svg`. Tout le reste en est rendu — icône de
fenêtre, PNG du paquet Linux et du README, `.ico` multi-résolutions de
l'installeur Windows, `.icns` de l'application macOS, logo de la fenêtre
« À propos » et de la page de garde des manuels. Jamais deux dessins
différents selon l'endroit.

    python -m anticythere.logo            (régénère docs/logo_*.png, .ico, .icns)
"""

from __future__ import annotations

import argparse
import os
import struct
from pathlib import Path

from PyQt6 import QtCore, QtGui

#: la source unique du logo
SOURCE = Path(__file__).resolve().parent.parent / "docs" / "logo.svg"
#: tailles PNG publiées (16 → 1024)
TAILLES = (16, 32, 64, 128, 256, 512, 1024)


def render(size: int) -> QtGui.QImage:
    """Le logo rendu depuis le SVG source, carré de `size` pixels."""
    from PyQt6 import QtSvg
    img = QtGui.QImage(size, size, QtGui.QImage.Format.Format_ARGB32)
    img.fill(QtCore.Qt.GlobalColor.transparent)
    rendu = QtSvg.QSvgRenderer(str(SOURCE))
    if rendu.isValid():
        p = QtGui.QPainter(img)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
        rendu.render(p, QtCore.QRectF(0, 0, size, size))
        p.end()
    return img


def _png(img: QtGui.QImage) -> bytes:
    buf = QtCore.QBuffer()
    buf.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    data = bytes(buf.data())
    buf.close()
    return data


def write_ico(path, sizes=(16, 24, 32, 48, 64, 128, 256)) -> None:
    """Écrit un .ico multi-résolutions, chaque image étant un PNG embarqué.

    Qt ne sait pas écrire l'ICO ; le format l'autorise depuis Vista, et il est
    assez simple pour être assemblé à la main.
    """
    pngs = [(s, _png(render(s))) for s in sizes]
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


#: types ICNS des images PNG (macOS 10.7+) : taille en pixels
_ICNS = (("icp4", 16), ("icp5", 32), ("icp6", 64), ("ic07", 128),
         ("ic08", 256), ("ic09", 512), ("ic10", 1024),
         ("ic11", 32), ("ic12", 64), ("ic13", 256), ("ic14", 512))


def write_icns(path) -> None:
    """Écrit l'icône macOS (.icns), chaque entrée étant un PNG : format
    assemblé à la main, sans `iconutil` (absent hors macOS)."""
    blocs = b""
    cache: dict[int, bytes] = {}
    for code, s in _ICNS:
        data = cache.setdefault(s, _png(render(s)))
        blocs += code.encode("ascii") + struct.pack(">I", 8 + len(data)) + data
    with open(path, "wb") as fh:
        fh.write(b"icns" + struct.pack(">I", 8 + len(blocs)) + blocs)


def app_icon() -> QtGui.QIcon:
    """Icône de fenêtre, en plusieurs tailles."""
    icon = QtGui.QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(QtGui.QPixmap.fromImage(render(s)))
    return icon


def pixmap(size: int = 96) -> QtGui.QPixmap:
    """Le logo pour la fenêtre « À propos »."""
    return QtGui.QPixmap.fromImage(render(size))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Rend le logo depuis docs/logo.svg")
    ap.add_argument("--out", default=str(SOURCE.parent))
    args = ap.parse_args(argv)
    from PyQt6 import QtWidgets
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    os.makedirs(args.out, exist_ok=True)
    for s in TAILLES:
        render(s).save(os.path.join(args.out, f"logo_{s}.png"))
    write_ico(os.path.join(args.out, "logo.ico"))
    write_icns(os.path.join(args.out, "logo.icns"))
    print(f"{SOURCE.name} -> logo_{{16..1024}}.png, logo.ico, logo.icns "
          f"dans {args.out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
