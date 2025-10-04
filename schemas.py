
from pydantic import BaseModel
from typing import Optional

class JobOut(BaseModel):
    id: int
    title: str
    description: str
    tags: str
    script_text: str
    voice: str
    speed: float
    publish_iso: Optional[str]
    thumbnail_path: str
    audio_path: Optional[str]
    video_path: Optional[str]
    youtube_video_id: Optional[str]
    status: str
    progress_msg: str

    class Config:
        orm_mode = True
