"""
Génération des maillages 3D : roues dentées, arbres, platines, pointeurs,
cadrans, boîtier.  Aucune dépendance à Qt — uniquement numpy, ce qui rend
ce module testable en console.

3D mesh generation: gears, arbors, plates, pointers, dials, case.
No Qt dependency — numpy only, so this module is testable headless.

Deux profils de denture sont proposés :

* ``"triangular"`` — triangles quasi équilatéraux, **le profil réel de la
  machine antique** (pas circulaire moyen 1,6 mm) ;
* ``"involute"``  — développante de cercle, le profil moderne, qui seul
  garantit un rapport instantané constant.
"""

from __future__ import annotations

import math

import numpy as np

Mesh = tuple[np.ndarray, np.ndarray]          # (vertices Nx3, faces Mx3)


# --------------------------------------------------------------- profils 2D
def gear_outline(n_teeth: int, module: float, profile: str = "triangular",
                 pressure_angle: float = 20.0,
                 pts_per_flank: int = 4) -> np.ndarray:
    """Contour fermé d'une roue, dans le plan (x, y), centré sur l'origine.

    Le contour est *étoilé* par rapport au centre, ce qui permet une
    triangulation en bandes triviale.
    """
    rp = module * n_teeth / 2.0
    if profile == "triangular":
        # dents triangulaires : sommet sur le cercle de tête, base sur le pied
        ra = rp + 0.55 * module
        rf = rp - 0.65 * module
        pts = []
        for i in range(n_teeth):
            a0 = 2.0 * math.pi * i / n_teeth
            a1 = 2.0 * math.pi * (i + 0.5) / n_teeth
            pts.append((rf * math.cos(a0), rf * math.sin(a0)))
            pts.append((ra * math.cos(a1), ra * math.sin(a1)))
        return np.array(pts, dtype=np.float32)

    # --- développante de cercle -------------------------------------------
    alpha = math.radians(pressure_angle)
    rb = rp * math.cos(alpha)
    ra = rp + module
    rf = max(rp - 1.25 * module, 0.15 * rp)
    inv_a = math.tan(alpha) - alpha
    half = math.pi / (2.0 * n_teeth)          # demi-épaisseur au primitif

    def involute(t):
        return np.array([rb * (math.cos(t) + t * math.sin(t)),
                         rb * (math.sin(t) - t * math.cos(t))])

    t_max = math.sqrt(max((ra / rb) ** 2 - 1.0, 1e-9))
    # Une dent s'AFFINE en montant : l'angle balayé par le flanc entre le
    # cercle de base et la tête vaut (t - arctan t). Si cet angle dépasse la
    # demi-épaisseur, les deux flancs se croiseraient et la dent se
    # refermerait sur elle-même — c'est le phénomène de pointe de dent, réel
    # sur les petites roues. On borne alors le rayon de tête.
    def swept(t):
        """Angle balayé depuis le cercle PRIMITIF (et non depuis la base :
        le flanc a déjà tourné de inv(alpha) pour aller de l'un à l'autre)."""
        return (t - math.atan(t)) - inv_a

    top_min = 0.12 * half            # épaisseur minimale conservée au sommet
    if swept(t_max) > half - top_min:
        lo, hi = 0.0, t_max
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            if swept(mid) > half - top_min:
                hi = mid
            else:
                lo = mid
        t_max = lo

    # Le flanc ne commence pas au cercle de base mais au CREUX de dent : dès
    # que N dépasse ~40, le creux (rp - 1.25 m) est au-dessus du cercle de
    # base, et démarrer plus bas ferait balayer au flanc un angle énorme,
    # jusqu'à recouvrir la dent voisine.
    t_min = math.sqrt(max((max(rf, rb) / rb) ** 2 - 1.0, 0.0))
    ts = np.linspace(t_min, t_max, pts_per_flank + 1)
    flank = np.array([involute(t) for t in ts])
    # Recalage sur le CERCLE PRIMITIF, seule référence valable : c'est là que
    # l'épaisseur de dent vaut la moitié du pas. Se caler sur le premier point
    # du flanc serait faux, puisqu'il ne part plus du cercle de base.
    t_pitch = math.tan(alpha)              # car (rp/rb)^2 - 1 = tan^2(alpha)
    p_pitch = involute(t_pitch)
    phi_pitch = math.atan2(p_pitch[1], p_pitch[0])
    rot = -phi_pitch - half
    c, s = math.cos(rot), math.sin(rot)
    R = np.array([[c, -s], [s, c]])
    flank = flank @ R.T

    pitch_half = math.pi / n_teeth        # demi-pas angulaire : milieu du creux
    pts = []
    for i in range(n_teeth):
        a = 2.0 * math.pi * i / n_teeth
        c, s = math.cos(a), math.sin(a)
        Rt = np.array([[c, -s], [s, c]])
        left = flank @ Rt.T                             # pied à a - half
        right = (flank * np.array([1.0, -1.0])) @ Rt.T  # miroir : pied à a + half
        # contour strictement croissant en angle : fond de creux, flanc gauche
        # qui monte, sommet, flanc droit redescendu — le creux suivant est
        # apporté par la dent suivante.
        pts.append([rf * math.cos(a - pitch_half), rf * math.sin(a - pitch_half)])
        pts.extend(left.tolist())
        pts.extend(right[::-1].tolist())
    return np.array(pts, dtype=np.float32)


