# api/kubah_lava_routes.py
"""
API Monitoring Kubah Lava (Persyaratan 1)
Menampilkan:
- Nama gunung
- Status aktivitas
- Tinggi kubah lava
- Volume kubah lava
- Pertumbuhan kubah lava
- Riwayat perubahan
- Grafik perkembangan (data series)
- Waktu update terakhir
"""
from flask import Blueprint, jsonify, request
from utils.level_mapper import GUNUNG_TARGET
from database.queries import get_latest_status, get_kubah_lava_data

kubah_lava_bp = Blueprint("kubah_lava_api", __name__)

@kubah_lava_bp.route("/api/kubah-lava")
def api_kubah_lava_all():
    summary = []
    for slug, meta in GUNUNG_TARGET.items():
        status = get_latest_status(slug)
        records = get_kubah_lava_data(slug, limit=50)
        latest_rec = records[0] if records else None
        
        summary.append({
            "slug": slug,
            "nama_gunung": meta["nama"],
            "lokasi": meta["lokasi"],
            "status_aktivitas": status.get("level_label") if status else "Normal",
            "level_code": status.get("level") if status else "I",
            "color": status.get("color") if status else "#4C9A7E",
            "tinggi_kubah_m": latest_rec.get("tinggi_m") if latest_rec else None,
            "volume_kubah_m3": latest_rec.get("volume_m3") if latest_rec else None,
            "pertumbuhan_kubah_m3": latest_rec.get("perubahan_volume_m3") if latest_rec else None,
            "status_morfologi": latest_rec.get("status_morfologi") if latest_rec else "Tidak teramati",
            "lokasi_kubah": latest_rec.get("lokasi_kubah") if latest_rec else "-",
            "waktu_update_terakhir": latest_rec.get("fetched_at") if latest_rec else (status.get("fetched_at") if status else None),
            "total_riwayat": len(records),
            "riwayat": records,
        })
    return jsonify({"kubah_lava": summary})

@kubah_lava_bp.route("/api/kubah-lava/<slug>")
def api_kubah_lava_detail(slug):
    if slug not in GUNUNG_TARGET:
        return jsonify({"error": "Gunung tidak dipantau"}), 404
        
    meta = GUNUNG_TARGET[slug]
    status = get_latest_status(slug)
    limit = int(request.args.get("limit", 50))
    records = get_kubah_lava_data(slug, limit=limit)
    latest_rec = records[0] if records else None

    # Chart data series
    chart_series = []
    for r in reversed(records):
        chart_series.append({
            "tanggal": r.get("tanggal") or r.get("fetched_at", "")[:10],
            "volume_m3": r.get("volume_m3"),
            "tinggi_m": r.get("tinggi_m"),
            "perubahan_m3": r.get("perubahan_volume_m3")
        })

    return jsonify({
        "slug": slug,
        "nama_gunung": meta["nama"],
        "lokasi": meta["lokasi"],
        "status_aktivitas": status.get("level_label") if status else "Normal",
        "level_code": status.get("level") if status else "I",
        "tinggi_kubah_m": latest_rec.get("tinggi_m") if latest_rec else None,
        "volume_kubah_m3": latest_rec.get("volume_m3") if latest_rec else None,
        "pertumbuhan_kubah_m3": latest_rec.get("perubahan_volume_m3") if latest_rec else None,
        "status_morfologi": latest_rec.get("status_morfologi") if latest_rec else "Tidak teramati",
        "waktu_update_terakhir": latest_rec.get("fetched_at") if latest_rec else (status.get("fetched_at") if status else None),
        "chart_series": chart_series,
        "riwayat": records
    })
