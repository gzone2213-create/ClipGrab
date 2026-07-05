from flask import Blueprint, request, jsonify

from utils import is_valid_url, sanitize_url, detect_platform
from services import fetch_video_info, resolve_download_url, ExtractionError

api = Blueprint("api", __name__, url_prefix="/api")


@api.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@api.post("/info")
def info():
    payload = request.get_json(silent=True) or {}
    raw_url = payload.get("url", "")
    url = sanitize_url(raw_url)

    if not is_valid_url(url):
        return jsonify({"error": "Please paste a valid video URL."}), 400

    if not detect_platform(url):
        return jsonify({
            "error": "This site isn't supported yet. Try YouTube, Facebook, Instagram, TikTok, or Twitter/X."
        }), 400

    try:
        data = fetch_video_info(url)
    except ExtractionError as exc:
        return jsonify({"error": str(exc)}), 422

    return jsonify(data), 200


@api.post("/download")
def download():
    payload = request.get_json(silent=True) or {}
    raw_url = payload.get("url", "")
    format_id = str(payload.get("format_id", "")).strip()
    url = sanitize_url(raw_url)

    if not is_valid_url(url):
        return jsonify({"error": "Please paste a valid video URL."}), 400

    if not format_id:
        return jsonify({"error": "No format selected."}), 400

    try:
        result = resolve_download_url(url, format_id)
    except ExtractionError as exc:
        return jsonify({"error": str(exc)}), 422

    if not result.get("download_url"):
        return jsonify({"error": "Could not generate a download link for this format."}), 422

    return jsonify(result), 200