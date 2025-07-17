import requests
from bs4 import BeautifulSoup

def scrape_tides_maree_info(port_slug, max_items=6):
    url = f"https://maree.info/{port_slug}"
    r = requests.get(url)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # Sélection du tableau des marées hautes/basses
    # (la structure HTML peut légèrement varier suivant le port)
    table = soup.find('table')
    rows = table.select('tr')[1:]  # ignorer l'en-tête

    tides = []
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 2:
            time = cols[0].get_text(strip=True)
            height = cols[1].get_text(strip=True)
            tides.append({'time': time, 'height': height})
        if len(tides) >= max_items:
            break

    return tides

if __name__ == "__main__":
    port = "136"  # Arcachon – Jetée d'Eyrac (cf. maree.info/136) :contentReference[oaicite:1]{index=1}
    data = scrape_tides_maree_info(port)
    print("Prochaines marées (arcachon) :")
    for tide in data:
        print(f"{tide['time']} → {tide['height']}")
