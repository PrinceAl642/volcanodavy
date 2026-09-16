# utils/parsers.py
"""
Parser Regex untuk mengekstrak data terstruktur dari laporan ringkasan MAGMA ESDM.
"""
import re

def parse_gempa_from_ringkasan(text, tanggal=None):
    results = []
    if not text:
        return results

    seen_types = set()

    # Format 1: "26 kali gempa Guguran dengan amplitudo 2-12 mm dan lama gempa 50.44-196.22 detik"
    matches = re.finditer(r'(\d+)\s*kali\s*gempa\s+([A-Za-z\s/]+?)\s*dengan\s+amplitudo\s+([\d.,\-]+)\s*mm(?:.*?lama\s*gempa\s+([\d.,\-]+)\s*detik)?', text, re.IGNORECASE)
    for m in matches:
        jumlah = int(m.group(1))
        jenis = m.group(2).strip()
        amp_raw = m.group(3)
        dur_raw = m.group(4)
        
        amp_max = None
        if amp_raw:
            parts = re.findall(r'[\d.,]+', amp_raw)
            if parts:
                amp_max = float(parts[-1].replace(',', '.'))
                
        dur_max = None
        if dur_raw:
            parts = re.findall(r'[\d.,]+', dur_raw)
            if parts:
                dur_max = float(parts[-1].replace(',', '.'))
                
        seen_types.add(jenis.lower())
        results.append({
            "tanggal": tanggal,
            "jenis_gempa": jenis,
            "jumlah": jumlah,
            "amplitudo_max": amp_max,
            "durasi_max": dur_max,
            "catatan": m.group(0).strip(),
        })

    # Global amp/dur fallbacks
    amp_max_global = None
    amp_m = re.search(r'amplitudo\s+(?:maksimum\s+)?(?:antara\s+)?(\d+(?:[.,]\d+)?)\s*(?:[\u2013\-]\s*(\d+(?:[.,]\d+)?))?\s*mm', text, re.IGNORECASE)
    if amp_m:
        amp_max_global = float((amp_m.group(2) or amp_m.group(1)).replace(',', '.'))

    dur_max_global = None
    dur_m = re.search(r'durasi\s+(?:maksimum\s+)?(?:antara\s+)?(\d+(?:[.,]\d+)?)\s*(?:[\u2013\-]\s*(\d+(?:[.,]\d+)?))?\s*detik', text, re.IGNORECASE)
    if dur_m:
        dur_max_global = float((dur_m.group(2) or dur_m.group(1)).replace(',', '.'))

    patterns = [
        (r'(?:gempa\s+)?(?:vulkanik\s+dalam|VA)\s*(?:\(VA\))?\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*kali', 'VA'),
        (r'(?:gempa\s+)?(?:vulkanik\s+dangkal|VB)\s*(?:\(VB\))?\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*kali', 'VB'),
        (r'(?:gempa\s+)?(?:multifase|multi\s*fase|MP)\s*(?:\(MP\))?\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*kali', 'MP'),
        (r'(?:gempa\s+)?guguran\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*kali', 'Guguran'),
        (r'(?:gempa\s+)?hembusan\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*kali', 'Hembusan'),
        (r'(?:gempa\s+)?(?:tektonik\s+lokal|TL)\s*(?:\(TL\))?\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*kali', 'Tektonik Lokal'),
        (r'(?:gempa\s+)?(?:tektonik\s+jauh|TJ)\s*(?:\(TJ\))?\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*kali', 'Tektonik Jauh'),
        (r'(?:gempa\s+)?(?:low\s*frequency|LF)\s*(?:\(LF\))?\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*kali', 'LF'),
        (r'(?:gempa\s+)?(?:tornillo)\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*kali', 'Tornillo'),
        (r'(?:gempa\s+)?(?:hybrid|HB|fase\s+banyak)\s*(?:\(HB\))?\s*(?:sebanyak\s+|terekam\s+|tercatat\s+)?(\d+)\s*kali', 'Hybrid'),
    ]

    for pattern, jenis in patterns:
        if jenis.lower() in seen_types:
            continue
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            seen_types.add(jenis.lower())
            results.append({
                "tanggal": tanggal,
                "jenis_gempa": jenis,
                "jumlah": int(m.group(1)),
                "amplitudo_max": amp_max_global,
                "durasi_max": dur_max_global,
                "catatan": None,
            })

    tremor_m = re.search(r'tremor\s+(menerus|harmonik|non[\-\s]?harmonik)', text, re.IGNORECASE)
    if tremor_m:
        tremor_amp = None
        ta = re.search(r'tremor.*?amplitudo\s+(\d+(?:[.,]\d+)?)\s*(?:[\u2013\-]\s*(\d+(?:[.,]\d+)?))?\s*mm', text, re.IGNORECASE)
        if ta:
            tremor_amp = float((ta.group(2) or ta.group(1)).replace(',', '.'))
        
        jenis_tremor = f"Tremor {tremor_m.group(1).title()}"
        if jenis_tremor.lower() not in seen_types:
            results.append({
                "tanggal": tanggal,
                "jenis_gempa": jenis_tremor,
                "jumlah": 1,
                "amplitudo_max": tremor_amp or amp_max_global,
                "durasi_max": None,
                "catatan": "Tremor menerus (kontinyu)",
            })

    return results

