@echo off
rem Search page on the PLANT library (manufacturing demo). Opens http://127.0.0.1:7860 once the model has loaded.
rem Record note (top right) records a voice note in the browser and indexes it like any other file.
set DEVICE=cuda
set WORKSPACE=plant
cd /d "%~dp0.."
rem Uses "python" from PATH. To use another one:  set PYTHON=C:\path\to\python.exe
if not defined PYTHON set PYTHON=python
"%PYTHON%" -u app\server.py
