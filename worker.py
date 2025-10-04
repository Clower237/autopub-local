# worker.py — traitement + upload YouTube par utilisateur + compat Render
import threading, time, os, smtplib
from email.mime.text import MIMEText
from datetime import datetime
from pathlib import Path
import pytz

from sqlalchemy.orm import Session

from database import SessionLocal
from models import Job, User
from tts import synthesize
from video import render_video

from youtube_uploader import upload_to_youtube

# Dossiers (persistants si APP_DATA_DIR défini)
DATA_DIR = Path(os.getenv("APP_DATA_DIR", ".")).resolve()
STORAGE_DIR = (DATA_DIR / "storage").resolve()
(STORAGE_DIR / "audio").mkdir(parents=True, exist_ok=True)
(STORAGE_DIR / "video").mkdir(parents=True, exist_ok=True)

TZ = pytz.timezone(os.getenv("TIMEZONE", "UTC"))
_worker_started = False

# -----------------------
# Email (facultatif)
# -----------------------
def send_email(subject: str, body: str, to_email: str):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    from_addr = os.getenv("SMTP_FROM", user or "")
    if not host or not user or not password or not to_email:
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    try:
        import smtplib
        smtp = smtplib.SMTP(host, port)
        smtp.starttls()
        smtp.login(user, password)
        smtp.sendmail(from_addr, [to_email], msg.as_string())
        smtp.quit()
    except Exception:
        pass

# -----------------------
# Upload YouTube (immédiat / programmé)
# -----------------------
def handle_upload_for_job(db: Session, job: Job):
    try:
        job.status = "UPLOADING"
        job.progress_msg = "Envoi vers YouTube…"
        db.commit()

        tags_list = []
        if job.tags:
            tags_list = [t.strip() for t in job.tags.split(",") if t.strip()]

        publish_dt_utc = None
        if job.publish_iso and job.publish_iso.strip():
            publish_dt_utc = datetime.fromisoformat(job.publish_iso.replace("Z", "+00:00"))

        video_id = upload_to_youtube(
            user_id=job.user_id,
            video_path=job.video_path,
            title=job.title,
            description=job.description or "",
            tags=tags_list,
            publish_time=publish_dt_utc,
            thumbnail_path=job.thumbnail_path,
        )
        job.youtube_video_id = video_id

        if publish_dt_utc is None:
            job.status = "PUBLISHED"
            job.progress_msg = "Vidéo publiée immédiatement sur YouTube."
        else:
            job.status = "SCHEDULED"
            job.progress_msg = f"Uploadé en privé. Publication programmée pour {publish_dt_utc} UTC."
        db.commit()

    except Exception as e:
        job.status = "FAILED"
        job.progress_msg = f"Upload échoué : {e}"
        db.commit()

# -----------------------
# Traitement d’un job
# -----------------------
def _process_job(db: Session, job: Job):
    try:
        job.status = "RENDERING"
        job.progress_msg = "Synthèse audio + rendu vidéo…"
        db.commit()

        # 1) TTS
        audio_path = str(STORAGE_DIR / "audio" / f"{job.id}.mp3")
        synthesize(
            job.script_text,
            audio_path,
            voice=job.voice,
            speed=job.speed,
            pitch=None
        )
        job.audio_path = audio_path
        db.commit()

        # 2) Rendu vidéo
        video_path = str(STORAGE_DIR / "video" / f"{job.id}.mp4")
        render_video(job.thumbnail_path, audio_path, video_path)
        job.video_path = video_path

        # 3) Prêt localement
        job.status = "DONE"
        job.progress_msg = "Vidéo prête localement. Passage à l’upload YouTube…"
        db.commit()

        # 4) Upload
        handle_upload_for_job(db, job)

        # 5) Email (optionnel)
        user = db.query(User).get(job.user_id)
        if user:
            vid = job.youtube_video_id or "—"
            send_email(
                subject="AutoPub — Vidéo envoyée sur YouTube",
                body=f"Titre: {job.title}\nStatut: {job.status}\nMessage: {job.progress_msg}\nYouTube: https://youtube.com/watch?v={vid}",
                to_email=user.email
            )

    except Exception as e:
        job.status = "FAILED"
        job.progress_msg = str(e)
        db.commit()

# -----------------------
# Boucle
# -----------------------
def _loop():
    while True:
        with SessionLocal() as db:
            job = (
                db.query(Job)
                  .filter(Job.status == "READY")
                  .order_by(Job.created_at.asc())
                  .first()
            )
            if not job:
                time.sleep(1.0)
                continue
            _process_job(db, job)

def ensure_worker_running():
    global _worker_started
    if _worker_started:
        return
    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    _worker_started = True

def poke_worker():
    return
