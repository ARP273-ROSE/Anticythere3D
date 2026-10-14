"""
Tests — exécutables sans écran : ``python -m tests.test_mechanism``
ou ``pytest`` si disponible.

Les valeurs de référence sont celles calculées indépendamment sous SageMath
(``anticythere_verif.sage``), en arithmétique rationnelle exacte.
"""

from __future__ import annotations

import datetime as dt
import math
import sys
from fractions import Fraction as F

import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anticythere import astro, geometry as geo, i18n            # noqa: E402
from anticythere import layout as lay                            # noqa: E402
from anticythere.kinematics import (EXPECTED, PLANETS, RATIOS, TEETH,  # noqa
                                    Mechanism, PinAndSlot, self_check)

FAILURES: list[str] = []


def check(cond: bool, label: str, detail: str = ""):
    if cond:
        print(f"  OK   {label}")
    else:
        print(f"  FAIL {label}  {detail}")
        FAILURES.append(label)


# ---------------------------------------------------------------- rapports
def test_ratios():
    print("\n[1] Rapports d'engrenages — exacts (Fraction)")
    check(not self_check(), "tous les trains donnent la valeur attendue",
          str(self_check()))
    for name, expected in EXPECTED.items():
        check(RATIOS[name] == expected, f"{name} = {expected}")
    check(RATIOS["saros"] == F(4, 223) * F(235, 19),
          "Saros = 4 tours pour 223 lunaisons")
    check(RATIOS["exeligmos"] == F(235, 12711),
          "exeligmos = 1 tour en 54,09 ans")
    check(abs(1 / float(RATIOS["exeligmos"]) - 54.09) < 0.01,
          "exeligmos ~ 54,09 ans")


def test_carrier_and_anomalistic_month():
    print("\n[2] Porte-satellite et mois anomalistique")
    T_YEAR = 365.24219
    per = 1.0 / float(RATIOS["carrier_e3"])
    check(abs(per - 8.8826) < 0.001, f"periode de e3 = {per:.4f} ans (8,8826)")
    rel = float(RATIOS["moon_sid"]) - float(RATIOS["carrier_e3"])
    month = T_YEAR / rel
    check(abs(month - 27.5533) < 0.001,
          f"mois anomalistique machine = {month:.4f} j (27,5533)")
    check(abs(month - 27.554550) < 0.002,
          f"ecart au mois anomalistique reel = {abs(month-27.554550)*24*60:.1f} min")
    sid = T_YEAR / float(RATIOS["moon_sid"])
    check(abs(sid - 27.321266) < 1e-5, f"mois sideral machine = {sid:.6f} j")


def test_pin_and_slot():
    print("\n[3] Tenon et fente")
    p = PinAndSlot()
    check(abs(p.amplitude_deg - 6.5796) < 0.001,
          f"amplitude = {p.amplitude_deg:.4f} deg (arcsin(1,1/9,6))")
    # l'extremum de delta doit valoir l'amplitude
    worst = max(abs(p.delta_turns(x / 2000.0)) * 360.0 for x in range(2000))
    check(abs(worst - p.amplitude_deg) < 0.02,
          f"extremum numerique = {worst:.4f} deg")
    # moyenne nulle sur un tour : un tour pour un tour
    s = sum(p.delta_turns(x / 2000.0) for x in range(2000)) / 2000.0
    check(abs(s) < 1e-6, "moyenne de la modulation nulle (1 tour pour 1 tour)")
    # rapport de vitesse : extremes attendus
    check(abs(p.speed_ratio(0.0) - 9.6 / 10.7) < 1e-9, "vitesse min = r/(r+eps)")
    check(abs(p.speed_ratio(0.5) - 9.6 / 8.5) < 1e-9, "vitesse max = r/(r-eps)")


