"""
Tests d'interface — nécessitent un affichage (xvfb suffit) :

    xvfb-run -a python tests/test_gui.py

Vérifient ce que les tests sans écran ne peuvent pas voir : tooltips
réellement posés, bascule de langue complète, cadrans régénérés, exports.
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6 import QtCore, QtGui, QtTest, QtWidgets  # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, label: str, detail: str = ""):
    if cond:
        print(f"  OK   {label}")
    else:
        print(f"  FAIL {label}  {detail}")
        FAILURES.append(label)


INTERACTIVE = (QtWidgets.QPushButton, QtWidgets.QCheckBox, QtWidgets.QComboBox,
               QtWidgets.QSlider, QtWidgets.QDial, QtWidgets.QDateEdit)


def main() -> int:
    app = QtWidgets.QApplication([])
    from anticythere.mainwindow import MainWindow

    print("=" * 70)
    print("  TESTS D'INTERFACE")
    print("=" * 70)

    w = MainWindow()
    w.show()
    app.processEvents()

    # ------------------------------------------------ tooltips exhaustifs
    print("\n[G1] Tooltip sur chaque widget interactif, dans les deux langues")
    for lang in ("fr", "en"):
        w.set_language(lang)
        app.processEvents()
        missing = []
        for cls in INTERACTIVE:
            for wd in w.findChildren(cls):
                if not wd.isVisibleTo(w):
                    continue
                if not wd.toolTip().strip():
                    label = (wd.text() if hasattr(wd, "text") and wd.text()
                             else type(wd).__name__)
                    missing.append(label)
        check(not missing, f"({lang}) aucun widget sans tooltip", str(missing))

    # ------------------------------------------------ bascule de langue
    print("\n[G2] La bascule de langue change TOUT")
    w.set_language("fr")
    app.processEvents()
    fr_texts = (w.btn_play.text(), w.gb_crank.title(),
                w.table.item(0, 0).text() if w.table.rowCount() else "")
    fr_tip = w.dial.toolTip()
    w.set_language("en")
    app.processEvents()
    en_texts = (w.btn_play.text(), w.gb_crank.title(),
                w.table.item(0, 0).text() if w.table.rowCount() else "")
    check(all(a != b for a, b in zip(fr_texts, en_texts)),
          "boutons, titres et tableau changent de langue",
          f"{fr_texts} vs {en_texts}")
    check(w.dial.toolTip() != fr_tip, "les tooltips changent aussi")
    check(w.view3d.dial_lang == "en" and w.view_vec.dial_lang == "en",
          "les cadrans graves suivent la langue")

    # ------------------------------------------------ dimensionnement
    print("\n[G3] Mise en page a l'ouverture")
    screen = app.primaryScreen().availableGeometry()
    check(w.width() <= screen.width() and w.height() <= screen.height(),
          f"fenetre {w.width()}x{w.height()} tient dans l'ecran "
          f"{screen.width()}x{screen.height()}")
    check(w.dock_controls.width() >= 300, "panneau de commandes assez large",
          str(w.dock_controls.width()))
    check(w.stack.width() > 400, "la vue 3D garde la part du lion",
          str(w.stack.width()))
    check(abs(w.dial.width() - w.dial.height()) <= w.dial.width(),
          "la manivelle ne deborde pas")

    # ------------------------------------------------ menu eclipses
    print("\n[G4] Navigation vers une eclipse")
    import datetime as dt
    from anticythere import astro
    jd = astro.julian_day(dt.datetime(2026, 8, 12, 17, 40,
                                      tzinfo=dt.timezone.utc))
    w._goto_jd(jd)
    app.processEvents()
    ecl = astro.eclipse_possible(w.epoch_jd + w.mech.days)
    check(ecl["type"] == "solar" and ecl["certain"],
          "12/08/2026 : eclipse solaire certaine detectee", str(ecl))

    # ------------------------------------------------ exports vectoriels
    print("\n[G5] Exports")
    w.set_render_mode("vector")
    app.processEvents()
    ok_svg = w.view_vec.export_svg("/tmp/_test_export.svg")
    ok_pdf = w.view_vec.export_pdf("/tmp/_test_export.pdf")
    check(ok_svg and os.path.getsize("/tmp/_test_export.svg") > 10000,
          "export SVG non vide")
    check(ok_pdf and os.path.getsize("/tmp/_test_export.pdf") > 5000,
          "export PDF non vide")
    with open("/tmp/_test_export.svg", "rb") as fh:
        svg = fh.read()
    check(b"<image" not in svg, "le SVG ne contient aucune image bitmap")

    # ------------------------------------------------ cadran arrière
    # Deux défauts signalés en usage : des cadrans qui se chevauchaient, et
    # des spirales sans aucune inscription. Les deux sont verrouillés ici.
    print("\n[G6] Cadran arriere : encombrement et inscriptions")
    from anticythere import dialface as df, layout as lay

    check(lay.BACK_DIAL_SPAN >= max(lay.CASE_WIDTH, lay.CASE_HEIGHT),
          "la texture du dos couvre toute la plaque",
          f"{lay.BACK_DIAL_SPAN} < {max(lay.CASE_WIDTH, lay.CASE_HEIGHT)}")

    disques = [("metonique", lay.METONIC_CENTER, lay.METONIC_RADIUS),
               ("saros", lay.SAROS_CENTER, lay.SAROS_RADIUS),
               ("callippique", lay.ARBORS["o"], lay.CALLIPPIC_RADIUS),
               ("exeligmos", lay.ARBORS["i"], lay.EXELIGMOS_RADIUS),
               ("jeux", lay.GAMES_CENTER, 13.0)]
    chevauchements = []
    for i in range(len(disques)):
        for j in range(i + 1, len(disques)):
            (n1, c1, r1), (n2, c2, r2) = disques[i], disques[j]
            d = math.hypot(c1[0] - c2[0], c1[1] - c2[1])
            if d < r1 + r2:
                chevauchements.append(f"{n1}/{n2} ({r1 + r2 - d:.2f} mm)")
    check(not chevauchements, "aucun cadran arriere n'en chevauche un autre",
          ", ".join(chevauchements))

    starts = df.metonic_year_starts()
    check(len(starts) == 19 and starts[-1] == 222,
          "19 annees metoniques, la derniere commence au mois 222")
    check(len(df.SAROS_SOLAR) + len(df.SAROS_LUNAR) > 0
          and max(df.SAROS_SOLAR | df.SAROS_LUNAR) < 223,
          "les glyphes d'eclipse tombent dans les 223 cases du Saros")
    check(all(len(court) <= 4 for _, court in df.CORINTHIAN_MONTHS)
          and len(df.CORINTHIAN_MONTHS) == 12,
          "12 mois corinthiens, abreges a 4 lettres pour tenir dans la case")

    # ------------------------------------------------ manivelle a la souris
    print("\n[G7] Manivelle saisie a la souris (3D)")
    w.set_language("fr")
    w.set_render_mode("3d")
    app.processEvents()
    v = w.view3d
    if hasattr(v, "crank_handle"):
        v.setCameraPosition(distance=420, elevation=35, azimuth=-60)
        v.update(); app.processEvents()
        tourner_manivelle_3d(app, w, v)
    else:
        check(False, "vue 3D indisponible : manivelle 3D non testee")

    print("\n[G8] Manivelle saisie a la souris (vectoriel)")
    w.set_render_mode("vector")
    w.view_vec.look_at("front")
    app.processEvents()
    tourner_manivelle_2d(app, w, w.view_vec)

    # ------------------------------------------------ molette
    print("\n[G9] Molette de la souris")
    for vue, lire, nom in ((w.view3d, lambda x: -x.opts["distance"], "3D"),
                           (w.view_vec, lambda x: x._zoom, "vectoriel")):
        if nom == "3D" and not hasattr(vue, "crank_handle"):
            continue
        w.set_render_mode("3d" if nom == "3D" else "vector")
        app.processEvents()
        avant = lire(vue)
        molette(app, vue, +240)
        check(lire(vue) > avant, f"molette vers l'avant = zoom avant ({nom})")
        avant = lire(vue)
        molette(app, vue, -240)
        check(lire(vue) < avant, f"molette vers l'arriere = zoom arriere ({nom})")
        for _ in range(60):
            molette(app, vue, +480)
        if nom == "3D":
            check(vue.opts["distance"] >= 40.0, "le zoom 3D est borne "
                  f"(distance {vue.opts['distance']:.0f} mm)")
    t0 = w.mech.turns
    w.dial.setFocus()
    molette(app, w.dial, -120)
    check(w.mech.turns != t0, "la molette sur le bouton rond fait tourner "
                              "la manivelle")

    # ------------------------------------------------ eclatement reel
    print("\n[G10] Eclatement dans la vue 3D")
    w.set_render_mode("3d")
    app.processEvents()
    if hasattr(v, "_gears"):
        from anticythere import layout as lay
        ecarts, z_prec = [], {}
        for val in (0, 25, 50, 75, 100):
            w.sld_explode.setValue(val)
            app.processEvents()
            e = val / 100.0
            for nom_r, item in v._gears.items():
                m = item.transform()
                x, y, z = m.column(3).x(), m.column(3).y(), m.column(3).z()
                ref = lay.gear_placement(nom_r, 0.0, v._carrier)
                if math.hypot(x - ref[0], y - ref[1]) > 1e-4:
                    ecarts.append((nom_r, val, "plan"))
                if abs(z - lay.gear_placement(nom_r, e, v._carrier)[2]) > 1e-4:
                    ecarts.append((nom_r, val, "z"))
                if nom_r in z_prec and z < z_prec[nom_r] - 1e-6:
                    ecarts.append((nom_r, val, "recul"))
                z_prec[nom_r] = z
        check(not ecarts, "les roues affichees suivent l'eclatement calcule, "
              "sans bouger dans leur plan", str(ecarts[:5]))
        # les arbres affiches : position (k et K suivent le porte-satellite)
        # et longueur PROLONGEE jusqu'aux cadrans, celle que le test [14]
        # verifie contre toutes les roues
        faux = []
        for val in (0, 100):
            w.sld_explode.setValue(val)
            v.set_angles(v._angles, 0.3)
            app.processEvents()
            for arbre, item in v._arbors.items():
                m = item.transform()
                x, y = lay.arbor_position(arbre, 0.3)
                z0, z1 = lay.arbor_span(arbre, val / 100.0)
                if (math.hypot(m.column(3).x() - x, m.column(3).y() - y) > 1e-4
                        or abs(m.column(3).z() - z0) > 1e-4
                        or abs(m.column(2).z() - (z1 - z0)) > 1e-4):
                    faux.append((arbre, val))
        check(not faux, "les arbres affiches ont la position et la longueur "
              "prolongee controlees par le test [14]", str(faux[:5]))
        w.sld_explode.setValue(0)
    w.set_render_mode("vector")
    check(not w.sld_explode.isEnabled(),
          "curseur d'eclatement grise en vectoriel (rien a y voir)")
    w.set_render_mode("3d")

    # ------------------------------------------------ anglais integral
    print("\n[G11] Interface en anglais : aucun texte francais")
    w.set_language("en")
    app.processEvents()
    textes = textes_visibles(w)
    for page in ("manual", "science", "shortcuts", "about"):
        textes.append(("aide " + page,
                       QtGui.QTextDocumentFragment.fromHtml(
                           w.help_html(page)).toPlainText()))
    francais = [(ou, _FR.search(t.replace("et al.", "")).group(0), t[:70])
                for ou, t in textes if semble_francais(t)]
    check(not francais, f"{len(textes)} textes affiches, aucun en francais",
          "\n    ".join(map(str, francais[:12])))
    def bouton_standard():
        bb = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        return bb.buttons()[0].text().replace("&", "")
    check(bouton_standard() == "Cancel", "boutons standard de Qt en anglais")
    w.set_language("fr")
    app.processEvents()
    check(bouton_standard() == "Annuler",
          "boutons standard de Qt traduits en francais (qtbase_fr)",
          bouton_standard())
    textes_fr = textes_visibles(w)
    anglais = [(ou, _EN.search(t).group(0), t[:70])
               for ou, t in textes_fr if semble_anglais(t)]
    check(not anglais, f"et l'inverse : {len(textes_fr)} textes, aucun en "
          "anglais dans l'interface francaise",
          "\n    ".join(map(str, anglais[:12])))

    # ------------------------------------------------ recentrer = vraie remise a zero
    print("\n[G12] Recentrer apres un roulis et la vue arriere")
    v = w.view3d
    if hasattr(v, "roll"):
        v.look_at("iso")
        r0 = v.opts["rotation"]
        v.roll(30)
        v.look_at("back")
        v.look_at("iso")
        check((v.opts["rotation"] - r0).length() < 1e-5,
              "la vue de trois quarts est la meme, quel que soit le roulis precedent")

    # ------------------------------------------------ « A propos » avec le logo
    print("\n[G13] Le logo dans « A propos »")
    vus = []

    def _voir():
        dlg = QtWidgets.QApplication.activeModalWidget()
        if dlg is None:
            QtCore.QTimer.singleShot(50, _voir)
            return
        logo = dlg.findChild(QtWidgets.QLabel, "logo_a_propos")
        vus.append(logo is not None and not logo.pixmap().isNull())
        dlg.close()
    QtCore.QTimer.singleShot(50, _voir)
    w._help("about")
    check(vus == [True], "le logo (meme source SVG) est affiche")

    print("\n" + "=" * 70)
    if FAILURES:
        print(f"  {len(FAILURES)} ECHEC(S) : {FAILURES}")
        return 1
    print("  TOUS LES TESTS D'INTERFACE PASSENT")
    return 0


# ----------------------------------------------------------------- outils
def _deplacer(app, vue, point, boutons):
    ev = QtGui.QMouseEvent(
        QtCore.QEvent.Type.MouseMove, QtCore.QPointF(point),
        QtCore.QPointF(vue.mapToGlobal(QtCore.QPoint(int(point.x()),
                                                     int(point.y())))),
        QtCore.Qt.MouseButton.NoButton, boutons,
        QtCore.Qt.KeyboardModifier.NoModifier)
    app.sendEvent(vue, ev)
    app.processEvents()


def molette(app, vue, delta):
    centre = QtCore.QPointF(vue.width() / 2, vue.height() / 2)
    ev = QtGui.QWheelEvent(
        centre, QtCore.QPointF(vue.mapToGlobal(centre.toPoint())),
        QtCore.QPoint(0, 0), QtCore.QPoint(0, delta),
        QtCore.Qt.MouseButton.NoButton, QtCore.Qt.KeyboardModifier.NoModifier,
        QtCore.Qt.ScrollPhase.NoScrollPhase, False)
    app.sendEvent(vue, ev)
    app.processEvents()


def _quart_de_tour(app, w, vue, point_a):
    """Saisit la poignee et lui fait faire un quart de tour, sens horaire vu
    de face (le sens qui fait avancer le temps). Renvoie le nombre de tours
    de b1 parcourus et les sorties avant / apres."""
    from anticythere import layout as lay
    o0, t0 = w.mech.outputs(), w.mech.turns
    depart = point_a(None)
    QtTest.QTest.mousePress(vue, QtCore.Qt.MouseButton.LeftButton,
                            QtCore.Qt.KeyboardModifier.NoModifier,
                            depart.toPoint())
    a0 = 2 * math.pi * w.mech.gear_angles()["a1"]
    n = 24
    for k in range(1, n + 1):
        p = point_a(a0 - (math.pi / 2) * k / n)
        _deplacer(app, vue, p, QtCore.Qt.MouseButton.LeftButton)
    QtTest.QTest.mouseRelease(vue, QtCore.Qt.MouseButton.LeftButton,
                              QtCore.Qt.KeyboardModifier.NoModifier,
                              p.toPoint())
    return w.mech.turns - t0, o0, w.mech.outputs()


def _verifier_quart(label, dt, o0, o1):
    from anticythere import layout as lay
    attendu = -0.25 / lay.CRANK_PER_TURN          # +0,0538 tour de b1
    check(abs(dt - attendu) < 0.10 * abs(attendu),
          f"{label} : un quart de tour de poignee -> {dt:+.4f} tour de b1 "
          f"(attendu {attendu:+.4f}, soit {attendu * 365.24:.1f} jours)")
    check(abs(o1.mean_sun - o0.mean_sun) > 0.04
          and abs(o1.moon_true - o0.moon_true) > 0.5
          and o1.metonic != o0.metonic and o1.saros != o0.saros,
          f"{label} : les cadrans avancent (Soleil "
          f"{(o1.mean_sun - o0.mean_sun) * 360:+.1f} deg, Lune "
          f"{(o1.moon_true - o0.moon_true) * 360:+.0f} deg)")


def tourner_manivelle_3d(app, w, v):
    from anticythere import layout as lay
    a, b = v.crank_handle()
    centre = v.project((a + b) / 2)
    check(v.hit_crank(centre), "la poignee est saisissable sous la souris")
    loin = QtCore.QPointF(20, 20)
    check(not v.hit_crank(loin), "un clic loin de la poignee ne la saisit pas")
    ax, ay, z = v.crank_axis()
    zh = v.crank_grip_z()
    rot0 = QtGui.QQuaternion(v.opts["rotation"])

    def point(ang):
        if ang is None:
            return centre
        return v.project((ax + lay.CRANK_RADIUS * math.cos(ang),
                          ay + lay.CRANK_RADIUS * math.sin(ang), zh))
    dt, o0, o1 = _quart_de_tour(app, w, v, point)
    _verifier_quart("3D", dt, o0, o1)
    check(v.opts["rotation"] == rot0,
          "saisir la manivelle ne fait pas tourner la camera")
    check(w.dial.value() == int(round((w.mech.turns % 1) * 360)) % 360,
          "le bouton rond suit la manivelle")
    # glisser AILLEURS : la camera tourne, la machine ne bouge pas
    t0 = w.mech.turns
    QtTest.QTest.mousePress(v, QtCore.Qt.MouseButton.LeftButton,
                            QtCore.Qt.KeyboardModifier.NoModifier, QtCore.QPoint(30, 30))
    for k in range(1, 8):
        _deplacer(app, v, QtCore.QPointF(30 + 12 * k, 30 + 4 * k),
                  QtCore.Qt.MouseButton.LeftButton)
    QtTest.QTest.mouseRelease(v, QtCore.Qt.MouseButton.LeftButton,
                              QtCore.Qt.KeyboardModifier.NoModifier,
                              QtCore.QPoint(114, 58))
    check(v.opts["rotation"] != rot0 and w.mech.turns == t0,
          "glisser hors de la manivelle tourne la vue, pas la machine")


def tourner_manivelle_2d(app, w, vv):
    from anticythere import layout as lay
    t = vv.scene_transform(float(vv.width()), float(vv.height()))
    ax, ay = lay.ARBORS["a"]
    hx, hy = vv.crank_handle()
    check(vv.hit_crank(t.map(QtCore.QPointF(hx, hy))),
          "la poignee est saisissable dans le rendu vectoriel")

    def point(ang):
        if ang is None:
            return t.map(QtCore.QPointF(hx, hy))
        return t.map(QtCore.QPointF(ax + lay.CRANK_RADIUS * math.cos(ang),
                                    ay + lay.CRANK_RADIUS * math.sin(ang)))
    pan0 = QtCore.QPointF(vv._pan)
    dt, o0, o1 = _quart_de_tour(app, w, vv, point)
    _verifier_quart("vectoriel", dt, o0, o1)
    check(vv._pan == pan0, "saisir la manivelle ne deplace pas le dessin")


def textes_visibles(w):
    """Tout ce que l'utilisateur peut lire : textes, titres, infobulles,
    menus, listes, tableau, legende."""
    out = []
    for wd in w.findChildren(QtWidgets.QWidget):
        if not wd.isVisibleTo(w) and not isinstance(wd, QtWidgets.QMenu):
            continue
        for attr in ("text", "title", "toolTip", "placeholderText",
                     "windowTitle"):
            f = getattr(wd, attr, None)
            if callable(f):
                try:
                    t = f()
                except TypeError:
                    continue
                if isinstance(t, str) and t.strip():
                    out.append((f"{type(wd).__name__}.{attr}", t))
        if isinstance(wd, QtWidgets.QComboBox):
            out += [("QComboBox.item", wd.itemText(i)) for i in range(wd.count())]
        if isinstance(wd, QtWidgets.QTextBrowser):
            out.append(("QTextBrowser", wd.toPlainText()))
    for act in w.findChildren(QtGui.QAction):
        for t in (act.text(), act.toolTip()):
            if t.strip():
                out.append(("QAction", t))
    for r in range(w.table.rowCount()):
        for c in range(2):
            it = w.table.item(r, c)
            if it is not None and it.text().strip():
                out.append(("table", it.text()))
                if it.toolTip():
                    out.append(("table.tip", it.toolTip()))
    for c in range(w.table.columnCount()):
        h = w.table.horizontalHeaderItem(c)
        if h is not None:
            out.append(("table.header", h.text()))
    return out


import re as _re  # noqa: E402

_FR = _re.compile(r"[éèêàçùôîœ]|\b(le|la|les|des|une|du|et|pour|avec|dans|"
                  r"sur|roue|roues|cadran|jours?|vue)\b", _re.I)
_EN = _re.compile(r"\b(the|and|with|of|to|gear|gears|wheel|show|turn|"
                  r"view|years?|days?)\b", _re.I)


def semble_francais(t: str) -> bool:
    # les noms grecs et propres (Thoth, Nemea...) n'ont ni accent ni article
    # (« Freeth et al. » est une citation, identique dans les deux langues)
    return bool(_FR.search(t.replace("Français", "").replace("et al.", "")))


def semble_anglais(t: str) -> bool:
    return bool(_EN.search(t.replace("English", "")))


if __name__ == "__main__":
    raise SystemExit(main())
