"""
Fenêtre principale : vue 3D, commandes, report des cadrans, explications.
Main window: 3D view, controls, dial readings, explanations.
"""

from __future__ import annotations

import csv
import math
from datetime import datetime, timezone

from PyQt6 import QtCore, QtGui, QtWidgets

from . import astro
from . import layout as lay
from .i18n import (DEFAULT_LANG, GAMES_NAMES, LANGUAGES, PLANET_NAMES,
                   EGYPTIAN_MONTHS, phase_name, tr, zodiac_sign)
from .kinematics import PLANETS, RATIOS, TEETH, Mechanism
from .view2d import HAS_SVG, VectorView
from .view3d import MechanismView

SUBSYSTEM_KEYS = ["input", "moon", "anomaly", "metonic", "callippic",
                  "saros", "exeligmos"]


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, lang: str = DEFAULT_LANG):
        super().__init__()
        self.lang = lang

        # calage de la machine sur le ciel réel à J2000, puis on avance
        self.epoch_jd = astro.julian_day(
            datetime(2000, 1, 1, 12, tzinfo=timezone.utc))
        offs = astro.calibration_offsets(self.epoch_jd, None)
        offs["planets"] = astro.calibrate_planets(self.epoch_jd)
        self.mech = Mechanism(offsets=offs)
        now = datetime.now(timezone.utc)
        self.mech.days = astro.julian_day(now) - self.epoch_jd

        self._dial_prev = 0
        self._playing = False
        self._spinning = False

        # deux rendus : 3D temps réel, et vectoriel exportable en SVG/PDF
        self.view3d = MechanismView.create(self)
        self.view_vec = VectorView(self)
        self.stack = QtWidgets.QStackedWidget(self)
        self.stack.addWidget(self.view3d)
        self.stack.addWidget(self.view_vec)
        self.setCentralWidget(self.stack)
        self.view = self.view3d

        self._build_controls()
        self._build_readings()
        self._build_explanations()
        self._build_menus()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(33)

        self.status = self.statusBar()
        self.retranslate()
        self._setup_geometry()
        self.refresh()

    # ------------------------------------------------------- mise en place
    def _setup_geometry(self):
        """Dimensionne fenêtre et panneaux pour l'écran réel.

        Sans cela, sur un écran plus petit que la taille demandée, Qt comprime
        les panneaux : les commandes se chevauchent et le contenu est tronqué
        dès l'ouverture.
        """
        screen = QtWidgets.QApplication.primaryScreen()
        avail = (screen.availableGeometry() if screen
                 else QtCore.QRect(0, 0, 1280, 800))
        w = min(1560, int(avail.width() * 0.94))
        h = min(940, int(avail.height() * 0.94))
        self.resize(w, h)
        self.move(avail.left() + (avail.width() - w) // 2,
                  avail.top() + max(0, (avail.height() - h) // 2))

        # largeurs de départ : commandes à gauche, lectures à droite, le
        # reste pour la machine — qui doit garder la part du lion
        left = 340
        right = max(360, min(430, int(w * 0.28)))
        self.resizeDocks([self.dock_controls], [left],
                         QtCore.Qt.Orientation.Horizontal)
        self.resizeDocks([self.dock_readings, self.dock_expl], [right, right],
                         QtCore.Qt.Orientation.Horizontal)
        # les deux panneaux de droite se partagent la hauteur : le tableau des
        # cadrans un peu plus que les explications
        self.resizeDocks([self.dock_readings, self.dock_expl],
                         [int(h * 0.55), int(h * 0.45)],
                         QtCore.Qt.Orientation.Vertical)

    # ------------------------------------------------------------- panneaux
    def _dock(self, area, widget, objname, scroll: bool = False):
        """Ajoute un panneau. `scroll` l'enveloppe dans une zone défilante :
        sans cela, un panneau plus haut que la fenêtre voit son contenu
        tronqué ou écrasé au démarrage."""
        d = QtWidgets.QDockWidget(self)
        d.setObjectName(objname)
        if scroll:
            area_w = QtWidgets.QScrollArea()
            area_w.setWidgetResizable(True)
            area_w.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
            area_w.setHorizontalScrollBarPolicy(
                QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            area_w.setWidget(widget)
            d.setWidget(area_w)
        else:
            d.setWidget(widget)
        d.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable
                      | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self.addDockWidget(area, d)
        return d

    def _build_controls(self):
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)

        self.gb_crank = QtWidgets.QGroupBox()
        gv = QtWidgets.QVBoxLayout(self.gb_crank)
        self.dial = QtWidgets.QDial()
        self.dial.setRange(0, 359)
        self.dial.setWrapping(True)
        self.dial.setNotchesVisible(True)
        # un QDial doit rester carré, sinon il déborde sur ses voisins
        self.dial.setMinimumSize(128, 128)
        self.dial.setMaximumHeight(150)
        self.dial.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                QtWidgets.QSizePolicy.Policy.Fixed)
        self.dial.valueChanged.connect(self._crank_moved)
        gv.addWidget(self.dial)

        row = QtWidgets.QHBoxLayout()
        self.btn_play = QtWidgets.QPushButton()
        self.btn_play.setCheckable(True)
        self.btn_play.toggled.connect(self._toggle_play)
        row.addWidget(self.btn_play)
        self.btn_reset = QtWidgets.QPushButton()
        self.btn_reset.clicked.connect(self._reset)
        row.addWidget(self.btn_reset)
        gv.addLayout(row)

        self.lbl_speed = QtWidgets.QLabel()
        gv.addWidget(self.lbl_speed)
        self.speed = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.speed.setRange(1, 400)
        self.speed.setValue(40)
        gv.addWidget(self.speed)

        steps = QtWidgets.QHBoxLayout()
        self.btn_day = QtWidgets.QPushButton()
        self.btn_day.clicked.connect(lambda: self._step(1.0))
        self.btn_month = QtWidgets.QPushButton()
        self.btn_month.clicked.connect(lambda: self._step(29.530588853))
        self.btn_year = QtWidgets.QPushButton()
        self.btn_year.clicked.connect(lambda: self._step(365.24219))
        for b in (self.btn_day, self.btn_month, self.btn_year):
            steps.addWidget(b)
        gv.addLayout(steps)

        self.lbl_date = QtWidgets.QLabel()
        gv.addWidget(self.lbl_date)
        self.date_edit = QtWidgets.QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setDateRange(QtCore.QDate(1000, 1, 1),
                                    QtCore.QDate(3000, 1, 1))
        self.date_edit.setDate(QtCore.QDate.currentDate())
        gv.addWidget(self.date_edit)
        self.btn_goto = QtWidgets.QPushButton()
        self.btn_goto.clicked.connect(self._goto_date)
        gv.addWidget(self.btn_goto)
        v.addWidget(self.gb_crank)

        # ---- affichage
        self.gb_view = QtWidgets.QGroupBox()
        vv = QtWidgets.QVBoxLayout(self.gb_view)
        self.chk_case = QtWidgets.QCheckBox(); self.chk_case.setChecked(True)
        self.chk_plates = QtWidgets.QCheckBox(); self.chk_plates.setChecked(True)
        self.chk_labels = QtWidgets.QCheckBox(); self.chk_labels.setChecked(True)
        for c, attr in ((self.chk_case, "show_case"),
                        (self.chk_plates, "show_plates"),
                        (self.chk_labels, "show_labels")):
            c.toggled.connect(lambda st, a=attr: self._set_view_flag(a, st))
            vv.addWidget(c)

        self.lbl_explode = QtWidgets.QLabel()
        vv.addWidget(self.lbl_explode)
        self.sld_explode = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.sld_explode.setRange(0, 100)
        self.sld_explode.valueChanged.connect(self._set_explode)
        vv.addWidget(self.sld_explode)

        # ---- navigation : zoom, rotation, recentrage
        self.gb_nav = QtWidgets.QGroupBox()
        nv = QtWidgets.QVBoxLayout(self.gb_nav)
        zr = QtWidgets.QHBoxLayout()
        self.btn_zoom_in = QtWidgets.QPushButton("＋")
        self.btn_zoom_out = QtWidgets.QPushButton("－")
        self.btn_zoom_in.clicked.connect(lambda: self.view.zoom(0.8))
        self.btn_zoom_out.clicked.connect(lambda: self.view.zoom(1.25))
        zr.addWidget(self.btn_zoom_in); zr.addWidget(self.btn_zoom_out)
        self.btn_home = QtWidgets.QPushButton()
        self.btn_home.clicked.connect(lambda: self.view.reset_view())
        zr.addWidget(self.btn_home)
        nv.addLayout(zr)

        grid = QtWidgets.QGridLayout()
        self.btn_up = QtWidgets.QPushButton("▲")
        self.btn_down = QtWidgets.QPushButton("▼")
        self.btn_left = QtWidgets.QPushButton("◀")
        self.btn_right = QtWidgets.QPushButton("▶")
        self.btn_roll_l = QtWidgets.QPushButton("↺")
        self.btn_roll_r = QtWidgets.QPushButton("↻")
        self.btn_up.clicked.connect(lambda: self.view.rotate(0, 12))
        self.btn_down.clicked.connect(lambda: self.view.rotate(0, -12))
        self.btn_left.clicked.connect(lambda: self.view.rotate(-12, 0))
        self.btn_right.clicked.connect(lambda: self.view.rotate(12, 0))
        self.btn_roll_l.clicked.connect(lambda: self.view.roll(-12))
        self.btn_roll_r.clicked.connect(lambda: self.view.roll(12))
        for b in (self.btn_up, self.btn_down, self.btn_left, self.btn_right,
                  self.btn_roll_l, self.btn_roll_r, self.btn_zoom_in,
                  self.btn_zoom_out):
            b.setMaximumWidth(52)
        grid.addWidget(self.btn_roll_l, 0, 0)
        grid.addWidget(self.btn_up, 0, 1)
        grid.addWidget(self.btn_roll_r, 0, 2)
        grid.addWidget(self.btn_left, 1, 0)
        grid.addWidget(self.btn_down, 1, 1)
        grid.addWidget(self.btn_right, 1, 2)
        nv.addLayout(grid)

        self.chk_spin = QtWidgets.QCheckBox()
        self.chk_spin.toggled.connect(lambda s: setattr(self, "_spinning", s))
        nv.addWidget(self.chk_spin)
        self.lbl_nav_hint = QtWidgets.QLabel()
        self.lbl_nav_hint.setWordWrap(True)
        self.lbl_nav_hint.setStyleSheet("color:#555; font-size:10px;")
        nv.addWidget(self.lbl_nav_hint)
        v.addWidget(self.gb_nav)

        self.lbl_render = QtWidgets.QLabel()
        vv.addWidget(self.lbl_render)
        self.cmb_render = QtWidgets.QComboBox()
        self.cmb_render.addItems(["", ""])
        self.cmb_render.currentIndexChanged.connect(
            lambda i: self.set_render_mode("vector" if i else "3d"))
        vv.addWidget(self.cmb_render)

        self.lbl_profile = QtWidgets.QLabel()
        vv.addWidget(self.lbl_profile)
        self.cmb_profile = QtWidgets.QComboBox()
        self.cmb_profile.addItems(["", ""])
        self.cmb_profile.currentIndexChanged.connect(self._set_profile)
        vv.addWidget(self.cmb_profile)

        self.lbl_highlight = QtWidgets.QLabel()
        vv.addWidget(self.lbl_highlight)
        self.cmb_highlight = QtWidgets.QComboBox()
        self.cmb_highlight.currentIndexChanged.connect(self._set_highlight)
        vv.addWidget(self.cmb_highlight)
        v.addWidget(self.gb_view)
        v.addStretch(1)

        # largeur imposée au CONTENU, pas au panneau : le dock garde alors
        # une largeur cohérente et rien n'est comprimé au démarrage
        w.setMinimumWidth(300)
        self.dock_controls = self._dock(
            QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, w, "controls",
            scroll=True)
        self.dock_controls.setMinimumWidth(320)

    def _build_readings(self):
        self.table = QtWidgets.QTableWidget(0, 2)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumWidth(340)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.dock_readings = self._dock(
            QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.table, "readings")

    def _build_explanations(self):
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)
        self.lbl_expl = QtWidgets.QLabel()
        v.addWidget(self.lbl_expl)
        self.cmb_expl = QtWidgets.QComboBox()
        self.cmb_expl.currentIndexChanged.connect(self._show_explanation)
        v.addWidget(self.cmb_expl)
        self.txt_expl = QtWidgets.QTextBrowser()
        self.txt_expl.setMinimumHeight(180)
        v.addWidget(self.txt_expl)
        w.setMinimumWidth(340)
        self.dock_expl = self._dock(
            QtCore.Qt.DockWidgetArea.RightDockWidgetArea, w, "explanations")

    def _build_menus(self):
        mb = self.menuBar()
        self.m_file = mb.addMenu("")
        self.act_shot = self.m_file.addAction("", self._screenshot)
        self.act_svg = self.m_file.addAction("", self._export_svg)
        self.act_pdf = self.m_file.addAction("", self._export_pdf)
        self.act_svg.setEnabled(False)
        self.act_pdf.setEnabled(False)
        self.act_export = self.m_file.addAction("", self._export_csv)
        self.m_file.addSeparator()
        self.act_stl = self.m_file.addAction("", self._export_stl)
        self.m_file.addSeparator()
        self.act_quit = self.m_file.addAction("", self.close)
        self.act_quit.setShortcut("Ctrl+Q")

        self.m_eclipse = mb.addMenu("")
        self.act_eclipses = self.m_eclipse.addAction("", self._show_eclipses)
        self.act_eclipses.setShortcut("E")

        self.m_view = mb.addMenu("")
        self.act_front = self.m_view.addAction("", lambda: self.view.look_at("front"))
        self.act_back = self.m_view.addAction("", lambda: self.view.look_at("back"))
        self.act_iso = self.m_view.addAction("", lambda: self.view.look_at("iso"))
        self.act_front.setShortcut("F"); self.act_back.setShortcut("B")
        self.act_iso.setShortcut("I")

        self.m_lang = mb.addMenu("")
        self.lang_actions = {}
        grp = QtGui.QActionGroup(self)
        for code, label in LANGUAGES.items():
            a = QtGui.QAction(label, self, checkable=True)
            a.setChecked(code == self.lang)
            a.triggered.connect(lambda _c, k=code: self.set_language(k))
            grp.addAction(a); self.m_lang.addAction(a)
            self.lang_actions[code] = a

        self.m_help = mb.addMenu("")
        self.act_update = self.m_help.addAction(
            "", lambda: self._check_update(manual=True))
        self.m_help.addSeparator()
        self.act_manual = self.m_help.addAction("", lambda: self._help("manual"))
        self.act_science = self.m_help.addAction("", lambda: self._help("science"))
        self.act_keys = self.m_help.addAction("", lambda: self._help("shortcuts"))
        self.m_help.addSeparator()
        self.act_about = self.m_help.addAction("", lambda: self._help("about"))
        self.act_manual.setShortcut("F1")

    # ------------------------------------------------------------ traduction
    def retranslate(self):
        L = self.lang
        self.setWindowTitle(tr("app.title", L))
        self.gb_crank.setTitle(tr("ctrl.title", L))
        self.dial.setToolTip(tr("ctrl.crank.tip", L))
        self.btn_play.setText(tr("ctrl.pause" if self._playing else "ctrl.play", L))
        self.btn_play.setToolTip(tr("ctrl.play.tip", L))
        self.btn_reset.setText(tr("ctrl.reset", L))
        self.btn_reset.setToolTip(tr("ctrl.reset.tip", L))
        self.lbl_speed.setText(tr("ctrl.speed", L))
        self.speed.setToolTip(tr("ctrl.speed.tip", L))
        self.btn_day.setText(tr("ctrl.step.day", L))
        self.btn_month.setText(tr("ctrl.step.month", L))
        self.btn_year.setText(tr("ctrl.step.year", L))
        for b in (self.btn_day, self.btn_month, self.btn_year):
            b.setToolTip(tr("ctrl.warning.direction", L))
        self.lbl_date.setText(tr("ctrl.date", L))
        self.btn_goto.setText(tr("ctrl.goto", L))
        self.btn_goto.setToolTip(tr("ctrl.goto.tip", L))
        self.date_edit.setToolTip(tr("ctrl.date.tip", L))

        self.gb_nav.setTitle(tr("nav.title", L))
        self.btn_home.setText(tr("nav.home", L))
        self.btn_home.setToolTip(tr("nav.home.tip", L))
        self.btn_zoom_in.setToolTip(tr("nav.zoom.in", L))
        self.btn_zoom_out.setToolTip(tr("nav.zoom.out", L))
        for b, key in ((self.btn_up, "nav.up"), (self.btn_down, "nav.down"),
                       (self.btn_left, "nav.left"), (self.btn_right, "nav.right"),
                       (self.btn_roll_l, "nav.roll.left"),
                       (self.btn_roll_r, "nav.roll.right")):
            b.setToolTip(tr(key, L))
        self.chk_spin.setText(tr("view.spin", L))
        self.chk_spin.setToolTip(tr("nav.spin.tip", L))
        self.lbl_nav_hint.setText(tr("nav.hint", L))
        self.gb_view.setTitle(tr("view.title", L))
        self.chk_case.setText(tr("view.case", L))
        self.chk_case.setToolTip(tr("view.case.tip", L))
        self.chk_plates.setText(tr("view.plates", L))
        self.chk_plates.setToolTip(tr("view.plates.tip", L))
        self.chk_labels.setText(tr("view.labels", L))
        self.chk_labels.setToolTip(tr("view.labels.tip", L))
        self.lbl_explode.setText(tr("view.explode", L))
        self.sld_explode.setToolTip(tr("view.explode.tip", L))
        self.lbl_render.setText(tr("view.render", L))
        self.cmb_render.setToolTip(tr("view.render.tip", L))
        self.cmb_render.blockSignals(True)
        self.cmb_render.setItemText(0, tr("view.render.3d", L))
        self.cmb_render.setItemText(1, tr("view.render.vector", L))
        self.cmb_render.blockSignals(False)
        self.lbl_profile.setText(tr("view.profile", L))
        self.cmb_profile.setToolTip(tr("view.profile.tip", L))
        self.cmb_profile.blockSignals(True)
        self.cmb_profile.setItemText(0, tr("view.profile.triangular", L))
        self.cmb_profile.setItemText(1, tr("view.profile.involute", L))
        self.cmb_profile.blockSignals(False)

        self.lbl_highlight.setText(tr("view.highlight", L))
        self.cmb_highlight.setToolTip(tr("view.highlight.tip", L))
        self.cmb_highlight.blockSignals(True)
        cur = self.cmb_highlight.currentIndex()
        self.cmb_highlight.clear()
        self.cmb_highlight.addItem(tr("view.highlight.none", L))
        for k in SUBSYSTEM_KEYS:
            self.cmb_highlight.addItem(tr(f"sub.{k}", L))
        self.cmb_highlight.setCurrentIndex(max(cur, 0))
        self.cmb_highlight.blockSignals(False)

        self.lbl_expl.setText(tr("expl.select", L))
        self.cmb_expl.setToolTip(tr("expl.select.tip", L))
        self.cmb_expl.blockSignals(True)
        cur = self.cmb_expl.currentIndex()
        self.cmb_expl.clear()
        for k in SUBSYSTEM_KEYS:
            self.cmb_expl.addItem(tr(f"sub.{k}", L))
        self.cmb_expl.setCurrentIndex(max(cur, 0))
        self.cmb_expl.blockSignals(False)
        self._show_explanation()

        self.dock_controls.setWindowTitle(tr("ctrl.title", L))
        self.dock_readings.setWindowTitle(tr("dial.title", L))
        self.dock_expl.setWindowTitle(tr("expl.title", L))
        self.table.setHorizontalHeaderLabels(
            [tr("dial.title", L), tr("app.ready", L)])

        self.m_file.setTitle(tr("menu.file", L))
        self.act_shot.setText(tr("menu.file.screenshot", L))
        self.act_svg.setText(tr("menu.file.svg", L))
        self.act_pdf.setText(tr("menu.file.pdf", L))
        self.act_svg.setToolTip(tr("menu.file.svg.tip", L))
        self.act_pdf.setToolTip(tr("menu.file.svg.tip", L))
        self.act_export.setText(tr("menu.file.export", L))
        self.act_stl.setText(tr("menu.file.stl", L))
        self.act_stl.setToolTip(tr("menu.file.stl.tip", L))
        self.act_quit.setText(tr("menu.file.quit", L))
        self.m_eclipse.setTitle(tr("menu.eclipse", L))
        self.act_eclipses.setText(tr("menu.eclipse.next", L))
        self.act_eclipses.setToolTip(tr("menu.eclipse.tip", L))
        self.m_view.setTitle(tr("menu.view", L))
        self.act_front.setText(tr("menu.view.front", L))
        self.act_back.setText(tr("menu.view.back", L))
        self.act_iso.setText(tr("menu.view.iso", L))
        self.m_lang.setTitle(tr("menu.lang", L))
        self.m_help.setTitle(tr("menu.help", L))
        self.act_update.setText(tr("menu.help.update", L))
        self.act_update.setToolTip(tr("menu.help.update.tip", L))
        self.act_manual.setText(tr("menu.help.manual", L))
        self.act_science.setText(tr("menu.help.science", L))
        self.act_keys.setText(tr("menu.help.shortcuts", L))
        self.act_about.setText(tr("menu.help.about", L))
        self.refresh()

    def set_language(self, code: str):
        self.lang = code
        # les cadrans gravés portent les noms des signes dans la langue de
        # l'interface : il faut régénérer leurs textures, sinon ils restent
        # dans la langue de départ
        for v in (self.view3d, self.view_vec):
            v.dial_lang = code
        if hasattr(self.view3d, "build"):
            self.view3d.build()
            self.refresh()
        self.view_vec.update()
        self.retranslate()

    # ------------------------------------------------------------- commandes
    def _crank_moved(self, value: int):
        delta = value - self._dial_prev
        if delta > 180:
            delta -= 360
        elif delta < -180:
            delta += 360
        self._dial_prev = value
        self.mech.turns += delta / 360.0
        self.refresh()

    def _toggle_play(self, on: bool):
        self._playing = on
        self.btn_play.setText(tr("ctrl.pause" if on else "ctrl.play", self.lang))

    def _step(self, days: float):
        self.mech.advance_days(days)
        self.refresh()

    def _reset(self):
        self.mech.turns = 0.0
        self.refresh()

    def _goto_date(self):
        d = self.date_edit.date()
        dt = datetime(d.year(), d.month(), d.day(), 12, tzinfo=timezone.utc)
        self.mech.days = astro.julian_day(dt) - self.epoch_jd
        self.refresh()

    def set_render_mode(self, mode: str):
        """Bascule entre la 3D temps réel et le rendu vectoriel."""
        self.view = self.view_vec if mode == "vector" else self.view3d
        self.stack.setCurrentWidget(self.view)
        idx = 1 if mode == "vector" else 0
        if self.cmb_render.currentIndex() != idx:
            self.cmb_render.blockSignals(True)
            self.cmb_render.setCurrentIndex(idx)
            self.cmb_render.blockSignals(False)
        self.act_svg.setEnabled(mode == "vector" and HAS_SVG)
        self.act_pdf.setEnabled(mode == "vector")
        self.refresh()

    def _set_view_flag(self, attr: str, state: bool):
        for v in (self.view3d, self.view_vec):
            setattr(v, attr, state)
            v.apply_visibility()

    def _set_explode(self, value: int):
        for v in (self.view3d, self.view_vec):
            v.explode = value / 100.0
        self.refresh()

    def _set_profile(self, index: int):
        profile = "triangular" if index == 0 else "involute"
        for v in (self.view3d, self.view_vec):
            v.set_profile(profile)
        self.refresh()

    def _set_highlight(self, index: int):
        h = None if index <= 0 else SUBSYSTEM_KEYS[index - 1]
        for v in (self.view3d, self.view_vec):
            v.highlight = h
            v.apply_visibility()

    def _tick(self):
        if self._spinning:
            self.view.rotate(0.5, 0.0)
        if self._playing:
            self.mech.advance_days(self.speed.value() / 30.0)
            self.refresh()

    # ------------------------------------------------------------- clavier
    def keyPressEvent(self, ev):
        k = ev.key()
        K = QtCore.Qt.Key
        step = 15.0 if ev.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier \
            else 5.0
        if k in (K.Key_Plus, K.Key_Equal):
            self.view.zoom(0.85)
        elif k in (K.Key_Minus, K.Key_Underscore):
            self.view.zoom(1.18)
        elif k == K.Key_Left:
            self.view.rotate(-step, 0.0)
        elif k == K.Key_Right:
            self.view.rotate(step, 0.0)
        elif k == K.Key_Up:
            self.view.rotate(0.0, step)
        elif k == K.Key_Down:
            self.view.rotate(0.0, -step)
        elif k == K.Key_PageUp:
            self.view.roll(step)
        elif k == K.Key_PageDown:
            self.view.roll(-step)
        elif k == K.Key_R:
            self.view.reset_view()
        elif k == K.Key_Space:
            self.btn_play.toggle()
        else:
            super().keyPressEvent(ev)

    # -------------------------------------------------------------- affichage
    def refresh(self):
        o = self.mech.outputs()
        self.view.set_angles(self.mech.gear_angles(), o.carrier_e3)
        self.view.set_pointers(o.mean_sun, o.moon_true, o.metonic, o.saros)
        if hasattr(self.view, "set_planets"):
            self.view.set_planets(o.planets, o.moon_true, o.mean_sun)
        self._fill_table(o)
        self.status.showMessage(tr("status.turns", self.lang, turns=o.turns,
                                   days=o.days, years=o.days / 365.24219))

    def _row(self, label: str, value: str, tip: str = ""):
        r = self.table.rowCount()
        self.table.insertRow(r)
        a = QtWidgets.QTableWidgetItem(label)
        b = QtWidgets.QTableWidgetItem(value)
        if tip:
            a.setToolTip(tip); b.setToolTip(tip)
        f = a.font()
        if not value:
            f.setBold(True); a.setFont(f)
            a.setBackground(QtGui.QColor(60, 70, 90))
            b.setBackground(QtGui.QColor(60, 70, 90))
        self.table.setItem(r, 0, a)
        self.table.setItem(r, 1, b)

    def _fill_table(self, o):
        L = self.lang
        self.table.setRowCount(0)
        jd = self.epoch_jd + o.days
        dt = astro.from_julian_day(jd)

        self._row(tr("dial.front", L), "")
        self._row(tr("dial.date", L), dt.strftime("%d/%m/%Y"))
        doy = (jd - astro.julian_day(datetime(dt.year, 1, 1, tzinfo=timezone.utc)))
        eg = int(doy) % 365
        self._row(tr("dial.egyptian", L),
                  f"{EGYPTIAN_MONTHS[min(eg // 30, 11)]} {eg % 30 + 1}")

        sign, deg = zodiac_sign(o.mean_sun * 360.0, L)
        self._row(tr("dial.sun", L), f"{sign} {deg:.1f}°", tr("dial.sun.tip", L))
        sign, deg = zodiac_sign(o.moon_true * 360.0, L)
        self._row(tr("dial.moon", L), f"{sign} {deg:.1f}°", tr("dial.moon.tip", L))
        self._row(tr("dial.anomaly", L), f"{o.moon_anomaly_deg:+.2f}°",
                  tr("dial.anomaly.tip", L))
        self._row(tr("dial.phase", L),
                  f"{phase_name(o.phase_turns, L)} — {o.phase_illum * 100:.0f} %",
                  tr("dial.phase.tip", L))
        sign, deg = zodiac_sign(o.nodes * 360.0, L)
        self._row(tr("dial.nodes", L), f"{sign} {deg:.1f}°", tr("dial.nodes.tip", L))

        self._row(tr("dial.back", L), "")
        self._row(tr("dial.metonic", L),
                  tr("dial.metonic.cell", L, n=o.metonic_cell) + " — " +
                  tr("dial.metonic.year", L, n=o.metonic_year),
                  tr("dial.metonic.tip", L))
        self._row(tr("dial.callippic", L), f"{o.callippic_quarter}/4",
                  tr("dial.callippic.tip", L))
        self._row(tr("dial.games", L), GAMES_NAMES[L][o.games_name],
                  tr("dial.games.tip", L))
        self._row(tr("dial.saros", L), tr("dial.saros.cell", L, n=o.saros_cell),
                  tr("dial.saros.tip", L))
        self._row(tr("dial.exeligmos", L),
                  tr("dial.exeligmos.value", L, h=o.exeligmos_hours),
                  tr("dial.exeligmos.tip", L))

        ecl = astro.eclipse_possible(jd)
        if ecl["type"] == "solar":
            txt = tr("dial.eclipse.solar", L)
        elif ecl["type"] == "lunar":
            txt = tr("dial.eclipse.lunar", L)
        else:
            txt = tr("dial.eclipse.none", L)
        if ecl["certain"]:
            txt += " — " + tr("dial.eclipse.certain", L)
        self._row("☾ ☉", txt)

        self._row(tr("dial.planets", L), "")
        for key in PLANETS:
            sign, deg = zodiac_sign(o.planets[key] * 360.0, L)
            self._row("   " + PLANET_NAMES[L][key], f"{sign} {deg:.1f}°")

        self._row(tr("dial.compare", L), "")
        # la machine affiche le Soleil MOYEN : on la compare au Soleil moyen
        ds = (o.mean_sun * 360.0 - astro.sun_mean_longitude(jd) + 180) % 360 - 180
        dm = (o.moon_true * 360.0 - astro.moon_longitude(jd) + 180) % 360 - 180
        self._row("   " + tr("dial.sun", L), f"{ds:+.2f}°", tr("dial.compare.tip", L))
        self._row("   " + tr("dial.moon", L), f"{dm:+.2f}°", tr("dial.compare.tip", L))
        self.table.resizeColumnsToContents()

    def _show_explanation(self):
        idx = max(self.cmb_expl.currentIndex(), 0)
        key = SUBSYSTEM_KEYS[idx]
        title = tr(f"sub.{key}", self.lang)
        body = tr(f"expl.{key}", self.lang).replace("\n", "<br>")
        self.txt_expl.setHtml(
            f"<h3 style='color:#8ab4d8'>{title}</h3><p>{body}</p>")

    # -------------------------------------------------------- éclipses
    def _show_eclipses(self):
        """Liste les prochaines éclipses ; un double-clic y emmène la machine."""
        L = self.lang
        jd0 = self.epoch_jd + self.mech.days
        QtWidgets.QApplication.setOverrideCursor(
            QtCore.Qt.CursorShape.WaitCursor)
        try:
            events = astro.next_eclipses(jd0, count=12)
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle(tr("menu.eclipse.next", L))
        dlg.resize(660, 440)
        v = QtWidgets.QVBoxLayout(dlg)
        v.addWidget(QtWidgets.QLabel(tr("eclipse.intro", L)))
        table = QtWidgets.QTableWidget(len(events), 4)
        table.setHorizontalHeaderLabels([
            tr("dial.date", L), tr("eclipse.kind", L),
            tr("eclipse.node", L), tr("eclipse.quality", L)])
        table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        for r, e in enumerate(events):
            d = astro.from_julian_day(e["jd"])
            kind = tr("eclipse.solar" if e["type"] == "solar"
                      else "eclipse.lunar", L)
            qual = tr("eclipse.central" if e["certain"]
                      else "eclipse.partial", L)
            for c, txt in enumerate((d.strftime("%d/%m/%Y  %Hh%M UTC"), kind,
                                     f"{e['arg']:.2f}°", qual)):
                item = QtWidgets.QTableWidgetItem(txt)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, e["jd"])
                if e["type"] == "solar":
                    item.setForeground(QtGui.QColor(150, 90, 20))
                table.setItem(r, c, item)
        table.resizeColumnsToContents()
        table.doubleClicked.connect(
            lambda idx: self._goto_jd(
                table.item(idx.row(), 0).data(QtCore.Qt.ItemDataRole.UserRole)))
        v.addWidget(table)

        note = QtWidgets.QLabel(tr("eclipse.note", L))
        note.setWordWrap(True)
        note.setStyleSheet("color:#555; font-size:11px;")
        v.addWidget(note)

        bb = QtWidgets.QDialogButtonBox()
        go = bb.addButton(tr("eclipse.goto", L),
                          QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        bb.addButton(QtWidgets.QDialogButtonBox.StandardButton.Close)
        go.clicked.connect(lambda: (
            self._goto_jd(table.item(max(table.currentRow(), 0), 0)
                          .data(QtCore.Qt.ItemDataRole.UserRole)), dlg.close()))
        bb.rejected.connect(dlg.close)
        v.addWidget(bb)
        dlg.exec()

    def _goto_jd(self, jd: float):
        """Emmène la machine à une date donnée en jour julien."""
        if jd is None:
            return
        self.mech.days = jd - self.epoch_jd
        d = astro.from_julian_day(jd)
        self.date_edit.setDate(QtCore.QDate(d.year, d.month, d.day))
        self.refresh()

    # ------------------------------------------------------ mise à jour
    def _check_update(self, manual: bool = False):
        """Interroge GitHub sans bloquer l'interface."""
        from . import updater

        self._updater_thread = QtCore.QThread(self)
        self._updater_worker = _UpdateChecker()
        self._updater_worker.moveToThread(self._updater_thread)
        self._updater_thread.started.connect(self._updater_worker.run)
        self._updater_worker.done.connect(
            lambda state: self._update_result(state, manual))
        self._updater_worker.done.connect(self._updater_thread.quit)
        self._updater_thread.start()
        if manual:
            self.status.showMessage(tr("update.checking", self.lang))

    def _update_result(self, state: dict, manual: bool):
        from . import updater

        L = self.lang
        self.status.showMessage(updater.summary(state, L))
        if not state.get("available"):
            if manual:
                QtWidgets.QMessageBox.information(
                    self, tr("menu.help.update", L), updater.summary(state, L))
            return

        box = QtWidgets.QMessageBox(self)
        box.setWindowTitle(tr("menu.help.update", L))
        box.setText(tr("update.available", L, version=state["version"],
                       current=updater.current_version()))
        notes = (state.get("notes") or "").strip()
        if notes:
            box.setDetailedText(notes[:4000])
        if state.get("url"):
            box.setStandardButtons(
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No)
            box.button(QtWidgets.QMessageBox.StandardButton.Yes).setText(
                tr("update.install", L))
            box.button(QtWidgets.QMessageBox.StandardButton.No).setText(
                tr("update.later", L))
        else:
            box.setInformativeText(tr("update.manual", L))
            box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        if box.exec() != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        self._download_update(state)

    def _download_update(self, state: dict):
        from . import updater

        L = self.lang
        dlg = QtWidgets.QProgressDialog(
            tr("update.downloading", L), tr("ctrl.pause", L), 0, 100, self)
        dlg.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        dlg.setAutoClose(False)
        dlg.show()

        def progress(done, total):
            if total:
                dlg.setValue(int(100 * done / total))
            QtWidgets.QApplication.processEvents()

        try:
            path = updater.download(state["url"], progress=progress)
        except Exception as exc:                     # réseau, disque, droits
            dlg.close()
            QtWidgets.QMessageBox.warning(
                self, tr("menu.help.update", L),
                tr("update.failed", L, error=str(exc)))
            return
        dlg.close()

        if not updater.running_as_frozen():
            QtWidgets.QMessageBox.information(
                self, tr("menu.help.update", L),
                tr("update.downloaded", L, path=path))
            return
        if updater.apply_update(path):
            QtWidgets.QApplication.quit()
        else:
            QtWidgets.QMessageBox.warning(
                self, tr("menu.help.update", L),
                tr("update.failed", L, error=path))

    # ----------------------------------------------------------------- aide
    def _help(self, which: str):
        L = self.lang
        if which == "shortcuts":
            html = ("<h3>%s</h3><table>"
                    "<tr><td><b>F</b></td><td>%s</td></tr>"
                    "<tr><td><b>B</b></td><td>%s</td></tr>"
                    "<tr><td><b>I</b></td><td>%s</td></tr>"
                    "<tr><td><b>F1</b></td><td>%s</td></tr>"
                    "<tr><td><b>Ctrl+Q</b></td><td>%s</td></tr></table>"
                    % (tr("menu.help.shortcuts", L), tr("menu.view.front", L),
                       tr("menu.view.back", L), tr("menu.view.iso", L),
                       tr("menu.help.manual", L), tr("menu.file.quit", L)))
        elif which == "science":
            rows = "".join(
                f"<tr><td>{k}</td><td align='right'><b>{v}</b></td>"
                f"<td align='right'>{float(v):.8f}</td></tr>"
                for k, v in RATIOS.items())
            html = ("<h3>%s</h3><p>%s</p><table cellpadding=4>"
                    "<tr><th>%s</th><th>%s</th><th>%s</th></tr>%s</table>"
                    % (tr("menu.help.science", L),
                       tr("label.gears", L, n=len(TEETH),
                          t=sum(TEETH.values())),
                       "sortie / output", "rapport exact / exact ratio",
                       "tours par an / turns per year", rows))
        elif which == "about":
            from . import __version__
            html = ("<h3>%s</h3><p>%s</p><p><b>Version %s</b></p>"
                    "<p>Freeth <i>et al.</i>, Nature 444 (2006), Nature 454 (2008),"
                    " Scientific Reports 11:5821 (2021).</p>"
                    "<p><a href='https://github.com/ARP273-ROSE/Anticythere3D'>"
                    "github.com/ARP273-ROSE/Anticythere3D</a></p>"
                    % (tr("app.title", L), tr("app.subtitle", L), __version__))
        else:
            html = self._manual_html()
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle(tr("menu.help", L))
        dlg.resize(760, 560)
        v = QtWidgets.QVBoxLayout(dlg)
        br = QtWidgets.QTextBrowser(); br.setHtml(html)
        v.addWidget(br)
        bb = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(dlg.close); bb.accepted.connect(dlg.close)
        v.addWidget(bb)
        dlg.exec()

    def _manual_html(self) -> str:
        L = self.lang
        parts = [f"<h2>{tr('menu.help.manual', L)}</h2>"]
        if L == "fr":
            parts.append(
                "<p>La machine n'a <b>qu'une seule entrée</b> : la manivelle. "
                "Tourne le bouton rond, ou clique « Animer ». Un tour complet "
                "vaut une année ; tous les pointeurs suivent.</p>"
                "<p>Décoche <b>Enveloppe</b> pour retirer le boîtier et voir "
                "les 33 roues. Le curseur <b>Éclatement</b> écarte les 16 plans "
                "d'engrènement. Le menu <b>Mettre en évidence</b> éteint tout "
                "sauf un sous-ensemble.</p>"
                "<p>Le panneau de droite donne en permanence ce que lisait le "
                "propriétaire de la machine, et, tout en bas, l'écart entre la "
                "machine et le ciel réel calculé par éphémérides modernes.</p>")
        else:
            parts.append(
                "<p>The mechanism has <b>a single input</b>: the crank. Turn the "
                "round knob, or click “Animate”. One full turn is one year; every "
                "pointer follows.</p>"
                "<p>Untick <b>Case</b> to remove the housing and see all 33 gears. "
                "The <b>Level explosion</b> slider spreads the 16 meshing planes "
                "apart. <b>Highlight</b> dims everything but one subsystem.</p>"
                "<p>The right-hand panel shows what the owner of the machine would "
                "have read, and at the bottom, the mechanism's error against modern "
                "ephemerides.</p>")
        for key in SUBSYSTEM_KEYS:
            parts.append(f"<h4>{tr(f'sub.{key}', L)}</h4>"
                         f"<p>{tr(f'expl.{key}', L).replace(chr(10), '<br>')}</p>")
        return "".join(parts)

    # --------------------------------------------------------------- export
    def _screenshot(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, tr("menu.file.screenshot", self.lang), "anticythere.png",
            "PNG (*.png)")
        if path:
            self.grab().save(path)
            self.status.showMessage(tr("msg.saved", self.lang, path=path))

    def _export_svg(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, tr("menu.file.svg", self.lang), "anticythere.svg",
            "SVG (*.svg)")
        if path and self.view_vec.export_svg(path):
            self.status.showMessage(tr("msg.saved", self.lang, path=path))

    def _export_pdf(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, tr("menu.file.pdf", self.lang), "anticythere.pdf",
            "PDF (*.pdf)")
        if path and self.view_vec.export_pdf(path):
            self.status.showMessage(tr("msg.saved", self.lang, path=path))

    def _export_stl(self):
        """Sort les 33 roues en STL — dans un fil séparé : sur une machine
        lente, la seconde de calcul gèlerait l'interface."""
        d = QtWidgets.QFileDialog.getExistingDirectory(
            self, tr("menu.file.stl", self.lang))
        if not d:
            return
        profile = "triangular" if self.cmb_profile.currentIndex() == 0 \
            else "involute"

        self._stl_thread = QtCore.QThread(self)
        self._stl_worker = _StlExporter(d, profile)
        self._stl_worker.moveToThread(self._stl_thread)
        self._stl_thread.started.connect(self._stl_worker.run)
        self._stl_worker.done.connect(self._stl_done)
        self._stl_worker.done.connect(self._stl_thread.quit)
        self.status.showMessage(tr("stl.working", self.lang))
        self._stl_thread.start()

    def _stl_done(self, ok: bool, message: str, path: str):
        if ok:
            QtWidgets.QMessageBox.information(
                self, tr("menu.file.stl", self.lang),
                message + "\n\n" + tr("stl.note", self.lang))
            self.status.showMessage(tr("msg.saved", self.lang, path=path))
        else:
            QtWidgets.QMessageBox.warning(
                self, tr("menu.file.stl", self.lang), message)

    def _export_csv(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, tr("menu.file.export", self.lang), "anticythere.csv",
            "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as fh:
            wr = csv.writer(fh)
            for r in range(self.table.rowCount()):
                wr.writerow([self.table.item(r, 0).text(),
                             self.table.item(r, 1).text()])
        self.status.showMessage(tr("msg.saved", self.lang, path=path))


class _StlExporter(QtCore.QObject):
    """Export STL dans un fil séparé — l'interface ne gèle pas."""

    done = QtCore.pyqtSignal(bool, str, str)

    def __init__(self, outdir: str, profile: str):
        super().__init__()
        self._outdir = outdir
        self._profile = profile

    def run(self):
        from .stl_export import export_all, summary
        try:
            rows = export_all(self._outdir, profile=self._profile)
            self.done.emit(True, summary(rows), self._outdir)
        except Exception as exc:                     # disque plein, droits…
            self.done.emit(False, str(exc), self._outdir)


class _UpdateChecker(QtCore.QObject):
    """Interroge l'API GitHub dans un fil séparé — l'interface reste fluide."""

    done = QtCore.pyqtSignal(dict)

    def run(self):
        from . import updater
        try:
            state = updater.check()
        except Exception as exc:                      # ne jamais faire tomber l'app
            state = {"ok": False, "available": False, "error": str(exc)}
        self.done.emit(state)
