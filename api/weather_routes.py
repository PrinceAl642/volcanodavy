# api/weather_routes.py
"""
API Cuaca Real-Time Gunung Api dari Open Meteo
"""
from flask import Blueprint, jsonify, request
from utils.level_mapper import GUNUNG_TARGET
from database.queries import get_cuaca_gunung
from monitoring.weather import fetch_weather_for_volcano, fetch_weather_all

weather_bp = Blueprint("weather_api", __name__)

@weather_bp.route("/api/cuaca/<slug>")
def api_cuaca_gunung(slug):
    if slug not in GUNUNG_TARGET:
        return jsonify({"error": "Gunung tidak dipantau"}), 404
        
    data = get_cuaca_gunung(slug)
    if not data or request.args.get("refresh") == "true":
        data = fetch_weather_for_volcano(slug)
        
    if not data:
        return jsonify({"gunung": slug, "status": "Data sementara tidak tersedia."})
    return jsonify({"gunung": slug, "cuaca": data})

@weather_bp.route("/api/cuaca")
def api_cuaca_all():
    refresh = request.args.get("refresh") == "true"
    if refresh:
        data = fetch_weather_all()
    else:
        data = {slug: get_cuaca_gunung(slug) for slug in GUNUNG_TARGET}
    return jsonify({"cuaca": data})
