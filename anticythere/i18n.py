"""
Internationalisation FR / EN. Toute chaîne visible passe par :func:`tr`.
Bilingual FR/EN strings. Every visible string goes through :func:`tr`.
"""

from __future__ import annotations

LANGUAGES = {"fr": "Français", "en": "English"}
DEFAULT_LANG = "fr"

T: dict[str, dict[str, str]] = {
    # ------------------------------------------------------------ général
    "app.title": {
        "fr": "Machine d'Anticythère — simulateur 3D",
        "en": "Antikythera Mechanism — 3D simulator"},
    "app.subtitle": {
        "fr": "Le premier calculateur astronomique, en état de marche",
        "en": "The first astronomical calculator, in working order"},
    "app.ready": {"fr": "Prêt", "en": "Ready"},

    # -------------------------------------------------------------- menus
    "menu.file": {"fr": "&Fichier", "en": "&File"},
    "menu.file.screenshot": {"fr": "Capture d'écran…", "en": "Screenshot…"},
    "menu.file.export": {"fr": "Exporter les valeurs (CSV)…",
                         "en": "Export readings (CSV)…"},
    "menu.file.svg": {"fr": "Exporter en SVG (vectoriel)…",
                      "en": "Export as SVG (vector)…"},
    "menu.file.pdf": {"fr": "Exporter en PDF (vectoriel, A3)…",
                      "en": "Export as PDF (vector, A3)…"},
    "menu.file.svg.tip": {
        "fr": "Disponible en rendu vectoriel. Le fichier ne contient que des\n"
              "courbes : on peut zoomer ou imprimer en A0 sans aucun pixel.",
        "en": "Available in vector mode. The file contains curves only:\n"
              "zoom in or print at A0 with no pixels at all."},
    "menu.file.quit": {"fr": "Quitter", "en": "Quit"},
    "menu.view": {"fr": "&Vue", "en": "&View"},
    "menu.view.case": {"fr": "Afficher l'enveloppe", "en": "Show the case"},
    "menu.view.plates": {"fr": "Afficher les platines", "en": "Show the plates"},
    "menu.view.labels": {"fr": "Afficher les noms des roues",
                         "en": "Show gear labels"},
    "menu.view.explode": {"fr": "Vue éclatée", "en": "Exploded view"},
    "menu.view.front": {"fr": "Face avant", "en": "Front face"},
    "menu.view.back": {"fr": "Face arrière", "en": "Back face"},
    "menu.view.iso": {"fr": "Vue 3/4", "en": "Isometric view"},
    "menu.view.reset": {"fr": "Recentrer la caméra", "en": "Reset camera"},
    "menu.lang": {"fr": "&Langue", "en": "&Language"},
    "menu.help": {"fr": "&Aide", "en": "&Help"},
    "menu.help.manual": {"fr": "Manuel d'utilisation", "en": "User manual"},
    "menu.help.science": {"fr": "Les mathématiques de la machine",
                          "en": "The mathematics of the mechanism"},
    "menu.help.shortcuts": {"fr": "Raccourcis clavier", "en": "Keyboard shortcuts"},
    "menu.help.about": {"fr": "À propos", "en": "About"},
    "menu.help.update": {"fr": "Rechercher une mise à jour…",
                         "en": "Check for updates…"},
    "menu.help.update.tip": {
        "fr": "Interroge les versions publiées sur GitHub et propose\n"
              "d'installer la plus récente.",
        "en": "Queries the releases published on GitHub and offers to\n"
              "install the newest one."},
    "menu.file.stl": {"fr": "Exporter les roues en STL…",
                      "en": "Export gears as STL…"},
    "menu.file.stl.tip": {
        "fr": "Écrit un fichier STL par roue, prêt à trancher, avec le jeu\n"
              "d'impression et l'alésage déjà appliqués, plus une nomenclature.",
        "en": "Writes one STL per gear, ready to slice, with printing clearance\n"
              "and bore already applied, plus a bill of materials."},
    "stl.note": {
        "fr": "Jeu de 0,15 mm retiré aux dents, alésage 3,2 mm (axe acier de "
              "3 mm).\nLes roues à bras sont des maillages composites : les "
              "trancheurs les fusionnent sans problème.",
        "en": "0.15 mm clearance removed from the teeth, 3.2 mm bore (3 mm "
              "steel rod).\nSpoked gears are composite meshes; slicers merge "
              "them without trouble."},

    # ------------------------------------------------------- mise à jour
    "update.checking": {"fr": "Recherche d'une mise à jour…",
                        "en": "Checking for updates…"},
    "update.available": {
        "fr": "La version {version} est disponible.\nVous utilisez la {current}.\n\n"
              "Voulez-vous l'installer maintenant ?",
        "en": "Version {version} is available.\nYou are running {current}.\n\n"
              "Install it now?"},
    "update.install": {"fr": "Installer", "en": "Install"},
    "update.later": {"fr": "Plus tard", "en": "Later"},
    "update.downloading": {"fr": "Téléchargement…", "en": "Downloading…"},
    "update.downloaded": {
        "fr": "Téléchargé ici :\n{path}\n\nComme le programme tourne depuis les "
              "sources, il n'est pas remplacé automatiquement.",
        "en": "Downloaded to:\n{path}\n\nSince the program runs from source, it "
              "is not replaced automatically."},
    "update.manual": {
        "fr": "Aucun fichier téléchargeable dans cette version : "
              "va le chercher sur la page des versions.",
        "en": "No downloadable file in this release: fetch it from the "
              "releases page."},
    "update.failed": {"fr": "La mise à jour a échoué : {error}",
                      "en": "Update failed: {error}"},

    # ---------------------------------------------------------- commandes
    "ctrl.title": {"fr": "Commandes", "en": "Controls"},
    "ctrl.crank": {"fr": "Manivelle", "en": "Crank"},
    "ctrl.crank.tip": {
        "fr": "Fais tourner la manivelle : c'est la seule entrée de la machine.\n"
              "Un tour complet = une année. Tout le reste en découle.",
        "en": "Turn the crank: it is the mechanism's only input.\n"
              "One full turn = one year. Everything else follows."},
    "ctrl.play": {"fr": "Animer", "en": "Animate"},
    "ctrl.pause": {"fr": "Pause", "en": "Pause"},
    "ctrl.play.tip": {
        "fr": "Fait tourner la manivelle en continu.",
        "en": "Turns the crank continuously."},
    "ctrl.speed": {"fr": "Vitesse", "en": "Speed"},
    "ctrl.speed.tip": {
        "fr": "Nombre de jours simulés par seconde.",
        "en": "Simulated days per second."},
    "ctrl.step.day": {"fr": "+1 jour", "en": "+1 day"},
    "ctrl.step.month": {"fr": "+1 lunaison", "en": "+1 lunation"},
    "ctrl.step.year": {"fr": "+1 an", "en": "+1 year"},
    "ctrl.back": {"fr": "Reculer", "en": "Step back"},
    "ctrl.reset": {"fr": "Remettre à l'époque", "en": "Reset to epoch"},
    "ctrl.reset.tip": {
        "fr": "Ramène la machine à sa date de calage.",
        "en": "Returns the mechanism to its calibration date."},
    "ctrl.date": {"fr": "Date affichée", "en": "Displayed date"},
    "ctrl.goto": {"fr": "Aller à cette date", "en": "Go to this date"},
    "ctrl.warning.direction": {
        "fr": "Sur la vraie machine, on ne tourne que dans un sens :\n"
              "reculer ferait rattraper le jeu de 30 roues en série.",
        "en": "On the real machine you only ever turn one way:\n"
              "reversing would take up the backlash of 30 gears in series."},

    # ------------------------------------------------------------- cadrans
    "dial.title": {"fr": "Ce qu'affichent les cadrans",
                   "en": "What the dials read"},
    "dial.front": {"fr": "Face avant", "en": "Front face"},
    "dial.back": {"fr": "Face arrière", "en": "Back face"},
    "dial.date": {"fr": "Date", "en": "Date"},
    "dial.egyptian": {"fr": "Calendrier égyptien", "en": "Egyptian calendar"},
    "dial.sun": {"fr": "Soleil (zodiaque)", "en": "Sun (zodiac)"},
    "dial.sun.tip": {
        "fr": "Le pointeur du Soleil moyen est aussi le pointeur de date :\n"
              "un tour de manivelle = un tour de zodiaque = un an.",
        "en": "The mean Sun pointer is also the date pointer:\n"
              "one crank turn = one lap of the zodiac = one year."},
    "dial.moon": {"fr": "Lune (zodiaque)", "en": "Moon (zodiac)"},
    "dial.moon.tip": {
        "fr": "Rapport exact 254/19 : la Lune fait 254 tours du ciel\n"
              "pendant que le Soleil en fait 19. Roue de 127 dents obligatoire.",
        "en": "Exact ratio 254/19: the Moon laps the sky 254 times while\n"
              "the Sun does 19. A 127-tooth gear is unavoidable."},
    "dial.moon.mean": {"fr": "Lune moyenne", "en": "Mean Moon"},
    "dial.anomaly": {"fr": "Correction d'anomalie", "en": "Anomaly correction"},
    "dial.anomaly.tip": {
        "fr": "Écart entre la Lune vraie et la Lune moyenne, produit par le\n"
              "tenon et la fente. Amplitude maximale : ±6,58°.",
        "en": "Difference between true and mean Moon, produced by the\n"
              "pin-and-slot device. Maximum amplitude: ±6.58°."},
    "dial.phase": {"fr": "Phase de la Lune", "en": "Moon phase"},
    "dial.phase.tip": {
        "fr": "Fraction éclairée = (1 − cos φ)/2, où φ est l'élongation\n"
              "Lune − Soleil. Un différentiel fait la soustraction.",
        "en": "Illuminated fraction = (1 − cos φ)/2, φ being the Moon−Sun\n"
              "elongation. A differential performs the subtraction."},
    "dial.nodes": {"fr": "Ligne des nœuds", "en": "Line of nodes"},
    "dial.nodes.tip": {
        "fr": "Les nœuds reculent d'un tour en 18,6 ans. C'est leur position\n"
              "qui décide s'il y a éclipse ou non.",
        "en": "The nodes regress once every 18.6 years. Their position\n"
              "decides whether an eclipse occurs."},
    "dial.metonic": {"fr": "Cadran métonique", "en": "Metonic dial"},
    "dial.metonic.tip": {
        "fr": "Spirale de 5 tours et 235 cases : 19 ans = 235 lunaisons.\n"
              "Rapport exact 5/19.",
        "en": "5-turn spiral, 235 cells: 19 years = 235 lunations.\n"
              "Exact ratio 5/19."},
    "dial.metonic.cell": {"fr": "case {n}/235", "en": "cell {n}/235"},
    "dial.metonic.year": {"fr": "année {n}/19 du cycle",
                          "en": "year {n}/19 of the cycle"},
    "dial.callippic": {"fr": "Cadran callippique", "en": "Callippic dial"},
    "dial.callippic.tip": {
        "fr": "76 ans = 4 cycles métoniques moins un jour. Rapport 1/76.",
        "en": "76 years = 4 Metonic cycles minus one day. Ratio 1/76."},
    "dial.games": {"fr": "Cadran des Jeux", "en": "Games dial"},
    "dial.games.tip": {
        "fr": "Un tour en 4 ans : les jeux panhelléniques.",
        "en": "One turn in 4 years: the panhellenic games."},
    "dial.saros": {"fr": "Spirale du Saros", "en": "Saros spiral"},
    "dial.saros.tip": {
        "fr": "4 tours, 223 cases : 223 lunaisons = 6 585,32 jours.\n"
              "Une éclipse se répète presque à l'identique un Saros plus tard.",
        "en": "4 turns, 223 cells: 223 lunations = 6,585.32 days.\n"
              "An eclipse repeats almost identically one Saros later."},
    "dial.saros.cell": {"fr": "case {n}/223", "en": "cell {n}/223"},
    "dial.exeligmos": {"fr": "Cadran de l'exeligmos", "en": "Exeligmos dial"},
    "dial.exeligmos.tip": {
        "fr": "Un Saros ne fait pas un nombre entier de jours : il reste un\n"
              "tiers de jour, soit 8 heures. Ce cadran donne la correction.",
        "en": "A Saros is not a whole number of days: a third of a day is\n"
              "left over, i.e. 8 hours. This dial gives the correction."},
    "dial.exeligmos.value": {"fr": "ajouter {h} h", "en": "add {h} h"},
    "dial.eclipse.none": {"fr": "pas d'éclipse en vue",
                          "en": "no eclipse due"},
    "dial.eclipse.solar": {"fr": "éclipse de Soleil possible",
                           "en": "solar eclipse possible"},
    "dial.eclipse.lunar": {"fr": "éclipse de Lune possible",
                           "en": "lunar eclipse possible"},
    "dial.eclipse.certain": {"fr": "éclipse quasi certaine",
                             "en": "eclipse near-certain"},
    "dial.planets": {"fr": "Planètes (modèle 2021)", "en": "Planets (2021 model)"},
    "dial.compare": {"fr": "Écart machine / ciel réel",
                     "en": "Mechanism vs real sky"},
    "dial.compare.tip": {
        "fr": "Comparaison avec les éphémérides modernes : c'est l'erreur\n"
              "réelle de l'instrument, accumulée depuis son calage.",
        "en": "Comparison with modern ephemerides: the instrument's real\n"
              "error, accumulated since calibration."},

    # -------------------------------------------------------- explications
    "expl.title": {"fr": "Explications", "en": "Explanations"},
    "expl.select": {"fr": "Choisis un sous-ensemble :",
                    "en": "Pick a subsystem:"},
    "sub.input": {"fr": "Entrée et roue motrice", "en": "Input and main wheel"},
    "sub.moon": {"fr": "Train de la Lune", "en": "Moon train"},
    "sub.anomaly": {"fr": "Anomalie lunaire (tenon et fente)",
                    "en": "Lunar anomaly (pin and slot)"},
    "sub.metonic": {"fr": "Cycle métonique", "en": "Metonic cycle"},
    "sub.callippic": {"fr": "Cycle callippique", "en": "Callippic cycle"},
    "sub.saros": {"fr": "Saros (éclipses)", "en": "Saros (eclipses)"},
    "sub.exeligmos": {"fr": "Exeligmos", "en": "Exeligmos"},

    "expl.input": {
        "fr": "Une manivelle attaque la roue a1 (48 dents), qui entraîne par une "
              "roue de champ la grande roue b1 — 223 dents, 4 bras, 13 cm de "
              "diamètre sur l'original. Un tour de b1 = une année.\n\n"
              "Pourquoi 223 dents ? Parce que 223 est premier et qu'il faut ce "
              "nombre pour fabriquer le Saros. C'est un problème de théorie des "
              "nombres qui a fixé la taille de l'objet.\n\n"
              "Les 4 bras ne sont pas décoratifs : ils laissent passer les arbres "
              "voisins. Sans eux, rien ne tiendrait dans le boîtier.",
        "en": "A crank drives gear a1 (48 teeth), which through a crown gear turns "
              "the great wheel b1 — 223 teeth, 4 spokes, 13 cm across on the "
              "original. One turn of b1 = one year.\n\n"
              "Why 223 teeth? Because 223 is prime and that number is required to "
              "build the Saros. A number-theory constraint set the size of the "
              "whole object.\n\n"
              "The 4 spokes are not decorative: neighbouring arbors pass through "
              "them. Without them nothing would fit in the case."},
    "expl.moon": {
        "fr": "b2 (64) → c1 (38), c2 (48) → d1 (24), d2 (127) → e2 (32).\n\n"
              "Produit des rapports : (64/38)·(48/24)·(127/32) = 254/19, "
              "exactement. En 19 ans, la Lune fait 254 tours du ciel — c'est "
              "235 lunaisons plus 19 tours du Soleil.\n\n"
              "254 = 2 × 127, et 127 est premier : la roue de 127 dents est la "
              "signature du cycle métonique dans le train lunaire. Personne "
              "n'irait tailler 127 dents par hasard.",
        "en": "b2 (64) → c1 (38), c2 (48) → d1 (24), d2 (127) → e2 (32).\n\n"
              "Product of ratios: (64/38)·(48/24)·(127/32) = 254/19, exactly. "
              "In 19 years the Moon laps the sky 254 times — that is 235 "
              "lunations plus the Sun's 19 laps.\n\n"
              "254 = 2 × 127, and 127 is prime: the 127-tooth wheel is the "
              "signature of the Metonic cycle inside the lunar train. Nobody "
              "cuts 127 teeth by accident."},
    "expl.anomaly": {
        "fr": "La Lune ne va pas à vitesse constante : près du périgée elle file, "
              "près de l'apogée elle traîne. L'écart atteint 6,3°.\n\n"
              "La machine le reproduit par un dispositif à tenon et fente : la "
              "roue k1 porte une goupille qui coulisse dans une fente de k2, et "
              "les deux axes sont décalés de 1,1 mm seulement. Un tour pour un "
              "tour — mais pas à vitesse constante. Amplitude : arcsin(1,1/9,6) "
              "= 6,58°, plus juste que la valeur transmise par Ptolémée.\n\n"
              "Le trait de génie : ces deux roues sont montées sur e3, qui tourne "
              "en 8,88 ans — la précession de l'apogée lunaire. La modulation a "
              "donc pour période la différence des deux rotations, soit "
              "27,553 jours : le mois anomalistique, à deux minutes près. "
              "Ce nombre n'est écrit nulle part : il émerge du mécanisme.",
        "en": "The Moon does not move at constant speed: near perigee it races, "
              "near apogee it lags. The difference reaches 6.3°.\n\n"
              "The mechanism reproduces this with a pin-and-slot device: wheel k1 "
              "carries a pin sliding in a slot in k2, and the two axes are offset "
              "by a mere 1.1 mm. One turn for one turn — but not at constant "
              "speed. Amplitude: arcsin(1.1/9.6) = 6.58°, closer to the truth "
              "than the value handed down by Ptolemy.\n\n"
              "The stroke of genius: both wheels ride on e3, which turns once in "
              "8.88 years — the precession of the lunar apogee. The modulation's "
              "period is therefore the difference of the two rotations, i.e. "
              "27.553 days: the anomalistic month, to within two minutes. "
              "That number is written nowhere: it emerges from the mechanism."},
    "expl.metonic": {
        "fr": "19 années solaires valent 235 lunaisons à deux heures près. "
              "Ce n'est pas un hasard : 235/19 est la meilleure approximation "
              "rationnelle du nombre de lunaisons par an (12,368 26…) — c'est la "
              "sixième réduite de son développement en fraction continue.\n\n"
              "Train : b2 (64) → l1 (38), l2 (53) → m1 (96), m2 (15) → n1 (53). "
              "Le produit vaut exactement 5/19 : le pointeur fait 5 tours en "
              "19 ans, ce qui parcourt les 5 spires et les 235 cases de la "
              "spirale.\n\n"
              "Erreur du cycle : 2 h 05 sur 19 ans, soit un jour tous les 219 ans.",
        "en": "19 solar years equal 235 lunations to within two hours. This is no "
              "accident: 235/19 is the best rational approximation of the number "
              "of lunations per year (12.368 26…) — the sixth convergent of its "
              "continued fraction.\n\n"
              "Train: b2 (64) → l1 (38), l2 (53) → m1 (96), m2 (15) → n1 (53). "
              "The product is exactly 5/19: the pointer makes 5 turns in 19 years, "
              "sweeping the spiral's 5 coils and 235 cells.\n\n"
              "Cycle error: 2 h 05 over 19 years, i.e. one day every 219 years."},
    "expl.callippic": {
        "fr": "Callippe remarqua que le cycle de Méton, appliqué comme 19 ans = "
              "6 940 jours, est un peu trop long. Il proposa de prendre quatre "
              "cycles et de retirer un jour : 76 ans = 27 759 jours, soit une "
              "année de 365,25 jours exactement.\n\n"
              "C'est l'année julienne, adoptée par Rome trois siècles plus tard — "
              "avec la même erreur d'un jour tous les 128 ans, celle que la "
              "réforme grégorienne corrigera en 1582.\n\n"
              "Sur la machine : n2 (15) → p1 (60), p2 (12) → o1 (60), soit 1/20 "
              "du pointeur métonique, donc 1/76 de tour par an.",
        "en": "Callippus noticed that Meton's cycle, applied as 19 years = 6,940 "
              "days, runs slightly long. He proposed taking four cycles and "
              "dropping one day: 76 years = 27,759 days, i.e. a year of exactly "
              "365.25 days.\n\n"
              "That is the Julian year, adopted by Rome three centuries later — "
              "with the same error of one day per 128 years, the one the Gregorian "
              "reform would fix in 1582.\n\n"
              "On the mechanism: n2 (15) → p1 (60), p2 (12) → o1 (60), i.e. 1/20 "
              "of the Metonic pointer, hence 1/76 turn per year."},
    "expl.saros": {
        "fr": "Une éclipse demande trois coïncidences : bonne phase, proximité "
              "d'un nœud, et distance de la Lune. Le Saros est l'intervalle qui "
              "est entier dans les trois horloges à la fois :\n\n"
              "   223 mois synodiques   = 6 585,32 j\n"
              "   242 mois draconitiques = 6 585,36 j\n"
              "   239 mois anomalistiques = 6 585,54 j\n\n"
              "Train : …m3 (27) → e3 (223), e4 (188) → f1 (53), f2 (30) → g1 (54). "
              "Le rapport vaut 940/4237 = (4/223)·(235/19) : quatre tours de "
              "pointeur pour 223 lunaisons, soit les 4 spires et 223 cases de la "
              "spirale. Il faut une roue de 223 dents, car 223 est premier.",
        "en": "An eclipse needs three coincidences: right phase, nearness to a "
              "node, and the Moon's distance. The Saros is the interval that is "
              "whole in all three clocks at once:\n\n"
              "   223 synodic months     = 6,585.32 d\n"
              "   242 draconic months    = 6,585.36 d\n"
              "   239 anomalistic months = 6,585.54 d\n\n"
              "Train: …m3 (27) → e3 (223), e4 (188) → f1 (53), f2 (30) → g1 (54). "
              "The ratio is 940/4237 = (4/223)·(235/19): four pointer turns per "
              "223 lunations, matching the spiral's 4 coils and 223 cells. "
              "A 223-tooth wheel is required, because 223 is prime."},
    "expl.exeligmos": {
        "fr": "Le Saros ne dure pas un nombre entier de jours : il reste 7 h 51, "
              "soit environ un tiers de jour. Pendant ce temps la Terre tourne de "
              "116°, si bien que l'éclipse suivante est visible bien plus à "
              "l'ouest.\n\n"
              "Trois Saros ramènent à la même longitude : c'est l'exeligmos, "
              "54 ans et 33 jours. Le petit cadran porte 0 h, 8 h et 16 h — la "
              "correction horaire à ajouter à l'heure lue dans le glyphe.\n\n"
              "Train : g2 (20) → h1 (60), h2 (15) → i1 (60), soit 1/12 ; comme le "
              "pointeur du Saros fait 4 tours par Saros, celui-ci en fait 1/3.",
        "en": "A Saros is not a whole number of days: 7 h 51 min are left over, "
              "about a third of a day. In that time the Earth turns 116°, so the "
              "next eclipse is seen far to the west.\n\n"
              "Three Saroses return to the same longitude: that is the exeligmos, "
              "54 years and 33 days. The small dial reads 0 h, 8 h and 16 h — the "
              "correction to add to the hour given by the glyph.\n\n"
              "Train: g2 (20) → h1 (60), h2 (15) → i1 (60), i.e. 1/12; since the "
              "Saros pointer turns 4 times per Saros, this one turns 1/3."},

    # ------------------------------------------------------------- vue 3D
    # ---------------------------------------------------------- navigation
    "nav.title": {"fr": "Navigation", "en": "Navigation"},
    "nav.home": {"fr": "Recentrer", "en": "Reset"},
    "nav.zoom.in": {"fr": "Zoomer  (touche +)", "en": "Zoom in  (+ key)"},
    "nav.zoom.out": {"fr": "Dézoomer  (touche −)", "en": "Zoom out  (− key)"},
    "nav.up": {"fr": "Basculer vers le haut  (↑)", "en": "Tilt up  (↑)"},
    "nav.down": {"fr": "Basculer vers le bas  (↓)", "en": "Tilt down  (↓)"},
    "nav.left": {"fr": "Tourner à gauche  (←)", "en": "Turn left  (←)"},
    "nav.right": {"fr": "Tourner à droite  (→)", "en": "Turn right  (→)"},
    "nav.roll.left": {"fr": "Rouler à gauche  (Page ↓)",
                      "en": "Roll left  (Page ↓)"},
    "nav.roll.right": {"fr": "Rouler à droite  (Page ↑)",
                       "en": "Roll right  (Page ↑)"},
    "nav.spin.tip": {
        "fr": "Fait tourner lentement le point de vue, sans toucher\n"
              "au mécanisme lui-même.",
        "en": "Slowly rotates the viewpoint, without touching the\n"
              "mechanism itself."},
    "nav.hint": {
        "fr": "Souris : glisser = tourner · molette = zoomer · "
              "clic droit = déplacer (3D) ou pivoter (vectoriel) · "
              "double-clic = recentrer.\n"
              "Clavier : ← ↑ → ↓ tourner · Page ↑↓ rouler · + − zoomer · "
              "R recentrer · Maj = pas plus grand.\n"
              "La rotation est libre : rien ne bloque aux pôles, on peut "
              "retourner complètement la machine.",
        "en": "Mouse: drag = rotate · wheel = zoom · right-click = pan (3D) or "
              "roll (vector) · double-click = reset.\n"
              "Keyboard: ← ↑ → ↓ rotate · Page ↑↓ roll · + − zoom · R reset · "
              "Shift = larger step.\n"
              "Rotation is unconstrained: nothing locks at the poles, the "
              "machine can be turned upside down."},
    "view.title": {"fr": "Affichage", "en": "Display"},
    "view.case": {"fr": "Enveloppe", "en": "Case"},
    "view.case.tip": {
        "fr": "Décoche pour retirer le boîtier et voir tout le mécanisme.",
        "en": "Uncheck to remove the case and see the whole mechanism."},
    "view.plates": {"fr": "Platines", "en": "Plates"},
    "view.labels": {"fr": "Noms des roues", "en": "Gear labels"},
    "view.explode": {"fr": "Éclatement des étages", "en": "Level explosion"},
    "view.explode.tip": {
        "fr": "Écarte les 16 plans d'engrènement pour voir comment ils "
              "s'empilent.",
        "en": "Spreads the 16 meshing planes apart to reveal how they stack."},
    "view.render": {"fr": "Rendu", "en": "Rendering"},
    "view.render.3d": {"fr": "3D (OpenGL, antialiasé)",
                       "en": "3D (OpenGL, antialiased)"},
    "view.render.vector": {"fr": "vectoriel 2D (sans pixels)",
                           "en": "2D vector (pixel-free)"},
    "view.render.tip": {
        "fr": "Le rendu vectoriel dessine les dentures réelles en courbes :\n"
              "molette pour zoomer, glisser pour déplacer, et export SVG ou PDF\n"
              "sans perte. La 3D reste plus parlante pour l'empilement des étages.",
        "en": "Vector mode draws the real tooth outlines as curves: wheel to\n"
              "zoom, drag to pan, and lossless SVG or PDF export. The 3D view\n"
              "shows the stacking of levels better."},
    "view.profile": {"fr": "Profil des dents", "en": "Tooth profile"},
    "view.profile.triangular": {"fr": "triangulaire (antique)",
                                "en": "triangular (ancient)"},
    "view.profile.involute": {"fr": "développante (moderne)",
                              "en": "involute (modern)"},
    "view.profile.tip": {
        "fr": "Les dents de la vraie machine sont des triangles quasi "
              "équilatéraux : le rapport moyen est juste, mais le rapport "
              "instantané oscille. La développante, inconnue des Grecs, est le "
              "seul profil qui garantisse un rapport constant à tout instant.",
        "en": "The real machine's teeth are near-equilateral triangles: the mean "
              "ratio is exact, but the instantaneous ratio wobbles. The involute, "
              "unknown to the Greeks, is the only profile giving a constant ratio "
              "at every instant."},
    "view.labels": {"fr": "Noms des roues", "en": "Gear labels"},
    "view.labels.tip": {
        "fr": "Affiche le nom et le nombre de dents de chaque roue\n"
              "(rendu vectoriel).",
        "en": "Shows each gear's name and tooth count (vector mode)."},
    "view.highlight": {"fr": "Mettre en évidence", "en": "Highlight"},
    "view.highlight.none": {"fr": "(tout afficher)", "en": "(show everything)"},
    "view.spin": {"fr": "Rotation auto", "en": "Auto-rotate"},

    # ------------------------------------------------------------- divers
    "unit.days": {"fr": "jours", "en": "days"},
    "unit.years": {"fr": "ans", "en": "years"},
    "unit.turns": {"fr": "tours", "en": "turns"},
    "unit.deg": {"fr": "°", "en": "°"},
    "label.gears": {"fr": "{n} roues, {t} dents au total",
                    "en": "{n} gears, {t} teeth in total"},
    "label.since": {"fr": "depuis l'époque de calage",
                    "en": "since the calibration epoch"},
    "status.turns": {"fr": "Manivelle : {turns:.3f} tours  ·  {days:.1f} jours  "
                           "·  {years:.2f} ans",
                     "en": "Crank: {turns:.3f} turns  ·  {days:.1f} days  "
                           "·  {years:.2f} years"},
    "msg.saved": {"fr": "Enregistré : {path}", "en": "Saved: {path}"},
    "msg.nogl": {
        "fr": "OpenGL n'est pas disponible sur cette machine : la vue 3D est "
              "remplacée par un schéma 2D animé, qui montre les mêmes rotations.",
        "en": "OpenGL is unavailable on this machine: the 3D view is replaced by "
              "an animated 2D diagram showing the same rotations."},
}

