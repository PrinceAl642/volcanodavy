import json
import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone
from functools import wraps
import requests
from bs4 import BeautifulSoup
from flask import (
    Flask, jsonify, request, session,
    send_from_directory, render_template
)
from werkzeug.security import generate_password_hash, check_password_hash

# ----------------------------------------------------------------------
# Konfigurasi
# ----------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "volcano.db")
SNAPSHOT_DIR = os.path.join(BASE_DIR, "snapshots")
MAX_SNAPSHOTS_PER_CAMERA = 30

STATUS_URL = "https://magma.esdm.go.id/v1/gunung-api/tingkat-aktivitas"
CCTV_URL_TEMPLATE = "https://magma.esdm.go.id/v1/gunung-api/cctv/{code}"

STATUS_POLL_SECONDS = 2 * 60
CCTV_AUTO_POLL_SECONDS = 5 * 60
AUTO_CCTV_POLL = True

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8967073652:AAFHnr--UsEny4JfoFRsdRQ5k_fX9rdO2PY")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "6274528706")
TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

GUNUNG_TARGET = {
    "merapi": {"aliases": ["merapi"], "cctv_code": "MER"},
    "slamet": {"aliases": ["slamet"], "cctv_code": "SLA"},
    "sindoro": {"aliases": ["sindoro"], "cctv_code": "SND"},
    "sumbing": {"aliases": ["sumbing"], "cctv_code": "SMB"},
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
}

LEVEL_MAP = {
    "normal": {"level": "I", "label": "Normal", "color": "#4C9A7E"},
    "waspada": {"level": "II", "label": "Waspada", "color": "#E8B923"},
    "siaga": {"level": "III", "label": "Siaga", "color": "#E8730C"},
    "awas": {"level": "IV", "label": "Awas", "color": "#C1272D"},
}

LEVEL_ORDER = {"I": 1, "II": 2, "III": 3, "IV": 4}

app = Flask(__name__)
app.secret_key = os.environ.get("VOLCANO_APP_SECRET", "ganti-secret-key-ini-di-produksi")
app.config.update(SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_HTTPONLY=True)

# Kunci Threading (Locking)
_status_lock = threading.Lock()
_cctv_lock = threading.Lock()

_last_status_fetch = {"success": False, "message": "Belum pernah diambil", "time": None}
_last_cctv_fetch = {"success": False, "message": "Belum pernah diambil", "time": None}

# ----------------------------------------------------------------------
# Database
# ----------------------------------------------------------------------
def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    with get_conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gunung TEXT NOT NULL,
                level TEXT,
                level_label TEXT,
                color TEXT,
                ringkasan TEXT,
                sumber TEXT,
                fetched_at TEXT NOT NULL,
                raw_json TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS cctv_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gunung TEXT NOT NULL,
                camera_name TEXT,
                source_url TEXT,
                local_path TEXT,
                fetched_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS gempa_vulkanik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gunung TEXT NOT NULL,
                tanggal TEXT,
                jenis_gempa TEXT,
                jumlah INTEGER,
                amplitudo_max REAL,
                durasi_max REAL,
                catatan TEXT,
                fetched_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS gas_vulkanik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gunung TEXT NOT NULL,
                tanggal TEXT,
                so2_flux REAL,
                co2_flux REAL,
                h2s_detected INTEGER DEFAULT 0,
                metode_pengukuran TEXT,
                catatan TEXT,
                fetched_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS awan_panas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gunung TEXT NOT NULL,
                tanggal TEXT,
                jenis TEXT,
                jarak_luncur_m REAL,
                arah TEXT,
                durasi_detik REAL,
                catatan TEXT,
                fetched_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS kubah_lava (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gunung TEXT NOT NULL,
                tanggal TEXT,
                volume_m3 REAL,
                perubahan_volume_m3 REAL,
                lokasi_kubah TEXT,
                status_morfologi TEXT,
                catatan TEXT,
                fetched_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS peringatan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gunung TEXT NOT NULL,
                tipe TEXT,
                level_sebelum TEXT,
                level_sesudah TEXT,
                pesan TEXT,
                terkirim_at TEXT NOT NULL,
                channel TEXT,
                status_kirim TEXT
            )"""
        )
        conn.commit()

# --- User Management ---
def create_user(username, password):
    with get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, generate_password_hash(password), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            return True, None
        except sqlite3.IntegrityError:
            return False, "Username sudah dipakai."

def verify_user(username, password):
    with get_conn() as conn:
        cur = conn.execute("SELECT password_hash FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        return bool(row) and check_password_hash(row[0], password)

# --- Status History ---
def save_status_snapshot(slug, data):
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT level, ringkasan FROM status_history WHERE gunung=? ORDER BY id DESC LIMIT 1",
            (slug,),
        )
        last = cur.fetchone()
        old_level = last[0] if last else None
        is_new = last is None or last[0] != data.get("level") or last[1] != data.get("ringkasan")

        if is_new:
            conn.execute(
                """INSERT INTO status_history
                (gunung, level, level_label, color, ringkasan, sumber, fetched_at, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    slug,
                    data.get("level"),
                    data.get("level_label"),
                    data.get("color"),
                    data.get("ringkasan"),
                    data.get("sumber"),
                    data.get("fetched_at"),
                    json.dumps(data, ensure_ascii=False),
                ),
            )
            conn.commit()

    # Parse and save structured data from ringkasan
    # ALWAYS attempt extraction even if status hasn't changed,
    # to ensure structured data is never lost.
    ringkasan = data.get("ringkasan", "")
    fetched_at = data.get("fetched_at", datetime.now(timezone.utc).isoformat())
    tanggal = fetched_at[:10] if fetched_at else None

    if ringkasan:
        try:
            # Check if we already have data for this tanggal to avoid duplicates
            with get_conn() as conn:
                cur = conn.execute(
                    "SELECT COUNT(*) FROM gempa_vulkanik WHERE gunung=? AND fetched_at=?",
                    (slug, fetched_at)
                )
                already_parsed = cur.fetchone()[0] > 0

            if not already_parsed:
                gempa_records = parse_gempa_from_ringkasan(ringkasan, tanggal)
                if gempa_records:
                    save_gempa_data(slug, gempa_records, fetched_at)

                gas_records = parse_gas_from_ringkasan(ringkasan, tanggal)
                if gas_records:
                    save_gas_data(slug, gas_records, fetched_at)

                ap_records = parse_awan_panas_from_ringkasan(ringkasan, tanggal)
                if ap_records:
                    save_awan_panas_data(slug, ap_records, fetched_at)

                kl_records = parse_kubah_lava_from_ringkasan(ringkasan, tanggal)
                if kl_records:
                    save_kubah_lava_data(slug, kl_records, fetched_at)
        except Exception as e:
            print(f"[WARN] Gagal parse ringkasan untuk {slug}: {e}")

    # Check alert trigger
    new_level = data.get("level")
    if old_level and new_level and is_new:
        check_and_send_alert(slug, old_level, new_level, data)

    return is_new

