# api/gas_routes.py
"""
API Gas Vulkanik
"""
from flask import Blueprint, jsonify, request
from utils.level_mapper import GUNUNG_TARGET
from database.queries import get_gas_data

gas_bp = Blueprint("gas_api", __name__)

@gas_bp.route("/api/gas/<slug>")
def api_gas(slug):
    if slug not in GUNUNG_TARGET:
        return jsonify({"error": "Gunung tidak dipantau"}), 404
    limit = int(request.args.get("limit", 50))
    return jsonify({"gunung": slug, "data": get_gas_data(slug, limit)})
