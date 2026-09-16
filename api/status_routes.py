# api/status_routes.py
"""
API Status Gunung Api Indonesia
"""
from flask import Blueprint, jsonify, request
from utils.level_mapper import GUNUNG_TARGET
from database.queries import get_latest_status, get_status_history, save_status_snapshot
from monitoring.magma_scraper import fetch_all_status, get_last_status_fetch_info

status_bp = Blueprint("status_api", __name__)

@status_bp.route("/api/status")
def api_status_all():
    out = {}
    for slug, meta in GUNUNG_TARGET.items():
        st = get_latest_status(slug)
        if st:
            st["meta"] = meta
            out[slug] = st
        else:
            out[slug] = {
                "level": "I",
                "level_label": "Status Aktivitas Tidak Tersedia",
                "color": "#8b9bb4",
                "ringkasan": "Data sementara tidak tersedia.",
                "sumber": "MAGMA Indonesia",
                "fetched_at": None,
                "meta": meta
            }
    return jsonify({"gunung": out, "fetch_status": get_last_status_fetch_info()})

@status_bp.route("/api/history/<slug>")
def api_history(slug):
    if slug not in GUNUNG_TARGET:
        return jsonify({"error": "Gunung tidak dipantau"}), 404
    limit = int(request.args.get("limit", 50))
    return jsonify({"gunung": slug, "history": get_status_history(slug, limit)})

@status_bp.route("/api/refresh", methods=["POST"])
def api_refresh():
    fresh = fetch_all_status()
    for slug, data in fresh.items():
        save_status_snapshot(slug, data)
    return jsonify({"fetch_status": get_last_status_fetch_info()})
