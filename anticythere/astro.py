"""
Astronomie de référence : sert à CALER la machine sur le ciel réel à une
date donnée, et à mesurer l'écart entre la machine et la réalité.

Reference astronomy: used to CALIBRATE the mechanism against the real sky at
a given date, and to measure the mechanism's error.

Formules : Meeus, *Astronomical Algorithms*, 2e éd., ch. 7 (jour julien),
ch. 25 (Soleil), ch. 47 (Lune, termes principaux). Précision visée :
~0,01° pour le Soleil, ~0,2° pour la Lune — largement suffisant pour
comparer un instrument dont les cadrans se lisent au degré.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

J2000 = 2451545.0
DEG = math.pi / 180.0


# --------------------------------------------------------------------- dates
def julian_day(dt: datetime) -> float:
    """Jour julien (UTC). Calendrier grégorien après 1582-10-15, julien avant.

    Gère les dates antiques (années négatives au sens astronomique).
    """
    y, m = dt.year, dt.month
    d = (dt.day + dt.hour / 24.0 + dt.minute / 1440.0 + dt.second / 86400.0)
    if m <= 2:
        y -= 1
        m += 12
    gregorian = (dt.year, dt.month, dt.day) >= (1582, 10, 15)
    if gregorian:
        a = y // 100
        b = 2 - a + a // 4
    else:
        b = 0
    return (math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1))
            + d + b - 1524.5)


def from_julian_day(jd: float) -> datetime:
    """Inverse de :func:`julian_day` (UTC)."""
    z = math.floor(jd + 0.5)
    f = (jd + 0.5) - z
    if z < 2299161:
        a = z
    else:
        alpha = math.floor((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - math.floor(alpha / 4)
    b = a + 1524
    c = math.floor((b - 122.1) / 365.25)
    d = math.floor(365.25 * c)
    e = math.floor((b - d) / 30.6001)
    day = b - d - math.floor(30.6001 * e) + f
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    di = int(day)
    frac = day - di
    secs = frac * 86400.0
    base = datetime(int(year), int(month), di, tzinfo=timezone.utc)
    return base + timedelta(seconds=secs)


def centuries(jd: float) -> float:
    """Siècles juliens depuis J2000.0."""
    return (jd - J2000) / 36525.0


# --------------------------------------------------------------------- Soleil
def sun_mean_longitude(jd: float) -> float:
    t = centuries(jd)
    return (280.46646 + 36000.76983 * t + 0.0003032 * t * t) % 360.0


def sun_mean_anomaly(jd: float) -> float:
    t = centuries(jd)
    return (357.52911 + 35999.05029 * t - 0.0001537 * t * t) % 360.0


def sun_longitude(jd: float) -> float:
    """Longitude apparente du Soleil (degrés), équation du centre incluse."""
    t = centuries(jd)
    l0 = sun_mean_longitude(jd)
    m = sun_mean_anomaly(jd) * DEG
    c = ((1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(m)
         + (0.019993 - 0.000101 * t) * math.sin(2 * m)
         + 0.000289 * math.sin(3 * m))
    return (l0 + c) % 360.0


# ----------------------------------------------------------------------- Lune
def moon_arguments(jd: float) -> dict:
    """Arguments fondamentaux de la Lune (degrés), Meeus ch. 47."""
    t = centuries(jd)
    return dict(
        Lp=(218.3164477 + 481267.88123421 * t - 0.0015786 * t * t) % 360.0,
        D=(297.8501921 + 445267.1114034 * t - 0.0018819 * t * t) % 360.0,
        M=(357.5291092 + 35999.0502909 * t - 0.0001536 * t * t) % 360.0,
        Mp=(134.9633964 + 477198.8675055 * t + 0.0087414 * t * t) % 360.0,
        F=(93.2720950 + 483202.0175233 * t - 0.0036539 * t * t) % 360.0,
        Omega=(125.0445479 - 1934.1362891 * t + 0.0020754 * t * t) % 360.0,
    )


#: six premiers termes de la table 47.A de Meeus : coefficient (degrés)
#: et multiplicateurs de (D, M, M', F)
_MOON_TERMS = [
    (6.288774, 0, 0, 1, 0),
    (1.274027, 2, 0, -1, 0),
    (0.658314, 2, 0, 0, 0),
    (0.213618, 0, 0, 2, 0),
    (-0.185116, 0, 1, 0, 0),
    (-0.114332, 0, 0, 0, 2),
    (0.058793, 2, 0, -2, 0),
    (0.057066, 2, -1, -1, 0),
    (0.053322, 2, 0, 1, 0),
    (0.045758, 2, -1, 0, 0),
    (-0.040923, 0, 1, -1, 0),
    (-0.034720, 1, 0, 0, 0),
    (-0.030383, 0, 1, 1, 0),
    (0.015327, 2, 0, 0, -2),
    (-0.012528, 0, 0, 1, 2),
    (0.010980, 0, 0, 1, -2),
]


def moon_longitude(jd: float) -> float:
    """Longitude géocentrique de la Lune (degrés)."""
    a = moon_arguments(jd)
    total = 0.0
    for coef, cd, cm, cmp_, cf in _MOON_TERMS:
        arg = (cd * a["D"] + cm * a["M"] + cmp_ * a["Mp"] + cf * a["F"]) * DEG
        total += coef * math.sin(arg)
    return (a["Lp"] + total) % 360.0


def moon_node_longitude(jd: float) -> float:
    """Longitude du nœud ascendant (degrés) — rétrograde, période 18,6 ans."""
    return moon_arguments(jd)["Omega"]


def elongation(jd: float) -> float:
    """Élongation Lune - Soleil (degrés, 0..360). 0 = nouvelle Lune."""
    return (moon_longitude(jd) - sun_longitude(jd)) % 360.0


def illuminated_fraction(jd: float) -> float:
    return (1.0 - math.cos(elongation(jd) * DEG)) / 2.0


# ------------------------------------------------------------------ éclipses
#: limites d'éclipse, en degrés d'écart au nœud (Meeus ch. 54).
#: au-delà de LIMIT, rien ; en deçà de CENTRAL, l'éclipse est certaine ;
#: entre les deux, elle dépend de la parallaxe et du lieu d'observation.
SOLAR_LIMIT = 18.5
SOLAR_CENTRAL = 15.4
LUNAR_LIMIT = 12.2
LUNAR_CENTRAL = 9.5


def eclipse_possible(jd: float) -> dict:
    """Teste grossièrement si une éclipse est possible à cette date.

    Renvoie ``{'type': None|'solar'|'lunar', 'certain': bool, 'arg': float}``.
    Ce n'est PAS un calcul d'éclipse complet : c'est le critère qualitatif
    que la machine elle-même mécanise (syzygie proche d'un nœud).
    """
    e = elongation(jd)
    a = moon_arguments(jd)
    # argument de latitude, ramené à l'écart au nœud le plus proche
    f = a["F"] % 180.0
    dist = min(f, 180.0 - f)
    near_new = min(e, 360.0 - e) < 12.0
    near_full = abs(e - 180.0) < 12.0
    if near_new and dist < SOLAR_LIMIT:
        return dict(type="solar", certain=dist < SOLAR_CENTRAL, arg=dist)
    if near_full and dist < LUNAR_LIMIT:
        return dict(type="lunar", certain=dist < LUNAR_CENTRAL, arg=dist)
    return dict(type=None, certain=False, arg=dist)


# ------------------------------------------------- recherche des éclipses
def _syzygy_gap(jd: float, target: float) -> float:
    """Écart à la syzygie visée (0 = nouvelle Lune, 180 = pleine), dans
    l'intervalle ]-180, 180]."""
    return ((elongation(jd) - target + 180.0) % 360.0) - 180.0


def find_syzygies(jd_start: float, days: float = 1200.0) -> list:
    """Toutes les nouvelles et pleines Lunes de la période, par bissection."""
    out = []
    for target, kind in ((0.0, "new"), (180.0, "full")):
        t = jd_start
        prev = _syzygy_gap(t, target)
        while t < jd_start + days:
            t2 = t + 0.5
            cur = _syzygy_gap(t2, target)
            if prev < 0.0 <= cur:                 # passage par la syzygie
                a, b = t, t2
                for _ in range(60):
                    m = 0.5 * (a + b)
                    if _syzygy_gap(m, target) < 0.0:
                        a = m
                    else:
                        b = m
                out.append((0.5 * (a + b), kind))
            prev, t = cur, t2
    return sorted(out)


def next_eclipses(jd_start: float, count: int = 8,
                  days: float = 1500.0) -> list:
    """Prochaines éclipses : date exacte, type, écart au nœud, certitude.

    On cherche d'abord les syzygies, puis on teste chacune : c'est la
    démarche même que mécanise le Saros.
    """
    res = []
    for jd, kind in find_syzygies(jd_start, days):
        a = moon_arguments(jd)
        f = a["F"] % 180.0
        dist = min(f, 180.0 - f)
        if kind == "new" and dist < SOLAR_LIMIT:
            res.append(dict(jd=jd, type="solar", arg=dist,
                            certain=dist < SOLAR_CENTRAL))
        elif kind == "full" and dist < LUNAR_LIMIT:
            res.append(dict(jd=jd, type="lunar", arg=dist,
                            certain=dist < LUNAR_CENTRAL))
        if len(res) >= count:
            break
    return res


# --------------------------------------------------------------- calibration
def calibration_offsets(jd: float, mech) -> dict:
    """Décalages à appliquer aux sorties pour caler la machine sur le ciel.

    On règle la machine une fois pour toutes à la date `jd` (comme le faisait
    son propriétaire), puis elle avance avec ses propres rapports.
    """
    a = moon_arguments(jd)
    return dict(
        # la machine affiche le Soleil MOYEN : on la cale dessus
        mean_sun=sun_mean_longitude(jd) / 360.0,
        # ... et la Lune MOYENNE, l'anomalie étant ajoutée ensuite par le
        # tenon-fente ; sans quoi la correction serait comptée deux fois
        moon=a["Lp"] / 360.0,
        # phase du tenon-fente = anomalie moyenne réelle à l'époque
        anomaly=a["Mp"] / 360.0,
        nodes=a["Omega"] / 360.0,
        metonic=0.0,
        saros=0.0,
        planets={},
    )


def calibrate_planets(jd: float) -> dict:
    """Longitudes héliocentriques moyennes très simplifiées, pour caler les
    index planétaires à l'époque (les planètes ne sont pas l'objet de ce
    simulateur : le palier 2 ne les comporte pas)."""
    t = centuries(jd)
    mean = {"mercury": 252.250906 + 149472.6746358 * t,
            "venus": 181.979801 + 58517.8156760 * t,
            "mars": 355.433000 + 19141.6964471 * t,
            "jupiter": 34.351519 + 3036.3027748 * t,
            "saturn": 50.077444 + 1223.5110686 * t}
    return {k: (v % 360.0) / 360.0 for k, v in mean.items()}