def test_dials():
    print("\n[4] Cadrans : retour a l'origine apres un cycle complet")
    m = Mechanism()
    m.turns = 19.0
    o = m.outputs()
    check(abs(o.metonic - 5.0) < 1e-9, "19 ans -> pointeur metonique : 5 tours")
    m.turns = 76.0
    check(abs(m.outputs().callippic - 1.0) < 1e-9,
          "76 ans -> cadran callippique : 1 tour")
    saros_years = 223.0 * 19.0 / 235.0
    m.turns = saros_years
    o = m.outputs()
    check(abs(o.saros - 4.0) < 1e-9, "1 Saros -> pointeur du Saros : 4 tours")
    check(abs(o.exeligmos - 1.0 / 3.0) < 1e-9,
          "1 Saros -> exeligmos : 1/3 de tour")
    m.turns = 3 * saros_years
    check(abs(m.outputs().exeligmos - 1.0) < 1e-9,
          "3 Saros -> exeligmos : 1 tour complet")
    # bug de frontiere attrape par l'audit SageMath : a exactement 1 Saros,
    # (1/3 % 1)*3 = 0,999... en flottant -> secteur 1 (« +0 h ») au lieu de 2
    m.turns = saros_years
    o = m.outputs()
    check(o.exeligmos_hours == 8,
          f"apres exactement 1 Saros : correction +8 h (lu {o.exeligmos_hours})")
    m.turns = 2 * saros_years
    check(m.outputs().exeligmos_hours == 16,
          "apres exactement 2 Saros : correction +16 h")
    m.turns = 3 * saros_years
    check(m.outputs().exeligmos_hours == 0,
          "apres 3 Saros : retour a +0 h")


def test_planets():
    print("\n[5] Relations de periode des planetes (Freeth et al. 2021)")
    real = {"mercury": 0.2408467, "venus": 0.6151973, "mars": 1.8808476,
            "jupiter": 11.862615, "saturn": 29.447498}
    for name, d in PLANETS.items():
        t_sid = 1.0 / float(d["sidereal_ratio"])
        err = abs(t_sid / real[name] - 1.0)
        check(err < 1e-3, f"{name}: T = {t_sid:.6f} an, erreur {err:.2e}")


def test_astro():
    print("\n[6] Astronomie de reference")
    jd = astro.julian_day(dt.datetime(2000, 1, 1, 12, tzinfo=dt.timezone.utc))
    check(abs(jd - 2451545.0) < 1e-6, f"J2000 = {jd}")
    back = astro.from_julian_day(jd)
    check(back.year == 2000 and back.month == 1 and back.day == 1,
          f"aller-retour jour julien -> {back.date()}")
    # equinoxe de printemps : longitude du Soleil proche de 0
    jd_eq = astro.julian_day(dt.datetime(2026, 3, 20, 9, 46,
                                         tzinfo=dt.timezone.utc))
    lon = astro.sun_longitude(jd_eq)
    check(min(lon, 360 - lon) < 0.2,
          f"equinoxe : longitude du Soleil = {lon:.3f} deg")


def test_calibration():
    print("\n[7] Calage de la machine sur le ciel")
    epoch = astro.julian_day(dt.datetime(2000, 1, 1, 12, tzinfo=dt.timezone.utc))
    offs = astro.calibration_offsets(epoch, None)
    offs["planets"] = astro.calibrate_planets(epoch)
    m = Mechanism(offsets=offs)
    worst_moon = worst_sun = 0.0
    for year in range(1950, 2051, 5):
        jd = astro.julian_day(dt.datetime(year, 6, 15, 12, tzinfo=dt.timezone.utc))
        m.days = jd - epoch
        o = m.outputs()
        dm = (o.moon_true * 360 - astro.moon_longitude(jd) + 180) % 360 - 180
        ds = (o.mean_sun * 360 - astro.sun_mean_longitude(jd) + 180) % 360 - 180
        worst_moon = max(worst_moon, abs(dm))
        worst_sun = max(worst_sun, abs(ds))
    check(worst_sun < 0.01, f"erreur max sur le Soleil moyen : {worst_sun:.3f} deg")

    # L'erreur sur la Lune n'est pas un defaut du code : elle a trois causes
    # physiques identifiables, dont on verifie qu'elles bornent le resultat.
    #  (a) termes de la theorie lunaire que la machine ne mecanise pas :
    #      evection 1,274 deg + variation 0,658 deg + equation annuelle 0,186 ...
    budget_terms = 1.274 + 0.658 + 0.186 + 0.114
    #  (b) derive du mois sideral : 254/19 contre la valeur vraie, sur 50 ans
    sid_err = abs(365.24219 / float(RATIOS["moon_sid"]) / 27.321662 - 1.0)
    laps = 50.0 * float(RATIOS["moon_sid"])
    budget_sid = laps * 360.0 * sid_err
    #  (c) derive de la precession de l'apogee (8,8826 contre 8,8504 ans)
    dphase = abs(50.0 / 8.8826 - 50.0 / 8.8504)
    budget_aps = 6.58 * abs(math.sin(2 * math.pi * dphase))
    budget = budget_terms + budget_sid + budget_aps
    print(f"       budget d'erreur : theorie {budget_terms:.2f} + mois sideral "
          f"{budget_sid:.2f} + apogee {budget_aps:.2f} = {budget:.2f} deg")
    check(worst_moon < budget,
          f"erreur max sur la Lune {worst_moon:.2f} deg < budget physique "
          f"{budget:.2f} deg")
    check(worst_moon > 0.5, "l'erreur est bien non nulle (la machine derive)")


