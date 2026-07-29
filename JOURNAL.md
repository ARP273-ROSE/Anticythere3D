# Anticythere3D — journal

## 2026-07-29 — création du simulateur

Demande de Kevin : programme complet, GUI, vue 3D, enveloppe amovible,
mécanisme qui fonctionne, explications, report des cadrans, bilingue,
multiplateforme, README + aide + tooltips bilingues, tout vérifié sous SageMath.

### Livré
- Moteur cinématique en fractions exactes (`kinematics.py`) — rapports identiques
  à ceux calculés sous SageMath.
- Astronomie de référence (`astro.py`), **validée contre skyfield** :
  erreur < 0,015° sur le Soleil et < 0,04° sur la Lune entre 1900 et 2050.
- Implantation des 15 arbres par optimisation sous contraintes (SageMath+scipy) :
  17 entraxes exacts au micron, aucune collision, 277 × 257 mm.
- Géométrie 3D paramétrique : dents triangulaires (antiques) ou développante,
  roues à bras pour b1/e3/e4, spirales métonique et Saros.
- Interface PyQt6 + pyqtgraph/OpenGL, repli 2D automatique sans OpenGL.
- 115 clés i18n × 2 langues, aucune manquante ; tooltips partout.
- 10 séries de tests headless : **toutes passent**.

### Environnement de test
Conteneur Docker `anticythere-dev` (python:3.12-slim + PyQt6, pyqtgraph,
PyOpenGL, numpy, skyfield, xvfb). Tests et captures :
`docker exec -w /workspace/GitHub/Anticythere3D anticythere-dev \
  xvfb-run -a python tests/test_mechanism.py`

### Limites assumées (à améliorer si Kevin le souhaite)
- Les cadrans 3D sont schématiques : pas de graduations gravées, pas de
  glyphes d'éclipse dessinés (la prédiction, elle, est calculée).
- Les planètes sont calculées et affichées en valeurs, mais pas modélisées
  en 3D : le palier 2 retenu pour la fabrication ne les comporte pas.
- Les petites roues sont visuellement noyées sous b1 et e3 — c'est la réalité
  de la machine ; utiliser « Mettre en évidence » et « Éclatement ».
- Testé sous Linux (xvfb). Windows et macOS non testés faute de machine.

## 2026-07-29 (suite) — fond clair et rendu vectoriel

Demande de Kevin : « ça peut pas être sur fond clair les engrenages et en
vectoriel pour éviter pixels ? »

- **Palette claire** : fond parchemin `#F5F0E6`, couleurs des sous-ensembles
  reprises en teintes soutenues (bronze, argent bleuté, brique, bleu, vert,
  prune, bleu-violet) pour rester lisibles sur clair. La 3D et le vectoriel
  partagent la même palette (`layout.COLORS`, `layout.BACKGROUND`).
- **Antialiasing 8×** (MSAA) sur la vue 3D : `QSurfaceFormat.setSamples(8)`
  dans `run.py`, **avant** la création de `QApplication` — sinon sans effet.
  Réglable par `--samples`.
- **Nouveau module `view2d.py`** : rendu vectoriel QPainter avec les dentures
  réelles, molette = zoom, glisser = déplacer, faces avant/arrière/toutes,
  et **export SVG et PDF A3**. Vérifié : le SVG ne contient aucune image
  bitmap (103 polygones + chemins), le PDF est produit par Qt en A3.
- Ce module remplace aussi l'ancien repli 2D rudimentaire quand OpenGL manque.
- **Bug corrigé** : les roues à bras (b1, e3, e4) étaient dessinées en
  remplissant leur évidement avec la couleur de fond — ce disque opaque
  effaçait toutes les roues situées dessous. Remplacé par une différence de
  `QPainterPath` (jante ajourée réelle), puis union des bras et du moyeu.
- Case à cocher « Noms des roues » ajoutée (le drapeau existait sans UI).