def parse_gas_from_ringkasan(text, tanggal=None):
    results = []
    if not text:
        return results

    so2_flux = None
    co2_flux = None
    h2s = False
    metode = None
    catatan_parts = []

    so2_m = re.search(r'(?:emisi|flux|kadar)\s*SO2?\s*(?:sebesar\s+)?(\d+(?:[.,]\d+)?)\s*(?:ton/?(?:hari|day))', text, re.IGNORECASE)
    if so2_m:
        so2_flux = float(so2_m.group(1).replace(',', '.'))
        catatan_parts.append(f"SO2 flux: {so2_flux} ton/hari")

    co2_m = re.search(r'(?:emisi|flux|kadar)\s*CO2?\s*(?:sebesar\s+)?(\d+(?:[.,]\d+)?)\s*(?:ton/?(?:hari|day)|ppm|gram)', text, re.IGNORECASE)
    if co2_m:
        co2_flux = float(co2_m.group(1).replace(',', '.'))
        catatan_parts.append(f"CO2 flux: {co2_flux}")

    if re.search(r'(?:H2S|hidrogen\s+sulfida|belerang)\s*(?:terdeteksi|teramati|tercium|terasa)', text, re.IGNORECASE):
        h2s = True
        catatan_parts.append("H2S terdeteksi")

    gas_visual = re.search(r'(?:asap|gas|emisi|kolom)\s+(?:kawah|puncak)?\s*(?:berwarna\s+)?(putih|kelabu|abu[\-\s]?abu|hitam|kebiruan)', text, re.IGNORECASE)
    if gas_visual:
        catatan_parts.append(f"Warna emisi: {gas_visual.group(1)}")

    tinggi_m = re.search(r'(?:asap|gas|kolom|emisi).*?tinggi\s*(?:sekitar\s+|maksimum\s+|antara\s+)?(\d+(?:[.,]\d+)?)\s*(?:[\u2013\-]\s*(\d+(?:[.,]\d+)?))?\s*(?:m(?:eter)?\b|m\s)', text, re.IGNORECASE)
    if tinggi_m:
        tinggi_val = tinggi_m.group(2) or tinggi_m.group(1)
        catatan_parts.append(f"Tinggi kolom: {tinggi_val} m")

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
    results = []
    if not text:
        return results

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
    results = []
    if not text:
        return results

    volume = None
    perubahan = None
    tinggi = None
    lokasi = None
    status = None
    catatan_parts = []

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

    tinggi_m = re.search(
        r'tinggi\s+(?:kubah\s+)?(?:lava\s+)?(?:mencapai|sekitar|sebesar)?\s*(\d+(?:[.,]\d+)?)\s*m(?:eter)?',
        text, re.IGNORECASE
    )
    if tinggi_m:
        tinggi = float(tinggi_m.group(1).replace(',', '.'))
        catatan_parts.append(f"Tinggi: {tinggi} m")

    lok_m = re.search(r'kubah\s+lava\s+(?:di\s+)?(puncak|tengah|barat\s*daya|timur\s*laut|selatan|utara|kawah)', text, re.IGNORECASE)
    if lok_m:
        lokasi = lok_m.group(1).strip()

    if re.search(r'kubah.*?(?:aktif\s+)?tumbuh', text, re.IGNORECASE):
        status = "aktif tumbuh"
    elif re.search(r'kubah.*?stabil', text, re.IGNORECASE):
        status = "stabil"
    elif re.search(r'kubah.*?(?:runtuh|longsor|kolaps)', text, re.IGNORECASE):
        status = "parsial runtuh"

    if re.search(r'kubah\s+lava', text, re.IGNORECASE) and not catatan_parts:
        catatan_parts.append("Kubah lava teramati")

    if volume is not None or tinggi is not None or status or catatan_parts:
        results.append({
            "tanggal": tanggal,
            "volume_m3": volume,
            "perubahan_volume_m3": perubahan,
            "tinggi_m": tinggi,
            "lokasi_kubah": lokasi,
            "status_morfologi": status,
            "catatan": "; ".join(catatan_parts) if catatan_parts else None,
        })

    return results
