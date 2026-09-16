# monitoring/cctv_scraper.py
"""
Scraper Snapshot CCTV Kamera Gunung Api dari MAGMA Indonesia
Mendukung penanganan fallback: "CCTV tidak ada atau tidak bisa diakses"
"""
import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from utils.level_mapper import GUNUNG_TARGET
from database.db import SNAPSHOT_DIR
from database.queries import save_cctv_snapshot

CCTV_URL_TEMPLATE = "https://magma.esdm.go.id/v1/gunung-api/cctv/{code}"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_last_cctv_fetch = {"success": False, "message": "CCTV tidak ada atau tidak bisa diakses", "time": None}

def get_last_cctv_fetch_info():
    return _last_cctv_fetch

def fetch_cctv_for(slug):
    global _last_cctv_fetch
    if slug not in GUNUNG_TARGET:
        return []
        
    meta = GUNUNG_TARGET[slug]
    cctv_code = meta.get("cctv_code")
    if not cctv_code:
        _last_cctv_fetch = {"success": False, "message": "CCTV tidak ada atau tidak bisa diakses", "time": datetime.now(timezone.utc).isoformat()}
        return []

    url = CCTV_URL_TEMPLATE.format(code=cctv_code)
    now_iso = datetime.now(timezone.utc).isoformat()
    saved = []
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            raise Exception("Halaman CCTV tidak dapat diakses")
            
        soup = BeautifulSoup(resp.text, "html.parser")
        imgs = soup.find_all("img")
        cam_dir = os.path.join(SNAPSHOT_DIR, slug)
        os.makedirs(cam_dir, exist_ok=True)
        count = 0

        for img in imgs:
            src = img.get("src") or img.get("data-src")
            if not src or any(x in src.lower() for x in ["logo", "icon", "sprite", ".svg", "bg-", "banner"]):
                continue
            full_url = src if src.startswith("http") else requests.compat.urljoin(url, src)
            camera_name = (img.get("alt") or img.get("title") or f"Kamera {count+1}").strip()
            camera_slug = re.sub(r"[^a-zA-Z0-9]+", "-", camera_name).strip("-").lower() or f"kamera-{count+1}"

            try:
                img_resp = requests.get(full_url, headers=HEADERS, timeout=10)
                if img_resp.status_code == 200 and len(img_resp.content) > 1000:
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

        if saved:
            _last_cctv_fetch = {
                "success": True,
                "message": f"{len(saved)} kamera CCTV ditemukan & tersimpan",
                "time": now_iso,
            }
        else:
            _last_cctv_fetch = {
                "success": False,
                "message": "CCTV tidak ada atau tidak bisa diakses",
                "time": now_iso,
            }
    except Exception as e:
        _last_cctv_fetch = {"success": False, "message": "CCTV tidak ada atau tidak bisa diakses", "time": now_iso}
    return saved