# ------------------------------------------------------- listes ordonnées
ZODIAC = {
    "fr": ["Bélier", "Taureau", "Gémeaux", "Cancer", "Lion", "Vierge",
           "Balance", "Scorpion", "Sagittaire", "Capricorne", "Verseau",
           "Poissons"],
    "en": ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
           "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius",
           "Pisces"],
}

#: mois du calendrier égyptien (365 jours), écrits en grec sur la machine
EGYPTIAN_MONTHS = ["Thoth", "Phaophi", "Athyr", "Choiak", "Tybi", "Mechir",
                   "Phamenoth", "Pharmouthi", "Pachon", "Payni", "Epiphi",
                   "Mesore"]

GAMES_NAMES = {
    "fr": {"isthmia": "Isthmia", "olympia": "Olympia",
           "nemea": "Nemea", "pythia": "Pythia"},
    "en": {"isthmia": "Isthmia", "olympia": "Olympia",
           "nemea": "Nemea", "pythia": "Pythia"},
}

PLANET_NAMES = {
    "fr": {"mercury": "Mercure", "venus": "Vénus", "mars": "Mars",
           "jupiter": "Jupiter", "saturn": "Saturne"},
    "en": {"mercury": "Mercury", "venus": "Venus", "mars": "Mars",
           "jupiter": "Jupiter", "saturn": "Saturn"},
}

