
from moviepy.editor import ImageClip, AudioFileClip
from PIL import Image
import os

TARGET_W, TARGET_H = 1920, 1080

def ensure_1080p(img_path: str) -> str:
    img = Image.open(img_path).convert('RGB')
    img_ratio = img.width / img.height
    target_ratio = TARGET_W / TARGET_H
    if abs(img_ratio - target_ratio) < 1e-3:
        out = img
    elif img_ratio > target_ratio:
        new_w = TARGET_W
        new_h = int(TARGET_W / img_ratio)
        resized = img.resize((new_w, new_h), Image.LANCZOS)
        canvas = Image.new('RGB', (TARGET_W, TARGET_H), (0,0,0))
        top = (TARGET_H - new_h)//2
        canvas.paste(resized, (0, top))
        out = canvas
    else:
        new_h = TARGET_H
        new_w = int(TARGET_H * img_ratio)
        resized = img.resize((new_w, new_h), Image.LANCZOS)
        canvas = Image.new('RGB', (TARGET_W, TARGET_H), (0,0,0))
        left = (TARGET_W - new_w)//2
        canvas.paste(resized, (left, 0))
        out = canvas
    out_path = os.path.splitext(img_path)[0] + "_1080p.jpg"
    out.save(out_path, quality=95)
    return out_path

def render_video(thumbnail_path: str, audio_path: str, out_path: str):
    fixed_thumb = ensure_1080p(thumbnail_path)
    audio = AudioFileClip(audio_path)
    image = ImageClip(fixed_thumb, duration=audio.duration)
    video = image.set_audio(audio).set_fps(24)
    video.write_videofile(
        out_path,
        codec="libx264",
        audio_codec="aac",
        fps=24,
        preset="veryfast",
        threads=2,
        verbose=False,
        logger=None
    )