def test_geometry():
    print("\n[8] Geometrie 3D")
    import numpy as np
    total = 0
    for name, n in TEETH.items():
        if name not in lay.LEVELS:
            continue
        v, f = geo.gear_mesh(n, lay.MODULE, lay.GEAR_THICKNESS)
        total += len(f)
        if not (np.isfinite(v).all() and f.max() < len(v)):
            check(False, f"maillage de {name}")
            return
    check(True, f"33 maillages valides, {total} faces au total")
    v, f = geo.spoked_gear_mesh(223, 1.0, 3.0)
    check(len(f) > 0 and f.max() < len(v), "roue a bras b1")
    out = geo.gear_outline(50, 1.0, "involute")
    r = np.hypot(out[:, 0], out[:, 1])
    check(r.min() > 23.0 and r.max() < 27.0,
          f"developpante : rayons entre {r.min():.2f} et {r.max():.2f} mm")


def test_layout():
    print("\n[9] Implantation : entraxes et collisions")
    pairs = [("a1", "b1"), ("b2", "c1"), ("c2", "d1"), ("d2", "e2"),
             ("e5", "k1"), ("k2", "e6"), ("e1", "b3"), ("b2", "l1"),
             ("l2", "m1"), ("m2", "n1"), ("n2", "p1"), ("p2", "o1"),
             ("m3", "e3"), ("e4", "f1"), ("f2", "g1"), ("g2", "h1"),
             ("h2", "i1")]
    worst = 0.0
    for a, b in pairs:
        xa, ya = lay.ARBORS[lay.ARBOR_OF[a]]
        xb, yb = lay.ARBORS[lay.ARBOR_OF[b]]
        d = math.hypot(xa - xb, ya - yb)
        want = lay.MODULE * (TEETH[a] + TEETH[b]) / 2.0
        worst = max(worst, abs(d - want))
    check(worst < 0.01, f"17 entraxes exacts a {worst*1000:.1f} um pres")
    xk, yk = lay.ARBORS["k"]
    xK, yK = lay.ARBORS["K"]
    eps = math.hypot(xk - xK, yk - yK)
    check(abs(eps - 1.1 * lay.MODULE / 0.5093) < 0.01,
          f"excentricite du tenon-fente a l'echelle : {eps:.3f} mm")
    check(len(lay.LEVELS) == 33, f"{len(lay.LEVELS)} roues implantees")


