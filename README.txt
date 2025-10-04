
AutoPub Local (100% gratuit, Windows)
=====================================

Ce projet tourne sur **ton PC Windows** sans coût, avec base SQLite.
- Crée des vidéos (miniature 1080p fixe + voix off **x1.3**), longues (jusqu'à ~2h).
- Programme la publication en **uploadant en avance** (l'auto-upload YouTube s'activera quand tu mettras `client_secret.json`).
- Envoi d'email optionnel quand la vidéo est prête.

Étapes (clic par clic)
----------------------
1) Installe **Python 3.10+** (https://www.python.org/downloads/) — coche "Add Python to PATH".
2) Installe **FFmpeg** (gratuit) :
   - Option A (simple) : via winget (Windows 10/11) → Ouvre PowerShell et tape :
       winget install --id=Gyan.FFmpeg -e
     Puis ferme/réouvre la fenêtre.
   - Option B (manuel) : télécharge un ZIP "ffmpeg" (build statique), dézippe et ajoute le dossier `bin` à la variable PATH.
3) Télécharge ce dossier (ZIP), dézippe-le (par ex. sur le Bureau).
4) Double-clique **run_first_time.bat** (installe les dépendances) puis **run_server.bat**.
5) Ouvre ton navigateur sur **http://localhost:8000** (Swagger: **http://localhost:8000/docs**).

Créer ton compte et ta 1ère vidéo
---------------------------------
- Dans /docs :
  1) POST /auth/register → email + mot de passe (tu récupères un access_token).
  2) Clique le bouton "Authorize" en haut → colle `Bearer <access_token>`.
  3) POST /jobs → remplis les champs (titre, description, tags, miniature, texte, voix et vitesse (1.3 par défaut)).
  4) GET /jobs → pour voir l’avancement. Le MP3 est dans `storage/audio/`, la vidéo MP4 dans `storage/video/`.

Activer l’upload YouTube (quand tu veux)
----------------------------------------
- Place **client_secret.json** (Google OAuth) à la racine du dossier.
- L’upload auto est prévu côté code; il sera activé dans une prochaine étape guidée.

Email de notification (optionnel)
---------------------------------
- Édite `.env` et renseigne SMTP_* (ex. Gmail + App Password).

Notes
-----
- 100% gratuit tant que tu exécutes sur ton PC. La publication programmée ne nécessite pas que le PC reste allumé (car YouTube publie à l'heure choisie si tu as uploadé en avance).
- Si tu veux accéder "en ligne" depuis l'extérieur sans payer, tu peux créer un tunnel temporaire gratuit (ex: Cloudflare Quick Tunnel), mais il faut que ton PC soit allumé pendant l'utilisation.
