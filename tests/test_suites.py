# -*- coding: utf-8 -*-
"""Les deux suites historiques, lancées par pytest (CI : kit.json « tests_ci »).

test_mechanism.py et test_gui.py sont des scripts qui comptent leurs échecs
et rendent un code de sortie ; pytest seul les verrait « passer » quoi qu'il
arrive (leurs fonctions n'utilisent pas assert). On les lance donc comme des
programmes et on juge le code de sortie.

    xvfb-run -a python -m pytest -q tests/test_suites.py
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent


def _lancer(script, env):
    r = subprocess.run([sys.executable, str(RACINE / 'tests' / script)], cwd=RACINE,
                       env=env, capture_output=True, text=True, timeout=1200)
    sortie = r.stdout + r.stderr
    assert r.returncode == 0, sortie[-6000:]
    return sortie


def test_mecanisme_sans_ecran():
    sortie = _lancer('test_mechanism.py', {**os.environ, 'QT_QPA_PLATFORM': 'offscreen'})
    assert 'TOUS LES TESTS PASSENT' in sortie


@pytest.mark.skipif(sys.platform.startswith('linux') and not os.environ.get('DISPLAY'),
                    reason="vue 3D : il faut un vrai serveur X (xvfb-run)")
def test_interface_sous_xvfb():
    # pas d'« offscreen » : il ne fournit aucun contexte OpenGL
    env = {k: v for k, v in os.environ.items() if k != 'QT_QPA_PLATFORM'}
    sortie = _lancer('test_gui.py', env)
    assert "TOUS LES TESTS D'INTERFACE PASSENT" in sortie