def get_status_history(slug, limit=50):
    with get_conn() as conn:
        cur = conn.execute(
            """SELECT level, level_label, color, ringkasan, sumber, fetched_at
            FROM status_history WHERE gunung=? ORDER BY id DESC LIMIT ?""",
            (slug, limit),
        )
        rows = cur.fetchall()
        return [
            {
                "level": r[0], "level_label": r[1], "color": r[2],
                "ringkasan": r[3], "sumber": r[4], "fetched_at": r[5]
            }
            for r in rows
        ]

def get_latest_status(slug):
    hist = get_status_history(slug, limit=1)
    return hist[0] if hist else None

# --- CCTV Snapshots ---
def save_cctv_snapshot(slug, camera_name, source_url, local_path):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO cctv_snapshots
            (gunung, camera_name, source_url, local_path, fetched_at)
            VALUES (?, ?, ?, ?, ?)""",
            (slug, camera_name, source_url, local_path, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        
        cur = conn.execute(
            "SELECT id, local_path FROM cctv_snapshots WHERE gunung=? AND camera_name=? ORDER BY id DESC",
            (slug, camera_name),
        )
        rows = cur.fetchall()
        
        for old_id, old_path in rows[MAX_SNAPSHOTS_PER_CAMERA:]:
            conn.execute("DELETE FROM cctv_snapshots WHERE id=?", (old_id,))
            if old_path and os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass
        conn.commit()

def get_cctv_history(slug, limit=30):
    with get_conn() as conn:
        cur = conn.execute(
            """SELECT camera_name, source_url, local_path, fetched_at FROM cctv_snapshots
            WHERE gunung=? ORDER BY id DESC LIMIT ?""",
            (slug, limit),
        )
        rows = cur.fetchall()
        return [
            {
                "camera_name": r[0],
                "source_url": r[1],
                "snapshot_url": f"/snapshots/{os.path.relpath(r[2], SNAPSHOT_DIR)}" if r[2] else None,
                "fetched_at": r[3],
            }
            for r in rows
        ]

def get_latest_cctv_per_camera(slug):
    with get_conn() as conn:
        cur = conn.execute(
            """SELECT camera_name, source_url, local_path, fetched_at FROM cctv_snapshots
            WHERE gunung=? ORDER BY id DESC""",
            (slug,),
        )
        rows = cur.fetchall()
    
    seen, out = set(), []
    for camera_name, source_url, local_path, fetched_at in rows:
        if camera_name in seen:
            continue
        seen.add(camera_name)
        out.append({
            "camera_name": camera_name,
            "source_url": source_url,
            "snapshot_url": f"/snapshots/{os.path.relpath(local_path, SNAPSHOT_DIR)}" if local_path else None,
            "fetched_at": fetched_at,
        })
    return out

# --- Gempa Vulkanik ---
def save_gempa_data(slug, records, fetched_at):
    with get_conn() as conn:
        for rec in records:
            conn.execute(
                """INSERT INTO gempa_vulkanik
                (gunung, tanggal, jenis_gempa, jumlah, amplitudo_max, durasi_max, catatan, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (slug, rec.get("tanggal"), rec.get("jenis_gempa"), rec.get("jumlah"),
                 rec.get("amplitudo_max"), rec.get("durasi_max"), rec.get("catatan"), fetched_at)
            )
        conn.commit()

def get_gempa_data(slug, limit=50):
    with get_conn() as conn:
        cur = conn.execute(
            """SELECT id, tanggal, jenis_gempa, jumlah, amplitudo_max, durasi_max, catatan, fetched_at
            FROM gempa_vulkanik WHERE gunung=? ORDER BY id DESC LIMIT ?""",
            (slug, limit)
        )
        return [
            {"id": r[0], "tanggal": r[1], "jenis_gempa": r[2], "jumlah": r[3],
             "amplitudo_max": r[4], "durasi_max": r[5], "catatan": r[6], "fetched_at": r[7]}
            for r in cur.fetchall()
        ]

