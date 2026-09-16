# monitoring/usgs_earthquake.py
"""
Fetcher Data Gempa Bumi USGS (United States Geological Survey - Official Source)
Menyajikan data gempa tektonik global & regional Indonesia.
"""
import requests
from datetime import datetime, timezone
from database.queries import save_gempa_realtime

USGS_ALL_DAY_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
HEADERS = {"User-Agent": "VolcanoMonitoringCenter/2.0"}

def fetch_usgs_earthquakes():
    """Mengambil feed gempa bumi USGS real-time."""
    records = []
    try:
        r = requests.get(USGS_ALL_DAY_URL, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            features = data.get("features", [])
            for feat in features:
                props = feat.get("properties", {})
                geom = feat.get("geometry", {})
                coords = geom.get("coordinates", [0, 0, 0])
                
                lon = float(coords[0]) if len(coords) > 0 else 0.0
                lat = float(coords[1]) if len(coords) > 1 else 0.0
                depth = float(coords[2]) if len(coords) > 2 else 0.0
                
                # Filter region around Indonesia / SEA (-12 to 10 Lat, 90 to 142 Lon) or Mag >= 5.0
                is_indonesia = (-12.0 <= lat <= 10.0) and (90.0 <= lon <= 142.0)
                mag = float(props.get("mag") or 0.0)
                
                if is_indonesia or mag >= 5.0:
                    time_epoch = props.get("time", 0) / 1000.0
                    dt = datetime.fromtimestamp(time_epoch, tz=timezone.utc)
                    
                    gempa_id = f"usgs_{feat.get('id')}"
                    records.append({
                        "gempa_id": gempa_id,
                        "magnitudo": mag,
                        "kedalaman_km": depth,
                        "tanggal": dt.strftime("%Y-%m-%d"),
                        "jam": dt.strftime("%H:%M:%S"),
                        "lat": lat,
                        "lon": lon,
                        "lokasi": props.get("place", "Indonesia & Sejitarnya"),
                        "dirasakan": f"{props.get('felt') or '-'} laporan",
                        "potensi": "Monitoring USGS",
                        "sumber": "USGS Earthquake Hazards",
                    })
    except Exception as e:
        print(f"[WARN] Gagal fetch USGS gempa: {e}")
        
    if records:
        save_gempa_realtime(records)
    return records
