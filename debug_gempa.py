import re
import json

text = "Pengamatan Kegempaan 26 kali gempa Guguran dengan amplitudo 2-12 mm dan lama gempa 50.44-196.22 detik. 19 kali gempa Hybrid/Fase Banyak dengan amplitudo 2-39 mm, S-P 0.3-0.8 detik dan lama gempa 13.57-54.39 detik."
text2 = "Pengamatan Kegempaan 1 kali gempa Tektonik Jauh dengan amplitudo 4 mm, S-P 29 detik dan lama gempa 80 detik. 1 kali gempa Tremor Menerus dengan amplitudo 0.5 mm, dominan 0.5 mm."

def parse_gempa_from_ringkasan(text, tanggal=None):
    results = []
    if not text:
        return results

    # The format is often: "26 kali gempa Guguran dengan amplitudo 2-12 mm dan lama gempa 50.44-196.22 detik"
    # Or "1 kali gempa Tektonik Jauh"
    
    # Let's use a general pattern to extract all earthquakes
    # Format: <jumlah> kali gempa <jenis> dengan amplitudo <amp> mm dan lama gempa <dur> detik
    
    matches = re.finditer(r'(\d+)\s*kali\s*gempa\s+([A-Za-z\s/]+?)\s*dengan\s+amplitudo\s+([\d.,\-]+)\s*mm(?:.*?lama\s*gempa\s+([\d.,\-]+)\s*detik)?', text, re.IGNORECASE)
    
    for m in matches:
        jumlah = int(m.group(1))
        jenis = m.group(2).strip()
        amp_raw = m.group(3)
        dur_raw = m.group(4)
        
        # Parse max amplitude
        amp_max = None
        if amp_raw:
            parts = re.findall(r'[\d.,]+', amp_raw)
            if parts:
                amp_max = float(parts[-1].replace(',', '.'))
                
        # Parse max duration
        dur_max = None
        if dur_raw:
            parts = re.findall(r'[\d.,]+', dur_raw)
            if parts:
                dur_max = float(parts[-1].replace(',', '.'))
                
        results.append({
            "tanggal": tanggal,
            "jenis_gempa": jenis,
            "jumlah": jumlah,
            "amplitudo_max": amp_max,
            "durasi_max": dur_max,
            "catatan": m.group(0).strip(),
        })

    return results

print(json.dumps(parse_gempa_from_ringkasan(text), indent=2))
print(json.dumps(parse_gempa_from_ringkasan(text2), indent=2))
