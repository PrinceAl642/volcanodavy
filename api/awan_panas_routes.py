# api/awan_panas_routes.py
"""
API Awan Panas
"""
from flask import Blueprint, jsonify, request
from utils.level_mapper import GUNUNG_TARGET
from database.queries import get_awan_panas_data

awan_panas_bp = Blueprint("awan_panas_api", __name__)

@awan_panas_bp.route("/api/awan-panas/<slug>")
def api_awan_panas(slug):
    if slug not in GUNUNG_TARGET:
        return jsonify({"error": "Gunung tidak dipantau"}), 404
    limit = int(request.args.get("limit", 50))
    return jsonify({"gunung": slug, "data": get_awan_panas_data(slug, limit)})
