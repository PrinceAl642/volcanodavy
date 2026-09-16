# api/panduan_routes.py
"""
API Modul Edukasi & Keselamatan Pendakian
Halaman Khusus: Edukasi & Kondisi Darurat Lengkap (7 Protokol Presisi).
"""
from flask import Blueprint, jsonify, request
from database.queries import set_checklist_item, get_all_checklist_items

panduan_bp = Blueprint("panduan_api", __name__)

PANDUAN_DATA = {
    "syarat_mendaki": {
        "title": "Syarat Mendaki",
        "items": [
            {"nama": "Cek Status & Cuaca", "detail": "Cek status gunung melalui PVMBG & prakiraan cuaca BMKG/Open Meteo sebelum berangkat."},
            {"nama": "Perizinan Resmi (Simaksi)", "detail": "Daftar melalui jalur resmi (Simaksi) sesuai prosedur pengelola gunung."},
            {"nama": "Kabar Keluarga", "detail": "Beritahu keluarga atau rekan terdekat terkait rencana perjalanan & estimasi waktu turun."},
            {"nama": "Kondisi Fisik", "detail": "Pastikan kondisi fisik sehat prima. Jangan pernah mendaki sendirian (minimal 3 orang)."}
        ]
    },
    "checklist_peralatan": {
        "title": "Checklist Peralatan",
        "items": [
            {"key": "carrier", "label": "Carrier (40L-70L)"},
            {"key": "daypack", "label": "Daypack"},
            {"key": "sleeping_bag", "label": "Sleeping Bag"},
            {"key": "matras", "label": "Matras"},
            {"key": "tenda", "label": "Tenda Double Layer"},
            {"key": "headlamp", "label": "Headlamp + Baterai"},
            {"key": "senter_cadangan", "label": "Senter Cadangan"},
            {"key": "jaket", "label": "Jaket Gunung (Tebal/Windproof)"},
            {"key": "raincoat", "label": "Raincoat / Jas Hujan Mantol"},
            {"key": "emergency_blanket", "label": "Emergency Blanket (Aluminium)"},
            {"key": "sarung_tangan", "label": "Sarung Tangan"},
            {"key": "kupluk", "label": "Kupluk / Beanie"},
            {"key": "sepatu_hiking", "label": "Sepatu Hiking Berulir Dalam"},
            {"key": "tracking_pole", "label": "Trekking Pole"},
            {"key": "kompas", "label": "Kompas / Peta Offline"},
            {"key": "powerbank", "label": "Powerbank Kapasitas Tinggi"},
            {"key": "peluit", "label": "Peluit Darurat"},
            {"key": "pisau_lipat", "label": "Pisau Lipat Multi-tool"},
            {"key": "p3k", "label": "P3K & Obat Pribadi"},
            {"key": "air", "label": "Air Minum (Min. 3 Liter)"},
            {"key": "makanan_cadangan", "label": "Makanan & Logistik Darurat"},
            {"key": "kompor_portable", "label": "Kompor Portable"},
            {"key": "gas", "label": "Gas Portable"},
            {"key": "trash_bag", "label": "Trash Bag / Kantong Sampah Bawaan"}
        ]
    },
    "status_gunung": {
        "title": "Status Gunung Api",
        "levels": [
            {"level": "Level I (Normal)", "color": "#4C9A7E", "detail": "Aktivitas vulkanik tidak memperlihatkan peningkatan. Aman untuk pendakian sesuai batas kawah resmi."},
            {"level": "Level II (Waspada)", "color": "#E8B923", "detail": "Peningkatan aktivitas visual/seismik. Pendaki dilarang mendekati kawah dalam radius aman (1-3 km)."},
            {"level": "Level III (Siaga)", "color": "#E8730C", "detail": "Potensi erupsi meluas. Jalur pendakian ditutup total. Waspadai awan panas dan guguran lava."},
            {"level": "Level IV (Awas)", "color": "#C1272D", "detail": "Erupsi utama mengancam. Radius bahaya diperluas (5-12 km). Evakuasi total lereng & permukiman."}
        ]
    },
    "bahaya_gunung_api": {
        "title": "Bahaya Gunung Api",
        "items": [
            {"nama": "Awan Panas (Pyroclastic Flow)", "detail": "Campuran gas, abu, dan batuan pijar bersuhu 200–800°C meluncur >100 km/jam."},
            {"nama": "Lava Pijar", "detail": "Lelehan batuan pijar bersuhu >1000°C yang mengalir di alur kawah."},
            {"nama": "Lahar Hujan", "detail": "Banjir material erupsi bercampur air hujan di alur sungai lereng gunung."},
            {"nama": "Hujan Abu Vulkanik", "detail": "Partikel silika tajam yang mengganggu pernapasan (ISPA) dan penglihatan."},
            {"nama": "Gas Beracun", "detail": "Gas tak berwarna (CO, CO2, SO2, H2S) yang mengumpul di celah kawah."},
            {"nama": "Batu Pijar", "detail": "Lontaran material batuan berukuran besar saat letusan eksplosif."}
        ]
    },
    "protokol_darurat_presisi": [
        {
            "id": "hipotermia",
            "judul": "1. Hipotermia (Kedinginan Ekstrem)",
            "langkah": [
                "Pindahkan korban ke tempat kering dan terlindung dari angin.",
                "Segera ganti pakaian basah dengan yang kering.",
                "Bungkus tubuh dengan emergency blanket atau sleeping bag.",
                "Berikan minuman manis hangat (hanya jika korban sadar penuh).",
                "Lakukan skin-to-skin contact di dalam kantong tidur jika kondisi memburuk. Jangan dipijat keras."
            ]
        },
        {
            "id": "heat_stroke",
            "judul": "2. Heat Stroke (Serangan Panas)",
            "langkah": [
                "Pindahkan ke tempat teduh. Longgarkan atau lepas pakaian yang tebal.",
                "Kompres leher, ketiak, dan selangkangan dengan air dingin.",
                "Kipasi korban secara perlahan. Beri minum air kembang gula/oralit sedikit-sedikit jika sadar."
            ]
        },
        {
            "id": "terkilir_patah",
            "judul": "3. Terkilir & Patah Tulang",
            "langkah": [
                "Terkilir: Gunakan metode RICE (Rest, Ice, Compression, Elevation). Istirahatkan, kompres dingin, balut tekan, dan tinggikan area yang cedera.",
                "Patah Tulang: Jangan mencoba mengembalikan tulang. Pasang bidai (splint) menggunakan kayu/trekking pole agar tulang tidak bergerak saat evakuasi."
            ]
        },
        {
            "id": "gigitan_ular",
            "judul": "4. Gigitan Ular",
            "langkah": [
                "Tenangkan korban. Jaga area gigitan tetap berada di bawah level jantung.",
                "Imobilisasi (kurangi pergerakan) pada area gigitan dengan memasang bidai longgar.",
                "JANGAN dihisap, dibelek, atau diikat mati (turniket). Segera evakuasi ke fasilitas medis untuk Anti Bisa Ular (ABU)."
            ]
        },
        {
            "id": "tersesat",
            "judul": "5. Tersesat",
            "langkah": [
                "Gunakan metode STOP: Stop (Berhenti), Think (Berpikir rasional), Observe (Amati sekitar), Plan (Buat rencana).",
                "Jangan panik dan jangan terus berjalan membabi buta. Hemat air dan logistik.",
                "Tiup peluit 3 kali berturut-turut sebagai sinyal darurat internasional."
            ]
        },
        {
            "id": "erupsi_gempa_longsor",
            "judul": "6. Erupsi / Gempa / Longsor",
            "langkah": [
                "Erupsi: Hindari area lembah atau aliran sungai (potensi lahar dingin/awan panas). Bergerak berlawanan arah angin dari abu vulkanik. Gunakan masker/kain basah.",
                "Gempa: Jauhi tebing curam dan pohon besar yang rawan tumbang. Lindungi kepala."
            ]
        },
        {
            "id": "badai_petir",
            "judul": "7. Badai Petir",
            "langkah": [
                "Turun dari puncak atau area terbuka (sabana). Jauhi pohon tinggi yang berdiri sendirian.",
                "Letakkan barang berbahan logam (trekking pole, carrier berkerangka) agak jauh dari Anda.",
                "Lakukan posisi jongkok merunduk (lightning crouch): peluk lutut, kepala menunduk, dan jinjit (minimalkan kontak telapak kaki dengan tanah)."
            ]
        }
    ],
    "nomor_darurat": {
        "title": "Nomor Darurat Resmi",
        "contacts": [
            {"instansi": "BASARNAS (Search & Rescue)", "nomor": "115"},
            {"instansi": "Layanan Darurat Terpadu", "nomor": "112"},
            {"instansi": "PVMBG Pusat Vulkanologi", "nomor": "(022) 7272606"},
            {"instansi": "BPBD Daerah", "nomor": "112 / Posko BPBD"}
        ]
    }
}

@panduan_bp.route("/api/panduan")
def api_get_panduan():
    saved_checklist = get_all_checklist_items()
    data = dict(PANDUAN_DATA)
    
    items_with_state = []
    for item in data["checklist_peralatan"]["items"]:
        k = item["key"]
        items_with_state.append({
            "key": k,
            "label": item["label"],
            "checked": saved_checklist.get(k, False)
        })
    data["checklist_peralatan"]["items"] = items_with_state
    
    return jsonify(data)

@panduan_bp.route("/api/panduan/checklist", methods=["POST"])
def api_update_checklist():
    body = request.get_json(silent=True) or {}
    item_key = body.get("key")
    checked = bool(body.get("checked", False))
    
    if not item_key:
        return jsonify({"error": "Key item tidak valid"}), 400
        
    set_checklist_item(item_key, checked)
    return jsonify({"key": item_key, "checked": checked, "message": "Status checklist berhasil diperbarui."})
