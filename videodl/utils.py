"""
utils.py
----------------------------------
Reusable helper functions:
  - URL validation
  - Platform detection (YouTube / Facebook / Instagram / TikTok / Twitter)
  - Input sanitization
  - Human-friendly formatting (duration, filesize)
"""

import re
from urllib.parse import urlparse

# Whitelisted platforms and the domain fragments used to detect them.
PLATFORM_PATTERNS = {
    "YouTube": [r"youtube\.com", r"youtu\.be"],
    "Facebook": [r"facebook\.com", r"fb\.watch"],
    "Instagram": [r"instagram\.com"],
    "TikTok": [r"tiktok\.com"],
    "Twitter/X": [r"twitter\.com", r"x\.com"],
}

# Basic URL shape check (scheme + domain). Not a full RFC validator,
# just enough to reject junk input before we ever touch yt-dlp.
URL_REGEX = re.compile(
    r"^https?://"                      # http:// or https://
    r"([A-Za-z0-9-]+\.)+[A-Za-z]{2,}"  # domain
    r"(:\d+)?"                          # optional port
    r"(/.*)?$"                          # optional path
)


def is_valid_url(url: str) -> bool:
    """Return True if the string looks like a well-formed http(s) URL."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if len(url) > 2048:  # guard against absurdly long input
        return False
    if not URL_REGEX.match(url):
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except ValueError:
        return False


def detect_platform(url: str) -> str | None:
    """Identify which supported platform a URL belongs to, else None."""
    url_lower = url.lower()
    for platform, patterns in PLATFORM_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, url_lower):
                return platform
    return None


def sanitize_url(url: str) -> str:
    """Strip whitespace / stray characters that could break yt-dlp calls."""
    return url.strip().replace("\n", "").replace("\r", "").replace('"', "")


def format_duration(seconds) -> str:
    """Convert seconds (int/float) into HH:MM:SS or MM:SS."""
    if seconds is None:
        return "N/A"
    try:
        seconds = int(seconds)
    except (ValueError, TypeError):
        return "N/A"
    hrs, rem = divmod(seconds, 3600)
    mins, secs = divmod(rem, 60)
    if hrs:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def format_filesize(num_bytes) -> str:
    """Convert bytes into a human-readable string (KB / MB / GB)."""
    if not num_bytes:
        return "Unknown"
    try:
        num_bytes = float(num_bytes)
    except (ValueError, TypeError):
        return "Unknown"
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"