# --- Gas Vulkanik ---
def save_gas_data(slug, records, fetched_at):
    with get_conn() as conn:
        for rec in records:
            conn.execute(
                """INSERT INTO gas_vulkanik
                (gunung, tanggal, so2_flux, co2_flux, h2s_detected, metode_pengukuran, catatan, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (slug, rec.get("tanggal"), rec.get("so2_flux"), rec.get("co2_flux"),
                 1 if rec.get("h2s_detected") else 0, rec.get("metode_pengukuran"),
                 rec.get("catatan"), fetched_at)
            )
        conn.commit()

def get_gas_data(slug, limit=50):
    with get_conn() as conn:
        cur = conn.execute(
            """SELECT id, tanggal, so2_flux, co2_flux, h2s_detected, metode_pengukuran, catatan, fetched_at
            FROM gas_vulkanik WHERE gunung=? ORDER BY id DESC LIMIT ?""",
            (slug, limit)
        )
        return [
            {"id": r[0], "tanggal": r[1], "so2_flux": r[2], "co2_flux": r[3],
             "h2s_detected": bool(r[4]), "metode_pengukuran": r[5], "catatan": r[6], "fetched_at": r[7]}
            for r in cur.fetchall()
        ]

# --- Awan Panas ---
def save_awan_panas_data(slug, records, fetched_at):
    with get_conn() as conn:
        for rec in records:
            conn.execute(
                """INSERT INTO awan_panas
                (gunung, tanggal, jenis, jarak_luncur_m, arah, durasi_detik, catatan, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (slug, rec.get("tanggal"), rec.get("jenis"), rec.get("jarak_luncur_m"),
                 rec.get("arah"), rec.get("durasi_detik"), rec.get("catatan"), fetched_at)
            )
        conn.commit()

def get_awan_panas_data(slug, limit=50):
    with get_conn() as conn:
        cur = conn.execute(
            """SELECT id, tanggal, jenis, jarak_luncur_m, arah, durasi_detik, catatan, fetched_at
            FROM awan_panas WHERE gunung=? ORDER BY id DESC LIMIT ?""",
            (slug, limit)
        )
        return [
            {"id": r[0], "tanggal": r[1], "jenis": r[2], "jarak_luncur_m": r[3],
             "arah": r[4], "durasi_detik": r[5], "catatan": r[6], "fetched_at": r[7]}
            for r in cur.fetchall()
        ]

# --- Kubah Lava ---
def save_kubah_lava_data(slug, records, fetched_at):
    with get_conn() as conn:
        for rec in records:
            conn.execute(
                """INSERT INTO kubah_lava
                (gunung, tanggal, volume_m3, perubahan_volume_m3, lokasi_kubah, status_morfologi, catatan, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (slug, rec.get("tanggal"), rec.get("volume_m3"), rec.get("perubahan_volume_m3"),
                 rec.get("lokasi_kubah"), rec.get("status_morfologi"), rec.get("catatan"), fetched_at)
            )
        conn.commit()

def get_kubah_lava_data(slug, limit=50):
    with get_conn() as conn:
        cur = conn.execute(
            """SELECT id, tanggal, volume_m3, perubahan_volume_m3, lokasi_kubah, status_morfologi, catatan, fetched_at
            FROM kubah_lava WHERE gunung=? ORDER BY id DESC LIMIT ?""",
            (slug, limit)
        )
        return [
            {"id": r[0], "tanggal": r[1], "volume_m3": r[2], "perubahan_volume_m3": r[3],
             "lokasi_kubah": r[4], "status_morfologi": r[5], "catatan": r[6], "fetched_at": r[7]}
            for r in cur.fetchall()
        ]

# --- Peringatan ---
def save_alert(slug, tipe, level_sebelum, level_sesudah, pesan, channel, status_kirim):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO peringatan
            (gunung, tipe, level_sebelum, level_sesudah, pesan, terkirim_at, channel, status_kirim)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (slug, tipe, level_sebelum, level_sesudah, pesan,
             datetime.now(timezone.utc).isoformat(), channel, status_kirim)
        )
        conn.commit()

def get_alerts(slug=None, limit=50):
    with get_conn() as conn:
        if slug:
            cur = conn.execute(
                """SELECT id, gunung, tipe, level_sebelum, level_sesudah, pesan, terkirim_at, channel, status_kirim
                FROM peringatan WHERE gunung=? ORDER BY id DESC LIMIT ?""",
                (slug, limit)
            )
        else:
            cur = conn.execute(
                """SELECT id, gunung, tipe, level_sebelum, level_sesudah, pesan, terkirim_at, channel, status_kirim
                FROM peringatan ORDER BY id DESC LIMIT ?""",
                (limit,)
            )
        return [
            {"id": r[0], "gunung": r[1], "tipe": r[2], "level_sebelum": r[3],
             "level_sesudah": r[4], "pesan": r[5], "terkirim_at": r[6],
             "channel": r[7], "status_kirim": r[8]}
            for r in cur.fetchall()
        ]

# ----------------------------------------------------------------------
# Parser: Ekstrak Data Terstruktur dari Ringkasan MAGMA
# ----------------------------------------------------------------------
def parse_gempa_from_ringkasan(text, tanggal=None):
    """Extract earthquake data from MAGMA Indonesia summary text."""
    results = []
    if not text:
        return results

    # Extract amplitude range
    amp_max = None
    amp_m = re.search(r'amplitudo\s+(?:maksimum\s+)?(?:antara\s+)?(\d+(?:[.,]\d+)?)\s*(?:[\u2013\-]\s*(\d+(?:[.,]\d+)?))?\s*mm', text, re.IGNORECASE)
    if amp_m:
        amp_max = float((amp_m.group(2) or amp_m.group(1)).replace(',', '.'))

    # Extract duration range
    dur_max = None
    dur_m = re.search(r'durasi\s+(?:maksimum\s+)?(?:antara\s+)?(\d+(?:[.,]\d+)?)\s*(?:[\u2013\-]\s*(\d+(?:[.,]\d+)?))?\s*detik', text, re.IGNORECASE)
    if dur_m:
        dur_max = float((dur_m.group(2) or dur_m.group(1)).replace(',', '.'))

    # Earthquake type patterns
    patterns = [
        (r'(?:gempa\s+)?(?:vulkanik\s+dalam|VA)\s*(?:\(VA\))?\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*kali', 'VA'),
        (r'(?:gempa\s+)?(?:vulkanik\s+dangkal|VB)\s*(?:\(VB\))?\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*kali', 'VB'),
        (r'(?:gempa\s+)?(?:vulkanik\s+dalam|VA)\s*(?:\(VA\))?\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*(?:kejadian|event)', 'VA'),
        (r'(?:gempa\s+)?(?:vulkanik\s+dangkal|VB)\s*(?:\(VB\))?\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*(?:kejadian|event)', 'VB'),
        (r'(?:gempa\s+)?(?:multifase|multi\s*fase|MP)\s*(?:\(MP\))?\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*kali', 'MP'),
        (r'(?:gempa\s+)?guguran\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*kali', 'Guguran'),
        (r'(?:gempa\s+)?hembusan\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*kali', 'Hembusan'),
        (r'(?:gempa\s+)?(?:tektonik\s+lokal|TL)\s*(?:\(TL\))?\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*kali', 'Tektonik Lokal'),
        (r'(?:gempa\s+)?(?:tektonik\s+jauh|TJ)\s*(?:\(TJ\))?\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*kali', 'Tektonik Jauh'),
        (r'(?:gempa\s+)?(?:low\s*frequency|LF)\s*(?:\(LF\))?\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*kali', 'LF'),
        (r'(?:gempa\s+)?(?:tornillo)\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*kali', 'Tornillo'),
        (r'(?:gempa\s+)?(?:hybrid|HB)\s*(?:\(HB\))?\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*kali', 'Hybrid'),
    ]

    seen_types = set()
    for pattern, jenis in patterns:
        if jenis in seen_types:
            continue
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            seen_types.add(jenis)
            results.append({
                "tanggal": tanggal,
                "jenis_gempa": jenis,
                "jumlah": int(m.group(1)),
                "amplitudo_max": amp_max,
                "durasi_max": dur_max,
                "catatan": None,
            })

    # Detect tremor
    tremor_m = re.search(r'tremor\s+(menerus|harmonik|non[\-\s]?harmonik)', text, re.IGNORECASE)
    if tremor_m:
        tremor_amp = None
        ta = re.search(r'tremor.*?amplitudo\s+(\d+(?:[.,]\d+)?)\s*(?:[\u2013\-]\s*(\d+(?:[.,]\d+)?))?\s*mm', text, re.IGNORECASE)
        if ta:
            tremor_amp = float((ta.group(2) or ta.group(1)).replace(',', '.'))
        results.append({
            "tanggal": tanggal,
            "jenis_gempa": f"Tremor {tremor_m.group(1).title()}",
            "jumlah": 1,
            "amplitudo_max": tremor_amp or amp_max,
            "durasi_max": None,
            "catatan": "Tremor menerus (kontinyu)",
        })

    return results

def parse_gas_from_ringkasan(text, tanggal=None):
    """Extract volcanic gas emission data from summary text."""
    results = []
    if not text:
        return results

    so2_flux = None
    co2_flux = None
    h2s = False
    metode = None
    catatan_parts = []

    # SO2 flux patterns
    so2_m = re.search(r'(?:emisi|flux|kadar)\s*SO2?\s*(?:sebesar\s+)?(\d+(?:[.,]\d+)?)\s*(?:ton/?(?:hari|day))', text, re.IGNORECASE)
    if so2_m:
        so2_flux = float(so2_m.group(1).replace(',', '.'))
        catatan_parts.append(f"SO2 flux: {so2_flux} ton/hari")

    # CO2 flux patterns
    co2_m = re.search(r'(?:emisi|flux|kadar)\s*CO2?\s*(?:sebesar\s+)?(\d+(?:[.,]\d+)?)\s*(?:ton/?(?:hari|day)|ppm|gram)', text, re.IGNORECASE)
    if co2_m:
        co2_flux = float(co2_m.group(1).replace(',', '.'))
        catatan_parts.append(f"CO2 flux: {co2_flux}")

    # H2S detection
    if re.search(r'(?:H2S|hidrogen\s+sulfida|belerang)\s*(?:terdeteksi|teramati|tercium|terasa)', text, re.IGNORECASE):
        h2s = True
        catatan_parts.append("H2S terdeteksi")

    # Gas emission visual
    gas_visual = re.search(r'(?:asap|gas|emisi|kolom)\s+(?:kawah|puncak)?\s*(?:berwarna\s+)?(putih|kelabu|abu[\-\s]?abu|hitam|kebiruan)', text, re.IGNORECASE)
    if gas_visual:
        catatan_parts.append(f"Warna emisi: {gas_visual.group(1)}")

    # Tinggi kolom gas
    tinggi_m = re.search(r'(?:asap|gas|kolom|emisi).*?tinggi\s*(?:sekitar\s+|maksimum\s+|antara\s+)?(\d+(?:[.,]\d+)?)\s*(?:[\u2013\-]\s*(\d+(?:[.,]\d+)?))?\s*(?:m(?:eter)?\b|m\s)', text, re.IGNORECASE)
    if tinggi_m:
        tinggi_val = tinggi_m.group(2) or tinggi_m.group(1)
        catatan_parts.append(f"Tinggi kolom: {tinggi_val} m")

    # DOAS method
    if re.search(r'DOAS', text, re.IGNORECASE):
        metode = "DOAS"
    elif re.search(r'Multi.?GAS|multi\s+gas', text, re.IGNORECASE):
        metode = "MultiGAS"

    if so2_flux is not None or co2_flux is not None or h2s or catatan_parts:
        results.append({
            "tanggal": tanggal,
            "so2_flux": so2_flux,
            "co2_flux": co2_flux,
            "h2s_detected": h2s,
            "metode_pengukuran": metode,
            "catatan": "; ".join(catatan_parts) if catatan_parts else None,
        })

    return results

def parse_awan_panas_from_ringkasan(text, tanggal=None):
    """Extract pyroclastic flow data from summary text."""
    results = []
    if not text:
        return results

    # Pattern: "awan panas guguran sejauh 1.500 m ke arah barat daya"
    ap_m = re.search(
        r'awan\s+panas\s+(guguran|letusan)\s*(?:meluncur\s+)?(?:sejauh\s+|jarak\s+(?:luncur\s+)?(?:maksimum\s+)?)?(?:sekitar\s+)?(\d+(?:[.,]\d+)?)\s*(m(?:eter)?|km)',
        text, re.IGNORECASE
    )
    if ap_m:
        jenis = ap_m.group(1).lower()
        jarak_raw = ap_m.group(2).replace('.', '').replace(',', '.')
        try:
            jarak = float(jarak_raw)
        except ValueError:
            jarak = None
        unit = ap_m.group(3).lower()
        if 'km' in unit:
            jarak = jarak * 1000 if jarak else None
            
        arah = None
        arah_m = re.search(
            r'(?:ke\s+)?(?:arah\s+)?(barat\s*daya|barat\s*laut|timur\s*laut|tenggara|utara|selatan|barat|timur)',
            text[ap_m.start():], re.IGNORECASE
        )
        if arah_m:
            arah = arah_m.group(1).strip()
            
        results.append({
            "tanggal": tanggal,
            "jenis": jenis,
            "jarak_luncur_m": jarak,
            "arah": arah,
            "durasi_detik": None,
            "catatan": ap_m.group(0).strip(),
        })

    # Also check for "guguran lava pijar" which is related
    lv_m = re.search(
        r'(\d+)\s*kali\s*guguran\s*lava\s*pijar.*?(?:jarak|sejauh)\s*(?:luncur\s+)?(?:maksimum\s+)?(?:sekitar\s+)?(\d+(?:[.,]\d+)?)\s*(m(?:eter)?|km)',
        text, re.IGNORECASE
    )
    if lv_m:
        jarak_raw = lv_m.group(2).replace('.', '').replace(',', '.')
        try:
            jarak = float(jarak_raw)
        except ValueError:
            jarak = None
        unit = lv_m.group(3).lower()
        if 'km' in unit:
            jarak = jarak * 1000 if jarak else None
            
        arah = None
        arah_m = re.search(
            r'(?:ke\s+)?(?:arah\s+)?(barat\s*daya|barat\s*laut|timur\s*laut|tenggara|utara|selatan|barat|timur)',
            text[lv_m.start():], re.IGNORECASE
        )
        if arah_m:
            arah = arah_m.group(1).strip()
            
        results.append({
            "tanggal": tanggal,
            "jenis": "guguran lava pijar",
            "jarak_luncur_m": jarak,
            "arah": arah,
            "durasi_detik": None,
            "catatan": f"{lv_m.group(1)} kali guguran lava pijar",
        })

    return results

def parse_kubah_lava_from_ringkasan(text, tanggal=None):
    """Extract lava dome data from summary text."""
    results = []
    if not text:
        return results

    volume = None
    perubahan = None
    lokasi = None
    status = None
    catatan_parts = []

    # Volume kubah lava
    vol_m = re.search(
        r'volume\s+(?:kubah\s+)?(?:lava\s+)?(?:saat\s+ini\s+)?(?:diperkirakan\s+)?(?:sebesar\s+)?(\d+(?:[.,]\d+)?)\s*(juta|ribu)?\s*(?:m(?:eter)?\s*(?:kubik|3|\u00b3)|m3)',
        text, re.IGNORECASE
    )
    if vol_m:
        vol_val = float(vol_m.group(1).replace(',', '.'))
        multiplier = vol_m.group(2)
        if multiplier and 'juta' in multiplier.lower():
            vol_val *= 1_000_000
        elif multiplier and 'ribu' in multiplier.lower():
            vol_val *= 1_000
        volume = vol_val
        catatan_parts.append(f"Volume: {vol_m.group(0).strip()}")

    # Perubahan volume
    delta_m = re.search(
        r'(?:perubahan|pertumbuhan|pertambahan)\s+(?:volume\s+)?(?:kubah\s+)?(?:lava\s+)?(?:sebesar\s+)?(\d+(?:[.,]\d+)?)\s*(juta|ribu)?\s*(?:m(?:eter)?\s*(?:kubik|3|\u00b3)|m3)',
        text, re.IGNORECASE
    )
    if delta_m:
        delta_val = float(delta_m.group(1).replace(',', '.'))
        multiplier = delta_m.group(2)
        if multiplier and 'juta' in multiplier.lower():
            delta_val *= 1_000_000
        elif multiplier and 'ribu' in multiplier.lower():
            delta_val *= 1_000
        perubahan = delta_val

    # Lokasi kubah
    lok_m = re.search(r'kubah\s+lava\s+(?:di\s+)?(puncak|tengah|barat\s*daya|timur\s*laut|selatan|utara|kawah)', text, re.IGNORECASE)
    if lok_m:
        lokasi = lok_m.group(1).strip()

    # Status morfologi
    if re.search(r'kubah.*?(?:aktif\s+)?tumbuh', text, re.IGNORECASE):
        status = "aktif tumbuh"
    elif re.search(r'kubah.*?stabil', text, re.IGNORECASE):
        status = "stabil"
    elif re.search(r'kubah.*?(?:runtuh|longsor|kolaps)', text, re.IGNORECASE):
        status = "parsial runtuh"

    # Lava dome mentions
    if re.search(r'kubah\s+lava', text, re.IGNORECASE) and not catatan_parts:
        catatan_parts.append("Kubah lava teramati")

    if volume is not None or status or catatan_parts:
        results.append({
            "tanggal": tanggal,
            "volume_m3": volume,
            "perubahan_volume_m3": perubahan,
            "lokasi_kubah": lokasi,
            "status_morfologi": status,
            "catatan": "; ".join(catatan_parts) if catatan_parts else None,
        })

    return results

# ----------------------------------------------------------------------
# Sistem Peringatan Dini (Early Warning System)
# ----------------------------------------------------------------------
def send_telegram_alert(message):
    """Send alert message via Telegram Bot API."""
    if not TELEGRAM_ENABLED:
        return False, "Telegram tidak dikonfigurasi"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True, "Terkirim"
    except requests.exceptions.RequestException as e:
        return False, f"Gagal mengirim: {e}"

def check_and_send_alert(slug, old_level, new_level, data):
    """Check if volcano level increased and send alert."""
    old_order = LEVEL_ORDER.get(old_level, 0)
    new_order = LEVEL_ORDER.get(new_level, 0)

    if new_order > old_order:
        gunung_name = slug.replace('-', ' ').title()
        level_label = data.get("level_label", new_level)
        ringkasan = data.get("ringkasan", "")

        emoji_map = {"II": "\u26a0\ufe0f", "III": "\ud83d\udea8", "IV": "\u2757"}
        emoji = emoji_map.get(new_level, "\u2139\ufe0f")

        message = (
            f"{emoji} <b>PERINGATAN GUNUNG API</b> {emoji}\n\n"
            f"\ud83c\udf0b <b>Gunung {gunung_name}</b>\n"
            f"\ud83d\udcc8 Status naik: Level {old_level} \u2192 Level {new_level} ({level_label})\n"
            f"\ud83d\udcc5 Waktu: {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')}\n\n"
            f"\ud83d\udcdd {ringkasan[:300]}\n\n"
            f"Sumber: MAGMA Indonesia - PVMBG"
        )

        success, status_msg = send_telegram_alert(message)
        save_alert(
            slug, "level_naik", old_level, new_level, message,
            "telegram", "terkirim" if success else f"gagal: {status_msg}"
        )
        print(f"[ALERT] {gunung_name}: Level {old_level} -> {new_level} | Telegram: {status_msg}")

    elif new_order < old_order:
        gunung_name = slug.replace('-', ' ').title()
        level_label = data.get("level_label", new_level)

        message = (
            f"\u2705 <b>UPDATE STATUS GUNUNG API</b>\n\n"
            f"\ud83c\udf0b <b>Gunung {gunung_name}</b>\n"
            f"\ud83d\udcc9 Status turun: Level {old_level} \u2192 Level {new_level} ({level_label})\n"
            f"\ud83d\udcc5 Waktu: {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')}\n\n"
            f"Sumber: MAGMA Indonesia - PVMBG"
        )

        success, status_msg = send_telegram_alert(message)
        save_alert(
            slug, "level_turun", old_level, new_level, message,
            "telegram", "terkirim" if success else f"gagal: {status_msg}"
        )

# ----------------------------------------------------------------------
# Scraper: Status
# ----------------------------------------------------------------------
def _normalize_level(raw_text):
    if not raw_text:
        return None
    text = raw_text.lower()
    for key, meta in LEVEL_MAP.items():
        if key in text:
            return meta
    return None

def fetch_all_status():
    global _last_status_fetch
    now_iso = datetime.now(timezone.utc).isoformat()
    results = {}
    try:
        resp = requests.get(STATUS_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        entries = []

        if "application/json" in content_type:
            data = resp.json()
            if isinstance(data, list):
                entries = data
            elif isinstance(data, dict):
                entries = data.get("data") or data.get("result") or []
        else:
            soup = BeautifulSoup(resp.text, "html.parser")
            text_blob = soup.get_text(" ", strip=True)
            for slug, meta in GUNUNG_TARGET.items():
                for alias in meta["aliases"]:
                    pattern = re.compile(rf"gunung\s*(api)?\s*{alias}.{{0,200}}", re.IGNORECASE)
                    m = pattern.search(text_blob)
                    if m:
                        entries.append({"nama": alias, "raw_text": m.group(0)})
                        break

        for slug, meta in GUNUNG_TARGET.items():
            match = None
            for entry in entries:
                nama = str(
                    entry.get("nama") or entry.get("name") or
                    entry.get("gunungapi") or entry.get("raw_text", "")
                ).lower()
                if any(alias in nama for alias in meta["aliases"]):
                    match = entry
                    break

            if match:
                raw_level_text = (
                    match.get("tingkat_aktivitas") or match.get("level") or
                    match.get("status") or match.get("raw_text") or ""
                )
                level_meta = _normalize_level(str(raw_level_text)) or LEVEL_MAP["normal"]
                results[slug] = {
                    "level": level_meta["level"],
                    "level_label": level_meta["label"],
                    "color": level_meta["color"],
                    "ringkasan": (
                        match.get("keterangan") or match.get("deskripsi") or str(raw_level_text)
                    )[:2000],
                    "sumber": STATUS_URL,
                    "fetched_at": now_iso,
                }
        _last_status_fetch = {
            "success": True,
            "message": f"Berhasil mengambil {len(results)}/{len(GUNUNG_TARGET)} gunung",
            "time": now_iso,
        }
    except requests.exceptions.RequestException as e:
        _last_status_fetch = {"success": False, "message": f"Gagal mengambil data: {e}", "time": now_iso}
    except Exception as e:
        _last_status_fetch = {
            "success": False,
            "message": f"Gagal parsing (struktur halaman berubah / diblokir anti-bot): {e}",
            "time": now_iso,
        }
    return results

def status_poll_loop():
    while True:
        with _status_lock:
            fresh = fetch_all_status()
            for slug, data in fresh.items():
                save_status_snapshot(slug, data)
        time.sleep(STATUS_POLL_SECONDS)

# ----------------------------------------------------------------------
# Scraper: CCTV
# ----------------------------------------------------------------------
def fetch_cctv_for(slug):
    global _last_cctv_fetch
    meta = GUNUNG_TARGET[slug]
    url = CCTV_URL_TEMPLATE.format(code=meta["cctv_code"])
    now_iso = datetime.now(timezone.utc).isoformat()
    saved = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        imgs = soup.find_all("img")
        cam_dir = os.path.join(SNAPSHOT_DIR, slug)
        os.makedirs(cam_dir, exist_ok=True)
        count = 0

        for img in imgs:
            src = img.get("src") or img.get("data-src")
            if not src or any(x in src.lower() for x in ["logo", "icon", "sprite", ".svg"]):
                continue
            full_url = src if src.startswith("http") else requests.compat.urljoin(url, src)
            camera_name = (img.get("alt") or img.get("title") or f"Kamera {count+1}").strip()
            camera_slug = re.sub(r"[^a-zA-Z0-9]+", "-", camera_name).strip("-").lower() or f"kamera-{count+1}"

            try:
                img_resp = requests.get(full_url, headers=HEADERS, timeout=15)
                img_resp.raise_for_status()
                ext = ".png" if "png" in img_resp.headers.get("content-type", "") else ".jpg"
                ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                local_path = os.path.join(cam_dir, f"{camera_slug}_{ts}{ext}")

                with open(local_path, "wb") as f:
                    f.write(img_resp.content)

                save_cctv_snapshot(slug, camera_name, full_url, local_path)
                saved.append(camera_name)
                count += 1
            except requests.exceptions.RequestException:
                continue

        _last_cctv_fetch = {
            "success": True,
            "message": (f"{len(saved)} kamera CCTV ditemukan & disimpan" if saved
                        else "Tidak ada CCTV yang terdeteksi untuk gunung ini di MAGMA Indonesia"),
            "time": now_iso,
        }
    except requests.exceptions.RequestException as e:
        _last_cctv_fetch = {"success": False, "message": f"Gagal mengambil halaman CCTV: {e}", "time": now_iso}
    except Exception as e:
        _last_cctv_fetch = {"success": False, "message": f"Gagal parsing halaman CCTV: {e}", "time": now_iso}
    return saved

def cctv_poll_loop():
    if not AUTO_CCTV_POLL:
        return
    while True:
        time.sleep(CCTV_AUTO_POLL_SECONDS)
        with _cctv_lock:
            for slug in GUNUNG_TARGET:
                fetch_cctv_for(slug)

# ----------------------------------------------------------------------
# Auth Helper
# ----------------------------------------------------------------------
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("username"):
            return jsonify({"error": "Belum login. Silakan masuk terlebih dahulu."}), 401
        return fn(*args, **kwargs)
    return wrapper

# ----------------------------------------------------------------------
# Routes: Frontend Halaman Utama
# ----------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

# ----------------------------------------------------------------------
# Routes: Authentication API
# ----------------------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def api_register():
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    if len(username) < 3:
        return jsonify({"error": "Username minimal 3 karakter."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password minimal 6 karakter."}), 400

    ok, err = create_user(username, password)
    if not ok:
        return jsonify({"error": err}), 409

    session["username"] = username
    return jsonify({"username": username, "message": "Akun berhasil dibuat."})

@app.route("/api/login", methods=["POST"])
def api_login():
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    if not verify_user(username, password):
        return jsonify({"error": "Username atau password salah."}), 401

    session["username"] = username
    return jsonify({"username": username, "message": "Berhasil masuk."})

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.pop("username", None)
    return jsonify({"message": "Berhasil keluar."})

@app.route("/api/me")
def api_me():
    username = session.get("username")
    if not username:
        return jsonify({"logged_in": False})
    return jsonify({"logged_in": True, "username": username})

# ----------------------------------------------------------------------
# Routes: Status Gunung API
# ----------------------------------------------------------------------
@app.route("/api/status")
# @login_required # Temporarily disabled for dashboard preview
def api_status_all():
    out = {slug: get_latest_status(slug) for slug in GUNUNG_TARGET}
    return jsonify({"gunung": out, "fetch_status": _last_status_fetch})

@app.route("/api/history/<slug>")
# @login_required
def api_history(slug):
    if slug not in GUNUNG_TARGET:
        return jsonify({"error": "Gunung tidak dipantau"}), 404
    limit = int(request.args.get("limit", 50))
    return jsonify({"gunung": slug, "history": get_status_history(slug, limit)})

@app.route("/api/refresh", methods=["POST"])
# @login_required
def api_refresh():
    with _status_lock:
        fresh = fetch_all_status()
        for slug, data in fresh.items():
            save_status_snapshot(slug, data)
    return jsonify({"fetch_status": _last_status_fetch})

# ----------------------------------------------------------------------
# Routes: CCTV API & Media Serve
# ----------------------------------------------------------------------
@app.route("/api/cctv/<slug>")
# @login_required
def api_cctv_latest(slug):
    if slug not in GUNUNG_TARGET:
        return jsonify({"error": "Gunung tidak dipantau"}), 404
    cams = get_latest_cctv_per_camera(slug)
    return jsonify({"gunung": slug, "tersedia": len(cams) > 0, "kamera": cams, "fetch_status": _last_cctv_fetch})

@app.route("/api/cctv/<slug>/refresh", methods=["POST"])
# @login_required
def api_cctv_refresh(slug):
    if slug not in GUNUNG_TARGET:
        return jsonify({"error": "Gunung tidak dipantau"}), 404
    with _cctv_lock:
        fetch_cctv_for(slug)
    cams = get_latest_cctv_per_camera(slug)
    return jsonify({"gunung": slug, "tersedia": len(cams) > 0, "kamera": cams, "fetch_status": _last_cctv_fetch})

@app.route("/api/cctv/<slug>/history")
# @login_required
def api_cctv_history(slug):
    if slug not in GUNUNG_TARGET:
        return jsonify({"error": "Gunung tidak dipantau"}), 404
    limit = int(request.args.get("limit", 30))
    return jsonify({"gunung": slug, "history": get_cctv_history(slug, limit)})

@app.route("/snapshots/<path:filename>")
def serve_snapshot(filename):
    return send_from_directory(SNAPSHOT_DIR, filename)

# ----------------------------------------------------------------------
# Routes: Monitoring Data APIs (NEW)
# ----------------------------------------------------------------------
@app.route("/api/gempa/<slug>")
# @login_required
def api_gempa(slug):
    if slug not in GUNUNG_TARGET:
        return jsonify({"error": "Gunung tidak dipantau"}), 404
    limit = int(request.args.get("limit", 50))
    return jsonify({"gunung": slug, "data": get_gempa_data(slug, limit)})

@app.route("/api/gas/<slug>")
# @login_required
def api_gas(slug):
    if slug not in GUNUNG_TARGET:
        return jsonify({"error": "Gunung tidak dipantau"}), 404
    limit = int(request.args.get("limit", 50))
    return jsonify({"gunung": slug, "data": get_gas_data(slug, limit)})

@app.route("/api/awan-panas/<slug>")
# @login_required
def api_awan_panas(slug):
    if slug not in GUNUNG_TARGET:
        return jsonify({"error": "Gunung tidak dipantau"}), 404
    limit = int(request.args.get("limit", 50))
    return jsonify({"gunung": slug, "data": get_awan_panas_data(slug, limit)})

@app.route("/api/kubah-lava/<slug>")
# @login_required
def api_kubah_lava(slug):
    if slug not in GUNUNG_TARGET:
        return jsonify({"error": "Gunung tidak dipantau"}), 404
    limit = int(request.args.get("limit", 50))
    return jsonify({"gunung": slug, "data": get_kubah_lava_data(slug, limit)})

@app.route("/api/dashboard/<slug>")
# @login_required
def api_dashboard(slug):
    if slug not in GUNUNG_TARGET:
        return jsonify({"error": "Gunung tidak dipantau"}), 404
    return jsonify({
        "gunung": slug,
        "status": get_latest_status(slug),
        "gempa": get_gempa_data(slug, 20),
        "gas": get_gas_data(slug, 10),
        "awan_panas": get_awan_panas_data(slug, 10),
        "kubah_lava": get_kubah_lava_data(slug, 10),
        "peringatan": get_alerts(slug, 10),
    })

# ----------------------------------------------------------------------
# Routes: Peringatan (Alert) APIs (NEW)
# ----------------------------------------------------------------------
@app.route("/api/peringatan")
# @login_required
def api_peringatan_all():
    limit = int(request.args.get("limit", 50))
    return jsonify({"data": get_alerts(limit=limit), "telegram_enabled": TELEGRAM_ENABLED})

@app.route("/api/peringatan/<slug>")
# @login_required
def api_peringatan_gunung(slug):
    if slug not in GUNUNG_TARGET:
        return jsonify({"error": "Gunung tidak dipantau"}), 404
    limit = int(request.args.get("limit", 50))
    return jsonify({"gunung": slug, "data": get_alerts(slug, limit), "telegram_enabled": TELEGRAM_ENABLED})

@app.route("/api/peringatan/test", methods=["POST"])
# @login_required
def api_peringatan_test():
    message = (
        "\u2705 <b>TES PERINGATAN GUNUNG API</b>\n\n"
        "Ini adalah pesan uji coba dari sistem monitoring gunung api.\n"
        f"Waktu: {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')}\n\n"
        "Jika Anda menerima pesan ini, maka integrasi Telegram berhasil."
    )
    success, status_msg = send_telegram_alert(message)
    return jsonify({
        "success": success,
        "message": status_msg,
        "telegram_enabled": TELEGRAM_ENABLED
    })

@app.route("/api/telegram-status")
def api_telegram_status():
    return jsonify({"enabled": TELEGRAM_ENABLED, "configured": bool(TELEGRAM_BOT_TOKEN)})

# ----------------------------------------------------------------------
# Routes: Server-Sent Events (SSE) for Real-Time Data Push
# ----------------------------------------------------------------------
@app.route("/api/stream")
def api_stream():
    """SSE endpoint for real-time push updates to the frontend."""
    def event_stream():
        last_data = {}
        while True:
            try:
                current = {}
                for slug in GUNUNG_TARGET:
                    status = get_latest_status(slug)
                    current[slug] = status

                # Check if data has changed
                if current != last_data:
                    payload = json.dumps({
                        "gunung": current,
                        "fetch_status": _last_status_fetch,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
                    last_data = {k: (dict(v) if v else None) for k, v in current.items()}
                else:
                    # Send heartbeat to keep connection alive
                    yield f": heartbeat\n\n"

                time.sleep(5)  # Check every 5 seconds
            except GeneratorExit:
                break
            except Exception as e:
                yield f"data: {{\"error\": \"{e}\"}}\n\n"
                time.sleep(10)

    from flask import Response
    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

# ----------------------------------------------------------------------
# Entry Point
# ----------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    with _status_lock:
        fresh = fetch_all_status()
        for slug, data in fresh.items():
            save_status_snapshot(slug, data)

    threading.Thread(target=status_poll_loop, daemon=True).start()
    if AUTO_CCTV_POLL:
        threading.Thread(target=cctv_poll_loop, daemon=True).start()

    print("=" * 60)
    print(" Indonesia Volcano Monitoring System")
    print(f" Telegram Alert: {'AKTIF' if TELEGRAM_ENABLED else 'NONAKTIF'}")
    print(" Buka browser dan kunjungi: http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)