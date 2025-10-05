# tts.py (extrait propre)
import asyncio, re
import edge_tts
from gtts import gTTS

def _rate_from_speed(speed: float) -> str:
    s = float(speed or 1.0)
    pct = round((s - 1.0) * 100)
    if pct >= 0:
        return f"+{pct}%"
    return f"{pct}%"

def _detect_lang_from_voice(voice: str | None) -> str:
    v = (voice or "").lower()
    if v.startswith("fr-"): return "fr"
    if v.startswith("en-"): return "en"
    if v.startswith("es-"): return "es"
    if v.startswith("pt-"): return "pt"
    if v.startswith("de-"): return "de"
    if v.startswith("it-"): return "it"
    return "en"

def _sanitize_text(text: str) -> str:
    t = text or ""
    t = re.sub(r"<[^>]+>", " ", t)     # enlève balises éventuelles
    t = re.sub(r"\s+", " ", t).strip()
    return t or " "

def _edge_tts_to_mp3(text: str, out_path: str, voice: str, speed: float):
    rate = _rate_from_speed(speed)
    communicate = edge_tts.Communicate(text, voice=voice or "fr-FR-DeniseNeural", rate=rate)
    async def _run():
        with open(out_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
    asyncio.run(_run())

def _gtts_to_mp3(text: str, out_path: str, voice: str):
    lang = _detect_lang_from_voice(voice)
    clean = _sanitize_text(text)
    gTTS(text=clean, lang=lang, slow=False).save(out_path)

def synthesize(text: str, out_path: str, voice: str = "fr-FR-DeniseNeural", speed: float = 1.1, pitch: str | None = None):
    """
    Tente edge-tts ; si ça échoue (ex. 403 sur Render), bascule vers gTTS.
    """
    try:
        _edge_tts_to_mp3(text, out_path, voice, speed)
        return
    except Exception as e:
        # log optionnel: print(f"edge-tts failed: {e}")
        _gtts_to_mp3(text, out_path, voice)
