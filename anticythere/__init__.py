"""Anticythere3D — simulateur de la machine d'Anticythère.

Antikythera Mechanism simulator.
"""

def _lire_version() -> str:
    """La version vit dans le fichier VERSION : une seule source.

    Ecrite a deux endroits, elle finit par diverger — et une application qui
    se croit en retard sur elle-meme propose une mise a jour a chaque
    demarrage, sans fin.
    """
    from pathlib import Path as _Path
    for base in (_Path(__file__).resolve().parent.parent,
                 _Path(__file__).resolve().parent):
        try:
            texte = (base / "VERSION").read_text(encoding="utf-8").strip()
            if texte:
                return texte
        except OSError:
            continue
    return ""


__version__ = _lire_version()
__all__ = ["__version__"]
