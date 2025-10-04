# tts.py — edge-tts via CLI, compatible Windows
import os, sys, subprocess
from typing import Optional

def _rate_from_speed(speed: float) -> str:
    try: sp = float(speed)
    except Exception: sp = 1.0
    pct = int(round((sp - 1.0) * 100))
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct}%"

def synthesize(
    text: str,
    out_path: str,
    voice: str = "fr-FR-DeniseNeural",
    speed: float = 1.0,
    pitch: Optional[str] = None,  # accepté mais ignoré
    **_ignored
):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    rate = _rate_from_speed(speed)
    cmd = [
        sys.executable, "-m", "edge_tts",
        "--voice", voice,
        "--text", text,
        "--rate", rate,
        "--write-media", out_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        err = r.stderr.strip() or r.stdout.strip() or "edge-tts failed"
        raise RuntimeError(err)
