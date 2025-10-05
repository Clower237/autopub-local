# tts.py — TTS avec fallback automatique
# - Essaie d'abord edge-tts (voix Neural)
# - En cas d'échec (ex: 403 sur Render), bascule vers gTTS
# - Signature stable: synthesize(text, out_path, voice, speed, pitch=None)

from __future__ import annotations
import asyncio
import re
from typing import Optional

import edge_tts
from gtts import gTTS


def _rate_from_speed(speed: float) -> str:
    """
    Convertit un multiplicateur (ex: 1.1) en rate pour edge-tts (ex: '+10%').
    """
    try:
        s = float(speed or 1.0)
    except Exception:
        s = 1.0
    pct = round((s - 1.0) * 100)
    return f"+{pct}%" if pct >= 0 else f"{pct}%"


def _detect_lang_from_voice(voice: Optional[str]) -> str:
    """
    Déduit la langue gTTS depuis le prefixe de la voix (fr-, en-, es-, …).
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
    """
    gTTS supporte mal les balises/SSML → on nettoie au cas où.
    """
    t = text or ""
    t = re.sub(r"<[^>]+>", " ", t)     # supprime balises
    t = re.sub(r"\s+", " ", t).strip() # espaces propres
    return t or " "


def _edge_tts_to_mp3(text: str, out_path: str, voice: Optional[str], speed: float) -> None:
    """
    Génère un MP3 avec edge-tts (peut lever une Exception, ex: 403/connexion).
    """
    rate = _rate_from_speed(speed)
    communicate = edge_tts.Communicate(
        text,
        voice=voice or "fr-FR-DeniseNeural",
        rate=rate
    )

    async def _run():
        with open(out_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])

    asyncio.run(_run())


def _gtts_to_mp3(text: str, out_path: str, voice: Optional[str]) -> None:
    """
    Repli gTTS : rapide et fiable sur Render.
    """
    lang = _detect_lang_from_voice(voice)
    clean = _sanitize_text(text)
    gTTS(text=clean, lang=lang, slow=False).save(out_path)


def synthesize(
    text: str,
    out_path: str,
    voice: str = "fr-FR-DeniseNeural",
    speed: float = 1.1,
    pitch: Optional[str] = None,
) -> None:
    """
    API principale utilisée par worker.py :
    - Tente edge-tts
    - Si échec, bascule automatiquement vers gTTS
    """
    try:
        _edge_tts_to_mp3(text, out_path, voice, speed)
        return
    except Exception as e:
        # Optionnel: logger l'erreur si tu veux diagnostiquer:
        # print(f"[tts] edge-tts failed, fallback to gTTS: {e}")
        _gtts_to_mp3(text, out_path, voice)
