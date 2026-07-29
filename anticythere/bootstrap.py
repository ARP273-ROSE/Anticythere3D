"""
Auto-installation des dépendances, **3D comprise**.

Self-installing dependency bootstrap, **including 3D**.

Ce module ne dépend que de la bibliothèque standard : il est importé avant
tout le reste, vérifie ce qui manque, et l'installe avec pip. S'il n'y a ni
réseau ni pip, il le dit clairement et laisse l'application démarrer dans le
mode qu'elle peut encore assurer (rendu vectoriel sans OpenGL).
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys

#: (module importable, spécification pip, indispensable ?, à quoi ça sert)
REQUIREMENTS = [
    ("PyQt6", "PyQt6>=6.6", True, "interface graphique / GUI toolkit"),
    ("numpy", "numpy>=1.24", True, "géométrie et calculs / geometry and maths"),
    ("pyqtgraph", "pyqtgraph>=0.13", False, "vue 3D / 3D view"),
    ("OpenGL", "PyOpenGL>=3.1", False, "rendu OpenGL / OpenGL rendering"),
]


def _installed(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def missing(only_required: bool = False) -> list[tuple[str, str, bool, str]]:
    return [r for r in REQUIREMENTS
            if not _installed(r[0]) and (r[2] or not only_required)]


def in_virtualenv() -> bool:
    return (hasattr(sys, "real_prefix")
            or sys.base_prefix != sys.prefix
            or bool(os.environ.get("VIRTUAL_ENV")))


def pip_available() -> bool:
    return _installed("pip")


def install(specs: list[str], quiet: bool = False) -> bool:
    """Installe avec le pip de l'interpréteur courant. Renvoie True si OK."""
    if not specs:
        return True
    if not pip_available():
        return False
    cmd = [sys.executable, "-m", "pip", "install"]
    # hors environnement virtuel, on installe pour l'utilisateur seulement :
    # jamais d'écriture dans les paquets système
    if not in_virtualenv():
        cmd.append("--user")
    if quiet:
        cmd.append("--quiet")
    cmd += specs
    try:
        subprocess.check_call(cmd)
        return True
    except (subprocess.CalledProcessError, OSError):
        return False


#: garde-fou : empêche une boucle de relance si l'installation échoue
_GUARD = "ANTICYTHERE3D_BOOTSTRAPPED"


def _refresh_import_paths() -> None:
    """Rend visibles, dans le processus courant, les paquets qui viennent
    d'être installés — notamment le ``site-packages`` utilisateur, absent de
    ``sys.path`` s'il n'existait pas au démarrage."""
    try:
        import site
        for path in filter(None, [getattr(site, "getusersitepackages",
                                          lambda: None)()]):
            if path not in sys.path:
                sys.path.append(path)
        if hasattr(site, "main"):
            site.main()
    except Exception:
        pass
    importlib.invalidate_caches()


def ensure(auto: bool = True, quiet: bool = False,
           relaunch: bool = True) -> dict:
    """Point d'entrée : vérifie, installe si besoin, et rend compte.

    Renvoie ``{'ok', 'installed', 'still_missing', 'has_3d'}``. Si des paquets
    ont été installés mais restent invisibles (cas courant d'une première
    installation en ``--user``), le programme **se relance lui-même** une fois.
    """
    todo = missing()
    report = {"installed": [], "still_missing": [], "ok": True, "has_3d": True}
    if todo and auto:
        names = ", ".join(t[0] for t in todo)
        print(f"[Anticythere3D] Dépendances manquantes : {names}")
        print("[Anticythere3D] Installation automatique en cours…")
        if install([t[1] for t in todo], quiet=quiet):
            report["installed"] = [t[0] for t in todo]
            _refresh_import_paths()
            if missing() and relaunch and not os.environ.get(_GUARD):
                # les paquets sont là mais pas importables dans ce processus :
                # on redémarre proprement, une seule fois
                print("[Anticythere3D] Redémarrage pour charger les nouveaux "
                      "paquets…")
                os.environ[_GUARD] = "1"
                try:
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                except OSError:
                    pass
    still = missing()
    report["still_missing"] = [t[0] for t in still]
    report["ok"] = not any(t[2] for t in still)
    report["has_3d"] = _installed("pyqtgraph") and _installed("OpenGL")
    return report


