# api/statistik_routes.py
"""
API Dashboard Statistik (Persyaratan 4)
Menampilkan:
- Jumlah gunung per status (Normal, Waspada, Siaga, Awas)
- Jumlah gempa hari ini
- Gunung paling aktif
- Grafik aktivitas 7 hari
- Grafik aktivitas 30 hari
- Grafik status gunung (Breakdown)
"""
from flask import Blueprint, jsonify
from datetime import datetime, timezone, timedelta
from database.queries import get_dashboard_statistics, get_conn
from utils.level_mapper import GUNUNG_TARGET

statistik_bp = Blueprint("statistik_api", __name__)

@statistik_bp.route("/api/statistik")
def api_statistik():
    basic_stats = get_dashboard_statistics()
    
    # Generate 7-day and 30-day timeline series from gempa_vulkanik & gempa_realtime tables
    now = datetime.now(timezone.utc)
    
    dates_7d = [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    dates_30d = [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(29, -1, -1)]
    
    counts_7d = {d: 0 for d in dates_7d}
    counts_30d = {d: 0 for d in dates_30d}

    with get_conn() as conn:
        # 1. Fetch volcanic events for 30 days
        cur_v = conn.execute(
            """SELECT tanggal, SUM(jumlah) as cnt FROM gempa_vulkanik
            WHERE tanggal >= ? GROUP BY tanggal""",
            (dates_30d[0],)
        )
        for r in cur_v.fetchall():
            tgl = r["tanggal"]
            cnt = r["cnt"] or 0
            if tgl in counts_30d:
                counts_30d[tgl] += cnt
            if tgl in counts_7d:
                counts_7d[tgl] += cnt

        # 2. Fetch realtime tectonic earthquakes for 30 days
        cur_r = conn.execute(
            """SELECT SUBSTR(fetched_at, 1, 10) as tgl, COUNT(*) as cnt FROM gempa_realtime
            WHERE fetched_at >= ? GROUP BY tgl""",
            (dates_30d[0],)
        )
        for r in cur_r.fetchall():
            tgl = r["tgl"]
            cnt = r["cnt"] or 0
            if tgl in counts_30d:
                counts_30d[tgl] += cnt
            if tgl in counts_7d:
                counts_7d[tgl] += cnt

    series_7d = [{"tanggal": d, "jumlah": counts_7d[d]} for d in dates_7d]
    series_30d = [{"tanggal": d, "jumlah": counts_30d[d]} for d in dates_30d]

    return jsonify({
        "status_counts": basic_stats["status_counts"],
        "total_gempa_today": basic_stats["total_gempa_today"],
        "most_active_volcano": basic_stats["most_active_volcano"],
        "grafik_7_hari": series_7d,
        "grafik_30_hari": series_30d,
        "total_gunung_dipantau": len(GUNUNG_TARGET)
    })
