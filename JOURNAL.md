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
