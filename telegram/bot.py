# telegram/bot.py
"""
Modul Integrasi Bot Telegram (HTTP API & python-telegram-bot)
"""
import os
import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8967073652:AAFHnr--UsEny4JfoFRsdRQ5k_fX9rdO2PY")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "6274528706")
TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

def send_telegram_message(message):
    """Mengirim pesan ke Telegram Chat ID yang telah dikonfigurasi."""
    if not TELEGRAM_ENABLED:
        return False, "Telegram tidak dikonfigurasi"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True, "Terkirim"
    except requests.exceptions.RequestException as e:
        return False, f"Gagal mengirim ke Telegram: {e}"

def is_telegram_configured():
    return TELEGRAM_ENABLED
