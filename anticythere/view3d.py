"""
Vue 3D du mécanisme (pyqtgraph.opengl) et repli 2D (QPainter) si OpenGL
n'est pas disponible.

3D view of the mechanism, with a 2D fallback when OpenGL is unavailable.
"""

from __future__ import annotations

import math

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

from . import geometry as geo
from . import layout as lay
from .view2d import VectorView


def _qcolor(rgba):
    return QtGui.QColor.fromRgbF(*rgba[:3], rgba[3] if len(rgba) > 3 else 1.0)

try:                                            # OpenGL optionnel
    import pyqtgraph.opengl as gl
    HAS_GL = True
except Exception:                               # pragma: no cover
    gl = None
    HAS_GL = False


# ---------------------------------------------------------------------------
class MechanismView(QtWidgets.QWidget):
    """Fabrique commune : renvoie la vue 3D si possible, sinon la vue 2D."""

    @staticmethod
    def create(parent=None):
        """Vue 3D si OpenGL est là, sinon la vue vectorielle (jamais d'échec)."""
        if HAS_GL:
            try:
                return GLMechanismView(parent)
            except Exception:
                pass
        return VectorView(parent)


# ---------------------------------------------------------------------------
if HAS_GL:

    class GLMechanismView(gl.GLViewWidget):
        """Rendu 3D : une pièce = un GLMeshItem, animé par une matrice."""

        def __init__(self, parent=None):
            # rotationMethod='quaternion' : rotation LIBRE dans tous les sens.
            # En mode 'euler' (défaut), l'élévation est bloquée à ±90° et on ne
            # peut pas retourner l'objet.
            super().__init__(parent, rotationMethod="quaternion")
            self.setCameraPosition(distance=360, elevation=24, azimuth=-62)
            self.opts["center"] = QtGui.QVector3D(*lay.CENTER)
            self.setBackgroundColor(_qcolor(lay.BACKGROUND))
            self.profile = "triangular"
            self.explode = 0.0
            self.highlight = None
            self.show_case = True
            self.show_plates = True
            self._gears: dict[str, object] = {}
            self._arbors: dict[str, object] = {}
            self._pointers: dict[str, object] = {}
            self._case: list = []
            self._plates: list = []
            self._dials: list = []
            self._angles: dict[str, float] = {}
            self._carrier = 0.0
            self._dial_cache: dict = {}
            self.dial_lang = "fr"
            self.build()

        # ------------------------------------------------------- construction
        def _add(self, mesh, color, draw_edges=False):
            v, f = mesh
            md = gl.MeshData(vertexes=v, faces=f)
            item = gl.GLMeshItem(meshdata=md, smooth=False, shader="shaded",
                                 color=color, drawEdges=draw_edges,
                                 edgeColor=(0, 0, 0, 0.25),
                                 glOptions="opaque" if color[3] >= 0.99
                                 else "translucent")
            self.addItem(item)
            return item

        def build(self):
            from .kinematics import TEETH

            for it in list(self.items):
                self.removeItem(it)
            self._gears.clear(); self._arbors.clear()
            self._pointers.clear(); self._case.clear(); self._plates.clear()
            self._dials.clear()

            for name, teeth in TEETH.items():
                if name not in lay.LEVELS:
                    continue
                sub = lay.SUBSYSTEM_OF.get(name, "input")
                color = lay.COLORS[sub]
                if name in lay.SPOKED:
                    mesh = geo.spoked_gear_mesh(
                        teeth, lay.MODULE, lay.GEAR_THICKNESS, z0=0.0,
                        bore=lay.ARBOR_RADIUS + 0.4,
                        spokes=lay.SPOKED[name], profile=self.profile)
                else:
                    mesh = geo.gear_mesh(teeth, lay.MODULE, lay.GEAR_THICKNESS,
                                         z0=0.0, bore=lay.ARBOR_RADIUS + 0.4,
                                         profile=self.profile)
                self._gears[name] = self._add(mesh, color)

            # plans de la façade et du dos, nécessaires avant les arbres
            zf_pre = lay.level_z(1) + 8.0
            zb_pre = lay.level_z(16) - 8.0
            for arbor in lay.ARBORS:
                z0, z1 = lay.arbor_extent(arbor)
                # les arbres de sortie TRAVERSENT jusqu'à leur cadran : c'est
                # eux qui portent les aiguilles — fin de la lévitation
                if arbor in ("n", "g", "o", "i"):
                    z0 = zb_pre - 12.0
                if arbor == "b":
                    z1 = zf_pre + 9.0
                mesh = geo.cylinder_mesh(lay.ARBOR_RADIUS, z0, z1 - z0, segments=14)
                self._arbors[arbor] = self._add(mesh, lay.COLORS["arbor"])

            # plans de référence de la façade et du dos
            zf = lay.level_z(1) + 8.0
            zb = lay.level_z(16) - 8.0
            self.z_front = zf + 8.0          # face extérieure du coffret
            self.z_back = zb - 10.0

            # aiguilles : maillage créé À PLAT (z0 = 0), c'est set_pointers qui
            # les place — sinon le décalage en z serait appliqué deux fois.
            # Chaque aiguille reçoit un MOYEU : elle est vissée sur son arbre,
            # pas posée en l'air.
            def hand(length, color):
                mesh = geo.merge([
                    geo.pointer_mesh(length, 0.0),
                    geo.disc_mesh(4.6, -0.6, 2.4, inner=1.2, segments=24)])
                return self._add(mesh, color)

            self._pointers["sun"] = hand(lay.SUN_HAND, (0.85, 0.65, 0.15, 1.0))
            self._pointers["moon"] = hand(lay.MOON_HAND, (0.80, 0.82, 0.86, 1.0))
            self._pointers["metonic"] = hand(lay.METONIC_RADIUS * 1.02,
                                             lay.COLORS["metonic"])
            self._pointers["saros"] = hand(lay.SAROS_RADIUS * 1.02,
                                           lay.COLORS["saros"])

            # ---- le Cosmos de la face avant : anneaux planétaires tournants
            # (modèle Freeth 2021), chacun marqué de sa petite sphère — le
            # sphairion des inscriptions
            self._planet_rings = {}
            self._planet_balls = {}
            z_cosmos = zf_pre + 9.5
            for idx, (pname, radius, color) in enumerate(lay.COSMOS_RINGS):
                zr = z_cosmos + 0.12 * idx
                ring = self._add(geo.disc_mesh(radius + 1.1, zr, 0.8,
                                               inner=radius - 1.1),
                                 (color[0], color[1], color[2], 0.95))
                self._planet_rings[pname] = (ring, radius, zr)
                ball = self._add(geo.sphere_mesh(3.1, 0.0), color)
                self._planet_balls[pname] = (ball, radius, zr)

            # anneau du zodiaque, visible même machine ouverte
            self._dials = [self._add(
                geo.disc_mesh(112.0, zf - 2.0, 1.2, inner=96.0),
                lay.COLORS["dial"])]
            self._dials.append(self._add(
                geo.disc_mesh(14.0, zf - 2.0, 1.6, inner=3.0),
                lay.COLORS["dial"]))
            self._dials.append(self._add(
                geo.spiral_mesh(5, 235, 22.0, 58.0, zb + 1.2),
                lay.COLORS["metonic"]))
            self._dials.append(self._add(
                geo.spiral_mesh(4, 223, 20.0, 52.0, zb - 6.0),
                lay.COLORS["saros"]))

            # platines : plaques de bois intérieures qui portent les arbres
            for z in (lay.level_z(1) + 4.0, lay.level_z(16) - 5.0):
                self._plates.append(self._add(
                    geo.translate(geo.plate_mesh(lay.CASE_WIDTH - 24.0,
                                                 lay.CASE_HEIGHT - 24.0, z, 1.5),
                                  lay.CASE_CX, lay.CASE_CY, 0.0),
                    lay.COLORS["plate"]))

            self._build_case(zf, zb)
            self.apply_visibility()

        # ---------------------------------------------------- cadrans gravés
        def _add_dial_texture(self, which: str, span: float, z: float,
                              cx: float, cy: float, flip: bool = False):
            """Pose un cadran dessiné en QPainter comme texture dans la scène."""
            from . import dialface

            key = (which, self.dial_lang)
            data = self._dial_cache.get(key)
            if data is None:
                img = (dialface.render_front_dial(1600, lang=self.dial_lang)
                       if which == "front"
                       else dialface.render_back_dial(1600, lang=self.dial_lang))
                data = dialface.image_to_array(img)
                self._dial_cache[key] = data
            # Quad à UV explicites (texquad) et non GLImageItem : celui-ci
            # transpose l'image en interne, ce qui rendait l'orientation
            # intraitable — c'est lui qui laissait le dos en miroir.
            from .texquad import TexturedQuadItem
            item = TexturedQuadItem(data, span, span, mirror_x=flip)
            m = QtGui.QMatrix4x4()
            m.translate(cx, cy, z)
            item.setTransform(m)
            self.addItem(item)
            self._case.append(item)
            return item

        # --------------------------------------------------------- boîtier
        def _build_case(self, zf: float, zb: float):
            """La machine FERMÉE : coffret de bois, plaques de bronze gravées,
            manivelle latérale. Tout ceci disparaît d'un clic."""
            W, H = lay.CASE_WIDTH, lay.CASE_HEIGHT
            cx, cy = lay.CASE_CX, lay.CASE_CY
            wood = (0.40, 0.27, 0.15, 1.0)
            bronze = (0.62, 0.50, 0.24, 1.0)
            z_front, z_back = self.z_front, self.z_back
            dark = (0.30, 0.24, 0.12, 1.0)

            # coffret de bois : quatre flancs + fond
            self._case = [self._add(
                geo.translate(geo.case_mesh(W, H, (z_front - z_back), wall=6.0),
                              cx, cy, (z_front + z_back) / 2.0), wood)]
            self._case.append(self._add(
                geo.translate(geo.plate_mesh(W, H, z_back, 3.0),
                              cx, cy, 0.0), wood))
            # façade de bronze pleine : c'est elle qui porte les cadrans
            self._case.append(self._add(
                geo.translate(geo.plate_mesh(W, H, z_front - 3.0, 3.0),
                              cx, cy, 0.0), bronze))
            # cadrans gravés : de vraies textures, avec les inscriptions
            # grecques. Un disque de bronze et quelques traits en volume ne
            # rendraient jamais ΚΡΙΟΣ ni ΜΕΤΩΝ lisibles.
            self._add_dial_texture("front", lay.FRONT_DIAL_SPAN,
                                   z_front + 0.6, 0.0, 0.0)
            self._add_dial_texture("back", lay.BACK_DIAL_SPAN,
                                   z_back - 0.6, cx, cy, flip=True)
            # manivelle sur le flanc, dans l'axe de la roue a1
            ax, ay = lay.ARBORS["a"]
            self._case.append(self._add(
                geo.translate(geo.crank_mesh(z_front - 2.0), ax, ay, 0.0),
                (0.55, 0.42, 0.20, 1.0)))
            # bille bicolore de la phase de Lune
            self._case.append(self._add(
                geo.sphere_mesh(7.0, z_front + 7.0), (0.92, 0.90, 0.84, 1.0)))

        # ------------------------------------------------------------ options
        def set_profile(self, profile: str):
            if profile != self.profile:
                self.profile = profile
                self.build()
                self.set_angles(self._angles, self._carrier)

        def apply_visibility(self):
            for it in self._case:
                it.setVisible(self.show_case)
            for it in self._plates:
                it.setVisible(self.show_plates)
            for name, item in self._gears.items():
                sub = lay.SUBSYSTEM_OF.get(name, "input")
                if self.highlight and sub != self.highlight:
                    item.setColor((0.55, 0.55, 0.55, 0.18))
                    item.setGLOptions("translucent")
                else:
                    item.setColor(lay.COLORS[sub])
                    item.setGLOptions("opaque")

        # ---------------------------------------------------------- animation
        def set_angles(self, angles: dict, carrier_turns: float):
            """Place chaque pièce : rotation propre + orbite du porte-satellite."""
            self._angles = angles
            self._carrier = carrier_turns
            ex, ey = lay.ARBORS["e"]
            ca = 2.0 * math.pi * carrier_turns

            for name, item in self._gears.items():
                x, y, z = lay.gear_position(name)
                if name in ("k1", "k2"):
                    # les axes k et K sont plantés sur e3 : ils orbitent
                    dx, dy = x - ex, y - ey
                    c, s = math.cos(ca), math.sin(ca)
                    x, y = ex + c * dx - s * dy, ey + s * dx + c * dy
                z += self.explode * (lay.LEVELS[name] - 8.5) * 6.0
                m = QtGui.QMatrix4x4()
                m.translate(x, y, z)
                m.rotate(360.0 * angles.get(name, 0.0), 0.0, 0.0, 1.0)
                item.setTransform(m)

            for arbor, item in self._arbors.items():
                x, y = lay.ARBORS[arbor]
                if arbor in ("k", "K"):
                    dx, dy = x - ex, y - ey
                    c, s = math.cos(ca), math.sin(ca)
                    x, y = ex + c * dx - s * dy, ey + s * dx + c * dy
                m = QtGui.QMatrix4x4()
                m.translate(x, y, 0.0)
                item.setTransform(m)

        def set_planets(self, planets: dict, moon_turns: float,
                        sun_turns: float):
            """Place la petite sphère de chaque anneau du Cosmos."""
            values = dict(planets)
            values["moon"] = moon_turns
            values["sun"] = sun_turns
            for pname, (ball, radius, zr) in self._planet_balls.items():
                turns = values.get(pname, 0.0)
                m = QtGui.QMatrix4x4()
                m.translate(0.0, 0.0, zr + 2.2)
                m.rotate(-360.0 * turns, 0.0, 0.0, 1.0)
                m.translate(radius, 0.0, 0.0)
                ball.setTransform(m)

        def set_pointers(self, sun_turns, moon_turns, metonic_turns, saros_turns):
            zb = self.z_back
            # chaque aiguille tourne autour du centre de SON cadran : celles du
            # dos ne sont pas sur l'axe central, mais au cœur de leur spirale.
            specs = (
                ("sun", sun_turns, 0.0, 0.0, self.z_front + 11.0, 1.0),
                ("moon", moon_turns, 0.0, 0.0, self.z_front + 13.0, 1.0),
                ("metonic", metonic_turns, lay.METONIC_CENTER[0],
                 lay.METONIC_CENTER[1], zb - 2.0, -1.0),
                ("saros", saros_turns, lay.SAROS_CENTER[0],
                 lay.SAROS_CENTER[1], zb - 4.0, -1.0),
            )
            for key, turns, px, py, z, mirror in specs:
                item = self._pointers.get(key)
                if item is None:
                    continue
                m = QtGui.QMatrix4x4()
                m.translate(px, py, z)
                # le dos est vu par-derrière : on y miroite l'aiguille comme
                # le cadran, sinon elle tournerait à l'envers de la gravure
                m.scale(mirror, 1.0, 1.0)
                m.rotate(-360.0 * turns, 0.0, 0.0, 1.0)
                item.setTransform(m)

        # ------------------------------------------------------- navigation
        def zoom(self, factor: float):
            """Rapproche (factor < 1) ou éloigne (factor > 1) la caméra."""
            d = self.opts["distance"] * factor
            self.setCameraParams(distance=max(40.0, min(d, 3000.0)))
            self.update()

        def rotate(self, d_azim: float, d_elev: float):
            """Orbite libre — aucun blocage aux pôles en mode quaternion."""
            self.orbit(d_azim, d_elev)
            self.update()

        def roll(self, angle: float):
            """Roulis autour de l'axe de visée (3ᵉ degré de liberté)."""
            q = QtGui.QQuaternion.fromAxisAndAngle(0.0, 0.0, 1.0, angle)
            self.opts["rotation"] = q * self.opts["rotation"]
            self.update()

        def reset_view(self):
            self.look_at("iso")

        def look_at(self, mode: str):
            if mode == "front":
                self.setCameraPosition(distance=330, elevation=88, azimuth=-90)
            elif mode == "back":
                self.setCameraPosition(distance=330, elevation=-88, azimuth=90)
            else:
                self.setCameraPosition(distance=360, elevation=24, azimuth=-62)
            self.opts["center"] = QtGui.QVector3D(*lay.CENTER)
            self.update()


# ---------------------------------------------------------------------------
