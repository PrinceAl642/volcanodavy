# monitoring/weather.py
"""
Fetcher Data Cuaca Gunung Api dari Open Meteo API (Official Open Weather Source)
"""
import requests
from utils.level_mapper import GUNUNG_TARGET
from database.queries import save_cuaca_gunung, get_cuaca_gunung

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
HEADERS = {"User-Agent": "VolcanoMonitoringCenter/2.0"}

def fetch_weather_for_volcano(slug):
    """Mengambil cuaca terkini dari Open Meteo untuk koordinat gunung api."""
    if slug not in GUNUNG_TARGET:
        return None
        
    meta = GUNUNG_TARGET[slug]
    lat = meta.get("lat")
    lon = meta.get("lon")
    
    if not lat or not lon:
        return None
        
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
        "timezone": "Asia/Jakarta"
    }
    
    try:
        r = requests.get(OPEN_METEO_URL, params=params, headers=HEADERS, timeout=8)
        if r.status_code == 200:
            data = r.json()
            curr = data.get("current", {})
            
            suhu = curr.get("temperature_2m")
            kelembapan = curr.get("relative_humidity_2m")
            hujan = curr.get("precipitation")
            angin = curr.get("wind_speed_10m")
            code = curr.get("weather_code", 0)
            
            # Map weather code to description
            kondisi = _map_weather_code(code, hujan)
            
            save_cuaca_gunung(slug, suhu, hujan, angin, kelembapan, kondisi)
            return get_cuaca_gunung(slug)
    except Exception as e:
        print(f"[WARN] Gagal fetch cuaca Open Meteo untuk {slug}: {e}")
        
    return get_cuaca_gunung(slug)

def fetch_weather_all():
    """Batch update cuaca untuk seluruh gunung api."""
    results = {}
    for slug in GUNUNG_TARGET:
        res = fetch_weather_for_volcano(slug)
        if res:
            results[slug] = res
    return results

def _map_weather_code(code, hujan=0):
    if hujan and hujan > 2.5:
        return "Hujan Lebat"
    elif hujan and hujan > 0:
        return "Hujan Ringan"
        
    code_map = {
        0: "Cerah",
        1: "Cerah Berawan",
        2: "Berawan",
        3: "Sangat Berawan / Mendung",
        45: "Kabut Tebal",
        48: "Kabut Embun",
        51: "Gerimis Ringan",
        61: "Hujan",
        80: "Hujan Lintas",
        95: "Badai Petir"
    }
    return code_map.get(code, "Cerah Berawan")
