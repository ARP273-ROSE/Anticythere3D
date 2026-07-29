#!/usr/bin/env python3
"""
Lanceur — Machine d'Anticythère, simulateur 3D.
Launcher — Antikythera Mechanism 3D simulator.

    python run.py                 installe ce qu'il faut, puis démarre
    python run.py --lang en       English interface
    python run.py --vector        démarrer en rendu vectoriel
    python run.py --no-install    ne rien installer automatiquement
    python run.py --check         vérifier les dépendances et sortir

Le programme installe lui-même ses dépendances, **3D comprise** : il suffit
d'un Python 3.10 ou plus récent.
"""

import argparse
import os
import sys

# --- auto-installation AVANT tout import de PyQt6 --------------------------
sys.path.insert(0, __file__.rsplit("/", 1)[0].rsplit("\\", 1)[0] or ".")
from anticythere import bootstrap                                # noqa: E402


def _crash_report(exc: BaseException) -> None:
    """Écrit l'erreur dans un fichier ET tente de l'afficher.

    Un exécutable construit en mode fenêtré n'a pas de console : sans ce
    filet, la moindre erreur au démarrage fermerait le programme sans que
    l'utilisateur voie quoi que ce soit.
    """
    import datetime
    import traceback

    text = "".join(traceback.format_exception(type(exc), exc,
                                              exc.__traceback__))
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"Anticythere3D — erreur au démarrage — {stamp}\n"
    try:
        here = os.path.dirname(os.path.abspath(sys.executable
                                               if getattr(sys, "frozen", False)
                                               else __file__))
        path = os.path.join(here, "anticythere3d-erreur.log")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(header + text + "\n")
    except OSError:
        path = "(impossible d'écrire le journal)"
    sys.stderr.write(header + text)
    try:
        from PyQt6 import QtWidgets
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        QtWidgets.QMessageBox.critical(
            None, "Anticythere3D",
            "Le programme n'a pas pu démarrer.\n\n"
            f"{type(exc).__name__}: {exc}\n\n"
            f"Détails enregistrés dans :\n{path}")
    except Exception:
        pass


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Antikythera Mechanism simulator / simulateur de la "
                    "machine d'Anticythère")
    ap.add_argument("--lang", choices=["fr", "en"], default="fr",
                    help="interface language / langue de l'interface")
    ap.add_argument("--samples", type=int, default=8,
                    help="antialiasing MSAA (0 = désactivé) / MSAA samples")
    ap.add_argument("--vector", action="store_true",
                    help="démarrer en rendu vectoriel / start in vector mode")
    ap.add_argument("--no-install", action="store_true",
                    help="ne pas installer les dépendances automatiquement")
    ap.add_argument("--check", action="store_true",
                    help="vérifier les dépendances puis quitter")
    args = ap.parse_args()

    report = bootstrap.ensure(auto=not (args.no_install or args.check))
    if args.check:
        print(bootstrap.describe(report))
        if report["ok"] and not bootstrap.qt_can_start():
            print()
            print(bootstrap.system_hint())
            return 2
        return 0 if report["ok"] else 1
    if not report["ok"]:
        print(bootstrap.describe(report), file=sys.stderr)
        return 1
    # Qt installé mais incapable de démarrer : sous Linux il manque des
    # bibliothèques système, et leur absence tue le processus sans exception
    if not bootstrap.qt_can_start():
        print(bootstrap.system_hint(), file=sys.stderr)
        return 3
    if report["installed"] or not report["has_3d"]:
        print(bootstrap.describe(report))

    from PyQt6 import QtGui, QtWidgets

    if args.samples > 0:
        # antialiasing : à régler AVANT la création de QApplication,
        # sinon la demande est ignorée
        fmt = QtGui.QSurfaceFormat()
        fmt.setSamples(args.samples)
        fmt.setDepthBufferSize(24)
        fmt.setStencilBufferSize(8)
        QtGui.QSurfaceFormat.setDefaultFormat(fmt)

    from anticythere.mainwindow import MainWindow

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Anticythere3D")
    win = MainWindow(lang=args.lang)
    if args.vector or not report["has_3d"]:
        win.set_render_mode("vector")
    win.show()
    return app.exec()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as _exc:           # noqa: BLE001 — filet volontaire
        _crash_report(_exc)
        sys.exit(1)
