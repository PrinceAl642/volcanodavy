import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
STATUS_URL = "https://magma.esdm.go.id/v1/gunung-api/tingkat-aktivitas"

GUNUNG_TARGET = {
    "merapi": {"aliases": ["merapi"], "cctv_code": "MER"},
    "slamet": {"aliases": ["slamet"], "cctv_code": "SLA"},
    "sindoro": {"aliases": ["sindoro", "sundoro"], "cctv_code": "SND"},
    "sumbing": {"aliases": ["sumbing"], "cctv_code": "SMB"},
}

LEVEL_MAP = {
    "normal": {"level": "I", "label": "Normal", "color": "#4C9A7E"},
    "waspada": {"level": "II", "label": "Waspada", "color": "#E8B923"},
    "siaga": {"level": "III", "label": "Siaga", "color": "#E8730C"},
    "awas": {"level": "IV", "label": "Awas", "color": "#C1272D"},
}

def _normalize_level(raw_text):
    if not raw_text: return None
    text = raw_text.lower()
    for key, meta in LEVEL_MAP.items():
        if key in text: return meta
    return None

def fetch_all_status():
    now_iso = datetime.now(timezone.utc).isoformat()
    results = {}
    try:
        resp = requests.get(STATUS_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table")
        if not table:
            tr = soup.find('div', class_='table-responsive')
            if tr: table = tr.find('table')
                
        if not table:
            raise Exception("Tabel tidak ditemukan di halaman.")
            
        current_level_text = "Level I (Normal)"
        
        entries = {}
        for tr in table.find_all("tr"):
            tds = tr.find_all(["td", "th"])
            if not tds: continue
            
            # Check if this row defines a new level
            for td in tds:
                a_tag = td.find("a")
                if a_tag and "Level" in a_tag.get_text():
                    current_level_text = a_tag.get_text(" ", strip=True)
                    break
                    
            # Check for volcano entries in this row
            for td in tds:
                cell_text = td.get_text(" ", strip=True)
                # Link contains 'gunung-api/laporan'
                report_link = td.find("a", href=True)
                report_url = report_link["href"] if report_link and "laporan" in report_link.get("href", "") else ""
                
                if "Lihat laporan" in cell_text or "-" in cell_text or report_url:
                    name_part = cell_text.split("-")[0].strip().lower()
                    if name_part and "tidak ada gunung" not in name_part and "level" not in name_part:
                        entries[name_part] = {
                            "nama": name_part,
                            "level_text": current_level_text,
                            "report_url": report_url
                        }
        
        print(f"Extracted {len(entries)} volcanoes from table.")
        
        # Now map to GUNUNG_TARGET
        for slug, meta in GUNUNG_TARGET.items():
            match = None
            for name_part, entry in entries.items():
                if any(alias in name_part for alias in meta["aliases"]):
                    match = entry
                    break
                    
            if match:
                raw_level_text = match["level_text"]
                level_meta = _normalize_level(raw_level_text) or LEVEL_MAP["normal"]
                
                # Fetch detailed ringkasan from report URL if available
                ringkasan = f"{raw_level_text}"
                if match["report_url"]:
                    try:
                        rep = requests.get(match["report_url"], headers=HEADERS, timeout=10)
                        if rep.status_code == 200:
                            rsoup = BeautifulSoup(rep.text, "html.parser")
                            sections = []
                            for div in rsoup.find_all("div", class_="card"):
                                card_text = div.get_text(" ", strip=True)
                                if "Pengamatan" in card_text or "Klimatologi" in card_text or "Keterangan" in card_text:
                                    sections.append(card_text)
                            if sections:
                                ringkasan = " | ".join(sections)
                    except Exception as e:
                        print(f"[WARN] Gagal mengambil laporan {slug}: {e}")
                        
                results[slug] = {
                    "level": level_meta["level"],
                    "level_label": level_meta["label"],
                    "color": level_meta["color"],
                    "ringkasan": ringkasan[:2000],
                    "sumber": match["report_url"] or STATUS_URL,
                    "fetched_at": now_iso,
                }
    except Exception as e:
        print(f"Error: {e}")
    return results

res = fetch_all_status()
import json
print(json.dumps(res, indent=2))
