"""
Mise à jour automatique depuis les *Releases* GitHub.

Automatic update from GitHub Releases.

Le principe : l'application demande à l'API GitHub quelle est la dernière
version publiée, compare avec la sienne, télécharge l'exécutable si besoin, et
le met en place. Sous Windows un programme **ne peut pas s'écraser lui-même**
tant qu'il tourne : on écrit donc un petit script qui attend la fermeture,
remplace le fichier et relance. Sous Linux et macOS le remplacement est direct.

Aucune dépendance : uniquement la bibliothèque standard.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

REPO = "ARP273-ROSE/Anticythere3D"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
TIMEOUT = 15


# ------------------------------------------------------------------ version
def current_version() -> str:
    from . import __version__
    return __version__


def parse_version(text: str) -> tuple:
    """« v1.4.2 » → (1, 4, 2). Tolère les suffixes."""
    nums = re.findall(r"\d+", text or "")
    return tuple(int(n) for n in nums[:4]) or (0,)


def is_newer(remote: str, local: str) -> bool:
    return parse_version(remote) > parse_version(local)


# --------------------------------------------------------------- interrogation
def _token() -> str | None:
    """Jeton facultatif — nécessaire seulement si le dépôt est privé.

    Lu dans la variable d'environnement ``ANTICYTHERE_GITHUB_TOKEN``, ou dans
    un fichier ``github_token.txt`` posé à côté du programme.
    """
    tok = os.environ.get("ANTICYTHERE_GITHUB_TOKEN")
    if tok:
        return tok.strip()
    here = os.path.dirname(os.path.abspath(sys.argv[0]))
    path = os.path.join(here, "github_token.txt")
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as fh:
                return fh.read().strip() or None
        except OSError:
            return None
    return None


def _request(url: str) -> urllib.request.Request:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "Anticythere3D-updater")
    tok = _token()
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    return req


def check(timeout: int = TIMEOUT) -> dict:
    """Interroge GitHub. Renvoie un état explicite, ne lève jamais.

    ``{'ok', 'available', 'version', 'url', 'name', 'notes', 'error'}``
    """
    out = {"ok": False, "available": False, "version": None, "url": None,
           "name": None, "notes": "", "error": None}
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(_request(API), timeout=timeout,
                                    context=ctx) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403, 404):
            out["error"] = ("dépôt privé ou introuvable : la mise à jour "
                            "automatique demande un dépôt public, ou un jeton "
                            "dans ANTICYTHERE_GITHUB_TOKEN")
        else:
            out["error"] = f"HTTP {exc.code}"
        return out
    except (urllib.error.URLError, OSError, ValueError) as exc:
        out["error"] = f"réseau indisponible ({exc})"
        return out

    out["ok"] = True
    out["version"] = (data.get("tag_name") or "").lstrip("vV")
    out["notes"] = data.get("body") or ""
    out["available"] = is_newer(out["version"], current_version())

    asset = pick_asset(data.get("assets") or [])
    if asset:
        out["url"] = asset.get("browser_download_url")
        out["name"] = asset.get("name")
    return out


def pick_asset(assets: list) -> dict | None:
    """Choisit le fichier qui correspond à la plateforme courante."""
    if sys.platform.startswith("win"):
        wanted = (".exe", "windows")
    elif sys.platform == "darwin":
        wanted = (".dmg", "macos", "darwin")
    else:
        wanted = ("linux", ".appimage", ".tar.gz")
    for a in assets:
        n = (a.get("name") or "").lower()
        if any(w in n for w in wanted):
            return a
    return assets[0] if assets else None


# ------------------------------------------------------------- installation
def running_as_frozen() -> bool:
    """Vrai si on tourne depuis un exécutable PyInstaller."""
    return getattr(sys, "frozen", False)


#: seules ces origines sont acceptées pour un binaire de mise à jour :
#: la page de releases du dépôt, et le CDN officiel des assets GitHub
TRUSTED_PREFIXES = (
    f"https://github.com/{REPO}/releases/download/",
    "https://objects.githubusercontent.com/",
    "https://release-assets.githubusercontent.com/",
)


def is_trusted_url(url: str) -> bool:
    return isinstance(url, str) and url.startswith(TRUSTED_PREFIXES)


def download(url: str, dest_dir: str | None = None,
             progress=None, timeout: int = 120) -> str:
    """Télécharge dans un fichier temporaire et renvoie son chemin.

    Refuse toute URL hors des origines de confiance : le binaire téléchargé
    sera exécuté, il ne doit pouvoir venir que des releases de CE dépôt.
    """
    if not is_trusted_url(url):
        raise ValueError(f"URL de mise à jour refusée : {url!r}")
    dest_dir = dest_dir or tempfile.mkdtemp(prefix="anticythere-update-")
    name = os.path.basename(url.split("?")[0]) or "update.bin"
    path = os.path.join(dest_dir, name)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(_request(url), timeout=timeout,
                                context=ctx) as resp, open(path, "wb") as fh:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            fh.write(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    return path


def apply_update(new_file: str) -> bool:
    """Met le nouveau binaire en place et relance l'application.

    Ne renvoie pas si tout va bien (le processus est remplacé ou quitte).
    """
    target = os.path.abspath(sys.executable if running_as_frozen()
                             else sys.argv[0])
    if sys.platform.startswith("win"):
        return _apply_windows(new_file, target)
    try:
        shutil.copymode(target, new_file)
    except OSError:
        os.chmod(new_file, 0o755)
    backup = target + ".old"
    try:
        if os.path.exists(backup):
            os.remove(backup)
        os.replace(target, backup)
        shutil.move(new_file, target)
    except OSError:
        return False
    os.execv(target, [target])
    return True


def _apply_windows(new_file: str, target: str) -> bool:
    """Sous Windows, un exécutable en cours ne peut pas être écrasé.

    On écrit un script qui attend la fermeture du programme, remplace le
    fichier, relance, puis s'efface.
    """
    script = os.path.join(tempfile.gettempdir(), "anticythere_update.cmd")
    body = f"""@echo off
setlocal
set TARGET="{target}"
set SOURCE="{new_file}"
echo Mise a jour d'Anticythere3D...
:wait
tasklist /FI "PID eq {os.getpid()}" 2>nul | find "{os.getpid()}" >nul
if not errorlevel 1 (
    ping -n 2 127.0.0.1 >nul
    goto wait
)
move /Y %SOURCE% %TARGET% >nul
if errorlevel 1 (
    echo Echec du remplacement. Le nouveau fichier est ici : %SOURCE%
    pause
    exit /b 1
)
start "" %TARGET%
del "%~f0"
"""
    try:
        with open(script, "w", encoding="ascii", errors="replace") as fh:
            fh.write(body)
        subprocess.Popen(["cmd", "/c", script],
                         creationflags=0x00000008 | 0x08000000)  # DETACHED
    except OSError:
        return False
    return True


def summary(state: dict, lang: str = "fr") -> str:
    """Phrase courte décrivant l'état, pour la barre de statut."""
    if state.get("error"):
        return (f"Mise à jour : {state['error']}" if lang == "fr"
                else f"Update: {state['error']}")
    if state.get("available"):
        return (f"Version {state['version']} disponible "
                f"(vous avez {current_version()})" if lang == "fr"
                else f"Version {state['version']} available "
                     f"(you have {current_version()})")
    return ("Le programme est à jour." if lang == "fr"
            else "The program is up to date.")
