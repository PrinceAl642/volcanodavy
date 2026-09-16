# telegram/notifier.py
"""
Penyusun Notifikasi & Peringatan Otomatis Telegram
- Notifikasi Instan Kejadian Baru (Instant Single Event Alert)
- Laporan Berkala Setiap 1 Jam (Hourly Heartbeat Report)
- Sistem Anti-Spam (MD5 Event Hash Deduplication)
- Antrean Offline (Offline Queue jika koneksi internet terputus)
"""
import hashlib
from telegram.bot import send_telegram_message
from database.queries import (
    save_alert,
    is_event_hash_sent,
    enqueue_telegram_message,
    get_pending_telegram_queue,
    delete_telegram_queue_item,
    increment_telegram_queue_attempts,
    get_dashboard_statistics,
    get_gempa_realtime
)
from utils.datetime_utils import get_wib_now
from utils.level_mapper import GUNUNG_TARGET

INDONESIAN_DAYS = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"]
INDONESIAN_MONTHS = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

def notify_event(gunung_slug, event_type, status_label, detail, sumber="PVMBG / BMKG", lokasi=None, magnitudo=None, kedalaman=None):
    """
    Mengirim notifikasi instan tunggal ke Telegram saat kejadian baru valid terdeteksi.
    """
    meta = GUNUNG_TARGET.get(gunung_slug, {})
    gunung_name = meta.get("nama", gunung_slug.replace('-', ' ').title())
    lokasi_str = lokasi or meta.get("lokasi", "Indonesia")
    
    wib_now = get_wib_now()
    hari_str = INDONESIAN_DAYS[wib_now.weekday()]
    month_name = INDONESIAN_MONTHS[wib_now.month]
    tanggal_str = f"{hari_str}, {wib_now.day} {month_name} {wib_now.year}"
    jam_str = wib_now.strftime("%H:%M:%S")

    # Generate unique event hash for Anti-Spam
    raw_hash_src = f"{gunung_slug}:{event_type}:{status_label}:{detail[:100]}:{wib_now.strftime('%Y-%m-%d')}"
    event_hash = hashlib.md5(raw_hash_src.encode('utf-8')).hexdigest()

    if is_event_hash_sent(event_hash):
        print(f"[ANTI-SPAM] Event sudah pernah dikirim ({gunung_name} - {event_type})")
        return True, "Dilewati (Anti-Spam Duplicate)"

    mag_val = str(magnitudo) if magnitudo is not None else "-"
    depth_val = str(kedalaman) if kedalaman is not None else "-"

    message = (
        f"🚨 <b>VOLCANO MONITORING CENTER</b> 🚨\n"
        f"🌋 <b>Gunung :</b> {gunung_name}\n"
        f"📍 <b>Lokasi :</b> {lokasi_str}\n"
        f"📢 <b>Status :</b> {status_label}\n"
        f"🌍 <b>Jenis Kejadian :</b> {event_type}\n"
        f"📏 <b>Magnitudo :</b> {mag_val}\n"
        f"⬇ <b>Kedalaman :</b> {depth_val}\n"
        f"📅 <b>Tanggal :</b> {tanggal_str}\n"
        f"🕒 <b>Jam :</b> {jam_str} WIB\n"
        f"📝 <b>Detail :</b> {detail}\n"
        f"🌐 <b>Sumber :</b> {sumber}"
    )

    success, status_msg = send_telegram_message(message)
    
    if not success:
        print(f"[OFFLINE QUEUE] Koneksi gagal, menyimpan pesan ke antrean: {status_msg}")
        enqueue_telegram_message(message)
        save_alert(gunung_slug, event_type, None, status_label, message, "telegram", "antrean_offline", event_hash)
    else:
        save_alert(gunung_slug, event_type, None, status_label, message, "telegram", "terkirim", event_hash)

    return success, status_msg

def send_hourly_heartbeat_report():
    """
    Mengirimkan Laporan Berkala Aktivitas Gunung Api & Gempa Bumi Indonesia setiap 1 jam sekali ke Telegram.
    """
    wib_now = get_wib_now()
    hari_str = INDONESIAN_DAYS[wib_now.weekday()]
    month_name = INDONESIAN_MONTHS[wib_now.month]
    tanggal_str = f"{hari_str}, {wib_now.day} {month_name} {wib_now.year}"
    jam_str = wib_now.strftime("%H:%M:%S")

    stats = get_dashboard_statistics()
    counts = stats.get("status_counts", {})
    recent_quakes = get_gempa_realtime(3)

    quake_lines = []
    if recent_quakes:
        for q in recent_quakes[:3]:
            quake_lines.append(f"• M {q.get('magnitudo')} - {q.get('lokasi')} ({q.get('jam')} WIB)")
        quake_str = "\n".join(quake_lines)
    else:
        quake_str = "• Tidak ada gempa signifikan dalam 1 jam terakhir."

    message = (
        f"📊 <b>LAPORAN BERKALA VOLCANO MONITORING CENTER (1 JAM)</b>\n\n"
        f"🌋 <b>Ringkasan Status Gunung Api:</b>\n"
        f"• 🟢 Normal (Level I): {counts.get('Normal', 0)} gunung\n"
        f"• 🟡 Waspada (Level II): {counts.get('Waspada', 0)} gunung\n"
        f"• 🟠 Siaga (Level III): {counts.get('Siaga', 0)} gunung\n"
        f"• 🔴 Awas (Level IV): {counts.get('Awas', 0)} gunung\n\n"
        f"🌐 <b>Gempa Bumi Terkini (BMKG/USGS):</b>\n"
        f"{quake_str}\n\n"
        f"📅 <b>Waktu Laporan:</b> {tanggal_str} {jam_str} WIB\n"
        f"🌐 <b>Sumber Data:</b> PVMBG MAGMA ESDM & BMKG TEWS"
    )

    success, status_msg = send_telegram_message(message)
    if not success:
        enqueue_telegram_message(message)
        save_alert("indonesia", "laporan_1jam", None, "Berkala", message, "telegram", "antrean_offline")
    else:
        save_alert("indonesia", "laporan_1jam", None, "Berkala", message, "telegram", "terkirim")

    print(f"[HOURLY REPORT] Laporan berkala 1 jam terkirim: {status_msg}")
    return success, status_msg

def flush_telegram_queue():
    """Mengirim ulang pesan antrean Telegram saat koneksi internet kembali pulih."""
    items = get_pending_telegram_queue(10)
    for item in items:
        item_id = item["id"]
        msg = item["message"]
        attempts = item["attempts"]
        
        if attempts > 5:
            delete_telegram_queue_item(item_id)
            continue
            
        success, _ = send_telegram_message(msg)
        if success:
            print(f"[OFFLINE QUEUE FLUSH] Pesan antrean #{item_id} berhasil terkirim!")
            delete_telegram_queue_item(item_id)
        else:
            increment_telegram_queue_attempts(item_id)
            break
