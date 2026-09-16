import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
}

r = requests.get('https://magma.esdm.go.id/v1/gunung-api/tingkat-aktivitas', headers=headers, timeout=15)
soup = BeautifulSoup(r.text, 'html.parser')

# Find the table
table = soup.find('table')
if table:
    print("=== TABLE FOUND ===")
    # Print out the raw HTML of the table (first 5000 chars)
    table_html = str(table)
    print(table_html[:5000])
    print("...")
    
    # Parse table rows
    print("\n=== TABLE ROWS ===")
    rows = table.find_all('tr')
    for i, tr in enumerate(rows[:30]):
        tds = tr.find_all(['td', 'th'])
        cells = [td.get_text(' ', strip=True) for td in tds]
        # Also check for rowspan/colspan
        attrs = []
        for td in tds:
            a = {}
            if td.get('rowspan'):
                a['rowspan'] = td['rowspan']
            if td.get('colspan'):
                a['colspan'] = td['colspan']
            attrs.append(a)
        print(f"Row {i}: {cells} attrs={attrs}")
        
        # Check for links within the row
        links = tr.find_all('a')
        for link in links:
            href = link.get('href', '')
            if 'gunung' in href.lower() or 'laporan' in link.get_text(strip=True).lower():
                print(f"  -> Link: {link.get_text(strip=True)} href={href}")
else:
    print("NO TABLE FOUND")
    
# Also check for div.table-responsive
print("\n=== Looking for table-responsive ===")
tr = soup.find('div', class_='table-responsive')
if tr:
    print("Found table-responsive")
    inner_table = tr.find('table')
    if inner_table:
        print(f"Table has {len(inner_table.find_all('tr'))} rows")
        # Print first few rows as HTML
        for row in inner_table.find_all('tr')[:5]:
            print(str(row)[:500])
            print()
