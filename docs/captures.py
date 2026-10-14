"""Captures d'écran RÉELLES des manuels, dans les deux langues.

La vue 3D exige un vrai serveur X (le mode « offscreen » de Qt ne fournit
aucun contexte OpenGL) :

    xvfb-run -a -s "-screen 0 1920x1080x24" python docs/captures.py

Toutes les captures sont prises à la même date (12 août 2026, éclipse totale
de Soleil) pour que le texte du manuel puisse citer ce qu'on y lit. Sorties :
docs/captures/<nom>-<langue>.png.
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
sys.path.insert(0, str(RACINE))
SORTIE = ICI / "captures"

from PyQt6 import QtCore, QtGui, QtWidgets  # noqa: E402

DATE = datetime(2026, 8, 12, 12, tzinfo=timezone.utc)
TAILLE = (1600, 940)


def attendre(app, ms=300):
    fin = time.time() + ms / 1000.0
    while time.time() < fin:
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)
        time.sleep(0.01)


def enregistrer(img, nom, lg):
    SORTIE.mkdir(exist_ok=True)
    chemin = SORTIE / f"{nom}-{lg}.png"
    if isinstance(img, QtGui.QPixmap):
        img = img.toImage()
    img.save(str(chemin))
    print("  ", chemin.relative_to(RACINE), f"{img.width()}x{img.height()}")


def bande(images, marge=12):
    """Assemble des captures côte à côte, séparées d'un filet blanc."""
    imgs = [i.toImage() if isinstance(i, QtGui.QPixmap) else i for i in images]
    h = max(i.height() for i in imgs)
    w = sum(i.width() for i in imgs) + marge * (len(imgs) - 1)
    out = QtGui.QImage(w, h, QtGui.QImage.Format.Format_RGB32)
    out.fill(QtGui.QColor("white"))
    p = QtGui.QPainter(out)
    x = 0
    for i in imgs:
        p.drawImage(x, 0, i)
        x += i.width() + marge
    p.end()
    return out


def dialogue_suivant(app, nom, lg, action, taille=None):
    """Capture la prochaine fenêtre modale ouverte par `action`, puis la ferme."""
    def _prendre():
        dlg = app.activeModalWidget()
        if dlg is None:
            QtCore.QTimer.singleShot(100, _prendre)
            return
        if taille:
            dlg.resize(*taille)
        attendre(app, 400)
        enregistrer(dlg.grab(), nom, lg)
        dlg.close()
    QtCore.QTimer.singleShot(300, _prendre)
    action()