def test_i18n():
    print("\n[10] Bilinguisme")
    missing = i18n.missing_keys()
    check(not missing, f"aucune cle manquante ({len(i18n.T)} cles x 2 langues)",
          str(missing[:6]))
    check(i18n.tr("app.title", "fr") != i18n.tr("app.title", "en"),
          "les deux langues different bien")
    for lang in ("fr", "en"):
        check(len(i18n.ZODIAC[lang]) == 12, f"12 signes du zodiaque ({lang})")
        check(len(i18n.PHASE_NAMES[lang]) == 8, f"8 phases de Lune ({lang})")
    check(i18n.zodiac_sign(35.0, "fr")[0] == "Taureau", "zodiaque : 35 deg = Taureau")
    check(i18n.tr("inexistant.key", "fr").startswith("<"),
          "cle absente signalee visiblement")

    # toute cle utilisee dans le code doit exister dans le dictionnaire :
    # sans ce controle, un tr("...") oublie s'affiche tel quel a l'ecran
    import glob
    import re
    used = set()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sources = glob.glob(os.path.join(root, "anticythere", "*.py")) + [
        os.path.join(root, "run.py")]
    for path in sources:
        with open(path, encoding="utf-8") as fh:
            used |= set(re.findall(r'\b_?tr?\(\s*[\'"]([a-z0-9_.]+)[\'"]',
                                   fh.read()))
    unknown = sorted(k for k in used if k not in i18n.T)
    check(not unknown, f"{len(used)} cles utilisees dans le code, toutes definies",
          str(unknown))

    # Et l'inverse : aucun texte AFFICHE ecrit en dur. On parcourt l'arbre
    # syntaxique de chaque module a la recherche des appels Qt qui affichent
    # du texte (setText, setToolTip, QMessageBox, QLabel(...), drawText...)
    # recevant une chaine litterale qui contient un mot. Un tel texte ne
    # passe pas par tr() : il resterait dans une seule langue.
    suspects = [f"{os.path.relpath(p, root)}:{ligne} {appel}({texte!r})"
                for p in sources for ligne, appel, texte in textes_en_dur(p)]
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8") as fh:
        fh.write("w.setText('Bonjour')\nw.setToolTip(tr('a.b', L))\n"
                 "QtWidgets.QMessageBox.warning(self, 'Titre', f'{x} mots')\n")
    temoin = list(textes_en_dur(fh.name))
    os.unlink(fh.name)
    check(len(temoin) == 3, "le scan attrape bien les textes en dur (temoin)",
          str(temoin))
    check(not suspects, "aucun texte affiche ecrit en dur (scan de "
                        f"{len(sources)} modules)", "\n    ".join(suspects))


#: appels Qt qui affichent le texte qu'on leur passe
APPELS_AFFICHAGE = {
    "setText", "setTitle", "setWindowTitle", "setToolTip", "setStatusTip",
    "setWhatsThis", "setPlaceholderText", "showMessage", "addItem", "addItems",
    "insertItem", "setItemText", "setInformativeText", "setDetailedText",
    "setHorizontalHeaderLabels", "setVerticalHeaderLabels", "addAction",
    "addMenu", "addTab", "setTabText", "information", "warning", "critical",
    "question", "about", "setLabelText", "getSaveFileName", "getOpenFileName",
    "getExistingDirectory", "drawText", "setHtml", "setPlainText", "addButton",
    "setPrefix", "setSuffix", "setDescription", "QLabel", "QPushButton",
    "QCheckBox", "QRadioButton", "QGroupBox", "QAction", "QMessageBox",
    "QProgressDialog", "QToolButton", "QMenu", "_row",
}
#: textes admis tels quels : nom propre du programme, filtres et noms de
#: fichiers proposes par defaut
TEXTES_NEUTRES = {"Anticythere3D", "PNG (*.png)", "SVG (*.svg)", "PDF (*.pdf)",
                  "CSV (*.csv)", "anticythere.png", "anticythere.svg",
                  "anticythere.pdf", "anticythere.csv"}


def textes_en_dur(path):
    import ast
    import re

    def texte(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            return n.value
        if isinstance(n, ast.JoinedStr):
            return "".join(v.value if isinstance(v, ast.Constant) else " "
                           for v in n.values)
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Mod)):
            return (texte(n.left) or "") + " " + (texte(n.right) or "")
        return None

    with open(path, encoding="utf-8") as fh:
        arbre = ast.parse(fh.read())
    for n in ast.walk(arbre):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        nom = (f.attr if isinstance(f, ast.Attribute)
               else f.id if isinstance(f, ast.Name) else None)
        if nom not in APPELS_AFFICHAGE:
            continue
        for arg in list(n.args) + [k.value for k in n.keywords]:
            t = texte(arg)
            if t is None or t.strip() in TEXTES_NEUTRES:
                continue
            # balises HTML, champs de format et entites ne sont pas des mots
            nu = re.sub(r"<[^>]*>", " ", t)
            nu = re.sub(r"\{[^}]*\}|%[sdf]|&\w+;", " ", nu)
            if re.search(r"[A-Za-zÀ-ÿ]{2,}", nu):
                yield n.lineno, nom, t[:50]