PHASE_NAMES = {
    "fr": ["Nouvelle Lune", "Premier croissant", "Premier quartier",
           "Gibbeuse croissante", "Pleine Lune", "Gibbeuse décroissante",
           "Dernier quartier", "Dernier croissant"],
    "en": ["New Moon", "Waxing crescent", "First quarter", "Waxing gibbous",
           "Full Moon", "Waning gibbous", "Last quarter", "Waning crescent"],
}


def tr(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    """Traduit une clé. Renvoie la clé elle-même si elle manque (visible en test)."""
    entry = T.get(key)
    if entry is None:
        return f"<{key}>"
    text = entry.get(lang) or entry.get(DEFAULT_LANG) or f"<{key}>"
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            pass
    return text


def zodiac_sign(longitude_deg: float, lang: str) -> tuple[str, float]:
    """Signe du zodiaque et degré dans le signe, pour une longitude écliptique."""
    lon = longitude_deg % 360.0
    idx = int(lon // 30.0)
    return ZODIAC[lang][idx], lon - 30.0 * idx


def phase_name(elongation_turns: float, lang: str) -> str:
    frac = elongation_turns % 1.0
    idx = int((frac * 8.0 + 0.5)) % 8
    return PHASE_NAMES[lang][idx]


def missing_keys() -> list[str]:
    """Clés dont une des deux langues manque — utilisé par les tests."""
    bad = []
    for key, entry in T.items():
        for lang in LANGUAGES:
            if not entry.get(lang):
                bad.append(f"{key}:{lang}")
    return bad
