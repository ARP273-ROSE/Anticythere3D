"""
Moteur cinématique de la machine d'Anticythère (palier 2 : les 30 roues
attestées + entrée + phase de Lune), plus les planètes du modèle 2021.

Kinematic engine of the Antikythera Mechanism (tier 2: the 30 attested
gears + input + Moon phase), plus the planets of the 2021 model.

Toutes les fractions sont EXACTES (fractions.Fraction) : les rapports sont
ceux des nombres de dents relevés par tomographie (Freeth et al. 2006, 2008)
et vérifiés indépendamment sous SageMath.

Convention interne
------------------
`t` = nombre de tours de la grande roue b1 depuis l'époque de calage.
1 tour de b1 = 1 année tropique = 365,24219 jours.
Tous les angles sont exprimés en TOURS (0 = origine, 1 = tour complet) et
convertis en degrés seulement à l'affichage.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from fractions import Fraction as F

TROPICAL_YEAR = 365.24219        # jours
SYNODIC_MONTH = 29.530588853     # jours (valeur moderne, pour comparaison)

# --------------------------------------------------------------------------
# Nombres de dents relevés (Freeth et al., Nature 444, 2006, Suppl. Notes ;
# Nature 454, 2008). Les roues étant corrodées, ce sont des estimations
# reconstruites — mais tous les rapports ci-dessous tombent exactement juste.
# --------------------------------------------------------------------------
TEETH = {
    "a1": 48, "b1": 223, "b2": 64, "b3": 32,
    "c1": 38, "c2": 48, "d1": 24, "d2": 127,
    "e1": 32, "e2": 32, "e3": 223, "e4": 188, "e5": 50, "e6": 50,
    "f1": 53, "f2": 30, "g1": 54, "g2": 20,
    "h1": 60, "h2": 15, "i1": 60,
    "k1": 50, "k2": 50,
    "l1": 38, "l2": 53, "m1": 96, "m2": 15, "m3": 27,
    "n1": 53, "n2": 15, "o1": 60, "p1": 60, "p2": 12,
}

# Chaînes (roue menante, roue menée). Deux roues de même lettre sont
# solidaires du même arbre et ne comptent qu'une fois.
TRAINS = {
    "metonic":    [("b2", "l1"), ("l2", "m1"), ("m2", "n1")],
    "callippic":  [("b2", "l1"), ("l2", "m1"), ("m2", "n1"),
                   ("n2", "p1"), ("p2", "o1")],
    "saros":      [("b2", "l1"), ("l2", "m1"), ("m3", "e3"),
                   ("e4", "f1"), ("f2", "g1")],
    "exeligmos":  [("b2", "l1"), ("l2", "m1"), ("m3", "e3"),
                   ("e4", "f1"), ("f2", "g1"), ("g2", "h1"), ("h2", "i1")],
    "moon_sid":   [("b2", "c1"), ("c2", "d1"), ("d2", "e2")],
    "carrier_e3": [("b2", "l1"), ("l2", "m1"), ("m3", "e3")],
}


def train_ratio(pairs) -> F:
    """Produit exact des rapports (menante / menée) le long d'un train."""
    r = F(1)
    for driver, driven in pairs:
        r *= F(TEETH[driver], TEETH[driven])
    return r


#: rapports exacts, en tours de sortie par tour de b1 (donc par année)
RATIOS = {name: train_ratio(pairs) for name, pairs in TRAINS.items()}
RATIOS["mean_sun"] = F(1)
#: ligne des nœuds : rétrograde. 12/223 n'est pas mécanisable (223 premier),
#: Freeth et al. 2021 proposent un train épicycloïdal réalisant -5/93.
RATIOS["nodes"] = F(-5, 93)

#: valeurs attendues, servant de test de non-régression
EXPECTED = {
    "metonic": F(5, 19), "callippic": F(1, 76), "saros": F(940, 4237),
    "exeligmos": F(235, 12711), "moon_sid": F(254, 19),
    "carrier_e3": F(477, 4237),
}

