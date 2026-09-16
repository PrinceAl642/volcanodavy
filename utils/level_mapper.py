# utils/level_mapper.py
"""
Level mapper dan basis data lengkap Gunung Api Indonesia (Pulau Jawa dan Luar Jawa).
Dilengkapi pemetaan kode CCTV MAGMA ESDM resmi.
"""

GUNUNG_TARGET = {
    # --- PULAU JAWA ---
    "merapi": {"nama": "Merapi", "lokasi": "DIY / Jawa Tengah", "ketinggian": 2968, "aliases": ["merapi"], "cctv_code": "MER", "lat": -7.5407, "lon": 110.4457},
    "merbabu": {"nama": "Merbabu", "lokasi": "Jawa Tengah", "ketinggian": 3145, "aliases": ["merbabu"], "cctv_code": "MRB", "lat": -7.4550, "lon": 110.4400},
    "slamet": {"nama": "Slamet", "lokasi": "Jawa Tengah", "ketinggian": 3428, "aliases": ["slamet"], "cctv_code": "SLA", "lat": -7.2420, "lon": 109.2080},
    "sumbing": {"nama": "Sumbing", "lokasi": "Jawa Tengah", "ketinggian": 3371, "aliases": ["sumbing"], "cctv_code": "SMB", "lat": -7.3840, "lon": 110.0700},
    "sindoro": {"nama": "Sindoro", "lokasi": "Jawa Tengah", "ketinggian": 3136, "aliases": ["sindoro", "sundoro"], "cctv_code": "SND", "lat": -7.3000, "lon": 109.9920},
    "lawu": {"nama": "Lawu", "lokasi": "Jawa Tengah / Jawa Timur", "ketinggian": 3265, "aliases": ["lawu"], "cctv_code": "LAW", "lat": -7.6250, "lon": 111.1920},
    "kelud": {"nama": "Kelud", "lokasi": "Jawa Timur", "ketinggian": 1731, "aliases": ["kelud"], "cctv_code": "KLD", "lat": -7.9300, "lon": 112.3080},
    "semeru": {"nama": "Semeru", "lokasi": "Jawa Timur", "ketinggian": 3676, "aliases": ["semeru"], "cctv_code": "SMR", "lat": -8.1080, "lon": 112.9220},
    "bromo": {"nama": "Bromo", "lokasi": "Jawa Timur", "ketinggian": 2329, "aliases": ["bromo"], "cctv_code": "BRM", "lat": -7.9420, "lon": 112.9530},
    "raung": {"nama": "Raung", "lokasi": "Jawa Timur", "ketinggian": 3332, "aliases": ["raung"], "cctv_code": "RNG", "lat": -8.1250, "lon": 114.0420},
    "ijen": {"nama": "Ijen", "lokasi": "Jawa Timur", "ketinggian": 2799, "aliases": ["ijen"], "cctv_code": "IJN", "lat": -8.0580, "lon": 114.2420},
    "papandayan": {"nama": "Papandayan", "lokasi": "Jawa Barat", "ketinggian": 2665, "aliases": ["papandayan"], "cctv_code": "PAP", "lat": -7.3200, "lon": 107.7300},
    "gede": {"nama": "Gede", "lokasi": "Jawa Barat", "ketinggian": 2958, "aliases": ["gede"], "cctv_code": "GDE", "lat": -6.7800, "lon": 106.9800},
    "pangrango": {"nama": "Pangrango", "lokasi": "Jawa Barat", "ketinggian": 3019, "aliases": ["pangrango"], "cctv_code": "PGR", "lat": -6.7700, "lon": 106.9700},
    "ciremai": {"nama": "Ciremai", "lokasi": "Jawa Barat", "ketinggian": 3078, "aliases": ["ciremai", "cereme"], "cctv_code": "CRM", "lat": -6.8920, "lon": 108.4000},
    "tangkuban-perahu": {"nama": "Tangkuban Perahu", "lokasi": "Jawa Barat", "ketinggian": 2084, "aliases": ["tangkuban", "tangkuban perahu"], "cctv_code": "TKP", "lat": -6.7700, "lon": 107.6000},
    "galunggung": {"nama": "Galunggung", "lokasi": "Jawa Barat", "ketinggian": 2168, "aliases": ["galunggung"], "cctv_code": "GLG", "lat": -7.2500, "lon": 108.0580},
    "salak": {"nama": "Salak", "lokasi": "Jawa Barat", "ketinggian": 2211, "aliases": ["salak"], "cctv_code": "SLK", "lat": -6.7200, "lon": 106.7300},
    "arjuno-welirang": {"nama": "Arjuno-Welirang", "lokasi": "Jawa Timur", "ketinggian": 3339, "aliases": ["arjuno", "welirang"], "cctv_code": "ARJ", "lat": -7.7250, "lon": 112.5800},
    "lamongan": {"nama": "Lamongan", "lokasi": "Jawa Timur", "ketinggian": 1651, "aliases": ["lamongan"], "cctv_code": "LMG", "lat": -7.9790, "lon": 113.3420},
    "kawi": {"nama": "Kawi-Butak", "lokasi": "Jawa Timur", "ketinggian": 2551, "aliases": ["kawi", "butak"], "cctv_code": "KWI", "lat": -7.9200, "lon": 112.4500},
    "wilis": {"nama": "Wilis", "lokasi": "Jawa Timur", "ketinggian": 2563, "aliases": ["wilis"], "cctv_code": "WLS", "lat": -7.8080, "lon": 111.7580},
    "argopuro": {"nama": "Argopuro", "lokasi": "Jawa Timur", "ketinggian": 3088, "aliases": ["argopuro"], "cctv_code": "AGP", "lat": -7.9650, "lon": 113.5650},

    # --- LUAR PULAU JAWA ---
    "rinjani": {"nama": "Rinjani", "lokasi": "Nusa Tenggara Barat", "ketinggian": 3726, "aliases": ["rinjani"], "cctv_code": "RNJ", "lat": -8.4200, "lon": 116.4700},
    "agung": {"nama": "Agung", "lokasi": "Bali", "ketinggian": 3031, "aliases": ["agung"], "cctv_code": "AGN", "lat": -8.3420, "lon": 115.5080},
    "batur": {"nama": "Batur", "lokasi": "Bali", "ketinggian": 1717, "aliases": ["batur"], "cctv_code": "BTR", "lat": -8.2420, "lon": 115.3750},
    "tambora": {"nama": "Tambora", "lokasi": "Nusa Tenggara Barat", "ketinggian": 2850, "aliases": ["tambora"], "cctv_code": "TMB", "lat": -8.2500, "lon": 118.0000},
    "ili-lewotolok": {"nama": "Ili Lewotolok", "lokasi": "Nusa Tenggara Timur", "ketinggian": 1423, "aliases": ["ili lewotolok"], "cctv_code": "LWT", "lat": -8.2720, "lon": 123.5050},
    "lewotobi": {"nama": "Lewotobi Laki-laki", "lokasi": "Nusa Tenggara Timur", "ketinggian": 1584, "aliases": ["lewotobi laki", "lewotobi"], "cctv_code": "LWT", "lat": -8.5380, "lon": 122.7750},
    "lewotobi-perempuan": {"nama": "Lewotobi Perempuan", "lokasi": "Nusa Tenggara Timur", "ketinggian": 1703, "aliases": ["lewotobi perempuan"], "cctv_code": "LWP", "lat": -8.5580, "lon": 122.7800},
    "dukono": {"nama": "Dukono", "lokasi": "Maluku Utara", "ketinggian": 1335, "aliases": ["dukono"], "cctv_code": "DKN", "lat": 1.6930, "lon": 127.8820},
    "ibu": {"nama": "Ibu", "lokasi": "Maluku Utara", "ketinggian": 1325, "aliases": ["ibu"], "cctv_code": "IBU", "lat": 1.4880, "lon": 127.6330},
    "gamalama": {"nama": "Gamalama", "lokasi": "Maluku Utara", "ketinggian": 1715, "aliases": ["gamalama"], "cctv_code": "GML", "lat": 0.8000, "lon": 127.3300},
    "gamkonora": {"nama": "Gamkonora", "lokasi": "Maluku Utara", "ketinggian": 1635, "aliases": ["gamkonora"], "cctv_code": "GKN", "lat": 1.3800, "lon": 127.5300},
    "soputan": {"nama": "Soputan", "lokasi": "Sulawesi Utara", "ketinggian": 1785, "aliases": ["soputan"], "cctv_code": "SPT", "lat": 1.1120, "lon": 124.7300},
    "karangetang": {"nama": "Karangetang", "lokasi": "Sulawesi Utara", "ketinggian": 1784, "aliases": ["karangetang"], "cctv_code": "KRG", "lat": 2.7800, "lon": 125.4000},
    "ruang": {"nama": "Ruang", "lokasi": "Sulawesi Utara", "ketinggian": 725, "aliases": ["ruang"], "cctv_code": "RNG", "lat": 2.3000, "lon": 125.3700},
    "lokon": {"nama": "Lokon", "lokasi": "Sulawesi Utara", "ketinggian": 1580, "aliases": ["lokon"], "cctv_code": "LKN", "lat": 1.3580, "lon": 124.7920},
    "awu": {"nama": "Awu", "lokasi": "Sulawesi Utara", "ketinggian": 1320, "aliases": ["awu"], "cctv_code": "AWU", "lat": 3.5500, "lon": 125.5000},
    "marapi": {"nama": "Marapi", "lokasi": "Sumatera Barat", "ketinggian": 2891, "aliases": ["marapi"], "cctv_code": "MRP", "lat": -0.3810, "lon": 100.4730},
    "sinabung": {"nama": "Sinabung", "lokasi": "Sumatera Utara", "ketinggian": 2460, "aliases": ["sinabung"], "cctv_code": "SIN", "lat": 3.1700, "lon": 98.3920},
    "kerinci": {"nama": "Kerinci", "lokasi": "Jambi / Sumatera Barat", "ketinggian": 3805, "aliases": ["kerinci"], "cctv_code": "KRC", "lat": -1.6970, "lon": 101.2640},
    "dempo": {"nama": "Dempo", "lokasi": "Sumatera Selatan", "ketinggian": 3173, "aliases": ["dempo"], "cctv_code": "DMP", "lat": -4.0300, "lon": 103.1300},
    "anak-krakatau": {"nama": "Anak Krakatau", "lokasi": "Lampung / Selat Sunda", "ketinggian": 157, "aliases": ["krakatau"], "cctv_code": "KRA", "lat": -6.1020, "lon": 105.4230},
}

LEVEL_MAP = {
    "normal": {"level": "I", "label": "Normal", "color": "#4C9A7E", "badge_class": "bg-success"},
    "waspada": {"level": "II", "label": "Waspada", "color": "#E8B923", "badge_class": "bg-warning text-dark"},
    "siaga": {"level": "III", "label": "Siaga", "color": "#E8730C", "badge_class": "bg-orange text-white"},
    "awas": {"level": "IV", "label": "Awas", "color": "#C1272D", "badge_class": "bg-danger"},
}

LEVEL_ORDER = {"I": 1, "II": 2, "III": 3, "IV": 4}

def normalize_level(raw_text):
    if not raw_text:
        return LEVEL_MAP["normal"]
    text = raw_text.lower()
    for key, meta in LEVEL_MAP.items():
        if key in text:
            return meta
    return LEVEL_MAP["normal"]
