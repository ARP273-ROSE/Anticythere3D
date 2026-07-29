"""
Export STL des roues, prêt pour l'impression 3D.

STL export of the gears, ready for 3D printing.

La géométrie affichée à l'écran n'est pas directement imprimable : il faut
ajouter un **jeu d'ajustement** (les dents sortent toujours un peu grasses en
FDM) et percer l'alésage à la cote de l'axe réel. Ce module s'en charge, et
produit un fichier par roue plus une nomenclature.

Utilisation :

    python -m anticythere.stl_export --out stl --clearance 0.15
"""

from __future__ import annotations

import argparse
import math
import os
import struct

import numpy as np

from . import geometry as geo
from . import layout as lay
from .kinematics import TEETH

Mesh = tuple[np.ndarray, np.ndarray]


# --------------------------------------------------------------------- STL
def write_stl(path: str, mesh: Mesh, name: str = "part") -> int:
    """Écrit un STL binaire. Renvoie le nombre de triangles."""
    verts, faces = mesh
    tri = verts[faces]                                   # (n, 3, 3)
    a = tri[:, 1] - tri[:, 0]
    b = tri[:, 2] - tri[:, 0]
    n = np.cross(a, b)
    norm = np.linalg.norm(n, axis=1, keepdims=True)
    n = np.divide(n, norm, out=np.zeros_like(n), where=norm > 1e-12)

    with open(path, "wb") as fh:
        fh.write(name.encode("ascii", "replace")[:79].ljust(80, b"\0"))
        fh.write(struct.pack("<I", len(faces)))
        for i in range(len(faces)):
            fh.write(struct.pack("<3f", *n[i]))
            for k in range(3):
                fh.write(struct.pack("<3f", *tri[i, k]))
            fh.write(struct.pack("<H", 0))
    return len(faces)


# ------------------------------------------------------- jeu d'ajustement
def offset_polygon(pts: np.ndarray, distance: float,
                   miter_limit: float = 2.5) -> np.ndarray:
    """Décale un contour fermé de `distance` (négatif = vers l'intérieur).

    Offset par bissectrice **avec compensation d'onglet** : sans elle, un
    sommet aigu — la pointe d'une dent — ne recule que de
    ``distance × cos(θ/2)``, et le jeu réel serait plus faible que demandé
    là où il compte le plus. Le facteur est plafonné par `miter_limit` pour
    éviter les pointes qui partent à l'infini.
    """
    p = np.asarray(pts, dtype=np.float64)
    nxt = np.roll(p, -1, axis=0)
    prv = np.roll(p, 1, axis=0)

    # sens de parcours : l'aire signée (formule du lacet) est positive dans le
    # sens trigonométrique. Les deux profils ne sont pas générés dans le même
    # sens, donc on ne peut pas le supposer — on le mesure.
    area = 0.5 * np.sum(p[:, 0] * nxt[:, 1] - nxt[:, 0] * p[:, 1])
    sign = 1.0 if area > 0 else -1.0

    def seg_normal(a, b):
        d = b - a
        L = np.linalg.norm(d, axis=1, keepdims=True)
        L[L < 1e-12] = 1e-12
        d = d / L
        return sign * np.stack([d[:, 1], -d[:, 0]], axis=1)   # normale sortante

    n1 = seg_normal(prv, p)
    n2 = seg_normal(p, nxt)
    s = n1 + n2
    L = np.linalg.norm(s, axis=1, keepdims=True)
    L[L < 1e-12] = 1e-12
    bisector = s / L
    # |n1 + n2| = 2 cos(theta/2)  ->  facteur d'onglet = 2 / |n1 + n2|
    miter = np.clip(2.0 / L, 1.0, miter_limit)
    return (p + distance * miter * bisector).astype(np.float32)


