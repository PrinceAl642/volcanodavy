import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
url = 'https://magma.esdm.go.id/v1/gunung-api/laporan/320476?signature=21039514f5b19db57a7d5973053dfa42785634b5e466901eb26abb6970dcf559'
r = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(r.text, 'html.parser')

print(f"Status: {r.status_code}")

for el in soup.find_all(['h4', 'div', 'p']):
    t = el.get_text(' ', strip=True)
    if 'Gempa' in t or 'Klimatologi' in t or 'Visual' in t or 'Pengamatan' in t or 'Keterangan' in t:
        cls = el.get('class', '')
        print(f"<{el.name} class='{cls}'>: {t[:300]}")
