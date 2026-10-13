@echo off
REM ====================================================================
REM  Isle Wars launcher. Double-click this file to play.
REM  First run sets up a small Python environment (needs internet once).
REM ====================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "GAMEPY="
REM reuse an existing environment if one is present
if exist "..\PYTHONDLVEXAMPLE\.venv\Scripts\python.exe" set "GAMEPY=..\PYTHONDLVEXAMPLE\.venv\Scripts\python.exe"
if not defined GAMEPY if exist ".venv\Scripts\python.exe" set "GAMEPY=.venv\Scripts\python.exe"

if not defined GAMEPY (
    echo ============================================
    echo   Isle Wars - first-time setup
    echo ============================================
    set "PYCMD="
    where py >nul 2>nul && set "PYCMD=py"
    if not defined PYCMD (
        where python >nul 2>nul && set "PYCMD=python"
    )
    if not defined PYCMD (
        echo.
        echo  Python 3 was not found on this PC.
        echo  Install it from https://www.python.org/downloads/
        echo  and TICK "Add Python to PATH" during setup, then run this again.
        echo.
        pause
        exit /b 1
    )
    echo  Creating the game environment ^(one time, ~1 minute^)...
    !PYCMD! -m venv .venv
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo  Setup failed - check your internet connection and try again.
        pause
        exit /b 1
    )
    set "GAMEPY=.venv\Scripts\python.exe"
)

REM sanity-check dependencies so problems surface with a message (not silently)
"!GAMEPY!" -c "import pygame, embasp" >nul 2>nul
if errorlevel 1 (
    echo.
    echo  The game environment is missing dependencies. Re-running setup...
    "!GAMEPY!" -m pip install -r requirements.txt
    if errorlevel 1 ( echo  Install failed - check your internet. & pause & exit /b 1 )
)

echo  Launching Isle Wars...
REM launch windowed (pythonw = no leftover console window)
set "GAMEPYW=!GAMEPY:python.exe=pythonw.exe!"
start "Isle Wars" "!GAMEPYW!" main.py
