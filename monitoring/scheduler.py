# monitoring/scheduler.py
"""
Pengelola Tugas Latar Belakang (Scheduler 24/7 Server-Side Daemon)
- Polling Realtime API: 10 detik (Status Gunung & Gempa BMKG/USGS)
- Laporan Berkala Telegram: 1 Jam sekali (3600 detik)
- Polling Cuaca Open Meteo: 3 menit
- Polling CCTV: 5 menit
- Flush Antrean Telegram Offline: 15 detik
Tetap berjalan 24 jam nonstop meskipun peramban (browser) ditutup.
"""
import time
import threading
from monitoring.magma_scraper import fetch_all_status
from monitoring.cctv_scraper import fetch_cctv_for
from monitoring.bmkg_earthquake import fetch_realtime_earthquakes
from monitoring.weather import fetch_weather_all
from telegram.notifier import flush_telegram_queue, send_hourly_heartbeat_report
from utils.level_mapper import GUNUNG_TARGET

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False

_status_lock = threading.Lock()
_cctv_lock = threading.Lock()
_gempa_lock = threading.Lock()
_weather_lock = threading.Lock()

def task_poll_status():
    with _status_lock:
        try:
            fetch_all_status()
        except Exception as e:
            print(f"[SCHEDULER WARN] Error poll status: {e}")

def task_poll_cctv():
    with _cctv_lock:
        try:
            for slug in GUNUNG_TARGET:
                fetch_cctv_for(slug)
        except Exception as e:
            print(f"[SCHEDULER WARN] Error poll cctv: {e}")

def task_poll_gempa():
    with _gempa_lock:
        try:
            fetch_realtime_earthquakes()
        except Exception as e:
            print(f"[SCHEDULER WARN] Error poll gempa: {e}")

def task_poll_weather():
    with _weather_lock:
        try:
            fetch_weather_all()
        except Exception as e:
            print(f"[SCHEDULER WARN] Error poll weather: {e}")

def task_hourly_telegram_report():
    try:
        send_hourly_heartbeat_report()
    except Exception as e:
        print(f"[SCHEDULER WARN] Error hourly report: {e}")

def task_flush_queue():
    try:
        flush_telegram_queue()
    except Exception as e:
        print(f"[SCHEDULER WARN] Error flush telegram queue: {e}")

def _thread_poll_loop(func, interval_seconds):
    while True:
        try:
            func()
        except Exception as e:
            print(f"[THREAD WARN] Error execution: {e}")
        time.sleep(interval_seconds)

def start_monitoring_scheduler():
    """Memulai scheduler background daemon 24/7."""
    threading.Thread(target=task_poll_status, daemon=True).start()
    threading.Thread(target=task_poll_gempa, daemon=True).start()
    threading.Thread(target=task_poll_weather, daemon=True).start()

    if HAS_APSCHEDULER:
        try:
            scheduler = BackgroundScheduler(daemon=True)
            scheduler.add_job(task_poll_status, 'interval', seconds=10, id="job_magma_status")
            scheduler.add_job(task_poll_gempa, 'interval', seconds=10, id="job_bmkg_gempa")
            scheduler.add_job(task_poll_weather, 'interval', seconds=180, id="job_weather")
            scheduler.add_job(task_poll_cctv, 'interval', seconds=300, id="job_cctv")
            scheduler.add_job(task_flush_queue, 'interval', seconds=15, id="job_telegram_queue")
            scheduler.add_job(task_hourly_telegram_report, 'interval', seconds=3600, id="job_hourly_report")
            scheduler.start()
            print("[SCHEDULER 24/7] APScheduler aktif (Realtime: 10s, Telegram Report: 1 Jam)")
            return scheduler
        except Exception as e:
            print(f"[SCHEDULER WARN] APScheduler failed: {e}")

    threading.Thread(target=_thread_poll_loop, args=(task_poll_status, 10), daemon=True).start()
    threading.Thread(target=_thread_poll_loop, args=(task_poll_gempa, 10), daemon=True).start()
    threading.Thread(target=_thread_poll_loop, args=(task_poll_weather, 180), daemon=True).start()
    threading.Thread(target=_thread_poll_loop, args=(task_poll_cctv, 300), daemon=True).start()
    threading.Thread(target=_thread_poll_loop, args=(task_flush_queue, 15), daemon=True).start()
    threading.Thread(target=_thread_poll_loop, args=(task_hourly_telegram_report, 3600), daemon=True).start()
    print("[SCHEDULER 24/7] Thread Background Loop aktif (10s Realtime Polling, 1 Jam Report Telegram)")
    return None
