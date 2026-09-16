# database/queries.py
"""
Fungsi-fungsi Query Database SQLite (CRUD operations)
"""
import os
import json
import sqlite3
from datetime import datetime, timezone
from database.db import get_conn, SNAPSHOT_DIR
from utils.level_mapper import GUNUNG_TARGET
from utils.datetime_utils import get_wib_now

MAX_SNAPSHOTS_PER_CAMERA = 30

# --- User Queries ---
def create_user(username, password_hash):
    with get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, password_hash, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            return True, None
        except sqlite3.IntegrityError:
            return False, "Username sudah dipakai."

def get_user_by_username(username):
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM users WHERE username=?", (username,))
        return cur.fetchone()

# --- Status History Queries ---
def get_latest_status(slug):
    with get_conn() as conn:
        cur = conn.execute(
            """SELECT level, level_label, color, ringkasan, sumber, fetched_at
            FROM status_history WHERE gunung=? ORDER BY id DESC LIMIT 1""",
            (slug,),
        )
        r = cur.fetchone()
        if r:
            return {
                "level": r["level"], "level_label": r["level_label"], "color": r["color"],
                "ringkasan": r["ringkasan"], "sumber": r["sumber"], "fetched_at": r["fetched_at"]
            }
        return None

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
                "level": r["level"], "level_label": r["level_label"], "color": r["color"],
                "ringkasan": r["ringkasan"], "sumber": r["sumber"], "fetched_at": r["fetched_at"]
            }
            for r in rows
        ]

def save_status_snapshot(slug, data):
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT level, ringkasan FROM status_history WHERE gunung=? ORDER BY id DESC LIMIT 1",
            (slug,),
        )
        last = cur.fetchone()
        old_level = last["level"] if last else None
        is_new = last is None or last["level"] != data.get("level") or last["ringkasan"] != data.get("ringkasan")

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

    return is_new, old_level

# --- Gempa Vulkanik Queries ---
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
        return [dict(r) for r in cur.fetchall()]

# --- Gas Vulkanik Queries ---
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
        rows = cur.fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["h2s_detected"] = bool(d["h2s_detected"])
            out.append(d)
        return out

# --- Awan Panas Queries ---
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
        return [dict(r) for r in cur.fetchall()]

# --- Kubah Lava Queries ---
def save_kubah_lava_data(slug, records, fetched_at):
    with get_conn() as conn:
        for rec in records:
            conn.execute(
                """INSERT INTO kubah_lava
                (gunung, tanggal, volume_m3, perubahan_volume_m3, tinggi_m, lokasi_kubah, status_morfologi, catatan, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (slug, rec.get("tanggal"), rec.get("volume_m3"), rec.get("perubahan_volume_m3"),
                 rec.get("tinggi_m"), rec.get("lokasi_kubah"), rec.get("status_morfologi"), rec.get("catatan"), fetched_at)
            )
        conn.commit()

def get_kubah_lava_data(slug=None, limit=50):
    with get_conn() as conn:
        if slug:
            cur = conn.execute(
                """SELECT id, gunung, tanggal, volume_m3, perubahan_volume_m3, tinggi_m, lokasi_kubah, status_morfologi, catatan, fetched_at
                FROM kubah_lava WHERE gunung=? ORDER BY id DESC LIMIT ?""",
                (slug, limit)
            )
        else:
            cur = conn.execute(
                """SELECT id, gunung, tanggal, volume_m3, perubahan_volume_m3, tinggi_m, lokasi_kubah, status_morfologi, catatan, fetched_at
                FROM kubah_lava ORDER BY id DESC LIMIT ?""",
                (limit,)
            )
        return [dict(r) for r in cur.fetchall()]

# --- CCTV Queries ---
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

def get_latest_cctv_per_camera(slug):
    with get_conn() as conn:
        cur = conn.execute(
            """SELECT camera_name, source_url, local_path, fetched_at FROM cctv_snapshots
            WHERE gunung=? ORDER BY id DESC""",
            (slug,),
        )
        rows = cur.fetchall()
    
    seen, out = set(), []
    for r in rows:
        camera_name = r["camera_name"]
        if camera_name in seen:
            continue
        seen.add(camera_name)
        local_path = r["local_path"]
        out.append({
            "camera_name": camera_name,
            "source_url": r["source_url"],
            "snapshot_url": f"/snapshots/{os.path.relpath(local_path, SNAPSHOT_DIR)}" if local_path else None,
            "fetched_at": r["fetched_at"],
        })
    return out

# --- Gempa Realtime Queries ---
def save_gempa_realtime(records):
    saved_new = []
    with get_conn() as conn:
        for rec in records:
            gempa_id = rec.get("gempa_id")
            cur = conn.execute("SELECT id FROM gempa_realtime WHERE gempa_id=?", (gempa_id,))
            if not cur.fetchone():
                conn.execute(
                    """INSERT INTO gempa_realtime
                    (gempa_id, magnitudo, kedalaman_km, tanggal, jam, lat, lon, lokasi, dirasakan, potensi, sumber, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        gempa_id, rec.get("magnitudo"), rec.get("kedalaman_km"),
                        rec.get("tanggal"), rec.get("jam"), rec.get("lat"), rec.get("lon"),
                        rec.get("lokasi"), rec.get("dirasakan"), rec.get("potensi"),
                        rec.get("sumber", "BMKG"),
                        datetime.now(timezone.utc).isoformat()
                    )
                )
                saved_new.append(rec)
        conn.commit()
    return saved_new

