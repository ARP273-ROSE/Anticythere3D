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

    def _register_shader() -> str:
        """Éclairage maison : la couleur d'une roue doit rester SA couleur.

        Le shader « shaded » de pyqtgraph éclaire depuis (1, −1, −1) en repère
        caméra : une face tournée vers l'observateur ne reçoit que 20 % de
        lumière ambiante. Toutes les roues vues de face sortaient presque
        noires, et la palette devenait illisible. Ici : 55 % d'ambiante, le
        reste en diffus depuis le haut-droite de l'observateur, sur les deux
        faces.
        """
        from pyqtgraph.opengl import shaders as sh
        name = "anticythere"
        if name not in sh.ShaderProgram.names:
            sh.ShaderProgram(name, [
                sh.VertexShader("""
                    uniform mat4 u_mvp;
                    uniform mat3 u_normal;
                    attribute vec4 a_position;
                    attribute vec3 a_normal;
                    attribute vec4 a_color;
                    varying vec4 v_color;
                    varying vec3 v_normal;
                    void main() {
                        v_normal = normalize(u_normal * a_normal);
                        v_color = a_color;
                        gl_Position = u_mvp * a_position;
                    }
                """),
                sh.FragmentShader("""
                    #ifdef GL_ES
                    precision mediump float;
                    #endif
                    varying vec4 v_color;
                    varying vec3 v_normal;
                    void main() {
                        vec3 n = normalize(v_normal);
                        float d = abs(dot(n, normalize(vec3(0.35, 0.55, 1.0))));
                        vec3 rgb = v_color.rgb * (0.55 + 0.50 * d);
                        gl_FragColor = vec4(min(rgb, vec3(1.0)), v_color.a);
                    }
                """)])
        return name

    try:
        SHADER = _register_shader()
    except Exception:                               # pragma: no cover
        SHADER = "shaded"

    def _closest_ray_segment(o, d, a, b) -> float:
        """Distance minimale entre le rayon o + t·d (t ≥ 0) et le segment [a, b]."""
        u = b - a
        w0 = o - a
        aa, bb, cc = float(d @ d), float(d @ u), float(u @ u)
        dd, ee = float(d @ w0), float(u @ w0)
        den = aa * cc - bb * bb
        if den < 1e-12:                         # rayon parallèle au segment
            t, s = 0.0, (ee / cc if cc > 0 else 0.0)
        else:
            t = (bb * ee - cc * dd) / den
            s = (aa * ee - bb * dd) / den
        s = min(1.0, max(0.0, s))
        t = max(0.0, float(((a + s * u - o) @ d) / aa))
        return float(np.linalg.norm(o + t * d - (a + s * u)))

    class GLMechanismView(gl.GLViewWidget):
        """Rendu 3D : une pièce = un GLMeshItem, animé par une matrice."""

        #: la poignée de la manivelle a été tournée de ce nombre de tours
        #: (tours de la roue a1, signe trigonométrique autour de +z)
        crank_turned = QtCore.pyqtSignal(float)

        #: rayon de saisie autour de la poignée (mm dans la scène, px à l'écran)
        GRAB_MM = 7.0
        GRAB_PX = 22.0

        def __init__(self, parent=None):
            # rotationMethod='quaternion' : rotation LIBRE dans tous les sens.
            # En mode 'euler' (défaut), l'élévation est bloquée à ±90° et on ne
            # peut pas retourner l'objet.
            super().__init__(parent, rotationMethod="quaternion")
            self.setCameraPosition(distance=360, elevation=24, azimuth=-62)
            self.opts["center"] = QtGui.QVector3D(*lay.CENTER)
            self.setBackgroundColor(_qcolor(lay.BACKGROUND))
            self.setMouseTracking(True)          # survol de la poignée
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
            #: pièces solidaires de la façade : (objet, matrice de base). Elles
            #: avancent avec l'étage 1 quand on éclate la machine.
            self._front: list = []
            self._walls = None
            self._crank = None
            self._angles: dict[str, float] = {}
            self._carrier = 0.0
            self._pointer_turns = (0.0, 0.0, 0.0, 0.0)
            self._planet_turns: tuple = ({}, 0.0, 0.0)
            self._dial_cache: dict = {}
            self._grab = None                    # angle courant pendant la saisie
            self._last_pos = None
            self.dial_lang = "fr"
            self.build()

        # ------------------------------------------------------- construction
        def _add(self, mesh, color, draw_edges=False):
            v, f = mesh
            md = gl.MeshData(vertexes=v, faces=f)
            item = gl.GLMeshItem(meshdata=md, smooth=False, shader=SHADER,
                                 color=color, drawEdges=draw_edges,
                                 edgeColor=(0, 0, 0, 0.25),
                                 glOptions="opaque" if color[3] >= 0.99
                                 else "translucent")
            self.addItem(item)
            return item

        def _front_item(self, item, base: QtGui.QMatrix4x4 | None = None):
            """Déclare une pièce solidaire de la façade (suit l'éclatement)."""
            self._front.append((item, QtGui.QMatrix4x4(base) if base is not None
                                else QtGui.QMatrix4x4()))
            return item

        def build(self):
            from .kinematics import TEETH

            for it in list(self.items):
                self.removeItem(it)
            self._gears.clear(); self._arbors.clear()
            self._pointers.clear(); self._case.clear(); self._plates.clear()
            self._dials.clear(); self._front.clear()

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

            # Arbres : un cylindre de hauteur UNITÉ, que set_angles étire entre
            # les bornes de lay.arbor_span. À l'éclatement, ils s'allongent avec
            # la pile au lieu de laisser les roues flotter.
            for arbor in lay.ARBORS:
                mesh = geo.cylinder_mesh(lay.ARBOR_RADIUS, 0.0, 1.0, segments=14)
                self._arbors[arbor] = self._add(mesh, lay.COLORS["arbor"])

            # plans de référence de la façade et du dos (machine montée)
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
            z_cosmos = zf + 9.5
            for idx, (pname, radius, color) in enumerate(lay.COSMOS_RINGS):
                zr = z_cosmos + 0.12 * idx
                ring = self._add(geo.disc_mesh(radius + 1.1, zr, 0.8,
                                               inner=radius - 1.1),
                                 (color[0], color[1], color[2], 0.95))
                self._front_item(ring)
                self._planet_rings[pname] = (ring, radius, zr)
                ball = self._add(geo.sphere_mesh(3.1, 0.0), color)
                self._planet_balls[pname] = (ball, radius, zr)

            # anneau du zodiaque, visible même machine ouverte
            self._dials = [self._front_item(self._add(
                geo.disc_mesh(112.0, zf - 2.0, 1.2, inner=96.0),
                lay.COLORS["dial"]))]
            self._dials.append(self._front_item(self._add(
                geo.disc_mesh(14.0, zf - 2.0, 1.6, inner=3.0),
                lay.COLORS["dial"])))
            self._dials.append(self._add(
                geo.spiral_mesh(5, 235, 22.0, 58.0, zb + 1.2),
                lay.COLORS["metonic"]))
            self._dials.append(self._add(
                geo.spiral_mesh(4, 223, 20.0, 52.0, zb - 6.0),
                lay.COLORS["saros"]))

            # platines : plaques de bois intérieures qui portent les arbres ;
            # celle de devant suit la façade
            for k, z in enumerate((lay.level_z(1) + 4.0, lay.level_z(16) - 5.0)):
                plate = self._add(
                    geo.translate(geo.plate_mesh(lay.CASE_WIDTH - 24.0,
                                                 lay.CASE_HEIGHT - 24.0, z, 1.5),
                                  lay.CASE_CX, lay.CASE_CY, 0.0),
                    lay.COLORS["plate"])
                if k == 0:
                    self._front_item(plate)
                self._plates.append(plate)

            self._build_case(zf, zb)
            self._build_crank()
            self.apply_visibility()
            self._apply_explode()

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
            if which == "front":
                self._front_item(item, m)
            return item

        # --------------------------------------------------------- boîtier
        def _build_case(self, zf: float, zb: float):
            """La machine FERMÉE : coffret de bois, plaques de bronze gravées.
            Tout ceci disparaît d'un clic."""
            W, H = lay.CASE_WIDTH, lay.CASE_HEIGHT
            cx, cy = lay.CASE_CX, lay.CASE_CY
            wood = (0.40, 0.27, 0.15, 1.0)
            bronze = (0.62, 0.50, 0.24, 1.0)
            z_front, z_back = self.z_front, self.z_back

            # coffret de bois : quatre flancs (étirés par l'éclatement) + fond
            self._walls = self._add(
                geo.translate(geo.case_mesh(W, H, (z_front - z_back), wall=6.0),
                              cx, cy, (z_front + z_back) / 2.0), wood)
            self._case = [self._walls]
            self._case.append(self._add(
                geo.translate(geo.plate_mesh(W, H, z_back, 3.0),
                              cx, cy, 0.0), wood))
            # façade de bronze pleine : c'est elle qui porte les cadrans
            self._case.append(self._front_item(self._add(
                geo.translate(geo.plate_mesh(W, H, z_front - 3.0, 3.0),
                              cx, cy, 0.0), bronze)))
            # cadrans gravés : de vraies textures, avec les inscriptions
            # grecques. Un disque de bronze et quelques traits en volume ne
            # rendraient jamais ΚΡΙΟΣ ni ΜΕΤΩΝ lisibles.
            self._add_dial_texture("front", lay.FRONT_DIAL_SPAN,
                                   z_front + 0.6, 0.0, 0.0)
            self._add_dial_texture("back", lay.BACK_DIAL_SPAN,
                                   z_back - 0.6, cx, cy, flip=True)
            # bille bicolore de la phase de Lune
            self._case.append(self._front_item(self._add(
                geo.sphere_mesh(7.0, z_front + 7.0), (0.92, 0.90, 0.84, 1.0))))

        def _build_crank(self):
            """La manivelle, dans l'axe de la roue a1. Elle reste visible sans
            l'enveloppe : c'est la seule commande de la machine, et on la
            saisit à la souris."""
            self._crank_z0 = self.z_front - 2.0
            self._crank = self._add(
                geo.crank_mesh(self._crank_z0, shaft_len=lay.CRANK_SHAFT,
                               arm=lay.CRANK_ARM, handle=lay.CRANK_HANDLE),
                (0.55, 0.42, 0.20, 1.0))

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

        # -------------------------------------------------------- éclatement
        def set_explode(self, value: float):
            """Éclate la machine LE LONG DES ARBRES (0 = montée, 1 = éclatée).

            Seule la profondeur change : chaque roue garde sa place dans son
            plan, les roues qui s'engrènent restent dans le même plan, les
            arbres s'allongent, la façade et ses cadrans avancent avec
            l'étage 1, le fond reste en place.
            """
            avant = lay.center(self.explode)
            self.explode = max(0.0, min(1.0, float(value)))
            self._apply_explode()
            self.set_angles(self._angles, self._carrier)
            self.set_pointers(*self._pointer_turns)
            self.set_planets(*self._planet_turns)
            # la caméra suit le milieu de la pile, sans perdre un déplacement
            # que l'utilisateur aurait fait
            apres = lay.center(self.explode)
            self.opts["center"] += QtGui.QVector3D(*(b - a for a, b in
                                                     zip(avant, apres)))
            self.update()

        def _apply_explode(self):
            dz = lay.front_shift(self.explode)
            for item, base in self._front:
                m = QtGui.QMatrix4x4()
                m.translate(0.0, 0.0, dz)
                item.setTransform(m * base)
            if self._walls is not None:
                # les flancs s'étirent du fond (fixe) jusqu'à la façade
                k = (self.z_front + dz - self.z_back) / (self.z_front - self.z_back)
                m = QtGui.QMatrix4x4()
                m.translate(0.0, 0.0, self.z_back)
                m.scale(1.0, 1.0, k)
                m.translate(0.0, 0.0, -self.z_back)
                self._walls.setTransform(m)

        # ---------------------------------------------------------- animation
        def set_angles(self, angles: dict, carrier_turns: float):
            """Place chaque pièce : rotation propre + orbite du porte-satellite."""
            self._angles = angles
            self._carrier = carrier_turns

            for name, item in self._gears.items():
                x, y, z = lay.gear_placement(name, self.explode, carrier_turns)
                m = QtGui.QMatrix4x4()
                m.translate(x, y, z)
                m.rotate(360.0 * angles.get(name, 0.0), 0.0, 0.0, 1.0)
                item.setTransform(m)

            for arbor, item in self._arbors.items():
                x, y = lay.ARBORS[arbor]
                if arbor in ("k", "K"):
                    x, y = lay.orbit(x, y, carrier_turns)
                z0, z1 = lay.arbor_span(arbor, self.explode)
                m = QtGui.QMatrix4x4()
                m.translate(x, y, z0)
                m.scale(1.0, 1.0, z1 - z0)
                item.setTransform(m)

            # la manivelle tourne avec la roue a1, dont elle est l'axe
            if self._crank is not None:
                ax, ay = lay.ARBORS["a"]
                m = QtGui.QMatrix4x4()
                m.translate(ax, ay, lay.front_shift(self.explode))
                m.rotate(360.0 * angles.get("a1", 0.0), 0.0, 0.0, 1.0)
                self._crank.setTransform(m)

        def set_planets(self, planets: dict, moon_turns: float,
                        sun_turns: float):
            """Place la petite sphère de chaque anneau du Cosmos."""
            self._planet_turns = (planets, moon_turns, sun_turns)
            values = dict(planets)
            values["moon"] = moon_turns
            values["sun"] = sun_turns
            dz = lay.front_shift(self.explode)
            for pname, (ball, radius, zr) in self._planet_balls.items():
                turns = values.get(pname, 0.0)
                m = QtGui.QMatrix4x4()
                m.translate(0.0, 0.0, zr + 2.2 + dz)
                m.rotate(-360.0 * turns, 0.0, 0.0, 1.0)
                m.translate(radius, 0.0, 0.0)
                ball.setTransform(m)

        def set_pointers(self, sun_turns, moon_turns, metonic_turns, saros_turns):
            self._pointer_turns = (sun_turns, moon_turns, metonic_turns,
                                   saros_turns)
            zb = self.z_back
            zf = self.z_front + lay.front_shift(self.explode)
            # chaque aiguille tourne autour du centre de SON cadran : celles du
            # dos ne sont pas sur l'axe central, mais au cœur de leur spirale.
            specs = (
                ("sun", sun_turns, 0.0, 0.0, zf + 11.0, 1.0),
                ("moon", moon_turns, 0.0, 0.0, zf + 13.0, 1.0),
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

        # ------------------------------------------------ manivelle à la souris
        def _mvp(self) -> QtGui.QMatrix4x4:
            w, h = max(1, self.width()), max(1, self.height())
            return self.projectionMatrix((0, 0, w, h), (0, 0, w, h)) \
                * self.viewMatrix()

        def mouse_ray(self, pos: QtCore.QPointF):
            """Lancer de rayon : origine et direction (monde) sous la souris."""
            w, h = max(1, self.width()), max(1, self.height())
            inv, ok = self._mvp().inverted()
            if not ok:
                return None
            x = 2.0 * pos.x() / w - 1.0
            y = 1.0 - 2.0 * pos.y() / h
            pts = []
            for zn in (-1.0, 1.0):
                v = inv.map(QtGui.QVector4D(x, y, zn, 1.0))
                if abs(v.w()) < 1e-12:
                    return None
                pts.append(np.array([v.x(), v.y(), v.z()]) / v.w())
            d = pts[1] - pts[0]
            n = np.linalg.norm(d)
            return (pts[0], d / n) if n > 0 else None

        def project(self, p) -> QtCore.QPointF | None:
            """Point de la scène -> pixel de la vue (None s'il est derrière)."""
            v = self._mvp().map(QtGui.QVector4D(float(p[0]), float(p[1]),
                                                float(p[2]), 1.0))
            if v.w() <= 1e-9:
                return None
            w, h = self.width(), self.height()
            return QtCore.QPointF((v.x() / v.w() + 1.0) * 0.5 * w,
                                  (1.0 - v.y() / v.w()) * 0.5 * h)

        def crank_axis(self):
            """Centre de l'axe de la manivelle et hauteur de la poignée."""
            ax, ay = lay.ARBORS["a"]
            z = self._crank_z0 + lay.front_shift(self.explode)
            return ax, ay, z

        def crank_grip_z(self) -> float:
            """Hauteur du milieu de la poignée : c'est dans ce plan qu'on
            mesure l'angle de la main."""
            a, b = self.crank_handle()
            return float((a[2] + b[2]) / 2.0)

        def crank_handle(self):
            """Segment de la poignée (deux points du monde), angle courant."""
            ax, ay, z = self.crank_axis()
            a = 2.0 * math.pi * self._angles.get("a1", 0.0)
            hx = ax + lay.CRANK_RADIUS * math.cos(a)
            hy = ay + lay.CRANK_RADIUS * math.sin(a)
            z0 = z + lay.CRANK_SHAFT + 4.0
            z1 = z0 + lay.CRANK_HANDLE + 6.0
            return np.array([hx, hy, z0]), np.array([hx, hy, z1])

        def hit_crank(self, pos: QtCore.QPointF) -> bool:
            """La souris est-elle sur la poignée ou le bras de la manivelle ?

            Lancer de rayon contre la poignée et le bras (rayon de saisie
            GRAB_MM), complété par une zone de GRAB_PX pixels autour de la
            poignée projetée : de loin, la poignée ne fait que quelques pixels.
            """
            if self._crank is None or not self._crank.visible():
                return False
            a, b = self.crank_handle()
            ray = self.mouse_ray(pos)
            if ray is not None:
                o, d = ray
                ax, ay, z = self.crank_axis()
                arm0 = np.array([ax, ay, z + lay.CRANK_SHAFT + 2.0])
                arm1 = np.array([a[0], a[1], arm0[2]])
                if (_closest_ray_segment(o, d, a, b) <= self.GRAB_MM
                        or _closest_ray_segment(o, d, arm0, arm1)
                        <= self.GRAB_MM * 0.7):
                    return True
            for p in (a, b, (a + b) / 2.0):
                s = self.project(p)
                if s is not None and math.hypot(s.x() - pos.x(),
                                                s.y() - pos.y()) <= self.GRAB_PX:
                    return True
            return False

        def crank_angle_at(self, pos: QtCore.QPointF) -> float | None:
            """Angle (radians, sens trigonométrique autour de +z) de la souris
            autour de l'axe de la manivelle.

            On coupe le rayon par le plan de la poignée ; si ce plan est vu par
            la tranche, on mesure l'angle à l'écran autour de l'axe projeté,
            en tenant compte du côté d'où l'on regarde.
            """
            ax, ay, _ = self.crank_axis()
            zh = self.crank_grip_z()
            ray = self.mouse_ray(pos)
            if ray is not None:
                o, d = ray
                if abs(d[2]) > 0.2:
                    t = (zh - o[2]) / d[2]
                    if t > 0:
                        px, py = o[0] + t * d[0], o[1] + t * d[1]
                        if math.hypot(px - ax, py - ay) > 1.0:
                            return math.atan2(py - ay, px - ax)
            c = self.project((ax, ay, zh))
            if c is None:
                return None
            ang = math.atan2(-(pos.y() - c.y()), pos.x() - c.x())
            cam = self.cameraPosition()
            return ang if cam.z() >= zh else -ang

        def mousePressEvent(self, ev):
            pos = ev.position()
            self._last_pos = pos
            if (ev.button() == QtCore.Qt.MouseButton.LeftButton
                    and self.hit_crank(pos)):
                self._grab = self.crank_angle_at(pos)
                self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
                ev.accept()
                return
            self._grab = None
            super().mousePressEvent(ev)

        def mouseMoveEvent(self, ev):
            pos = ev.position()
            buttons = ev.buttons()
            if self._grab is not None and buttons & QtCore.Qt.MouseButton.LeftButton:
                ang = self.crank_angle_at(pos)
                if ang is not None:
                    d = (ang - self._grab + math.pi) % (2.0 * math.pi) - math.pi
                    self._grab = ang
                    if d:
                        self.crank_turned.emit(d / (2.0 * math.pi))
                self._last_pos = pos
                ev.accept()
                return
            if buttons == QtCore.Qt.MouseButton.NoButton:
                # survol : la main ouverte annonce qu'on peut saisir
                if self.hit_crank(pos):
                    self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
                else:
                    self.unsetCursor()
                self._last_pos = pos
                return
            if buttons == QtCore.Qt.MouseButton.RightButton:
                # clic droit glissé = déplacer la scène
                last = self._last_pos or pos
                self.pan(pos.x() - last.x(), pos.y() - last.y(), 0.0,
                         relative="view")
                self._last_pos = pos
                self.mousePos = pos
                return
            self._last_pos = pos
            super().mouseMoveEvent(ev)

        def mouseReleaseEvent(self, ev):
            if self._grab is not None:
                self._grab = None
                self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor
                               if self.hit_crank(ev.position())
                               else QtCore.Qt.CursorShape.ArrowCursor)
                ev.accept()
                return
            super().mouseReleaseEvent(ev)

        def mouseDoubleClickEvent(self, ev):
            self.reset_view()

        def wheelEvent(self, ev):
            """Molette = zoom, borné. Celle de pyqtgraph lisait d'abord l'axe
            HORIZONTAL (un pavé tactile zoomait en glissant de côté) et ne
            bornait rien : on pouvait traverser la machine ou la perdre."""
            dy = ev.angleDelta().y()
            if dy == 0:
                dy = ev.pixelDelta().y() * 4
            if dy == 0:
                ev.ignore()
                return
            self.zoom(0.999 ** dy)
            ev.accept()

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
            self.opts["center"] = QtGui.QVector3D(*lay.center(self.explode))
            self.update()


# ---------------------------------------------------------------------------