def circle_outline(radius: float, segments: int = 48) -> np.ndarray:
    a = np.linspace(0.0, 2.0 * math.pi, segments, endpoint=False)
    return np.stack([radius * np.cos(a), radius * np.sin(a)], axis=1).astype(np.float32)


# ----------------------------------------------------------- extrusion 3D
def ring_prism(outer: np.ndarray, inner_radius: float, z0: float,
               thickness: float) -> Mesh:
    """Prisme entre un contour extérieur et un alésage circulaire.

    `outer` : contour (M,2) ; l'alésage est rééchantillonné sur M points
    pour que la triangulation soit une simple bande de quads.
    """
    m = len(outer)
    ang = np.arctan2(outer[:, 1], outer[:, 0])
    inner = np.stack([inner_radius * np.cos(ang),
                      inner_radius * np.sin(ang)], axis=1)

    z1 = z0 + thickness
    v = np.zeros((4 * m, 3), dtype=np.float32)
    v[0:m, :2] = outer;  v[0:m, 2] = z0          # ext bas
    v[m:2 * m, :2] = outer; v[m:2 * m, 2] = z1   # ext haut
    v[2 * m:3 * m, :2] = inner; v[2 * m:3 * m, 2] = z0
    v[3 * m:4 * m, :2] = inner; v[3 * m:4 * m, 2] = z1

    f = []
    for i in range(m):
        j = (i + 1) % m
        eb0, eb1 = i, j                 # ext bas
        et0, et1 = m + i, m + j         # ext haut
        ib0, ib1 = 2 * m + i, 2 * m + j
        it0, it1 = 3 * m + i, 3 * m + j
        f += [[eb0, eb1, et1], [eb0, et1, et0]]        # flanc extérieur
        f += [[ib1, ib0, it0], [ib1, it0, it1]]        # flanc de l'alésage
        f += [[ib0, ib1, eb1], [ib0, eb1, eb0]]        # face du bas
        f += [[et0, et1, it1], [et0, it1, it0]]        # face du haut
    return v, np.array(f, dtype=np.int32)


def gear_mesh(n_teeth: int, module: float, thickness: float, z0: float = 0.0,
              bore: float = 2.0, profile: str = "triangular") -> Mesh:
    return ring_prism(gear_outline(n_teeth, module, profile), bore, z0, thickness)


def spoked_gear_mesh(n_teeth: int, module: float, thickness: float,
                     z0: float = 0.0, bore: float = 2.5, spokes: int = 4,
                     rim_ratio: float = 0.86, hub_radius: float = 9.0,
                     spoke_width: float = 7.0,
                     profile: str = "triangular") -> Mesh:
    """Roue à bras — comme b1 (4 bras attestés), e3 et e4.

    C'est ce qui permet aux arbres voisins de traverser la roue : sans les
    bras, aucun train ne tiendrait dans le boîtier.
    """
    rp = module * n_teeth / 2.0
    r_rim = rp * rim_ratio
    meshes = [ring_prism(gear_outline(n_teeth, module, profile), r_rim, z0, thickness)]
    meshes.append(ring_prism(circle_outline(hub_radius, 32), bore, z0, thickness))
    for k in range(spokes):
        a = 2.0 * math.pi * k / spokes
        meshes.append(_box(length=r_rim - hub_radius + 1.0, width=spoke_width,
                           height=thickness, z0=z0,
                           offset=(hub_radius + (r_rim - hub_radius) / 2.0, 0.0),
                           angle=a))
    return merge(meshes)


def _box(length: float, width: float, height: float, z0: float,
         offset=(0.0, 0.0), angle: float = 0.0) -> Mesh:
    hx, hy = length / 2.0, width / 2.0
    base = np.array([[-hx, -hy], [hx, -hy], [hx, hy], [-hx, hy]], dtype=np.float32)
    base = base + np.array(offset, dtype=np.float32)
    c, s = math.cos(angle), math.sin(angle)
    base = base @ np.array([[c, s], [-s, c]], dtype=np.float32)
    v = np.zeros((8, 3), dtype=np.float32)
    v[0:4, :2] = base; v[0:4, 2] = z0
    v[4:8, :2] = base; v[4:8, 2] = z0 + height
    f = np.array([[0, 1, 2], [0, 2, 3],          # bas
                  [4, 6, 5], [4, 7, 6],          # haut
                  [0, 4, 5], [0, 5, 1],
                  [1, 5, 6], [1, 6, 2],
                  [2, 6, 7], [2, 7, 3],
                  [3, 7, 4], [3, 4, 0]], dtype=np.int32)
    return v, f