def test_stl():
    print("\n[11] Export STL")
    from anticythere import stl_export as sx
    from collections import Counter
    worst = None
    for name in ("b1", "d2", "m1", "k1", "n2"):
        v, f = sx.printable_gear(name, 1.0, 3.0, 0.15, 3.2, "involute")
        e = Counter()
        for tri in f:
            for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
                e[(min(a, b), max(a, b))] += 1
        opened = sum(1 for c in e.values() if c != 2)
        if opened:
            worst = (name, opened)
    check(worst is None, "maillages fermes (chaque arete partagee par 2 faces)",
          str(worst))
    # le jeu doit reellement retirer de la matiere
    big = sx.printable_gear("m1", 1.0, 3.0, 0.0, 3.2, "involute")[0]
    small = sx.printable_gear("m1", 1.0, 3.0, 0.30, 3.2, "involute")[0]
    import numpy as np
    r_big = np.hypot(big[:, 0], big[:, 1]).max()
    r_small = np.hypot(small[:, 0], small[:, 1]).max()
    # un jeu de 0,30 mm doit reculer le contour de 0,15 mm de chaque cote,
    # y compris a la pointe des dents (compensation d'onglet)
    recul = r_big - r_small
    check(abs(recul - 0.15) < 0.02,
          f"jeu 0,30 mm -> recul de {recul:.3f} mm a la pointe (attendu 0,150)")
    for prof in ("involute", "triangular"):
        p = geo.gear_outline(20, 1.0, prof)
        ang = np.unwrap(np.arctan2(p[:, 1], p[:, 0]))
        back = int((np.diff(ang) < -1e-9).sum())
        check(back == 0, f"contour {prof} monotone en angle "
                         f"({back} retours en arriere)")


def test_updater():
    print("\n[12] Mise a jour (kit Windows)")
    import updater
    check(updater._version_tuple("v1.2.3") == (1, 2, 3), "lecture de version")
    check(updater.is_newer("1.2.0", "1.1.9"), "1.2.0 > 1.1.9")
    check(not updater.is_newer("1.0.0", "1.0.0"), "meme version : pas de MAJ")
    check(not updater.is_newer("0.9.9", "1.0.0"), "version plus ancienne")
    check(not updater.is_packaged(), "depuis les sources : pas de paquet")
    check(updater.check("") is None, "version inconnue : aucune proposition")
    check(updater._hote_de_confiance("https://github.com/x/y/releases/download/v1/a.zip"),
          "GitHub est un hote de confiance")
    check(not updater._hote_de_confiance("http://github.com/x"), "http refuse")
    check(not updater._hote_de_confiance("https://exemple.org/a.zip"), "hote inconnu refuse")
    check(updater.REPO == "ARP273-ROSE/Anticythere3D", f"depot de distribution : {updater.REPO}")


def test_frozen():
    """Mode executable : sys.executable N'EST PAS un interpreteur Python.

    Sans ces garde-fous, l'exe se relance lui-meme avec des arguments qu'il ne
    comprend pas, conclut a tort que Qt ne demarre pas, et se ferme en
    silence — c'est exactement ce qui empechait l'exe Windows de s'ouvrir.
    """
    print("\n[13] Comportement en executable fige")
    import sys as _sys
    from anticythere import bootstrap
    had = hasattr(_sys, "frozen")
    _sys.frozen = True
    try:
        check(bootstrap.frozen(), "le mode fige est bien detecte")
        rep = bootstrap.ensure()
        check(rep["ok"] and not rep["installed"],
              "ensure() n'installe rien et declare l'application utilisable")
        check(bootstrap.install(["nimportequoi"]) is False,
              "install() refuse d'appeler pip depuis un executable")

        # l'invariant qui compte : AUCUN sous-processus ne doit etre lance,
        # puisqu'il relancerait l'executable au lieu d'un interpreteur.
        # (le resultat lui-meme depend des bibliotheques presentes : sur une
        # machine sans libGL, False est la bonne reponse)
        import subprocess
        calls = []
        real_run, real_call = subprocess.run, subprocess.check_call
        subprocess.run = lambda *a, **k: calls.append(a) or real_run(*a, **k)
        subprocess.check_call = lambda *a, **k: calls.append(a)
        try:
            res = bootstrap.qt_can_start()
        finally:
            subprocess.run, subprocess.check_call = real_run, real_call
        check(isinstance(res, bool) and not calls,
              f"qt_can_start() teste en direct, sans sous-processus (a={res})",
              str(calls))
    finally:
        if not had:
            del _sys.frozen


