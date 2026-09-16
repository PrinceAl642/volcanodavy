# monitoring/magma_scraper.py
"""
Scraper data real-time dari MAGMA Indonesia (ESDM).
Mendukung penanganan error robust dan penataan data terstruktur.
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from utils.level_mapper import GUNUNG_TARGET, LEVEL_MAP, normalize_level
from utils.parsers import (
    parse_gempa_from_ringkasan,
    parse_gas_from_ringkasan,
    parse_awan_panas_from_ringkasan,
    parse_kubah_lava_from_ringkasan,
)
from database.queries import (
    save_status_snapshot,
    save_gempa_data,
    save_gas_data,
    save_awan_panas_data,
    save_kubah_lava_data,
)
from telegram.notifier import notify_event

STATUS_URL = "https://magma.esdm.go.id/v1/gunung-api/tingkat-aktivitas"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
}

_last_status_fetch = {"success": False, "message": "Belum pernah diambil", "time": None}

def get_last_status_fetch_info():
    return _last_status_fetch

def fetch_all_status():
    global _last_status_fetch
    now_iso = datetime.now(timezone.utc).isoformat()
    results = {}
    try:
        resp = requests.get(STATUS_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table")
        if not table:
            tr = soup.find('div', class_='table-responsive')
            if tr:
                table = tr.find('table')
                
        if not table:
            raise Exception("Tabel data tidak ditemukan di MAGMA ESDM")
            
        current_level_text = "Level I (Normal)"
        entries = {}
        for tr in table.find_all("tr"):
            tds = tr.find_all(["td", "th"])
            if not tds:
                continue
            
            for td in tds:
                a_tag = td.find("a")
                if a_tag and "Level" in a_tag.get_text():
                    current_level_text = a_tag.get_text(" ", strip=True)
                    break
                    
            for td in tds:
                cell_text = td.get_text(" ", strip=True)
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
                        
        for slug, meta in GUNUNG_TARGET.items():
            match = None
            for name_part, entry in entries.items():
                if any(alias in name_part for alias in meta["aliases"]):
                    match = entry
                    break
                    
            if match:
                raw_level_text = match["level_text"]
                level_meta = normalize_level(raw_level_text)
                
                ringkasan = f"{raw_level_text}"
                if match["report_url"]:
                    try:
                        rep = requests.get(match["report_url"], headers=HEADERS, timeout=10)
                        if rep.status_code == 200:
                            rsoup = BeautifulSoup(rep.text, "html.parser")
                            sections = []
                            for div in rsoup.find_all("div", class_="card"):
                                card_text = div.get_text(" ", strip=True)
                                if any(k in card_text for k in ["Pengamatan", "Klimatologi", "Keterangan", "Kegempaan", "Lava"]):
                                    sections.append(card_text)
                            if sections:
                                ringkasan = " | ".join(sections)
                    except Exception as e:
                        print(f"[WARN] Gagal mengambil laporan detail {slug}: {e}")
                        
                results[slug] = {
                    "level": level_meta["level"],
                    "level_label": level_meta["label"],
                    "color": level_meta["color"],
                    "ringkasan": ringkasan[:2000],
                    "sumber": match["report_url"] or STATUS_URL,
                    "fetched_at": now_iso,
                }
            else:
                # Fallback bila gunung spesifik tidak terdaftar di ringkasan tabel utama
                results[slug] = {
                    "level": "I",
                    "level_label": "Normal",
                    "color": "#4C9A7E",
                    "ringkasan": "Data tidak tersedia secara langsung di tabel utama MAGMA.",
                    "sumber": STATUS_URL,
                    "fetched_at": now_iso,
                }

        _last_status_fetch = {
            "success": True,
            "message": f"Berhasil sinkronisasi data {len(results)} gunung",
            "time": now_iso,
        }
    except Exception as e:
        _last_status_fetch = {
            "success": False,
            "message": f"Gagal parsing data MAGMA: {e}",
            "time": now_iso,
        }
        return results

    # Save to database and trigger notifications if needed
    for slug, data in results.items():
        is_new, old_level = save_status_snapshot(slug, data)
        ringkasan = data.get("ringkasan", "")
        tanggal = now_iso[:10]

        if ringkasan and "tidak tersedia" not in ringkasan.lower():
            # Parse sub-modules
            gempa_recs = parse_gempa_from_ringkasan(ringkasan, tanggal)
            if gempa_recs:
                save_gempa_data(slug, gempa_recs, now_iso)
                # Check for volcanic earthquake trigger
                for g in gempa_recs:
                    if g.get("jumlah", 0) > 10 or (g.get("amplitudo_max") and g["amplitudo_max"] > 20):
                        notify_event(
                            slug, "gempa_vulkanik", data.get("level_label", "Waspada"),
                            f"Gempa Vulkanik ({g.get('jenis_gempa')}): {g.get('jumlah')} kejadian, Amp max: {g.get('amplitudo_max')} mm",
                            sumber=data.get("sumber")
                        )

            gas_recs = parse_gas_from_ringkasan(ringkasan, tanggal)
            if gas_recs:
                save_gas_data(slug, gas_recs, now_iso)
                for gas in gas_recs:
                    if (gas.get("so2_flux") and gas["so2_flux"] > 500) or gas.get("h2s_detected"):
                        notify_event(
                            slug, "gas_meningkat", data.get("level_label", "Siaga"),
                            f"Emisi gas vulkanik meningkat: {gas.get('catatan')}",
                            sumber=data.get("sumber")
                        )

            ap_recs = parse_awan_panas_from_ringkasan(ringkasan, tanggal)
            if ap_recs:
                save_awan_panas_data(slug, ap_recs, now_iso)
                for ap in ap_recs:
                    notify_event(
                        slug, "awan_panas", data.get("level_label", "Siaga"),
                        f"Terjadi Awan Panas: {ap.get('catatan')}, Jarak luncur: {ap.get('jarak_luncur_m')} m ke arah {ap.get('arah', 'kawah')}",
                        sumber=data.get("sumber")
                    )

            kl_recs = parse_kubah_lava_from_ringkasan(ringkasan, tanggal)
            if kl_recs:
                save_kubah_lava_data(slug, kl_recs, now_iso)
                for kl in kl_recs:
                    notify_event(
                        slug, "kubah_lava", data.get("level_label", "Siaga"),
                        f"Perkembangan kubah lava: Volume {kl.get('volume_m3')} m3, Perubahan {kl.get('perubahan_volume_m3')} m3, Status: {kl.get('status_morfologi')}",
                        sumber=data.get("sumber")
                    )

        # Trigger status change notification
        if is_new and old_level and old_level != data.get("level"):
            notify_event(
                slug, "status_berubah", data.get("level_label", "Perubahan Status"),
                f"Status Gunung berubah dari Level {old_level} menjadi Level {data.get('level')} ({data.get('level_label')})",
                sumber=data.get("sumber")
            )

    return results
