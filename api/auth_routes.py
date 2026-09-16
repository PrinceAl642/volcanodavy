# api/auth_routes.py
"""
API Authentication Routes (Login, Register, Logout, Me)
"""
from flask import Blueprint, jsonify, request, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.queries import create_user, get_user_by_username

auth_bp = Blueprint("auth_api", __name__)

@auth_bp.route("/api/register", methods=["POST"])
def api_register():
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    if len(username) < 3:
        return jsonify({"error": "Username minimal 3 karakter."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password minimal 6 karakter."}), 400

    ok, err = create_user(username, generate_password_hash(password))
    if not ok:
        return jsonify({"error": err}), 409

    session["username"] = username
    return jsonify({"username": username, "message": "Akun berhasil dibuat."})

@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    user = get_user_by_username(username)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Username atau password salah."}), 401

    session["username"] = username
    return jsonify({"username": username, "message": "Berhasil masuk."})

@auth_bp.route("/api/logout", methods=["POST"])
def api_logout():
    session.pop("username", None)
    return jsonify({"message": "Berhasil keluar."})

@auth_bp.route("/api/me")
def api_me():
    username = session.get("username")
    if not username:
        return jsonify({"logged_in": False})
    return jsonify({"logged_in": True, "username": username})