def test_explode():
    """L'éclatement écarte les étages LE LONG DES ARBRES, et rien d'autre.

    Défaut signalé : « les engrenages se rentrent dedans et changent de
    position ». L'ancienne formule ajoutait au pas des étages un décalage de
    sens contraire : vers 57 % les 16 plans se confondaient, puis
    s'inversaient. Ce test verrouille les quatre propriétés attendues.
    """
    print("\n[14] Eclatement des etages")
    from itertools import combinations
    valeurs = (0.0, 0.1, 0.25, 0.5, 0.75, 1.0)
    porte = (0.0, 0.137, 0.5, 0.81)            # positions du porte-satellite

    def tete(g):
        return lay.MODULE * (TEETH[g] / 2.0 + 1.0)

    # 1. aucune roue ne bouge dans son plan
    bouge = []
    for c in porte:
        ref = {g: lay.gear_placement(g, 0.0, c)[:2] for g in lay.LEVELS}
        for e in valeurs:
            for g in lay.LEVELS:
                x, y, _ = lay.gear_placement(g, e, c)
                if math.hypot(x - ref[g][0], y - ref[g][1]) > 1e-9:
                    bouge.append((g, e, c))
    check(not bouge, f"positions dans le plan inchangees "
                     f"({len(lay.LEVELS)} roues x {len(valeurs)} valeurs x "
                     f"{len(porte)} angles du porte-satellite)", str(bouge[:5]))

    # 2. les roues d'un meme plan restent dans le meme plan (engrenements)
    meme_plan = all(
        len({round(lay.gear_placement(g, e)[2], 9)
             for g in lay.LEVELS if lay.LEVELS[g] == lv}) == 1
        for lv in set(lay.LEVELS.values()) for e in valeurs)
    check(meme_plan, "les roues qui s'engrenent restent dans un meme plan")

    # 3. monotonie : l'ordre des etages ne change jamais, chaque roue avance
    # (ou reste) quand on augmente le curseur, et les jeux grandissent
    ordre = all(lay.level_z(lv, e) > lay.level_z(lv + 1, e)
                for e in valeurs for lv in range(1, lay.N_LEVELS))
    check(ordre, "l'ordre des 16 etages est conserve a toute valeur")
    avance = all(lay.gear_placement(g, b)[2] >= lay.gear_placement(g, a)[2]
                 for g in lay.LEVELS for a, b in zip(valeurs, valeurs[1:]))
    check(avance, "chaque roue s'ecarte de facon monotone")
    jeux = [lay.level_pitch(e) - lay.GEAR_THICKNESS for e in valeurs]
    check(all(b > a for a, b in zip(jeux, jeux[1:])) and jeux[0] > 0,
          f"jeu entre etages : {jeux[0]:.1f} mm monte, {jeux[-1]:.1f} mm eclate")

    # 4. aucune collision : cylindres englobants (rayon de tete, epaisseur)
    # des roues de plans differents, puis arbres contre roues
    collisions, jeu_min = [], float("inf")
    for e in valeurs:
        for c in porte:
            pos = {g: lay.gear_placement(g, e, c) for g in lay.LEVELS}
            for a, b in combinations(lay.LEVELS, 2):
                if lay.LEVELS[a] == lay.LEVELS[b]:
                    continue
                (xa, ya, za), (xb, yb, zb) = pos[a], pos[b]
                if math.hypot(xa - xb, ya - yb) >= tete(a) + tete(b):
                    continue                     # disques disjoints en plan
                jeu = max(za, zb) - (min(za, zb) + lay.GEAR_THICKNESS)
                jeu_min = min(jeu_min, jeu)
                if jeu <= 0:
                    collisions.append((a, b, e))
    check(not collisions, f"aucune roue n'en penetre une autre "
                          f"(jeu minimal {jeu_min:.2f} mm)", str(collisions[:5]))

    traverse = []
    for e in valeurs:
        for arbre, (x, y) in lay.ARBORS.items():
            z0, z1 = lay.arbor_extent(arbre, e)
            for g in lay.LEVELS:
                # une roue a bras laisse passer les arbres voisins : c'est la
                # raison d'etre de ses bras (b1, e3, e4)
                if lay.ARBOR_OF[g] == arbre or g in lay.SPOKED:
                    continue
                xg, yg, zg = lay.gear_placement(g, e)
                if math.hypot(x - xg, y - yg) >= tete(g) + lay.ARBOR_RADIUS:
                    continue
                if z0 < zg + lay.GEAR_THICKNESS and zg < z1:
                    traverse.append((arbre, g, e))
    check(not traverse, "aucun arbre ne traverse une roue pleine d'un autre "
                        "arbre, a toute valeur du curseur", str(traverse[:5]))

    # les arbres s'allongent avec la pile
    long0 = lay.arbor_span("e", 0.0)
    long1 = lay.arbor_span("e", 1.0)
    check((long1[1] - long1[0]) > (long0[1] - long0[0]) + 50,
          f"l'arbre e s'allonge : {long0[1] - long0[0]:.0f} -> "
          f"{long1[1] - long1[0]:.0f} mm")
    check(lay.front_shift(0.0) == 0.0 and lay.front_shift(1.0) > 150,
          f"la facade avance de {lay.front_shift(1.0):.0f} mm a 100 %")