## 2026-07-29 (suite) — navigation libre, machine fermée, auto-installation

Demandes de Kevin : « on doit pouvoir zoomer dézoomer et tourner le truc dans
tous les sens », « la machine fermée complète avec ses cadrans et manettes
fidèle et un bouton pour enlever l'enveloppe », « le programme doit être
capable d'installer tout seul tout ce dont il a besoin y compris la 3D ».

### Navigation
- Caméra 3D en **quaternion** (`GLViewWidget(rotationMethod="quaternion")`) :
  la rotation n'est plus bornée à ±90° d'élévation, on peut passer au-dessus
  du pôle et retourner complètement la machine. En mode 'euler' (défaut de
  pyqtgraph) c'était impossible.
- Méthodes communes aux deux vues : `zoom()`, `rotate()`, `roll()`,
  `reset_view()` — donc les mêmes boutons pilotent la 3D et le vectoriel.
- Groupe **Navigation** dans l'UI : zoom ±, croix de rotation, roulis,
  recentrer, rotation automatique.
- Raccourcis : flèches, Page ↑↓, +/−, R, Espace, Maj pour un pas plus grand.
- Vectoriel : molette = zoom, glisser = déplacer, clic droit = pivoter,
  Ctrl+molette = pivoter, double-clic = recentrer.

### Machine fermée
- Coffret de bois (4 flancs + fond), façade de bronze pleine, cadran gravé
  avec l'anneau du zodiaque (72 traits, 12 longs) et l'anneau calendaire de
  365 jours, spirales métonique et Saros gravées au dos, **manivelle** coudée
  sortant du flanc dans l'axe de a1, bille de phase lunaire.
- Boîtier recentré sur `CASE_CX = 24` : l'emprise réelle va de x = −112 (b1)
  à x = +160 (manivelle), le centre n'est donc pas l'arbre b.
- `LEVEL_PITCH` ramené de 4,5 à 3,4 mm : la machine était trop épaisse pour
  ressembler à l'original.
- **Bug corrigé** : les aiguilles flottaient hors du coffret — leur maillage
  était créé à une hauteur z, *puis* re-translaté à cette même hauteur par
  `set_pointers`, donc décalé deux fois. Maillages désormais créés à plat.

### Auto-installation
- `anticythere/bootstrap.py`, sans aucune dépendance : détecte les modules
  manquants, les installe avec pip (`--user` hors venv), rend visible le
  site-packages utilisateur puis **relance le programme une fois** si les
  paquets fraîchement installés ne sont pas encore importables.
- Vérifié depuis un conteneur `python:3.12-slim` **vierge** : les quatre
  paquets s'installent et `has_3d` passe à True dans la foulée.
- `qt_can_start()` : teste dans un **sous-processus isolé** que Qt démarre
  vraiment. Sous Linux, l'absence des bibliothèques xcb ne lève pas
  d'exception — elle tue le processus. Le test évite le crash et affiche la
  commande apt/dnf/pacman exacte. Un premier essai en `QT_QPA_PLATFORM=offscreen`
  passait à côté du problème : offscreen n'utilise pas xcb.

### Documentation et publication
- `docs/Manuel.tex` → `docs/Manuel.pdf` : 9 pages, bilingue FR/EN, illustré
  des captures réelles. Temporaires LaTeX supprimés.
- README refondu (auto-installation, navigation, rendu vectoriel).
- Dépôt publié : **https://github.com/ARP273-ROSE/Anticythere3D** (privé).

## 2026-07-29 (nuit) — STL, build automatique, cadrans gravés

### Export STL
Un fichier par roue, jeu d'impression et alésage appliqués, nomenclature CSV.
Les 33 maillages sont étanches. **Trois bugs de géométrie réels**, tous
attrapés par les tests :
1. le jeu d'impression *ajoutait* de la matière (orientation du contour non
   mesurée) ;
