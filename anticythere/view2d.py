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
        self.explode = 0.0             # sans effet en 2D, gardé pour l'interface
        self._angles: dict[str, float] = {}
        self._carrier = 0.0
        self._pointers = (0.0, 0.0, 0.0, 0.0)
        self._planets: dict[str, float] = {}
        self._zoom = 1.0
        self._pan = QtCore.QPointF(0.0, 0.0)
        self._rot = 0.0                 # rotation du plan, en degrés
        self._drag = None
        self._drag_button = None
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

    # --------------------------------------------------------- interactions
    def wheelEvent(self, ev):
        if ev.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
            self.roll(ev.angleDelta().y() / 12.0)     # Ctrl + molette = pivoter
        else:
            self.zoom(1.0015 ** -ev.angleDelta().y())

    def mousePressEvent(self, ev):
        self._drag = ev.position()
        self._drag_button = ev.button()

    def mouseMoveEvent(self, ev):
        if self._drag is None:
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

        span = 345.0
        scale = min(width / span, height / (span * 0.92)) * (
            1.0 if for_export else self._zoom)
        painter.save()
        if not for_export:
            painter.translate(self._pan)
        painter.translate(width / 2.0, height / 2.0)
        if self._rot:
            painter.rotate(self._rot)
        painter.scale(scale, -scale)             # y vers le haut
        painter.translate(-60.0, 0.0)            # recentre le nuage de roues

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

        # --- aiguilles -----------------------------------------------------
        self._draw_pointers(painter)
        painter.restore()

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
        gen.setTitle("Antikythera Mechanism")
        gen.setDescription("Vector rendering — Anticythere3D")
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
