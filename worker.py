import os, time, threading
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Job
from tts import synthesize
from video import render_video
from youtube_uploader import upload_video
from drive_uploader import upload_for_user

POLL_SECONDS = int(os.getenv("WORKER_POLL_SECONDS", "3"))
_worker_thread = None
_worker_stop = False

def _update(db: Session, job: Job, status: str, msg: str):
    job.status = status
    job.progress_msg = msg
    db.commit()

def _process_one(db: Session, job: Job):
    _update(db, job, "TTS", "Synthèse vocale…")
    audio_path = os.path.join("storage", f"job_{job.id}.mp3")
    synthesize(job.script_text, audio_path, voice=job.voice or "fr-FR-DeniseNeural", speed=job.speed or 1.1)
    job.audio_path = audio_path; db.commit()

    _update(db, job, "RENDER", "Rendu vidéo…")
    video_path = os.path.join("storage", f"job_{job.id}.mp4")
    render_video(job.thumbnail_path, audio_path, out_path=video_path)
    job.video_path = video_path; db.commit()

    _update(db, job, "UPLOADING", "Envoi vers Google Drive…")
    link = upload_for_user(job.user_id, video_path)
    if link:
        _update(db, job, "UPLOADING", f"Envoi Drive OK : {link}")
    else:
        _update(db, job, "UPLOADING", "Drive non connecté — on continue.")

    _update(db, job, "UPLOADING", "Envoi vers YouTube…")
    vid = upload_video(job.user_id, video_path, job.title, job.description or "", job.tags or "", job.publish_iso, job.thumbnail_path)
    job.youtube_video_id = vid or None
    _update(db, job, "DONE" if vid else "FAILED", "Tout bon ✅" if vid else "Upload YouTube échoué.")

def _loop():
    global _worker_stop
    db = SessionLocal()
    try:
        while not _worker_stop:
            job = db.query(Job).filter(Job.status.in_(["READY","RETRY"])).order_by(Job.id.asc()).first()
            if not job:
                time.sleep(POLL_SECONDS); continue
            try:
                _process_one(db, job)
            except Exception as e:
                _update(db, job, "FAILED", f"Erreur: {e}")
    finally:
        db.close()

def ensure_worker_running():
    global _worker_thread, _worker_stop
    if _worker_thread and _worker_thread.is_alive(): return
    _worker_stop = False
    _worker_thread = threading.Thread(target=_loop, daemon=True); _worker_thread.start()

def poke_worker():
    return "ok"
