"""
services.py
----------------------------------
All yt-dlp interaction lives here, isolated from the Flask route layer
so it stays easy to test and swap out later.
"""

import re
import yt_dlp
from utils import detect_platform, format_duration, format_filesize

QUALITY_LADDER = [144, 240, 360, 480, 720, 1080, 1440, 2160]


class ExtractionError(Exception):
    """Raised when yt-dlp fails to read/understand a URL."""
    pass


def clean_yt_error(message: str) -> str:
    """
    Remove ANSI color codes and clean yt-dlp error text
    so the frontend gets readable messages.
    """
    if not message:
        return "Unknown extraction error."
    # Remove terminal color escape codes
    message = re.sub(r"\x1b\[[0-9;]*m", "", str(message))
    message = message.replace("ERROR:", "").strip()
    return message


def _ydl_opts(extra=None):
    """Base yt-dlp options shared by every call."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": 20,
        "retries": 2,
    }
    if extra:
        opts.update(extra)
    return opts


def fetch_video_info(url: str) -> dict:
    """
    Extract metadata and all available formats without trying
    to force a specific downloadable format first.
    """
    try:
        # IMPORTANT:
        # Use a safe format selector for metadata extraction.
        # We are NOT downloading here, only reading available formats.
        opts = _ydl_opts({
            "format": None,   # don't force bestvideo+bestaudio here
        })

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

    except yt_dlp.utils.DownloadError as exc:
        raise ExtractionError(clean_yt_error(str(exc))) from exc
    except Exception as exc:
        raise ExtractionError(f"Could not read video info: {clean_yt_error(str(exc))}") from exc

    if not info:
        raise ExtractionError("No data returned for this URL.")

    formats = info.get("formats") or []
    if not formats:
        raise ExtractionError("No downloadable formats were found for this video.")

    video_formats = _select_video_formats(formats)
    audio_format = _select_best_audio(formats)

    return {
        "platform": detect_platform(url) or info.get("extractor_key", "Unknown"),
        "title": info.get("title", "Untitled"),
        "thumbnail": info.get("thumbnail"),
        "duration": format_duration(info.get("duration")),
        "duration_seconds": info.get("duration"),
        "uploader": info.get("uploader") or info.get("channel") or "Unknown",
        "formats": video_formats,
        "audio": audio_format,
        "source_url": url,
    }


def _select_video_formats(formats: list) -> list:
    """
    Pick one representative format per resolution rung.
    Prefer mp4 and formats with audio when possible.
    """
    best_by_height = {}

    for fmt in formats:
        height = fmt.get("height")
        vcodec = fmt.get("vcodec", "none")

        # skip audio-only formats
        if not height or vcodec == "none":
            continue

        rung = min(QUALITY_LADDER, key=lambda q: abs(q - height))

        has_audio = fmt.get("acodec", "none") != "none"
        ext = fmt.get("ext") or ""
        tbr = fmt.get("tbr") or 0

        # Prefer:
        # 1) has audio
        # 2) mp4
        # 3) higher bitrate
        score = (
            1 if has_audio else 0,
            1 if ext == "mp4" else 0,
            tbr,
        )

        current_best = best_by_height.get(rung)
        if current_best is None or score > current_best["_score"]:
            best_by_height[rung] = {
                "_score": score,
                "quality": "4K" if rung == 2160 else f"{rung}p",
                "format_id": fmt.get("format_id"),
                "ext": ext,
                "filesize": format_filesize(
                    fmt.get("filesize") or fmt.get("filesize_approx")
                ),
                "has_audio": has_audio,
                "url": fmt.get("url"),
            }

    ordered = sorted(best_by_height.items(), key=lambda kv: kv[0])

    return [
        {k: v for k, v in fmt.items() if k != "_score"}
        for _, fmt in ordered
    ]


def _select_best_audio(formats: list) -> dict | None:
    """Pick the highest bitrate audio-only stream."""
    audio_only = [
        f for f in formats
        if f.get("vcodec") == "none" and f.get("acodec", "none") != "none"
    ]

    if not audio_only:
        return None

    best = max(audio_only, key=lambda f: f.get("abr") or 0)

    return {
        "format_id": best.get("format_id"),
        "ext": best.get("ext"),
        "abr": best.get("abr"),
        "filesize": format_filesize(
            best.get("filesize") or best.get("filesize_approx")
        ),
        "url": best.get("url"),
    }


def resolve_download_url(url: str, format_id: str) -> dict:
    """
    Resolve a direct download URL for a selected format_id.
    """
    try:
        opts = _ydl_opts({
            "format": format_id
        })

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

    except yt_dlp.utils.DownloadError as exc:
        raise ExtractionError(clean_yt_error(str(exc))) from exc
    except Exception as exc:
        raise ExtractionError(clean_yt_error(str(exc))) from exc

    if not info:
        raise ExtractionError("Could not resolve a download link for this format.")

    # Sometimes yt-dlp returns requested_formats / requested_downloads
    requested_downloads = info.get("requested_downloads")
    if requested_downloads:
        target = requested_downloads[0]
        return {
            "download_url": target.get("url"),
            "ext": target.get("ext"),
            "filesize": format_filesize(
                target.get("filesize") or target.get("filesize_approx")
            ),
        }

    requested_formats = info.get("requested_formats")
    if requested_formats:
        target = requested_formats[0]
        return {
            "download_url": target.get("url"),
            "ext": target.get("ext"),
            "filesize": format_filesize(
                target.get("filesize") or target.get("filesize_approx")
            ),
        }

    return {
        "download_url": info.get("url"),
        "ext": info.get("ext"),
        "filesize": format_filesize(
            info.get("filesize") or info.get("filesize_approx")
        ),
    }