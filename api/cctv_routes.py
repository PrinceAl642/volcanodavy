# api/cctv_routes.py
"""
API CCTV Snapshots Kamera Gunung Api MAGMA Indonesia
"""
from flask import Blueprint, jsonify, request
from utils.level_mapper import GUNUNG_TARGET
from database.queries import get_latest_cctv_per_camera
from monitoring.cctv_scraper import fetch_cctv_for, get_last_cctv_fetch_info

cctv_bp = Blueprint("cctv_api", __name__)

@cctv_bp.route("/api/cctv/<slug>")
def api_cctv_latest(slug):
    if slug not in GUNUNG_TARGET:
        return jsonify({"error": "Gunung tidak dipantau", "message": "CCTV tidak ada atau tidak bisa diakses"}), 404
        
    cams = get_latest_cctv_per_camera(slug)
    if not cams:
        # Attempt fetch on-demand if missing
        fetch_cctv_for(slug)
        cams = get_latest_cctv_per_camera(slug)

    tersedia = len(cams) > 0
    message = f"{len(cams)} kamera CCTV aktif" if tersedia else "CCTV tidak ada atau tidak bisa diakses"

    return jsonify({
        "gunung": slug,
        "nama_gunung": GUNUNG_TARGET[slug]["nama"],
        "tersedia": tersedia,
        "kamera": cams,
        "message": message,
        "fetch_status": get_last_cctv_fetch_info()
    })

@cctv_bp.route("/api/cctv/<slug>/refresh", methods=["POST"])
def api_cctv_refresh(slug):
    if slug not in GUNUNG_TARGET:
        return jsonify({"error": "Gunung tidak dipantau", "message": "CCTV tidak ada atau tidak bisa diakses"}), 404
        
    fetch_cctv_for(slug)
    cams = get_latest_cctv_per_camera(slug)
    tersedia = len(cams) > 0
    message = f"{len(cams)} kamera CCTV aktif" if tersedia else "CCTV tidak ada atau tidak bisa diakses"

    return jsonify({
        "gunung": slug,
        "nama_gunung": GUNUNG_TARGET[slug]["nama"],
        "tersedia": tersedia,
        "kamera": cams,
        "message": message,
        "fetch_status": get_last_cctv_fetch_info()
    })