# --------------------------------------------------------------------------
# Relations de période des planètes (Freeth et al., Sci. Rep. 11:5821, 2021)
# (cycles synodiques, années) ; inferior = orbite intérieure à celle de la Terre
# --------------------------------------------------------------------------
PLANETS = {
    "mercury": dict(syn=1513, years=480, inferior=True),
    "venus":   dict(syn=289,  years=462, inferior=True),
    "mars":    dict(syn=133,  years=284, inferior=False),
    "jupiter": dict(syn=315,  years=344, inferior=False),
    "saturn":  dict(syn=427,  years=442, inferior=False),
}

for _p, _d in PLANETS.items():
    q, p = _d["years"], _d["syn"]
    # période sidérale déduite : q/(q+p) si inférieure, q/(q-p) sinon
    _d["sidereal_ratio"] = F(q + p, q) if _d["inferior"] else F(q - p, q)


# --------------------------------------------------------------------------
# Tenon et fente (pin-and-slot)
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class PinAndSlot:
    """Dispositif à tenon et fente des roues k1/k2.

    `eps` : distance entre les deux axes (mm) ; `r` : rayon du tenon (mm).
    Cotes relevées par tomographie : eps = 1,1 mm, r = 9,6 mm, ce qui donne
    une amplitude de arcsin(eps/r) = 6,58°, à comparer aux 6,29° de
    l'équation du centre réelle de la Lune.
    """

    eps: float = 1.1
    r: float = 9.6

    @property
    def amplitude_deg(self) -> float:
        return math.degrees(math.asin(self.eps / self.r))

    def delta_turns(self, rel_turns: float) -> float:
        """Écart angulaire (en tours) introduit par le dispositif.

        `rel_turns` est l'angle d'entrée mesuré dans le repère du
        porte-satellite, en tours. Formule exacte, pas une approximation :
            theta2 - theta1 = atan2(eps.sin(th), r + eps.cos(th))

        Le signe dépend du sens de montage du tenon ; on retient celui qui
        reproduit l'équation du centre (la Lune est en avance sur sa position
        moyenne dans la moitié du cycle qui suit le périgée), soit au premier
        ordre  delta ~ +(eps/r) sin(th)  à comparer à  +2e sin(M).
        """
        th = 2.0 * math.pi * rel_turns
        d = math.atan2(self.eps * math.sin(th), self.r + self.eps * math.cos(th))
        return d / (2.0 * math.pi)

    def speed_ratio(self, rel_turns: float) -> float:
        """Rapport de vitesse instantané d(theta2)/d(theta1)."""
        th = 2.0 * math.pi * rel_turns
        num = self.r * (self.r + self.eps * math.cos(th))
        den = self.r ** 2 + self.eps ** 2 + 2.0 * self.r * self.eps * math.cos(th)
        return num / den


# --------------------------------------------------------------------------
# État complet de la machine
# --------------------------------------------------------------------------
@dataclass
class Outputs:
    """Toutes les sorties de la machine pour un état donné."""

    turns: float                  # tours de manivelle depuis l'époque
    days: float                   # jours écoulés depuis l'époque
    mean_sun: float               # tours (= date dans le zodiaque)
    moon_mean: float              # Lune moyenne (sidérale)
    moon_true: float              # Lune corrigée de l'anomalie
    moon_anomaly_deg: float       # correction appliquée, en degrés
    carrier_e3: float             # porte-satellite (apogée lunaire)
    nodes: float                  # ligne des nœuds (rétrograde)
    phase_turns: float            # élongation Lune - Soleil
    phase_illum: float            # fraction éclairée, 0..1
    metonic: float                # tours du pointeur métonique
    metonic_cell: int             # case 1..235
    metonic_year: int             # année 1..19 du cycle
    callippic: float
    callippic_quarter: int        # 1..4
    saros: float
    saros_cell: int               # case 1..223
    exeligmos: float
    exeligmos_sector: int         # 1..3  (correction 0 h, 8 h, 16 h)
    exeligmos_hours: int          # 0, 8 ou 16
    games_year: int               # 1..4
    games_name: str               # clé i18n du jeu de l'année
    planets: dict = field(default_factory=dict)   # nom -> tours
    eclipse: dict = field(default_factory=dict)   # info éclipse de la lunaison


