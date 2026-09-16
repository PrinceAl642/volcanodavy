# api/gempa_routes.py
"""
API Data Gempa Vulkanik dan Gempa Real-time (Persyaratan 3)
"""
from flask import Blueprint, jsonify, request
from utils.level_mapper import GUNUNG_TARGET
from database.queries import get_gempa_data, get_gempa_realtime
from monitoring.bmkg_earthquake import fetch_realtime_earthquakes

gempa_bp = Blueprint("gempa_api", __name__)

@gempa_bp.route("/api/gempa/<slug>")
def api_gempa_vulkanik(slug):
    if slug not in GUNUNG_TARGET:
        return jsonify({"error": "Gunung tidak dipantau"}), 404
    limit = int(request.args.get("limit", 50))
    return jsonify({"gunung": slug, "data": get_gempa_data(slug, limit)})

@gempa_bp.route("/api/gempa-realtime")
def api_gempa_realtime():
    refresh = request.args.get("refresh", "false").lower() == "true"
    if refresh:
        data = fetch_realtime_earthquakes()
    else:
        data = get_gempa_realtime(50)
        if not data:
            data = fetch_realtime_earthquakes()
    return jsonify({"gempa_realtime": data, "total": len(data)})
