import re
import unicodedata
from urllib.parse import parse_qs, urlparse

_TRANSLIT = {"ʻ": "", "ʼ": "", "'": "", "`": "", "’": ""}


def slugify(text: str) -> str:
    for src, dst in _TRANSLIT.items():
        text = text.replace(src, dst)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "film"


_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def trailer_embed_url(url: str | None) -> str | None:
    """YouTube yoki Vimeo havolasidan iframe uchun embed manzil yasaydi.

    Boshqa saytlar qabul qilinmaydi (None qaytadi).
    """
    if not url:
        return None
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return None
    host = (parsed.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    path = parsed.path.strip("/")

    video_id: str | None = None
    if host == "youtu.be":
        video_id = path.split("/")[0]
    elif host in {"youtube.com", "youtube-nocookie.com"}:
        if path == "watch":
            video_id = (parse_qs(parsed.query).get("v") or [None])[0]
        elif path.startswith(("embed/", "shorts/", "live/")):
            video_id = path.split("/")[1]
    if video_id is not None:
        return f"https://www.youtube-nocookie.com/embed/{video_id}" if _YT_ID.match(video_id) else None

    if host in {"vimeo.com", "player.vimeo.com"}:
        digits = [part for part in path.split("/") if part.isdigit()]
        if digits:
            return f"https://player.vimeo.com/video/{digits[0]}"
    return None