2. le profil en développante faisait *grossir* la dent vers le sommet, et les
   grandes roues avaient un contour auto-intersecté — le flanc partait du
   cercle de base au lieu du creux, et le recalage angulaire ne se faisait pas
   sur le cercle primitif ;
3. l'offset par bissectrice ne reculait la pointe de dent que de
   `c/2·cos(θ/2)` → compensation d'onglet ajoutée (recul mesuré : 0,152 mm
   pour 0,150 demandé).

### Build et mise à jour
`.github/workflows/build.yml` : tests, puis PyInstaller sur Windows et Linux,
puis publication de la Release sur tag `v*`. **Release v1.0.0 en ligne**,
`Anticythere3D-windows.exe` (54 Mo) et `Anticythere3D-linux` (91 Mo).
`updater.py` interroge l'API, choisit le binaire de la plateforme, télécharge
et remplace (script différé sous Windows, où un exe en cours ne peut pas
s'écraser lui-même).

### Cadrans gravés
`dialface.py` — un seul code de dessin sert de texture 3D **et** de rendu
vectoriel. Face avant : douze signes en grec, mois égyptiens, lettres-index du
parapegma, 360 divisions. Face arrière : spirale métonique (5 tours, 235
cases), spirale du Saros (4 tours, 223 cases), cadrans des Jeux, de Callippe
et de l'exeligmos. Palette éclaircie.
Piège résolu : pour la face arrière, ni rotation ni échelle négative ne
corrigent le miroir — un plan retourné reste retourné. Il faut miroiter
l'image elle-même.

## 2026-07-29 (audit complet)

Demande de Kevin : audit complet (maths sous SageMath, perf, sécu,
anti-freeze, multiplateforme, bilinguisme), miroir du dos, et vérification
du système de mise à jour.

### Miroir du dos — RÉSOLU
Cause : GLImageItem transpose l'image en interne avant l'envoi à OpenGL
(vu dans son code source). Remplacé par `texquad.TexturedQuadItem`, un quad
à coordonnées UV explicites. Piège de pyqtgraph ≥ 0.13 : le pipeline fixe ne
reçoit plus les matrices, il faut pousser soi-même la MVP (sinon le quad
remplit l'écran). Formule de placement revalidée sous Sage pour le nouveau
pipeline : Y = cy + span·(1/2 − fy).

### Audit mathématique (docs/anticythere_audit.sage) — 9 sections
Rapports, chaînes d'animation, tenon-fente (formule du code = géométrie
exacte à 2·10⁻¹⁷ près), calage, limites d'éclipses, zodiaque/phases, jour
julien (cas de référence Meeus), cadrans, offset d'onglet STL.
**1 vrai bug trouvé** : à exactement 1 Saros, (1/3 % 1)·3 = 0,999… en
flottant → le cadran de l'exeligmos affichait « +0 h » au lieu de « +8 h »,
pile à la frontière la plus utilisée. Corrigé (epsilon d'1,7 s), testé.

### Performance / anti-freeze
refresh() : 0,5 ms par tick (budget 33 ms) — rien à faire.
Export STL (704 ms) déplacé dans un fil séparé. next_eclipses (46 ms)
conservé sous curseur d'attente.

### Sécurité
TLS vérifié (create_default_context), aucun eval/exec/shell=True.
Durcissement : le téléchargement de mise à jour refuse toute URL hors des
releases du dépôt et du CDN GitHub (`is_trusted_url`).

### Multiplateforme / bilinguisme
Chemins : trois `rsplit("/")` cassants sous Windows remplacés par os.path.
**Bug trouvé** : les cadrans gravés ne suivaient pas la bascule de langue
(dial_lang jamais mis à jour). Corrigé + régénération des textures.
6 widgets sans tooltip corrigés. Nouveau `tests/test_gui.py` (16 contrôles) :
tooltips exhaustifs dans les deux langues, bascule complète, mise en page,
navigation éclipse, exports SVG/PDF sans bitmap.

### Mise à jour vérifiée de bout en bout
Détection (0.9.0 → 1.0.0), refus d'URL étrangère, téléchargement réel du
binaire (91 Mo, progression), remplacement avec sauvegarde .old, relance.

---

## 2026-07-29 — Cadran arrière : encombrement et inscriptions

Deux défauts signalés en usage — « des cadrans grands et petits qui se
superposent, et sur les cadrans à spirale il n'y a aucune indication ».
Les deux étaient réels, et l'audit géométrique
(`anticythere_cadrans2.sage`) en a trouvé deux autres.

### 1. Cadrans qui se chevauchent — mesuré, pas estimé

| Paire | distance | somme des rayons | verdict |
|---|---|---|---|
| callippique / exeligmos | 22,08 mm | 25,00 mm | **chevauchement 2,92 mm** |
| Saros / Jeux | 58,58 mm | 59,25 mm | **chevauchement 0,67 mm** |

Le callippique et l'exeligmos sont portés par les arbres `o` et `i`, distants
de 22,08 mm seulement : leurs **centres sont gelés**, seul le rayon est
libre. Ramenés à 9,9 et 9,2 mm (3 mm de jeu). Le cadran des Jeux, lui, n'a
pas d'arbre : il est libre, et rejoint la zone réellement vide de la plaque,
côté grande roue (`GAMES_CENTER = (-70, 0)`).

Le titre du Saros a suivi : écrit au-dessus de sa spirale, il tombait dans la
métonique — il ne reste que 7,75 mm entre les deux. Il passe dessous.

### 2. La texture ne couvrait pas la plaque

`BACK_DIAL_SPAN` valait 300 mm pour un boîtier de **338 × 272,5 mm** : la
plaque était rognée de 19 mm à gauche et à droite. La constante se calcule
maintenant à partir du boîtier.

### 3. Le cadran arrière était en miroir dans la vue vectorielle

Trouvé en vérifiant le rendu 2D : les spirales partaient à 139 mm de leurs
aiguilles. `paint_back_dial` inverse les x — correct pour la texture 3D,
qu'on regarde par derrière, faux pour la vue vectorielle qui ne retourne pas
la scène. Le miroir devient un paramètre explicite (`mirrored`), et la vue 2D
passe `False`. La 3D est inchangée.

### 4. Les spirales n'avaient aucune inscription

Elles n'avaient que leurs traits de séparation. Elles portent maintenant :

* **Métonique** — le numéro d'année en chiffres grecs (Α…ΙΘ) en gras au début
  de chacune des 19 années, trait renforcé, et les **mois corinthiens**
  abrégés sur le tour extérieur, seul endroit où ils tiennent (une case fait
  6,7 mm). Les 7 années embolismiques sortent du critère (12k) mod 19 < 7, et
  la somme retombe sur 235 mois pile.
* **Saros** — les glyphes **Η** (Ἥλιος, Soleil) et **Σ** (Σελήνη, Lune) dans
  les cases d'éclipse. ⚠️ **Reconstitué, pas copié** : le motif est *calculé*
  par le module `astro` — syzygie proche d'un nœud, le critère même que la
  machine mécanise — sur les 223 mois d'un Saros. 48 cases solaires, 32
  lunaires ; un peu plus que les glyphes gravés, les limites retenues
  incluant des éclipses rasantes que le graveur n'a pas notées.

Deux pièges de rendu au passage : la taille de police doit venir de la
**largeur d'arc réelle** de la case (r·dθ), pas de la largeur du couloir —
sinon le texte déborde sur les cases voisines ; et la ligne gravée passe au
**milieu** du couloir, donc écrire au rayon exact de la spirale, c'est écrire
sur le trait.

`tests/test_gui.py` gagne une section [G6] qui verrouille les quatre points.