def cylinder_mesh(radius: float, z0: float, height: float,
                  segments: int = 20) -> Mesh:
    return ring_prism(circle_outline(radius, segments), radius * 0.35, z0, height)


def disc_mesh(radius: float, z0: float, thickness: float,
              inner: float = 0.0, segments: int = 64) -> Mesh:
    return ring_prism(circle_outline(radius, segments), max(inner, 0.01),
                      z0, thickness)


def pointer_mesh(length: float, z0: float, width: float = 3.0,
                 thickness: float = 1.2) -> Mesh:
    """Aiguille : triangle allongé partant du centre."""
    pts = np.array([[-width * 0.7, -width / 2], [length, -width * 0.25],
                    [length * 1.06, 0.0], [length, width * 0.25],
                    [-width * 0.7, width / 2]], dtype=np.float32)
    v = np.zeros((10, 3), dtype=np.float32)
    v[0:5, :2] = pts; v[0:5, 2] = z0
    v[5:10, :2] = pts; v[5:10, 2] = z0 + thickness
    f = [[0, 1, 2], [0, 2, 3], [0, 3, 4],
         [5, 7, 6], [5, 8, 7], [5, 9, 8]]
    for i in range(5):
        j = (i + 1) % 5
        f += [[i, j, 5 + j], [i, 5 + j, 5 + i]]
    return v, np.array(f, dtype=np.int32)


def spiral_mesh(turns: float, cells: int, r0: float, r1: float, z0: float,
                width: float = 1.2, thickness: float = 0.6,
                samples: int = 600) -> Mesh:
    """Rainure en spirale des cadrans arrière (métonique : 5 tours ; Saros : 4)."""
    t = np.linspace(0.0, turns * 2.0 * math.pi, samples)
    r = r0 + (r1 - r0) * t / t[-1]
    meshes = []
    for i in range(samples - 1):
        x0, y0 = r[i] * math.cos(t[i]), r[i] * math.sin(t[i])
        x1, y1 = r[i + 1] * math.cos(t[i + 1]), r[i + 1] * math.sin(t[i + 1])
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy) or 1e-6
        ang = math.atan2(dy, dx)
        meshes.append(_box(L, width, thickness, z0,
                           offset=((x0 + x1) / 2.0 / 1.0, (y0 + y1) / 2.0),
                           angle=0.0))
        # replace : boîte orientée le long du segment
        v, f = meshes[-1]
        c, s = math.cos(ang), math.sin(ang)
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        v[:, 0] -= cx; v[:, 1] -= cy
        xy = v[:, :2] @ np.array([[c, s], [-s, c]], dtype=np.float32).T
        v[:, :2] = xy
        v[:, 0] += cx; v[:, 1] += cy
    return merge(meshes)


def plate_mesh(width: float, height: float, z0: float,
               thickness: float) -> Mesh:
    """Plaque rectangulaire pleine."""
    return _box(width, height, thickness, z0)


def plate_with_window(width: float, height: float, z0: float, thickness: float,
                      cx: float, cy: float, radius: float) -> Mesh:
    """Plaque percée d'une fenêtre circulaire *quelconque part* — c'est la
    plaque de bronze de la face avant, qui laisse voir le cadran.

    Découpée en quatre bandes plus une couronne carré-cercle, ce qui évite
    toute triangulation complexe.
    """
    x0, x1 = -width / 2.0, width / 2.0
    y0, y1 = -height / 2.0, height / 2.0
    r = radius
    parts = []
    if cx - r > x0:
        w = (cx - r) - x0
        parts.append(_box(w, height, thickness, z0, offset=(x0 + w / 2.0, 0.0)))
    if x1 > cx + r:
        w = x1 - (cx + r)
        parts.append(_box(w, height, thickness, z0, offset=(x1 - w / 2.0, 0.0)))
    if y1 > cy + r:
        h = y1 - (cy + r)
        parts.append(_box(2 * r, h, thickness, z0, offset=(cx, y1 - h / 2.0)))
    if cy - r > y0:
        h = (cy - r) - y0
        parts.append(_box(2 * r, h, thickness, z0, offset=(cx, y0 + h / 2.0)))
    # couronne entre le carré circonscrit et le cercle
    ang = np.linspace(0.0, 2.0 * math.pi, 64, endpoint=False)
    sq = np.stack([np.clip(r / np.cos(ang + 1e-9), -r * 1.4142, r * 1.4142)
                   * np.cos(ang),
                   np.clip(r / np.cos(ang + 1e-9), -r * 1.4142, r * 1.4142)
                   * np.sin(ang)], axis=1)
    lim = np.maximum(np.abs(sq[:, 0]), np.abs(sq[:, 1]))
    sq = sq / np.maximum(lim[:, None] / r, 1e-9)
    ring = ring_prism(sq.astype(np.float32), r, z0, thickness)
    parts.append(geo_translate_local(ring, cx, cy))
    return merge(parts)