def main() -> int:
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        print("Il faut un vrai serveur X : xvfb-run -a python docs/captures.py")
        return 2
    # Dossier personnel fictif : la boîte d'enregistrement capturée ne montre
    # aucun chemin réel de la machine qui fabrique les captures.
    import shutil
    import tempfile
    lg0 = (sys.argv[1:] or ["fr"])[0]
    maison = Path(tempfile.gettempdir()) / "home" / ("utilisateur" if lg0 == "fr" else "user")
    shutil.rmtree(maison, ignore_errors=True)
    noms = ({"DESKTOP": "Bureau", "DOCUMENTS": "Documents", "PICTURES": "Images",
             "DOWNLOAD": "Téléchargements"} if lg0 == "fr" else
            {"DESKTOP": "Desktop", "DOCUMENTS": "Documents", "PICTURES": "Pictures",
             "DOWNLOAD": "Downloads"})
    for d in noms.values():
        (maison / d).mkdir(parents=True, exist_ok=True)
    (maison / "Documents" / "Anticythere").mkdir(exist_ok=True)
    (maison / ".config").mkdir(exist_ok=True)
    (maison / ".config" / "user-dirs.dirs").write_text("".join(
        f'XDG_{k}_DIR="$HOME/{v}"\n' for k, v in noms.items()), encoding="utf-8")
    os.environ["HOME"] = str(maison)
    for var in ("XDG_CONFIG_HOME", "XDG_DATA_HOME"):
        os.environ.pop(var, None)
    os.chdir(maison / "Documents")
    fmt = QtGui.QSurfaceFormat()
    fmt.setSamples(8)
    fmt.setDepthBufferSize(24)
    QtGui.QSurfaceFormat.setDefaultFormat(fmt)
    app = QtWidgets.QApplication([])
    from anticythere import astro, style
    from anticythere.logo import app_icon
    style.appliquer(app)
    app.setWindowIcon(app_icon())
    from anticythere.mainwindow import MainWindow

    # Une seule fenêtre par processus : la vue 3D garde ses programmes de
    # rendu (shaders) d'un contexte OpenGL à l'autre, et une seconde fenêtre
    # dans le même processus s'affiche vide. Le script se relance donc pour
    # chaque langue.
    langues = sys.argv[1:] or ["fr", "en"]
    if len(langues) > 1:
        import subprocess
        for lg in langues:
            r = subprocess.run([sys.executable, str(Path(__file__).resolve()), lg])
            if r.returncode:
                return r.returncode
        return 0
    for lg in langues:
        print(f"[{lg}]")
        w = MainWindow(lang=lg)
        w.resize(*TAILLE)
        w.show()
        w._goto_jd(astro.julian_day(DATE))
        attendre(app, 800)

        # 1. machine fermée, vue de trois quarts : la fenêtre entière
        w.view3d.look_at("iso")
        attendre(app)
        enregistrer(w.grab(), "fenetre", lg)

        # 2. face avant, de face
        w.view3d.look_at("front")
        attendre(app)
        enregistrer(w.grab(), "face-avant", lg)

        # 3. la face arrière
        w.view3d.look_at("back")
        attendre(app)
        enregistrer(w.view3d.grab(), "face-arriere", lg)

        # 4. mécanisme ouvert (enveloppe ôtée)
        w.chk_case.setChecked(False)
        w.view3d.look_at("iso")
        attendre(app)
        enregistrer(w.grab(), "ouvert", lg)

        # 5. manivelle : avant / après un tour (78,6 jours plus tard)
        w.chk_case.setChecked(True)
        w.view3d.look_at("iso")
        attendre(app)
        avant = w.grab()
        w.mech.days += 48 / 223 * 365.24219
        w.refresh()
        w._sync_dial()
        attendre(app)
        apres = w.grab()
        enregistrer(bande([avant.scaled(1000, 588, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                        QtCore.Qt.TransformationMode.SmoothTransformation),
                           apres.scaled(1000, 588, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                        QtCore.Qt.TransformationMode.SmoothTransformation)]),
                     "manivelle", lg)
        w._goto_jd(astro.julian_day(DATE))

        # 6. éclatement des étages : 0, 50, 100 %
        w.chk_case.setChecked(False)
        vues = []
        for val in (0, 50, 100):
            w.sld_explode.setValue(val)
            w.view3d.look_at("iso")
            w.view3d.rotate(0, 35)        # un peu plus haut : on voit les étages
            attendre(app, 500)
            img = w.view3d.grab().toImage()
            cote = min(img.width(), img.height())
            vues.append(img.copy((img.width() - cote) // 2, 0, cote, cote)
                        .scaled(600, 600, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                QtCore.Qt.TransformationMode.SmoothTransformation))
        enregistrer(bande(vues), "eclatement", lg)
        w.sld_explode.setValue(0)

        # 7. un train mis en évidence (le Saros)
        w.cmb_highlight.setCurrentIndex(6)
        w.view3d.look_at("iso")
        attendre(app, 500)
        enregistrer(w.view3d.grab(), "evidence-saros", lg)
        w.cmb_highlight.setCurrentIndex(0)
        w.chk_case.setChecked(True)

        # 8. rendu vectoriel (exportable en SVG/PDF), avec la légende
        w.set_render_mode("vector")
        w.chk_case.setChecked(False)
        w.view_vec.look_at("front")
        attendre(app, 500)
        enregistrer(w.grab(), "vectoriel", lg)
        w.chk_case.setChecked(True)
        w.view_vec.look_at("back")
        attendre(app, 500)
        enregistrer(w.view_vec.grab(), "vectoriel-arriere", lg)
        w.set_render_mode("3d")

        # 9. la liste des prochaines éclipses
        dialogue_suivant(app, "eclipses", lg, w._show_eclipses, (720, 470))
        # 10. « À propos », avec le logo
        dialogue_suivant(app, "a-propos", lg, lambda: w._help("about"))
        # 11. la boîte d'enregistrement complète (export SVG), sous Linux
        import interface_kit
        # barre latérale : le dossier personnel fictif et la racine, sans
        # les supports montés de la machine qui fabrique les captures
        interface_kit.emplacements = lambda: [
            str(maison), *(str(maison / d) for d in noms.values()), "/"]
        interface_kit.installer_dialogues_fichiers()
        w.set_render_mode("vector")
        dialogue_suivant(app, "enregistrer", lg, w._export_svg, (900, 520))
        w.set_render_mode("3d")
        w.close()
        w.deleteLater()
        attendre(app, 200)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
