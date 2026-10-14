"""
Rendu **vectoriel** du mécanisme : dessin QPainter antialiasé, avec les
dentures réelles, exportable en **SVG** et en **PDF** — donc sans aucun pixel,
zoomable à l'infini.

Vector rendering of the movement: antialiased QPainter drawing using the real
tooth outlines, exportable to **SVG** and **PDF** — no pixels at all.

Ce mode a un avantage que la 3D n'a pas : la sortie est un fichier de courbes,
imprimable en A0 sans perdre une dent. Il est aussi le repli automatique quand
OpenGL n'est pas disponible.
"""

from __future__ import annotations

import math

from PyQt6 import QtCore, QtGui, QtWidgets

from . import geometry as geo
from . import layout as lay

try:
    from PyQt6 import QtSvg
    HAS_SVG = True
except Exception:                                    # pragma: no cover
    QtSvg = None
    HAS_SVG = False


def _qcolor(rgba, alpha: float | None = None) -> QtGui.QColor:
    c = QtGui.QColor.fromRgbF(*rgba[:3], rgba[3] if len(rgba) > 3 else 1.0)
    if alpha is not None:
        c.setAlphaF(alpha)
    return c


class VectorView(QtWidgets.QWidget):
    """Vue vectorielle, face avant ou arrière, avec zoom et déplacement."""

    #: la poignée de la manivelle a été tournée de ce nombre de tours
    #: (tours de la roue a1, sens trigonométrique) — même signal qu'en 3D
    crank_turned = QtCore.pyqtSignal(float)

    #: rayon de saisie autour de la poignée, en mm et au minimum en pixels
    GRAB_MM = 7.0
    GRAB_PX = 14.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 400)
        self.setMouseTracking(True)
        self.profile = "triangular"
        self.dial_lang = "fr"
        self.face = "front"            # 'front' | 'back' | 'all'
        self.highlight = None
        self.show_case = True
        self.show_plates = True
        self.show_labels = True
        # L'éclatement se fait LE LONG DES ARBRES, c'est-à-dire dans l'axe de
        # visée de ce rendu : il n'y a rien à y montrer. Le curseur est grisé
        # par la fenêtre en mode vectoriel ; l'attribut reste pour l'interface.
        self.explode = 0.0
        self._angles: dict[str, float] = {}
        self._carrier = 0.0
        self._pointers = (0.0, 0.0, 0.0, 0.0)
        self._planets: dict[str, float] = {}
        self._zoom = 1.0
        self._pan = QtCore.QPointF(0.0, 0.0)
        self._rot = 0.0                 # rotation du plan, en degrés
        self._drag = None
        self._drag_button = None
        self._grab = None               # angle de la souris pendant la saisie
        self._outlines: dict[str, QtGui.QPolygonF] = {}
        self._build_outlines()

    # ------------------------------------------------------- géométrie 2D
    def _build_outlines(self):
        """Polygones locaux, calculés une seule fois puis simplement transformés."""
        from .kinematics import TEETH

        self._outlines.clear()
        for name in lay.LEVELS:
            pts = geo.gear_outline(TEETH[name], lay.MODULE, self.profile)
            poly = QtGui.QPolygonF([QtCore.QPointF(float(x), float(y))
                                    for x, y in pts])
            self._outlines[name] = poly

    def set_profile(self, profile: str):
        if profile != self.profile:
            self.profile = profile
            self._build_outlines()
            self.update()

    # ------------------------------------------------------------ interface
    def apply_visibility(self):
        self.update()

    def set_angles(self, angles: dict, carrier_turns: float):
        self._angles = angles
        self._carrier = carrier_turns
        self.update()

    def set_pointers(self, sun, moon, metonic, saros):
        self._pointers = (sun, moon, metonic, saros)
        self.update()

    def set_planets(self, planets: dict, moon_turns: float, sun_turns: float):
        self._planets = dict(planets)
        self._planets["moon"] = moon_turns
        self._planets["sun"] = sun_turns
        self.update()

    def look_at(self, mode: str):
        self.face = {"front": "front", "back": "back"}.get(mode, "all")
        self.update()

    def set_explode(self, value: float):
        """Sans effet visible ici (l'éclatement est dans l'axe de visée)."""
        self.explode = max(0.0, min(1.0, float(value)))

    # ------------------------------------------------------------ repère
    def _span_scale(self, width: float, height: float, for_export: bool) -> float:
        span = 345.0
        return min(width / span, height / (span * 0.92)) * (
            1.0 if for_export else self._zoom)

    def scene_transform(self, width: float, height: float,
                        for_export: bool = False) -> QtGui.QTransform:
        """Repère scène (mm, y vers le haut) -> pixels. Sert au dessin ET à la
        souris : la poignée saisie est exactement celle qui est dessinée."""
        scale = self._span_scale(width, height, for_export)
        t = QtGui.QTransform()
        if not for_export:
            t.translate(self._pan.x(), self._pan.y())
        t.translate(width / 2.0, height / 2.0)
        if self._rot:
            t.rotate(self._rot)
        t.scale(scale, -scale)                   # y vers le haut
        t.translate(-60.0, 0.0)                  # recentre le nuage de roues
        return t

    def to_scene(self, pos: QtCore.QPointF) -> QtCore.QPointF:
        inv, ok = self.scene_transform(float(self.width()),
                                       float(self.height())).inverted()
        return inv.map(pos) if ok else QtCore.QPointF(0.0, 0.0)

    # --------------------------------------------------------- manivelle
    def crank_visible(self) -> bool:
        return self.face in ("front", "all")

    def crank_handle(self) -> tuple[float, float]:
        """Centre de la poignée dans le plan (mm)."""
        ax, ay = lay.ARBORS["a"]
        a = 2.0 * math.pi * self._angles.get("a1", 0.0)
        return (ax + lay.CRANK_RADIUS * math.cos(a),
                ay + lay.CRANK_RADIUS * math.sin(a))

    def hit_crank(self, pos: QtCore.QPointF) -> bool:
        if not self.crank_visible():
            return False
        p = self.to_scene(pos)
        hx, hy = self.crank_handle()
        scale = self._span_scale(float(self.width()), float(self.height()), False)
        rayon = max(self.GRAB_MM, self.GRAB_PX / max(scale, 1e-6))
        return math.hypot(p.x() - hx, p.y() - hy) <= rayon

    def crank_angle_at(self, pos: QtCore.QPointF) -> float:
        p = self.to_scene(pos)
        ax, ay = lay.ARBORS["a"]
        return math.atan2(p.y() - ay, p.x() - ax)

    # --------------------------------------------------------- interactions
    def wheelEvent(self, ev):
        if ev.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
            self.roll(ev.angleDelta().y() / 12.0)     # Ctrl + molette = pivoter
        else:
            self.zoom(1.0015 ** -ev.angleDelta().y())

    def mousePressEvent(self, ev):
        if (ev.button() == QtCore.Qt.MouseButton.LeftButton
                and self.hit_crank(ev.position())):
            # saisie de la manivelle : la faire tourner fait avancer la machine
            self._grab = self.crank_angle_at(ev.position())
            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
            return
        self._drag = ev.position()
        self._drag_button = ev.button()

    def mouseMoveEvent(self, ev):
        if self._grab is not None:
            ang = self.crank_angle_at(ev.position())
            d = (ang - self._grab + math.pi) % (2.0 * math.pi) - math.pi
            self._grab = ang
            if d:
                self.crank_turned.emit(d / (2.0 * math.pi))
            return
        if self._drag is None:
            if self.hit_crank(ev.position()):
                self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
            else:
                self.unsetCursor()
            return
        d = ev.position() - self._drag
        if self._drag_button == QtCore.Qt.MouseButton.RightButton:
            self.roll(d.x() * 0.4)                    # bouton droit = pivoter
        else:
            self._pan += d                            # bouton gauche = déplacer
        self._drag = ev.position()
        self.update()

    def mouseReleaseEvent(self, ev):
        self._drag = None
        self._drag_button = None
        if self._grab is not None:
            self._grab = None
            self.unsetCursor()

    def mouseDoubleClickEvent(self, ev):
        self.reset_view()

    # --- interface commune avec la vue 3D ---------------------------------
    def zoom(self, factor: float):
        self._zoom = max(0.15, min(self._zoom / factor, 40.0))
        self.update()

    def rotate(self, d_azim: float, d_elev: float):
        """En 2D il n'y a qu'un axe : on assimile la rotation à un pivot."""
        self.roll(d_azim)

    def roll(self, angle: float):
        self._rot = (self._rot + angle) % 360.0
        self.update()

    def reset_view(self):
        self._zoom = 1.0
        self._pan = QtCore.QPointF(0.0, 0.0)
        self._rot = 0.0
        self.update()

    # ------------------------------------------------------------- dessin
    def _gears_to_draw(self):
        if self.face == "front":
            keep = lambda lv: lv <= 7          # noqa: E731
        elif self.face == "back":
            keep = lambda lv: lv >= 8          # noqa: E731
        else:
            keep = lambda lv: True             # noqa: E731
        names = [n for n, lv in lay.LEVELS.items() if keep(lv)]
        # du plus profond au plus proche : l'étage 16 est au fond
        return sorted(names, key=lambda n: -lay.LEVELS[n])

    def render_to(self, painter: QtGui.QPainter, width: float, height: float,
                  for_export: bool = False):
        """Dessine la scène — utilisé par l'écran comme par les exports."""
        from .kinematics import TEETH

        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)
        painter.fillRect(QtCore.QRectF(0, 0, width, height),
                         _qcolor(lay.BACKGROUND))

        scale = self._span_scale(width, height, for_export)
        painter.save()
        painter.setTransform(self.scene_transform(width, height, for_export),
                             True)

        ink = _qcolor(lay.INK)
        ex, ey = lay.ARBORS["e"]
        ca = 2.0 * math.pi * self._carrier

        # --- cadrans -------------------------------------------------------
        if self.show_plates:
            self._draw_dials(painter, ink)

        # --- roues ---------------------------------------------------------
        for name in self._gears_to_draw():
            sub = lay.SUBSYSTEM_OF.get(name, "input")
            dim = bool(self.highlight and sub != self.highlight)
            x, y = lay.ARBORS[lay.ARBOR_OF[name]]
            if name in ("k1", "k2"):
                dx, dy = x - ex, y - ey
                c, s = math.cos(ca), math.sin(ca)
                x, y = ex + c * dx - s * dy, ey + s * dx + c * dy

            painter.save()
            painter.translate(x, y)
            painter.rotate(360.0 * self._angles.get(name, 0.0))

            base = _qcolor(lay.COLORS[sub])
            fill = QtGui.QColor(base)
            fill.setAlphaF(0.10 if dim else 0.30)
            pen = QtGui.QPen(base if not dim else _qcolor(lay.COLORS[sub], 0.20),
                             0.55 if not dim else 0.3)
            pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(fill)

            if name in lay.SPOKED:
                # roue à bras : jante ajourée obtenue par différence de chemins,
                # surtout PAS par un disque opaque, qui masquerait les roues
                # situées dessous.
                rp = lay.MODULE * TEETH[name] / 2.0
                outer = QtGui.QPainterPath()
                outer.addPolygon(self._outlines[name])
                outer.closeSubpath()
                hole = QtGui.QPainterPath()
                hole.addEllipse(QtCore.QPointF(0, 0), rp * 0.86, rp * 0.86)
                shape = outer.subtracted(hole)
                for k in range(lay.SPOKED[name]):
                    spoke = QtGui.QPainterPath()
                    a = 2.0 * math.pi * k / lay.SPOKED[name]
                    t = QtGui.QTransform()
                    t.rotateRadians(a)
                    spoke.addPolygon(t.map(QtGui.QPolygonF([
                        QtCore.QPointF(6.0, -3.5),
                        QtCore.QPointF(rp * 0.87, -3.5),
                        QtCore.QPointF(rp * 0.87, 3.5),
                        QtCore.QPointF(6.0, 3.5)])))
                    shape = shape.united(spoke)
                hub = QtGui.QPainterPath()
                hub.addEllipse(QtCore.QPointF(0, 0), 9.0, 9.0)
                painter.drawPath(shape.united(hub))
            else:
                painter.drawPolygon(self._outlines[name])

            # repère de rotation : un rayon, pour voir tourner la roue
            if not dim:
                painter.setPen(QtGui.QPen(base, 0.9))
                r = lay.MODULE * TEETH[name] / 2.0
                painter.drawLine(QtCore.QPointF(0, 0), QtCore.QPointF(r * 0.92, 0))
            painter.restore()

        # --- arbres --------------------------------------------------------
        painter.setPen(QtGui.QPen(ink, 0.4))
        painter.setBrush(_qcolor(lay.COLORS["arbor"]))
        for arbor, (x, y) in lay.ARBORS.items():
            if arbor in ("k", "K"):
                dx, dy = x - ex, y - ey
                c, s = math.cos(ca), math.sin(ca)
                x, y = ex + c * dx - s * dy, ey + s * dx + c * dy
            painter.drawEllipse(QtCore.QPointF(x, y), lay.ARBOR_RADIUS,
                                lay.ARBOR_RADIUS)

        # --- aiguilles et manivelle ----------------------------------------
        self._draw_pointers(painter)
        if self.crank_visible():
            self._draw_crank(painter)
        painter.restore()

        # --- légende des couleurs -------------------------------------------
        if self.show_labels:
            self._draw_legend(painter, width, height, for_export)

        # --- étiquettes (hors transformation : texte toujours à l'endroit) --
        if self.show_labels and not self._rot:
            # les étiquettes restent horizontales : on ne les dessine que si
            # le plan n'est pas pivoté, sinon elles ne suivraient pas les roues
            self._draw_labels(painter, width, height, scale, for_export)

    def _draw_dials(self, painter: QtGui.QPainter, ink):
        """Les cadrans gravés, en vectoriel pur.

        On appelle exactement le même code que pour la texture 3D, mais
        directement sur le painter : les inscriptions grecques restent donc
        des courbes, nettes à tout zoom et dans les exports SVG et PDF.
        """
        from . import dialface

        painter.save()
        # le repère de la vue a y vers le haut ; on le remet vers le bas le
        # temps du cadran, sinon toutes les lettres seraient en miroir
        painter.scale(1.0, -1.0)
        if self.face in ("front", "all"):
            dialface.paint_front_dial(painter, 0.0, 0.0, 122.0,
                                      lang=self.dial_lang)
        if self.face in ("back", "all"):
            painter.save()
            painter.translate(lay.CASE_CX, -lay.CASE_CY)
            # la vue vectorielle ne retourne pas la scène : le cadran doit
            # être dessiné dans le même sens que les roues qui l'entraînent
            dialface.paint_back_dial(painter, 0.0, 0.0, 128.0,
                                     lang=self.dial_lang,
                                     with_background=self.face == "back",
                                     mirrored=False)
            painter.restore()
        painter.restore()

    def _draw_pointers(self, painter: QtGui.QPainter):
        sun, moon, met, sar = self._pointers
        painter.save()
        # (turns, longueur, couleur, largeur, centre)
        specs = []
        if self.face in ("front", "all"):
            specs += [(sun, lay.SUN_HAND, lay.COLORS["input"], 3.2, (0.0, 0.0)),
                      (moon, lay.MOON_HAND, lay.COLORS["moon"], 2.4, (0.0, 0.0))]
        if self.face in ("back", "all"):
            specs += [(met, lay.METONIC_RADIUS, lay.COLORS["metonic"], 2.4,
                       lay.METONIC_CENTER),
                      (sar, lay.SAROS_RADIUS, lay.COLORS["saros"], 2.4,
                       lay.SAROS_CENTER)]
        for turns, length, color, wid, (px, py) in specs:
            painter.save()
            painter.translate(px, py)
            painter.rotate(-360.0 * turns)
            painter.setPen(QtGui.QPen(_qcolor(color), 0.6))
            painter.setBrush(_qcolor(color))
            poly = QtGui.QPolygonF([QtCore.QPointF(-6.0, -wid / 2),
                                    QtCore.QPointF(length, -wid / 4),
                                    QtCore.QPointF(length * 1.05, 0.0),
                                    QtCore.QPointF(length, wid / 4),
                                    QtCore.QPointF(-6.0, wid / 2)])
            painter.drawPolygon(poly)
            # moyeu : l'aiguille est fixée sur son axe
            painter.setBrush(_qcolor(lay.COLORS["arbor"]))
            painter.drawEllipse(QtCore.QPointF(0, 0), 4.2, 4.2)
            painter.restore()

        # le Cosmos : anneaux planétaires et leurs petites sphères
        if self.face in ("front", "all") and self._planets:
            for pname, radius, color in lay.COSMOS_RINGS:
                turns = self._planets.get(pname)
                if turns is None:
                    continue
                painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
                painter.setPen(QtGui.QPen(_qcolor(color, 0.8), 1.6))
                painter.drawEllipse(QtCore.QPointF(0, 0), radius, radius)
                a = 2.0 * math.pi * turns
                painter.setBrush(_qcolor(color))
                painter.setPen(QtGui.QPen(_qcolor(lay.INK), 0.4))
                painter.drawEllipse(
                    QtCore.QPointF(radius * math.cos(a), radius * math.sin(a)),
                    3.2, 3.2)
        painter.restore()

    def _draw_crank(self, painter: QtGui.QPainter):
        """La manivelle vue de face : bras et poignée, que l'on saisit."""
        ax, ay = lay.ARBORS["a"]
        hx, hy = self.crank_handle()
        wood = QtGui.QColor.fromRgbF(0.55, 0.42, 0.20, 1.0)
        painter.save()
        painter.setPen(QtGui.QPen(_qcolor(lay.INK), 0.5))
        painter.setBrush(wood)
        pen = QtGui.QPen(wood, 5.0)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QtCore.QPointF(ax, ay), QtCore.QPointF(hx, hy))
        painter.setPen(QtGui.QPen(_qcolor(lay.INK), 0.6))
        painter.drawEllipse(QtCore.QPointF(ax, ay), 4.0, 4.0)
        painter.drawEllipse(QtCore.QPointF(hx, hy), 5.0, 5.0)
        painter.restore()

    def _draw_legend(self, painter, width, height, for_export):
        """Légende des couleurs des sous-ensembles, dans la langue choisie."""
        from .i18n import tr
        keys = [k for k in ("input", "moon", "anomaly", "metonic",
                            "callippic", "saros", "exeligmos")]
        font = painter.font()
        font.setPointSizeF(8.0)
        painter.setFont(font)
        fm = QtGui.QFontMetricsF(font)
        line = fm.height() + 3.0
        x0, y0 = 10.0, 10.0
        w = max(fm.horizontalAdvance(tr(f"sub.{k}", self.dial_lang))
                for k in keys) + 34.0
        painter.save()
        painter.setPen(QtGui.QPen(_qcolor(lay.INK, 0.35), 0.8))
        painter.setBrush(_qcolor(lay.BACKGROUND, 0.88))
        painter.drawRoundedRect(QtCore.QRectF(x0, y0, w, line * len(keys) + 8),
                                4, 4)
        for i, k in enumerate(keys):
            y = y0 + 4 + i * line
            painter.setPen(QtGui.QPen(_qcolor(lay.INK, 0.6), 0.6))
            painter.setBrush(_qcolor(lay.COLORS[k]))
            painter.drawRect(QtCore.QRectF(x0 + 6, y + 2, 16, line - 6))
            painter.setPen(_qcolor(lay.INK))
            painter.drawText(QtCore.QPointF(x0 + 28, y + fm.ascent() + 1),
                             tr(f"sub.{k}", self.dial_lang))
        painter.restore()

    def _draw_labels(self, painter, width, height, scale, for_export):
        from .kinematics import TEETH

        font = painter.font()
        font.setPointSizeF(max(6.0, 7.0 if for_export else 7.5))
        painter.setFont(font)
        painter.setPen(_qcolor(lay.INK, 0.85))
        pan = QtCore.QPointF(0, 0) if for_export else self._pan
        for name in self._gears_to_draw():
            if self.highlight and lay.SUBSYSTEM_OF.get(name) != self.highlight:
                continue
            x, y = lay.ARBORS[lay.ARBOR_OF[name]]
            r = lay.MODULE * TEETH[name] / 2.0
            sx = pan.x() + width / 2.0 + (x - 60.0) * scale
            sy = pan.y() + height / 2.0 - (y + r * 0.72) * scale
            if -40 < sx < width + 40 and 0 < sy < height:
                painter.drawText(QtCore.QPointF(sx - 12, sy),
                                 f"{name} ({TEETH[name]})")

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        self.render_to(p, float(self.width()), float(self.height()))
        p.end()

    # ------------------------------------------------------------- exports
    def export_svg(self, path: str, width: float = 1400.0,
                   height: float = 1100.0) -> bool:
        """Écrit un SVG : courbes pures, zoomable sans limite."""
        if not HAS_SVG:
            return False
        gen = QtSvg.QSvgGenerator()
        gen.setFileName(path)
        gen.setSize(QtCore.QSize(int(width), int(height)))
        gen.setViewBox(QtCore.QRectF(0, 0, width, height))
        from .i18n import tr
        gen.setTitle(tr("app.title", self.dial_lang))
        gen.setDescription(tr("svg.description", self.dial_lang))
        p = QtGui.QPainter()
        if not p.begin(gen):
            return False
        self.render_to(p, width, height, for_export=True)
        p.end()
        return True

    def export_pdf(self, path: str) -> bool:
        """Écrit un PDF vectoriel A3 paysage."""
        writer = QtGui.QPdfWriter(path)
        writer.setPageSize(QtGui.QPageSize(QtGui.QPageSize.PageSizeId.A3))
        writer.setPageOrientation(QtGui.QPageLayout.Orientation.Landscape)
        writer.setResolution(600)
        p = QtGui.QPainter()
        if not p.begin(writer):
            return False
        w = float(writer.width())
        h = float(writer.height())
        self.render_to(p, w, h, for_export=True)
        p.end()
        return True
