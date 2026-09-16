# monitoring/bmkg_earthquake.py
"""
Fetcher Data Gempa Real-time BMKG & PVMBG & USGS
Memperbarui data peta gempa bumi secara real-time.
"""
import requests
from database.queries import save_gempa_realtime, get_gempa_realtime
from monitoring.usgs_earthquake import fetch_usgs_earthquakes
from telegram.notifier import notify_event

BMKG_DIRASAKAN_URL = "https://data.bmkg.go.id/DataMKG/TEWS/gempadirasakan.json"
BMKG_AUTOGEMPA_URL = "https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0",
    "Accept": "application/json",
}

def fetch_realtime_earthquakes():
    """Mengambil data gempa real-time BMKG dan USGS."""
    records = []
    
    # 1. Fetch BMKG autogempa
    try:
        r = requests.get(BMKG_AUTOGEMPA_URL, headers=HEADERS, timeout=8)
        if r.status_code == 200:
            data = r.json()
            g = data.get("Infogempa", {}).get("gempa", {})
            if g:
                coordinates = g.get("Coordinates", "0,0").split(",")
                lat = float(coordinates[0]) if len(coordinates) > 0 else 0.0
                lon = float(coordinates[1]) if len(coordinates) > 1 else 0.0
                
                mag_str = str(g.get("Magnitude", "0")).replace(",", ".")
                try: mag = float(mag_str)
                except ValueError: mag = 0.0

                kedalaman_str = str(g.get("Kedalaman", "0")).replace(" km", "").replace(",", ".")
                try: kedalaman = float(kedalaman_str)
                except ValueError: kedalaman = 0.0

                gempa_id = f"bmkg_auto_{g.get('Tanggal')}_{g.get('Jam')}"
                records.append({
                    "gempa_id": gempa_id,
                    "magnitudo": mag,
                    "kedalaman_km": kedalaman,
                    "tanggal": g.get("Tanggal"),
                    "jam": g.get("Jam"),
                    "lat": lat,
                    "lon": lon,
                    "lokasi": g.get("Wilayah"),
                    "dirasakan": g.get("Dirasakan", "-"),
                    "potensi": g.get("Potensi", "Tidak berpotensi tsunami"),
                    "sumber": "BMKG TEWS"
                })
    except Exception as e:
        print(f"[WARN] Gagal fetch BMKG autogempa: {e}")

    # 2. Fetch BMKG dirasakan
    try:
        r = requests.get(BMKG_DIRASAKAN_URL, headers=HEADERS, timeout=8)
        if r.status_code == 200:
            data = r.json()
            list_gempa = data.get("Infogempa", {}).get("gempa", [])
            if isinstance(list_gempa, dict):
                list_gempa = [list_gempa]
                
            for g in list_gempa:
                coordinates = g.get("Coordinates", "0,0").split(",")
                lat = float(coordinates[0]) if len(coordinates) > 0 else 0.0
                lon = float(coordinates[1]) if len(coordinates) > 1 else 0.0
                
                mag_str = str(g.get("Magnitude", "0")).replace(",", ".")
                try: mag = float(mag_str)
                except ValueError: mag = 0.0

                kedalaman_str = str(g.get("Kedalaman", "0")).replace(" km", "").replace(",", ".")
                try: kedalaman = float(kedalaman_str)
                except ValueError: kedalaman = 0.0

                gempa_id = f"bmkg_dirasakan_{g.get('Tanggal')}_{g.get('Jam')}_{lat}_{lon}"
                records.append({
                    "gempa_id": gempa_id,
                    "magnitudo": mag,
                    "kedalaman_km": kedalaman,
                    "tanggal": g.get("Tanggal"),
                    "jam": g.get("Jam"),
                    "lat": lat,
                    "lon": lon,
                    "lokasi": g.get("Wilayah"),
                    "dirasakan": g.get("Dirasakan", "-"),
                    "potensi": g.get("Potensi", "Dirasakan masyarakat"),
                    "sumber": "BMKG TEWS"
                })
    except Exception as e:
        print(f"[WARN] Gagal fetch BMKG dirasakan: {e}")

    # 3. Fetch USGS
    try:
        fetch_usgs_earthquakes()
    except Exception as e:
        print(f"[WARN] Gagal fetch USGS: {e}")

    if records:
        newly_saved = save_gempa_realtime(records)
        for g in newly_saved:
            if g.get("magnitudo", 0) >= 5.0:
                notify_event(
                    "indonesia", "gempa_tektonik", "Waspada",
                    f"Gempa Tektonik Real-time M {g.get('magnitudo')} - {g.get('lokasi')} (Kedalaman {g.get('kedalaman_km')} km)",
                    sumber=g.get("sumber", "BMKG TEWS"),
                    lokasi=g.get("lokasi"),
                    magnitudo=g.get("magnitudo"),
                    kedalaman=f"{g.get('kedalaman_km')} km"
                )

    return get_gempa_realtime(50)
