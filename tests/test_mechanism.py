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

sys.path.insert(0, __file__.rsplit("/", 2)[0])

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


def main() -> int:
    print("=" * 70)
    print("  TESTS — Machine d'Anticythere")
    print("=" * 70)
    for fn in (test_ratios, test_carrier_and_anomalistic_month, test_pin_and_slot,
               test_dials, test_planets, test_astro, test_calibration,
               test_geometry, test_layout, test_i18n):
        fn()
    print("\n" + "=" * 70)
    if FAILURES:
        print(f"  {len(FAILURES)} ECHEC(S) : {FAILURES}")
        return 1
    print("  TOUS LES TESTS PASSENT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