def printable_gear(name: str, module: float, thickness: float,
                   clearance: float, bore: float, profile: str) -> Mesh:
    """Maillage d'une roue, corrigé du jeu d'impression."""
    teeth = TEETH[name]
    outline = geo.gear_outline(teeth, module, profile)
    if clearance:
        outline = offset_polygon(outline, -clearance / 2.0)
    if name in lay.SPOKED:
        rp = module * teeth / 2.0
        r_rim = rp * 0.86
        parts = [geo.ring_prism(outline, r_rim, 0.0, thickness),
                 geo.ring_prism(geo.circle_outline(9.0, 32), bore / 2.0,
                                0.0, thickness)]
        for k in range(lay.SPOKED[name]):
            a = 2.0 * math.pi * k / lay.SPOKED[name]
            parts.append(geo._box(r_rim - 9.0 + 1.0, 7.0, thickness, 0.0,
                                  offset=(9.0 + (r_rim - 9.0) / 2.0, 0.0),
                                  angle=a))
        return geo.merge(parts)
    return geo.ring_prism(outline, bore / 2.0, 0.0, thickness)


# ------------------------------------------------------------------ export
def export_all(outdir: str, module: float = lay.MODULE,
               thickness: float = 3.0, clearance: float = 0.15,
               bore: float = 3.2, profile: str = "involute",
               only: list[str] | None = None) -> list[dict]:
    """Écrit un STL par roue. Renvoie la nomenclature.

    Le profil par défaut est la **développante** : pour une réplique qui doit
    réellement tourner sur 33 roues en série, elle est bien plus tolérante que
    les triangles antiques. Passer ``profile="triangular"`` pour l'authenticité.
    """
    os.makedirs(outdir, exist_ok=True)
    rows = []
    names = only or [n for n in TEETH if n in lay.LEVELS]
    for name in sorted(names, key=lambda n: -TEETH[n]):
        mesh = printable_gear(name, module, thickness, clearance, bore, profile)
        path = os.path.join(outdir, f"{name}_{TEETH[name]}dents.stl")
        ntri = write_stl(path, mesh, f"Anticythere {name}")
        v = mesh[0]
        rows.append(dict(
            name=name, teeth=TEETH[name],
            diameter=round(module * TEETH[name], 2),
            outer=round(float(np.hypot(v[:, 0], v[:, 1]).max()) * 2.0, 2),
            thickness=thickness, bore=bore, triangles=ntri,
            subsystem=lay.SUBSYSTEM_OF.get(name, "input"),
            spoked=name in lay.SPOKED, file=os.path.basename(path)))
    _write_bom(os.path.join(outdir, "nomenclature.csv"), rows,
               module, thickness, clearance, bore, profile)
    return rows


def _write_bom(path: str, rows: list[dict], module, thickness, clearance,
               bore, profile) -> None:
    import csv
    with open(path, "w", newline="", encoding="utf-8") as fh:
        fh.write(f"# Anticythere3D - roues a imprimer\n")
        fh.write(f"# module={module} mm, epaisseur={thickness} mm, "
                 f"jeu={clearance} mm, alesage={bore} mm, profil={profile}\n")
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow(r)


def summary(rows: list[dict]) -> str:
    total_tri = sum(r["triangles"] for r in rows)
    biggest = max(rows, key=lambda r: r["outer"])
    return (f"{len(rows)} roues exportées, {total_tri} triangles au total.\n"
            f"Plus grande : {biggest['name']} ({biggest['teeth']} dents), "
            f"{biggest['outer']} mm hors tout.\n"
            f"Plateau minimum requis : {math.ceil(biggest['outer']) + 5} mm.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Export STL des roues")
    ap.add_argument("--out", default="stl", help="dossier de sortie")
    ap.add_argument("--module", type=float, default=lay.MODULE)
    ap.add_argument("--thickness", type=float, default=3.0)
    ap.add_argument("--clearance", type=float, default=0.15,
                    help="jeu d'impression retiré aux dents (mm)")
    ap.add_argument("--bore", type=float, default=3.2,
                    help="diamètre d'alésage (axe acier 3 mm + jeu)")
    ap.add_argument("--profile", choices=["involute", "triangular"],
                    default="involute")
    ap.add_argument("--only", nargs="*",
                    help="n'exporter que ces roues, ex : b2 l1 l2 m1 m2 n1")
    args = ap.parse_args(argv)

    rows = export_all(args.out, args.module, args.thickness, args.clearance,
                      args.bore, args.profile, args.only)
    print(summary(rows))
    print(f"Nomenclature : {os.path.join(args.out, 'nomenclature.csv')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