#: paquets système requis par Qt sous Linux (Windows et macOS n'en ont pas
#: besoin : les binaires PyQt6 embarquent tout)
LINUX_SYSTEM_LIBS = (
    "libgl1 libegl1 libglib2.0-0 libxkbcommon-x11-0 libdbus-1-3 "
    "libfontconfig1 libxcb-cursor0 libxcb-icccm4 libxcb-image0 "
    "libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 "
    "libxcb-xinerama0 libxcb-xkb1"
)


def qt_can_start(timeout: int = 60) -> bool:
    """Teste dans un **sous-processus** que Qt démarre réellement.

    Sous Linux, il ne suffit pas que PyQt6 soit installé : il faut aussi les
    bibliothèques X/xcb du système. Leur absence ne lève pas une exception
    Python, elle **tue le processus** — d'où le test isolé.
    """
    if not _installed("PyQt6"):
        return False
    env = dict(os.environ)
    has_display = bool(env.get("DISPLAY") or env.get("WAYLAND_DISPLAY"))
    if sys.platform.startswith("linux") and not has_display:
        # pas d'écran du tout : on ne peut tester que le mode hors écran
        env["QT_QPA_PLATFORM"] = "offscreen"
    # avec un écran, on teste la VRAIE plateforme (xcb / wayland) : c'est elle
    # qui réclame les bibliothèques système et qui tue le processus si elles
    # manquent — un test en 'offscreen' passerait à côté du problème.
    code = ("from PyQt6.QtWidgets import QApplication;"
            "QApplication([]);print('ok')")
    try:
        r = subprocess.run([sys.executable, "-c", code], env=env,
                           capture_output=True, timeout=timeout)
        return r.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def system_hint() -> str:
    """Message d'aide quand Qt ne peut pas démarrer faute de bibliothèques."""
    if not sys.platform.startswith("linux"):
        return ("Qt ne démarre pas. Vérifie que le pilote graphique est à jour, "
                "ou lance le programme avec  --vector .")
    return (
        "Qt est installé mais ne peut pas démarrer : il manque des "
        "bibliothèques système.\n"
        "  Debian / Ubuntu :  sudo apt install " + LINUX_SYSTEM_LIBS + "\n"
        "  Fedora :           sudo dnf install mesa-libGL mesa-libEGL "
        "libxkbcommon-x11 xcb-util-cursor xcb-util-wm xcb-util-image\n"
        "  Arch :             sudo pacman -S libglvnd libxkbcommon-x11 "
        "xcb-util-cursor xcb-util-wm xcb-util-image")


def describe(report: dict) -> str:
    lines = []
    if report["installed"]:
        lines.append("Installé : " + ", ".join(report["installed"]))
    if report["still_missing"]:
        lines.append("Toujours absent : " + ", ".join(report["still_missing"]))
    if not report["has_3d"]:
        lines.append("La vue 3D n'est pas disponible — l'application démarre "
                     "en rendu vectoriel, qui fait le même travail sans OpenGL.")
    if not report["ok"]:
        lines.append("Dépendances indispensables manquantes : installe-les à la "
                     "main avec  pip install -r requirements.txt")
    return "\n".join(lines) if lines else "Toutes les dépendances sont là."


if __name__ == "__main__":
    rep = ensure(auto="--check" not in sys.argv)
    print(describe(rep))
    if rep["ok"] and not qt_can_start():
        print()
        print(system_hint())
        sys.exit(2)
    sys.exit(0 if rep["ok"] else 1)
