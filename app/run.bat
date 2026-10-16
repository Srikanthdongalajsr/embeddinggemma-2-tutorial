@echo off
rem Search page for the EmbeddingGemma 2 video. Opens http://127.0.0.1:7860 once the model has loaded.
rem DEVICE=cuda keeps the search model on the GPU (less RAM, ~60 ms searches).
rem For the "no GPU needed" shot, change it to:  set DEVICE=cpu
set DEVICE=cuda
cd /d "%~dp0.."
rem Uses "python" from PATH. To use another one:  set PYTHON=C:\path\to\python.exe
if not defined PYTHON set PYTHON=python
"%PYTHON%" -u app\server.py
