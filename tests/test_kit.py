# -*- coding: utf-8 -*-
"""Cohérence du kit commun et points du standard des applications.

Ces écarts ne se voient que chez l'utilisateur : un verrou nommé que
l'installeur ne connaît pas, une version écrite deux fois, une clé de
kit.json oubliée, des données personnelles dans l'archive de mise à jour, un
second workflow de publication, une trace de crash natif effacée avant
d'avoir été lue, un style qui suit le thème du système, une boîte de
fichiers réduite sous Linux, un manuel absent dans une langue, deux logos.

    python -m pytest -q tests/test_kit.py
"""
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
KIT = json.loads((RACINE / 'kit.json').read_text(encoding='utf-8'))
sys.path.insert(0, str(RACINE))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


@pytest.fixture(scope='module')
def app():
    from PyQt6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


# --------------------------------------------------------------- kit commun
def test_fichiers_du_kit_identiques_au_gabarit():
    """Aucune copie modifiée à la main (vérifiable seulement là où le gabarit
    est présent, c'est-à-dire pas dans la CI)."""
    gabarits = RACINE.parent / '_kit_windows' / 'gabarits'
    if not gabarits.is_dir():
        pytest.skip('gabarit absent')
    for nom in ('reporting.py', 'updater.py', 'build_package.py', 'installer.iss',
                'build_unix.py', 'interface_kit.py'):
        assert (RACINE / nom).read_bytes() == (gabarits / nom).read_bytes(), nom
    wf = (RACINE / '.github' / 'workflows' / 'release.yml').read_bytes()
    assert wf == (gabarits / 'release-multiplateforme.yml').read_bytes()


def test_verrou_nomme_identique_a_l_installeur():
    iss = (RACINE / 'installer.iss').read_text(encoding='utf-8')
    assert 'AppMutex={#AppName}EnCours' in iss
    entree = (RACINE / KIT['point_entree']).read_text(encoding='utf-8')
    assert 'f"{NOM}EnCours"' in entree and f'NOM = "{KIT["nom_fichier"]}"' in entree


def test_version_unique():
    version = (RACINE / KIT['fichier_version']).read_text(encoding='utf-8').strip()
    assert re.fullmatch(r'\d+\.\d+\.\d+', version)
    journal = (RACINE / KIT['journal_technique']).read_text(encoding='utf-8')
    assert re.search(rf'^## {re.escape(version)}( |$)', journal, re.M), \
        'JOURNAL.md sans section pour la version'
    import anticythere
    assert anticythere.__version__ == version


def test_kit_json_complet():
    for cle in ('nom_technique', 'nom_fichier', 'nom_affiche', 'depot_distribution',
                'point_entree', 'icone', 'appid', 'icone_png', 'icone_grande',
                'icone_icns', 'nom_affiche_fr', 'nom_affiche_en', 'description_fr',
                'description_en', 'categories_linux', 'tests_ci'):
        assert KIT.get(cle), cle
    for chemin in [KIT['point_entree'], KIT['icone'].replace('\\', '/'),
                   KIT['icone_png'], KIT['icone_grande'], KIT['icone_icns'],
                   *KIT['modules'], *KIT['paquets'], *KIT['assets'], *KIT['tests_ci']]:
        assert (RACINE / chemin).exists(), chemin


def test_donnees_de_l_utilisateur_hors_de_l_archive():
    for nom in ('_rapports', 'reglages_rapports.json', '_crash_natif.log',
                'anticythere3d-erreur.log'):
        assert nom in KIT['fichiers_proteges'], nom


def test_un_seul_workflow_de_publication():
    wf = RACINE / '.github' / 'workflows'
    publient = [p.name for p in wf.glob('*.yml')
                if 'action-gh-release' in p.read_text(encoding='utf-8')
                or 'gh release create' in p.read_text(encoding='utf-8')]
    assert publient == ['release.yml'], publient


def test_donnees_hors_du_dossier_installe(tmp_path, monkeypatch):
    """Paquet installé (python/ à côté de app/) : rapports et journaux dans
    le profil, jamais dans app/, que la mise à jour remplace."""
    import run
    monkeypatch.setattr(run, '_empaquete', lambda: True)
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path))
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    dossier = run._dossier_donnees()
    assert RACINE not in dossier.parents and dossier != RACINE
    assert dossier.name == 'Anticythere3D'


def test_trace_de_crash_natif_relevee_avant_d_armer_faulthandler():
    """Ouvrir le fichier en écriture le vide : la trace de la session
    précédente doit être lue AVANT."""
    arbre = ast.parse((RACINE / 'run.py').read_text(encoding='utf-8'))
    fn = next(n for n in arbre.body
              if isinstance(n, ast.FunctionDef) and n.name == '_demarrer_rapports')
    lignes = {}
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            nom = getattr(n.func, 'attr', getattr(n.func, 'id', ''))
            lignes.setdefault(nom, n.lineno)
    assert lignes['relever_crash_natif'] < lignes['open'] < lignes['enable']


