@echo off
rem =====================================================================
rem  Anticythere3D - lancement sous Windows depuis les sources
rem  Cree un environnement isole la premiere fois, installe ce qu'il faut,
rem  puis demarre le simulateur. Double-cliquer suffit.
rem
rem  NOTE : l'environnement virtuel est cree en LOCAL (%LOCALAPPDATA%) et
rem  jamais dans le dossier du projet. Quand les sources vivent sur un
rem  partage reseau (W: = NAS), Windows refuse d'executer un python.exe
rem  situe sur le partage -> venv local obligatoire.
rem =====================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Anticythere3D

set "VENV=%LOCALAPPDATA%\Anticythere3D\venv"
set "VPY=%VENV%\Scripts\python.exe"

echo.
echo   Machine d'Anticythere - simulateur 3D
echo   -------------------------------------
echo.

rem --- 1. trouver Python -------------------------------------------------
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo   [X] Python est introuvable.
    echo.
    echo   Installe Python 3.10 ou plus recent depuis https://www.python.org/downloads/
    echo   en cochant "Add python.exe to PATH", puis relance ce fichier.
    echo.
    pause
    exit /b 1
)

rem --- 2. verifier la version --------------------------------------------
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo   [X] Python 3.10 ou plus recent est necessaire.
    %PY% --version
    pause
    exit /b 1
)

rem --- 3. environnement isole (local, hors du projet) ---------------------
if not exist "%VPY%" (
    echo   Premiere utilisation : creation de l'environnement...
    echo   ^(dans %VENV%^)
    %PY% -m venv "%VENV%"
    if errorlevel 1 (
        echo   [X] Echec de la creation de l'environnement.
        pause
        exit /b 1
    )
    echo   Installation des dependances ^(PyQt6, numpy, pyqtgraph, OpenGL^)...
    "%VPY%" -m pip install --upgrade pip --quiet
    "%VPY%" -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo   [X] Echec de l'installation des dependances.
        pause
        exit /b 1
    )
    echo   Termine.
    echo.
)

rem --- 4. lancement ------------------------------------------------------
echo   Demarrage...
"%VPY%" run.py %*
set "CODE=%ERRORLEVEL%"

if not "%CODE%"=="0" (
    echo.
    echo   Le programme s'est arrete avec le code %CODE%.
    if exist "anticythere3d-erreur.log" (
        echo   Detail dans : anticythere3d-erreur.log
        echo.
        powershell -NoProfile -Command "Get-Content 'anticythere3d-erreur.log' -Tail 20"
    )
    echo.
    pause
)
endlocal
exit /b %CODE%
