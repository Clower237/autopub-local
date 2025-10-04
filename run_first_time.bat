
@echo off
echo === AutoPub Local: Installation initiale ===
python -m venv venv
call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
echo Installation terminee.
pause
