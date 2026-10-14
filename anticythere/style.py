"""
Apparence figée du simulateur / Fixed look of the simulator.

L'interface ne dépend ni du thème clair/sombre du système, ni de sa couleur
d'accentuation, ni de ses polices : style Qt « Fusion », palette COMPLÈTE
(trois groupes, état désactivé compris), police embarquée (Source Sans 3,
dossier `polices/`) et feuille de style. Les couleurs reprennent celles de la
machine : parchemin du fond de la vue 3D (`layout.BACKGROUND`), bleu de nuit
et bronze du logo. Seule la mise à l'échelle (125 %, 150 %…) reste celle du
système : la neutraliser rendrait le texte minuscule sur un écran 4K.

The interface ignores the system's light/dark theme, accent colour and fonts.
"""

from __future__ import annotations

from pathlib import Path

POLICES = Path(__file__).resolve().parent / "polices"
FAMILLE = "Source Sans 3"

PARCHEMIN = "#F5F0E6"     # = layout.BACKGROUND, fond de la vue 3D
CARTE = "#FFFDF8"         # champs, listes, tableau
LIGNE = "#EFE8DA"         # lignes alternées
BOUTON = "#E8DFCC"
ENCRE = "#1C2433"         # texte
GRIS = "#7A7468"          # texte secondaire, désactivé
BORD = "#CDBF9F"
NUIT = "#1C2A42"          # bleu de nuit du logo : sélection, titres
BRONZE = "#A87C30"        # bronze du logo : accents
BRONZE_CLAIR = "#E2B45C"

#: rôles de palette pour interface_kit.appliquer_style (tous fournis)
COULEURS = {
    "fenetre": PARCHEMIN, "texte": ENCRE, "base": CARTE, "base_alt": LIGNE,
    "bouton": BOUTON, "texte_bouton": ENCRE, "selection": NUIT,
    "texte_selection": "#FFFFFF", "lien": "#2C5C8F", "infobulle": "#FFFBEF",
    "texte_infobulle": ENCRE, "desactive": GRIS, "clair": "#FFFFFF",
    "moyen": BORD, "sombre": "#8C7F66",
}

#: réglages fins au-dessus de la palette
FEUILLE = f"""
QMainWindow::separator {{ background: {BORD}; width: 3px; height: 3px; }}
QDockWidget::title {{ background: {LIGNE}; padding: 4px 6px;
    border-bottom: 1px solid {BORD}; }}
QGroupBox {{ border: 1px solid {BORD}; border-radius: 6px; margin-top: 14px;
    padding-top: 6px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px;
    color: {NUIT}; font-weight: 600; }}
QPushButton {{ background: {BOUTON}; border: 1px solid {BORD};
    border-radius: 5px; padding: 4px 10px; }}
QPushButton:hover {{ background: #F0E7D4; border-color: {BRONZE}; }}
QPushButton:pressed, QPushButton:checked {{ background: {BRONZE_CLAIR}; }}
QPushButton:disabled {{ color: {GRIS}; background: {LIGNE}; }}
QToolTip {{ background: #FFFBEF; color: {ENCRE}; border: 1px solid {BRONZE};
    padding: 4px; }}
QMenuBar {{ background: {LIGNE}; border-bottom: 1px solid {BORD}; }}
QMenuBar::item:selected {{ background: {NUIT}; color: #FFFFFF; }}
QMenu {{ background: {CARTE}; border: 1px solid {BORD}; }}
QMenu::item:selected {{ background: {NUIT}; color: #FFFFFF; }}
QMenu::separator {{ height: 1px; background: {BORD}; margin: 4px 8px; }}
QHeaderView::section {{ background: {LIGNE}; border: 0;
    border-right: 1px solid {BORD}; border-bottom: 1px solid {BORD};
    padding: 3px 6px; font-weight: 600; }}
QStatusBar {{ background: {LIGNE}; border-top: 1px solid {BORD}; }}
"""


def appliquer(app) -> str | None:
    """Impose le style figé ; renvoie la famille de police retenue."""
    try:
        import interface_kit
    except ImportError:                      # copie sans le kit : style minimal
        app.setStyle("Fusion")
        app.setStyleSheet(FEUILLE)
        return None
    return interface_kit.appliquer_style(
        app, COULEURS, polices=POLICES, famille=FAMILLE, taille=10,
        feuille=FEUILLE, sombre=False)


def style_de_base(app) -> str:
    """Nom du style Qt sous la feuille de style : avec une feuille, Qt
    enveloppe le style dans « QStyleSheetStyle », dont le nom est vide."""
    feuille = app.styleSheet()
    if not feuille:
        return app.style().name().lower()
    app.setStyleSheet("")
    try:
        return app.style().name().lower()
    finally:
        app.setStyleSheet(feuille)
