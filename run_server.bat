
@echo off
echo === AutoPub Local: Lancement du serveur ===
call venv\Scripts\activate
set PYTHONUTF8=1
python app.py
pause