def get_gempa_realtime(limit=100):
    with get_conn() as conn:
        cur = conn.execute(
            """SELECT id, gempa_id, magnitudo, kedalaman_km, tanggal, jam, lat, lon, lokasi, dirasakan, potensi, sumber, fetched_at
            FROM gempa_realtime ORDER BY id DESC LIMIT ?""",
            (limit,)
        )
        return [dict(r) for r in cur.fetchall()]

# --- Anti-Spam & Telegram Offline Queue ---
def is_event_hash_sent(event_hash):
    if not event_hash:
        return False
    with get_conn() as conn:
        cur = conn.execute("SELECT id FROM peringatan WHERE event_hash=?", (event_hash,))
        return cur.fetchone() is not None

def save_alert(slug, tipe, level_sebelum, level_sesudah, pesan, channel, status_kirim, event_hash=None):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO peringatan
            (gunung, tipe, level_sebelum, level_sesudah, pesan, terkirim_at, channel, status_kirim, event_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (slug, tipe, level_sebelum, level_sesudah, pesan,
             datetime.now(timezone.utc).isoformat(), channel, status_kirim, event_hash)
        )
        conn.commit()

def enqueue_telegram_message(message):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO telegram_queue (message, created_at, attempts) VALUES (?, ?, 0)",
            (message, datetime.now(timezone.utc).isoformat())
        )
        conn.commit()

def get_pending_telegram_queue(limit=20):
    with get_conn() as conn:
        cur = conn.execute("SELECT id, message, attempts FROM telegram_queue ORDER BY id ASC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]

def delete_telegram_queue_item(item_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM telegram_queue WHERE id=?", (item_id,))
        conn.commit()

def increment_telegram_queue_attempts(item_id):
    with get_conn() as conn:
        conn.execute("UPDATE telegram_queue SET attempts=attempts+1 WHERE id=?", (item_id,))
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
        return [dict(r) for r in cur.fetchall()]

# --- Cuaca Gunung Queries ---
def save_cuaca_gunung(slug, suhu, hujan, angin, kelembapan, kondisi):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO cuaca_gunung (gunung, suhu_c, hujan_mm, kecepatan_angin_kmh, kelembapan_pct, kondisi, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(gunung) DO UPDATE SET
                suhu_c=excluded.suhu_c, hujan_mm=excluded.hujan_mm,
                kecepatan_angin_kmh=excluded.kecepatan_angin_kmh,
                kelembapan_pct=excluded.kelembapan_pct, kondisi=excluded.kondisi,
                updated_at=excluded.updated_at""",
            (slug, suhu, hujan, angin, kelembapan, kondisi, datetime.now(timezone.utc).isoformat())
        )
        conn.commit()

def get_cuaca_gunung(slug):
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM cuaca_gunung WHERE gunung=?", (slug,))
        row = cur.fetchone()
        return dict(row) if row else None

# --- Panduan Checklist Queries ---
def set_checklist_item(item_key, checked):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO panduan_checklist (item_key, checked, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(item_key) DO UPDATE SET checked=excluded.checked, updated_at=excluded.updated_at""",
            (item_key, 1 if checked else 0, datetime.now(timezone.utc).isoformat())
        )
        conn.commit()

def get_all_checklist_items():
    with get_conn() as conn:
        cur = conn.execute("SELECT item_key, checked FROM panduan_checklist")
        return {r["item_key"]: bool(r["checked"]) for r in cur.fetchall()}

# --- Dashboard Statistik Queries ---
def get_dashboard_statistics():
    status_counts = {"Normal": 0, "Waspada": 0, "Siaga": 0, "Awas": 0, "Tidak Dipantau": 0}
    
    with get_conn() as conn:
        for slug in GUNUNG_TARGET:
            cur = conn.execute(
                "SELECT level_label FROM status_history WHERE gunung=? ORDER BY id DESC LIMIT 1",
                (slug,)
            )
            r = cur.fetchone()
            lbl = r["level_label"] if r and r["level_label"] else "Normal"
            if lbl in status_counts:
                status_counts[lbl] += 1
            else:
                status_counts["Normal"] += 1

        today_iso = get_wib_now().strftime("%Y-%m-%d")
        cur_rt = conn.execute(
            "SELECT COUNT(*) as cnt FROM gempa_realtime WHERE fetched_at LIKE ? OR tanggal LIKE ?",
            (f"{today_iso}%", f"%{today_iso}%")
        )
        rt_cnt = cur_rt.fetchone()["cnt"]

        cur_volc = conn.execute(
            "SELECT SUM(jumlah) as cnt FROM gempa_vulkanik WHERE fetched_at LIKE ?",
            (f"{today_iso}%",)
        )
        r_volc = cur_volc.fetchone()
        volc_cnt = r_volc["cnt"] if r_volc and r_volc["cnt"] else 0
        total_gempa_today = rt_cnt + volc_cnt

        cur_active = conn.execute(
            """SELECT gunung, SUM(jumlah) as total_event FROM gempa_vulkanik
            GROUP BY gunung ORDER BY total_event DESC LIMIT 1"""
        )
        row_act = cur_active.fetchone()
        most_active = {
            "gunung": row_act["gunung"].replace('-', ' ').title() if row_act else "Merapi",
            "total_event": row_act["total_event"] if row_act else 0
        }

    return {
        "status_counts": status_counts,
        "total_gempa_today": total_gempa_today,
        "most_active_volcano": most_active
    }