def test_point_d_entree_reel_check():
    """Le VRAI point d'entrée (pas un import de la fenêtre) : un import local
    mal placé dans main() ne se voit qu'ainsi. --check vérifie aussi style
    figé, menu Aide du kit, logo et manuels."""
    r = subprocess.run([sys.executable, 'run.py', '--check', '--no-install'],
                       cwd=RACINE, capture_output=True, text=True, timeout=300,
                       env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'})
    assert r.returncode == 0, r.stdout + r.stderr
    assert 'interface OK' in r.stdout


# ------------------------------------------------------------- style figé
def test_style_fige_independant_du_systeme(app):
    from PyQt6 import QtGui
    from anticythere import style
    # le système annonce un thème sombre : l'application n'en tient pas compte
    sombre = QtGui.QPalette(QtGui.QColor('#202020'))
    app.setPalette(sombre)
    famille = style.appliquer(app)
    assert style.style_de_base(app) == 'fusion'
    R, G = QtGui.QPalette.ColorRole, QtGui.QPalette.ColorGroup
    p = app.palette()
    assert p.color(G.Active, R.Window).name().upper() == style.PARCHEMIN
    assert p.color(G.Disabled, R.Window).name().upper() == style.PARCHEMIN
    assert p.color(G.Inactive, R.Base).name().upper() == style.CARTE.upper()
    assert p.color(G.Disabled, R.Text).name().upper() == style.GRIS.upper()
    assert famille == style.FAMILLE and app.font().family() == style.FAMILLE
    assert 'QGroupBox' in app.styleSheet()


# ---------------------------------------------------- explorateur de fichiers
def test_boite_de_fichiers_complete_sous_linux(app, monkeypatch, tmp_path):
    """Sous Linux, toutes les boîtes (export SVG/PDF/PNG/CSV, dossier STL)
    passent par la boîte Qt complète, barre latérale garnie."""
    import interface_kit
    from PyQt6 import QtWidgets
    monkeypatch.setenv('KIT_DIALOGUES', 'qt')
    vues = []

    def _exec(self):
        vues.append((self.testOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog),
                     [u.toLocalFile() for u in self.sidebarUrls()], self.fileMode()))
        return 0

    monkeypatch.setattr(QtWidgets.QFileDialog, 'exec', _exec)
    assert interface_kit.installer_dialogues_fichiers()
    try:
        QtWidgets.QFileDialog.getSaveFileName(None, 'svg', str(tmp_path / 'a.svg'),
                                              'SVG (*.svg)')
        QtWidgets.QFileDialog.getExistingDirectory(None, 'stl')
    finally:
        for nom, fn in interface_kit._ORIGINAUX.items():
            setattr(QtWidgets.QFileDialog, nom, fn)
        interface_kit._ORIGINAUX.clear()
    assert len(vues) == 2
    for qt_seule, laterale, _mode in vues:
        assert qt_seule and os.path.expanduser('~') in laterale
    assert vues[1][2] == QtWidgets.QFileDialog.FileMode.Directory


def test_exports_passent_par_qfiledialog():
    """Les exports appellent les fonctions statiques de QFileDialog, que le
    kit remplace : aucune boîte maison qui échapperait au standard."""
    src = (RACINE / 'anticythere' / 'mainwindow.py').read_text(encoding='utf-8')
    for fn in ('_screenshot', '_export_svg', '_export_pdf', '_export_csv'):
        corps = src[src.index(f'def {fn}('):]
        corps = corps[:corps.index('\n    def ', 10)]
        assert 'QFileDialog.getSaveFileName' in corps, fn
    assert 'QFileDialog.getExistingDirectory' in src


# ------------------------------------------------------------ manuel PDF
@pytest.mark.parametrize('langue', ['fr', 'en'])
def test_manuel_pdf_dans_les_deux_langues(langue):
    pdf = RACINE / 'docs' / f'manuel-{langue}.pdf'
    assert pdf.is_file() and pdf.stat().st_size > 200_000, pdf
    tex = (RACINE / 'docs' / 'src' / f'manuel-{langue}.tex').read_text(encoding='utf-8')
    assert 'logo_1024.png' in tex, "page de garde sans le logo"
    assert tex.count('\\capture') >= 6, "captures d'écran réelles"
    version = (RACINE / 'VERSION').read_text(encoding='utf-8').strip()
    assert version in (RACINE / 'docs' / 'src' / 'version.tex').read_text(encoding='utf-8')


def test_menu_aide_ouvre_le_manuel_de_la_langue(app, monkeypatch):
    import interface_kit
    from PyQt6 import QtGui
    ouverts = []
    monkeypatch.setattr(QtGui.QDesktopServices, 'openUrl',
                        lambda url: ouverts.append(url.toLocalFile()) or True)
    for lg in ('fr', 'en'):
        assert interface_kit.ouvrir_manuel([RACINE / 'docs'], lg)
    assert [Path(p).name for p in ouverts] == ['manuel-fr.pdf', 'manuel-en.pdf']


# ----------------------------------------------------------- icône et logo
def test_une_seule_source_pour_le_logo(app):
    from anticythere import logo
    svg = logo.SOURCE.read_text(encoding='utf-8')
    assert logo.SOURCE == RACINE / 'docs' / 'logo.svg' and '<svg' in svg
    # aucun second dessin dans le code
    src = (RACINE / 'anticythere' / 'logo.py').read_text(encoding='utf-8')
    assert 'drawEllipse' not in src and 'QSvgRenderer' in src
    for taille in (16, 32, 64, 128, 256, 512, 1024):
        assert (RACINE / 'docs' / f'logo_{taille}.png').exists(), taille
    assert (RACINE / 'docs' / 'logo.ico').read_bytes()[:4] == b'\x00\x00\x01\x00'
    assert (RACINE / 'docs' / 'logo.icns').read_bytes()[:4] == b'icns'
    # le PNG publié est bien le rendu du SVG d'aujourd'hui
    from PyQt6 import QtGui
    publie = QtGui.QImage(str(RACINE / 'docs' / 'logo_64.png')).convertToFormat(
        QtGui.QImage.Format.Format_ARGB32)
    assert publie == logo.render(64)
