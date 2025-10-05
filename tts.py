# tts.py — edge-tts avec repli automatique gTTS si 403/erreur réseau
import asyncio
import re

# 1) TTS Microsoft (edge-tts)
import edge_tts

# 2) Repli Google Translate TTS
from gtts import gTTS

def _rate_from_speed(speed: float) -> str:
    """
    Convertit un multiplicateur (ex: 1.3) en rate edge-tts (ex: +30%).
    """
    try:
        speed = float(speed or 1.0)
    except Exception:
        speed = 1.0
    delta = int(round((speed - 1.0) * 100))
    if   delta >  90: delta =  90
    if   delta < -90: delta = -90
    return (f"{'+' if delta >=0 else ''}{delta}%")

def _detect_lang_from_voice(voice: str) -> str:
    """
    Déduit la langue pour gTTS d'après la voix choisie.
    """
    v = (voice or "").lower()
    if v.startswith("fr-"): return "fr"
    if v.startswith("en-"): return "en"
    if v.startswith("es-"): return "es"
    if v.startswith("pt-"): return "pt"
    if v.startswith("de-"): return "de"
    if v.startswith("it-"): return "it"
    # fallback
    return "en"

def _sanitize_text(text: str) -> str:
    # gTTS supporte mal certains SSML ou balises — on nettoie au cas où
    t = text or ""
    # supprime balises SSML basiques
    t = re.sub(r"<[^>]+>", " ", t)
    # espaces propres
    t = re.sub(r"\s+", " ", t).strip()
    return t or " "

def _edge_tts_to_mp3(text: str, out_path: str, voice: str, speed: float):
    """
    Génère un MP3 avec edge-tts (peut lever Exception si 403).
    """
    rate = _rate_from_speed(speed)
    communicate = edge_tts.Communicate(text, voice=voice or "fr-FR-DeniseNeural", rate=rate)
    async def _run():
        with open(out_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
    asyncio.run(_run())

def _gtts_to_mp3(text: str, out_path: str, voice: str):
    """
    Repli gTTS : MP3 rapide, qualité correcte.
    """
    lang = _detect_lang_from_voice(voice)
    clean = _sanitize_text(text)
    gTTS(text=clean, lang=lang, slow=False).save(out_path)

def synthesize(text: str, out_path: str, voice: str = "fr-FR-DeniseNeural", speed: float = 1.1, pitch: str | None = None):
    """
    Tente edge-tts ; en cas d’échec (ex: 403 sur Render), bascule vers gTTS automatiquement.
    """
    try:
        _edge_tts_to_mp3(text, out_path, voice, speed)
        return
    except Exception as e:
        # Repli automatique — utile sur Render quand edge-tts retourne 403
        _gtts_to_mp3(text, out_path, voice)