GAMES = ["isthmia", "olympia", "nemea", "pythia"]


class Mechanism:
    """La machine complète. Sans état graphique : purement numérique."""

    def __init__(self, pin_slot: PinAndSlot | None = None,
                 offsets: dict | None = None):
        self.pin = pin_slot or PinAndSlot()
        # offsets de calage (en tours) appliqués à chaque sortie pour que la
        # machine corresponde au ciel réel à l'époque choisie
        self.offsets = dict(mean_sun=0.0, moon=0.0, nodes=0.0, anomaly=0.0,
                            metonic=0.0, saros=0.0, planets={})
        if offsets:
            self.offsets.update(offsets)
        self._turns = 0.0

    # ---------------------------------------------------------------- état
    @property
    def turns(self) -> float:
        return self._turns

    @turns.setter
    def turns(self, value: float) -> None:
        self._turns = float(value)

    @property
    def days(self) -> float:
        return self._turns * TROPICAL_YEAR

    @days.setter
    def days(self, value: float) -> None:
        self._turns = float(value) / TROPICAL_YEAR

    def advance_days(self, n: float) -> None:
        self.days = self.days + n

    # ------------------------------------------------------- sorties brutes
    def raw(self, name: str) -> float:
        """Rotation d'une sortie, en tours, sans calage."""
        return float(RATIOS[name]) * self._turns

    def moon_true_turns(self) -> tuple[float, float]:
        """Lune vraie (tours) et correction d'anomalie (degrés).

        La modulation du tenon-fente est indexée sur l'angle d'entrée mesuré
        dans le repère du porte-satellite e3 (formule de Willis) : sa période
        est donc le mois anomalistique, et non le mois sidéral.
        """
        mean = self.raw("moon_sid") + self.offsets["moon"]
        rel = self.anomaly_phase()
        d = self.pin.delta_turns(rel)
        return mean + d, d * 360.0

    def anomaly_phase(self) -> float:
        """Phase du tenon-fente (en tours) = anomalie moyenne de la Lune.

        C'est la différence entre la rotation de la Lune sidérale et celle du
        porte-satellite e3 (formule de Willis), calée à l'époque sur
        l'anomalie moyenne réelle.
        """
        return (self.raw("moon_sid") - self.raw("carrier_e3")
                + self.offsets["anomaly"])

    # -------------------------------------------------------------- lecture
    def outputs(self) -> Outputs:
        t = self._turns
        mean_sun = t + self.offsets["mean_sun"]
        moon_mean = self.raw("moon_sid") + self.offsets["moon"]
        moon_true, anom_deg = self.moon_true_turns()

        phase = moon_true - mean_sun
        illum = (1.0 - math.cos(2.0 * math.pi * phase)) / 2.0

        met = self.raw("metonic") + self.offsets["metonic"]
        met_frac = met % 5.0                     # 5 tours = 1 cycle métonique
        met_cell = int(met_frac / 5.0 * 235.0) + 1
        met_year = int((met / 5.0 % 1.0) * 19.0) + 1

        cal = self.raw("callippic")
        cal_q = int((cal % 1.0) * 4.0) + 1

        sar = self.raw("saros") + self.offsets["saros"]
        sar_frac = sar % 4.0                     # 4 tours = 1 Saros
        sar_cell = int(sar_frac / 4.0 * 223.0) + 1

        exe = self.raw("exeligmos")
        # epsilon : après exactement 1 Saros, exe vaut 1/3, mais en flottant
        # (1/3 % 1)*3 = 0,999…, et int() rendrait le secteur précédent — le
        # cadran dirait « +0 h » au moment précis où il faut lire « +8 h ».
        # 1e-9 tour d'exeligmos = 1,7 s : sans effet ailleurs.
        exe_sector = int((exe % 1.0) * 3.0 + 1e-9) + 1
        exe_hours = ((exe_sector - 1) % 3) * 8

        games_year = int(t % 4.0) + 1

        planets = {}
        for name, d in PLANETS.items():
            planets[name] = (float(d["sidereal_ratio"]) * t
                             + self.offsets["planets"].get(name, 0.0))

        return Outputs(
            turns=t, days=self.days,
            mean_sun=mean_sun, moon_mean=moon_mean, moon_true=moon_true,
            moon_anomaly_deg=anom_deg,
            carrier_e3=self.raw("carrier_e3"),
            nodes=self.raw("nodes") + self.offsets["nodes"],
            phase_turns=phase, phase_illum=illum,
            metonic=met, metonic_cell=met_cell, metonic_year=met_year,
            callippic=cal, callippic_quarter=cal_q,
            saros=sar, saros_cell=sar_cell,
            exeligmos=exe, exeligmos_sector=exe_sector, exeligmos_hours=exe_hours,
            games_year=games_year, games_name=GAMES[(games_year - 1) % 4],
            planets=planets,
        )

    # ------------------------------------------------- rotation des rouages
    def gear_angles(self) -> dict:
        """Angle de rotation (en tours) de CHAQUE roue, pour l'animation 3D.

        Deux roues du même arbre tournent ensemble ; le sous-ensemble
        k1/k2 est traité à part (rotation propre + rotation du porte-satellite).
        """
        t = self._turns
        a = {}
        # arbre b : la roue motrice
        a["b1"] = a["b2"] = t
        a["a1"] = -t * TEETH["b1"] / TEETH["a1"]

        # train de la Lune
        r = t * float(F(TEETH["b2"], TEETH["c1"]))
        a["c1"] = a["c2"] = -r
        r2 = -r * float(F(TEETH["c2"], TEETH["d1"]))
        a["d1"] = a["d2"] = -r2 if False else r2
        r3 = r2 * float(F(TEETH["d2"], TEETH["e2"]))
        a["e2"] = a["e5"] = -r3
        # le porte-satellite
        carrier = self.raw("carrier_e3")
        a["e3"] = a["e4"] = carrier
        # k1 : rotation absolue = entrée (rapport 1:1 depuis e5)
        a["k1"] = a["e5"]
        rel = self.anomaly_phase()
        a["k2"] = a["k1"] + self.pin.delta_turns(rel)
        a["e6"] = a["e1"] = -a["k2"]
        a["b3"] = -a["e1"]

        # métonique
        m = t * float(F(TEETH["b2"], TEETH["l1"]))
        a["l1"] = a["l2"] = -m
        m2 = -m * float(F(TEETH["l2"], TEETH["m1"]))
        a["m1"] = a["m2"] = a["m3"] = m2
        m3 = m2 * float(F(TEETH["m2"], TEETH["n1"]))
        a["n1"] = a["n2"] = -m3
        m4 = -m3 * float(F(TEETH["n2"], TEETH["p1"]))
        a["p1"] = a["p2"] = m4
        a["o1"] = -m4 * float(F(TEETH["p2"], TEETH["o1"]))

        # saros
        s = a["m3"] * float(F(TEETH["m3"], TEETH["e3"]))
        # (e3 est déjà posée par `carrier` : cohérence garantie par construction)
        s2 = carrier * float(F(TEETH["e4"], TEETH["f1"]))
        a["f1"] = a["f2"] = -s2
        s3 = -s2 * float(F(TEETH["f2"], TEETH["g1"]))
        a["g1"] = a["g2"] = s3
        s4 = s3 * float(F(TEETH["g2"], TEETH["h1"]))
        a["h1"] = a["h2"] = -s4
        a["i1"] = -s4 * float(F(TEETH["h2"], TEETH["i1"]))
        return a


def self_check() -> list[str]:
    """Vérifie les rapports contre les valeurs attendues. Renvoie les erreurs."""
    errs = []
    for name, expected in EXPECTED.items():
        got = RATIOS[name]
        if got != expected:
            errs.append(f"{name}: attendu {expected}, obtenu {got}")
    # cohérence du train du Saros : 4 tours pour 223 lunaisons
    if RATIOS["saros"] != F(4, 223) * F(235, 19):
        errs.append("saros != (4/223)x(235/19)")
    # exeligmos = 1/3 tour par Saros
    if RATIOS["exeligmos"] / RATIOS["saros"] != F(1, 12):
        errs.append("exeligmos/saros != 1/12")
    return errs