def graduation_ring(radius_in: float, radius_out: float, z0: float,
                    thickness: float, count: int, width: float = 0.9,
                    every: int = 0, long_extra: float = 0.0) -> Mesh:
    """Couronne de traits gravés — graduations d'un cadran."""
    parts = []
    for i in range(count):
        a = 2.0 * math.pi * i / count
        r_in = radius_in - (long_extra if every and i % every == 0 else 0.0)
        L = radius_out - r_in
        parts.append(_box(L, width, thickness, z0,
                          offset=(r_in + L / 2.0, 0.0), angle=a))
    return merge(parts)


def sphere_mesh(radius: float, z0: float, rings: int = 12,
                segments: int = 18) -> Mesh:
    """Sphère — la bille bicolore de la phase de Lune."""
    verts, faces = [], []
    for i in range(rings + 1):
        phi = math.pi * i / rings
        for j in range(segments):
            th = 2.0 * math.pi * j / segments
            verts.append([radius * math.sin(phi) * math.cos(th),
                          radius * math.sin(phi) * math.sin(th),
                          z0 + radius * math.cos(phi)])
    for i in range(rings):
        for j in range(segments):
            a = i * segments + j
            b = i * segments + (j + 1) % segments
            c = (i + 1) * segments + j
            d = (i + 1) * segments + (j + 1) % segments
            faces += [[a, b, d], [a, d, c]]
    return (np.array(verts, dtype=np.float32),
            np.array(faces, dtype=np.int32))


def crank_mesh(z0: float, shaft_len: float = 34.0, arm: float = 26.0,
               handle: float = 20.0) -> Mesh:
    """Manivelle : arbre sortant du flanc, bras coudé et poignée.

    C'est la seule commande de la machine — la « manette » que l'on tourne.
    """
    parts = [cylinder_mesh(3.2, z0, shaft_len, segments=16)]
    parts.append(_box(arm, 6.0, 4.0, z0 + shaft_len,
                      offset=(arm / 2.0 - 2.0, 0.0)))
    parts.append(geo_translate_local(
        cylinder_mesh(2.6, z0 + shaft_len + 4.0, handle, segments=12),
        arm - 4.0, 0.0))
    parts.append(geo_translate_local(
        cylinder_mesh(5.0, z0 + shaft_len + 4.0 + handle, 6.0, segments=12),
        arm - 4.0, 0.0))
    return merge(parts)


def geo_translate_local(mesh: Mesh, dx: float, dy: float) -> Mesh:
    v, f = mesh
    v = v.copy()
    v[:, 0] += dx
    v[:, 1] += dy
    return v, f


def case_mesh(width: float, height: float, depth: float,
              wall: float = 3.0) -> Mesh:
    """Boîtier ouvert (les 4 côtés), que l'on peut masquer pour voir dedans."""
    hw, hh = width / 2.0, height / 2.0
    parts = [
        _box(width, wall, depth, -depth / 2.0, offset=(0.0, hh)),
        _box(width, wall, depth, -depth / 2.0, offset=(0.0, -hh)),
        _box(wall, height, depth, -depth / 2.0, offset=(hw, 0.0)),
        _box(wall, height, depth, -depth / 2.0, offset=(-hw, 0.0)),
    ]
    return merge(parts)


# ------------------------------------------------------------------ outils
def merge(meshes: list[Mesh]) -> Mesh:
    """Concatène plusieurs maillages en un seul."""
    verts, faces, off = [], [], 0
    for v, f in meshes:
        verts.append(v)
        faces.append(f + off)
        off += len(v)
    if not verts:
        return np.zeros((0, 3), np.float32), np.zeros((0, 3), np.int32)
    return np.vstack(verts).astype(np.float32), np.vstack(faces).astype(np.int32)


def translate(mesh: Mesh, dx: float, dy: float, dz: float = 0.0) -> Mesh:
    v, f = mesh
    v = v.copy()
    v[:, 0] += dx; v[:, 1] += dy; v[:, 2] += dz
    return v, f


def mesh_stats(mesh: Mesh) -> dict:
    v, f = mesh
    return dict(vertices=len(v), faces=len(f),
                bbox=(v.min(axis=0).tolist(), v.max(axis=0).tolist()) if len(v) else None)