def test_palette():
    """Couleurs des sous-ensembles : distinctes pour tout le monde."""
    print("\n[15] Palette des sous-ensembles (CIEDE2000, daltonismes)")
    from itertools import combinations
    from anticythere import palette as pal
    keys = list(lay.SUBSYSTEMS)
    rgb = {k: lay.COLORS[k][:3] for k in keys}
    # l'implementation CIEDE2000 elle-meme, sur les paires de Sharma (2005)
    check(abs(pal.ciede2000((50, 2.6772, -79.7751), (50, 0, -82.7485))
              - 2.0425) < 1e-3
          and abs(pal.ciede2000((50, 2.5, 0), (73, 25, -18)) - 27.1492) < 1e-3,
          "CIEDE2000 conforme aux donnees de test de Sharma et al.")

    def pire(paires, vision):
        return min((pal.delta_e(rgb[a], rgb[b], vision), a, b)
                   for a, b in paires)

    toutes = list(combinations(keys, 2))
    d, a, b = pire(toutes, "normal")
    check(d > 20, f"vision normale : dE00 >= {d:.1f} entre TOUS les "
                  f"sous-ensembles (pire : {a}/{b})")
    for vision in ("deutan", "protan"):
        d, a, b = pire(lay.NEIGHBOURS, vision)
        check(d > 15, f"{vision} : dE00 >= {d:.1f} entre sous-ensembles "
                      f"voisins (pire : {a}/{b})")
        d, a, b = pire(toutes, vision)
        check(d > 10, f"{vision} : dE00 >= {d:.1f} entre tous (pire : {a}/{b})")
    d, a, b = pire(toutes, "tritan")
    check(d > 10, f"tritan : dE00 >= {d:.1f} entre tous (pire : {a}/{b})")
    k = min(pal.contrast(rgb[x], lay.BACKGROUND) for x in keys)
    check(k >= 3.0, f"contraste sur le fond parchemin >= {k:.2f}:1 (WCAG 3:1)")
    check(set(lay.SUBSYSTEM_OF) == set(lay.LEVELS),
          "chaque roue appartient a un sous-ensemble colore")


def test_crank():
    print("\n[16] Manivelle")
    check(lay.CRANK_PER_TURN == -TEETH["b1"] / TEETH["a1"],
          "un tour de b1 = 223/48 tours de manivelle, en sens contraire")
    m = Mechanism()
    a0 = m.gear_angles()["a1"]
    m.turns += 1.0 / lay.CRANK_PER_TURN           # un tour de poignee
    check(abs((m.gear_angles()["a1"] - a0) - 1.0) < 1e-12,
          "faire tourner la poignee d'un tour fait tourner a1 d'un tour")
    check(abs(m.days - (-48 / 223 * 365.24219)) < 1e-6,
          f"un tour de poignee = {abs(m.days):.1f} jours")


def main() -> int:
    print("=" * 70)
    print("  TESTS — Machine d'Anticythere")
    print("=" * 70)
    for fn in (test_ratios, test_carrier_and_anomalistic_month, test_pin_and_slot,
               test_dials, test_planets, test_astro, test_calibration,
               test_geometry, test_layout, test_i18n, test_stl, test_updater,
               test_frozen, test_explode, test_palette, test_crank):
        fn()
    print("\n" + "=" * 70)
    if FAILURES:
        print(f"  {len(FAILURES)} ECHEC(S) : {FAILURES}")
        return 1
    print("  TOUS LES TESTS PASSENT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
