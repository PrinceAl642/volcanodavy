# api/peringatan_routes.py
"""
API Peringatan & Integrasi Telegram (Instant Alert & Laporan 1 Jam)
"""
from flask import Blueprint, jsonify, request
from utils.level_mapper import GUNUNG_TARGET
from database.queries import get_alerts
from telegram.bot import is_telegram_configured
from telegram.notifier import notify_event, send_hourly_heartbeat_report

peringatan_bp = Blueprint("peringatan_api", __name__)

@peringatan_bp.route("/api/peringatan")
def api_peringatan_all():
    limit = int(request.args.get("limit", 50))
    return jsonify({"data": get_alerts(limit=limit), "telegram_enabled": is_telegram_configured()})

@peringatan_bp.route("/api/peringatan/<slug>")
def api_peringatan_gunung(slug):
    if slug not in GUNUNG_TARGET:
        return jsonify({"error": "Gunung tidak dipantau"}), 404
    limit = int(request.args.get("limit", 50))
    return jsonify({"gunung": slug, "data": get_alerts(slug, limit), "telegram_enabled": is_telegram_configured()})

@peringatan_bp.route("/api/peringatan/test", methods=["POST"])
def api_peringatan_test():
    success, status_msg = notify_event(
        "merapi", "erupsi", "Level III (Siaga)",
        "Erupsi terdeteksi di kawah utama dengan kolom abu setinggi 1.500m.",
        sumber="PVMBG MAGMA ESDM",
        lokasi="DIY / Jawa Tengah"
    )
    return jsonify({
        "success": success,
        "message": status_msg,
        "telegram_enabled": is_telegram_configured()
    })

@peringatan_bp.route("/api/peringatan/hourly-test", methods=["POST"])
def api_peringatan_hourly_test():
    success, status_msg = send_hourly_heartbeat_report()
    return jsonify({
        "success": success,
        "message": status_msg,
        "telegram_enabled": is_telegram_configured()
    })

@peringatan_bp.route("/api/telegram-status")
def api_telegram_status():
    return jsonify({"enabled": is_telegram_configured()})
