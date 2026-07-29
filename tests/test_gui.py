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

from PyQt6 import QtWidgets  # noqa: E402

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

    print("\n" + "=" * 70)
    if FAILURES:
        print(f"  {len(FAILURES)} ECHEC(S) : {FAILURES}")
        return 1
    print("  TOUS LES TESTS D'INTERFACE PASSENT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
