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
