# utils/datetime_utils.py
"""
Utility tanggal dan waktu zona WIB (Waktu Indonesia Barat).
"""
from datetime import datetime, timezone, timedelta

WIB_OFFSET = timedelta(hours=7)
WIB_TZ = timezone(WIB_OFFSET, name="WIB")

INDONESIAN_DAYS = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
INDONESIAN_MONTHS = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]

def get_wib_now():
    """Mengembalikan datetime terkini dalam WIB."""
    return datetime.now(timezone.utc).astimezone(WIB_TZ)

def format_wib_full(dt=None):
    """Format: Hari, DD Bulan YYYY HH:MM:SS WIB"""
    if dt is None:
        dt = get_wib_now()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc).astimezone(WIB_TZ)
    else:
        dt = dt.astimezone(WIB_TZ)
    
    day_name = INDONESIAN_DAYS[dt.weekday()]
    month_name = INDONESIAN_MONTHS[dt.month]
    return f"{day_name}, {dt.day} {month_name} {dt.year} {dt.strftime('%H:%M:%S')} WIB"

def format_wib_date_short(dt=None):
    """Format: YYYY-MM-DD"""
    if dt is None:
        dt = get_wib_now()
    return dt.strftime("%Y-%m-%d")

def format_wib_time_short(dt=None):
    """Format: HH:MM WIB"""
    if dt is None:
        dt = get_wib_now()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc).astimezone(WIB_TZ)
    else:
        dt = dt.astimezone(WIB_TZ)
    return f"{dt.strftime('%H:%M')} WIB"
