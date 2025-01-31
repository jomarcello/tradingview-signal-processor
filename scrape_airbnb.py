import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import random

def get_airbnb_data(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.airbnb.nl/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1'
    }

    listings = []
    
    try:
        print(f"Ophalen van pagina: {url}")
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Zoek naar JSON data in de pagina
        scripts = soup.find_all('script', {'type': 'application/json'})
        for script in scripts:
            if 'data-state' in script.attrs:
                try:
                    data = json.loads(script.string)
                    if 'niobeMinimalClientData' in data:
                        listings_data = data['niobeMinimalClientData'][0][1]['data']['presentation']['explore']['sections']['sections']
                        
                        for section in listings_data:
                            if 'sections' in section:
                                for subsection in section['sections']:
                                    if 'items' in subsection:
                                        for item in subsection['items']:
                                            if 'listing' in item:
                                                listing = item['listing']
                                                listings.append({
                                                    'name': listing.get('name', ''),
                                                    'url': f"https://www.airbnb.nl/rooms/{listing.get('id', '')}",
                                                    'price_per_night': listing.get('price', {}).get('price', {}).get('amount', '')
                                                })
                except:
                    continue
        
        return listings
    
    except Exception as e:
        print(f"Fout bij ophalen data: {str(e)}")
        return []

def scrape_multiple_pages(base_url, num_pages=5):
    all_listings = []
    current_url = base_url
    
    for page in range(num_pages):
        print(f"\nBezig met pagina {page + 1}/{num_pages}")
        
        # Haal data op van huidige pagina
        page_listings = get_airbnb_data(current_url)
        if page_listings:
            all_listings.extend(page_listings)
            print(f"✓ {len(page_listings)} listings gevonden op deze pagina")
        else:
            print("✗ Geen listings gevonden op deze pagina")
            break
            
        # Wacht tussen requests
        time.sleep(random.uniform(2, 4))
        
        # Update URL voor volgende pagina
        # Note: Dit moet mogelijk aangepast worden aan Airbnb's paginering systeem
        if 'cursor=' in current_url:
            current_url = current_url.split('cursor=')[0]
        current_url += f"&items_offset={(page + 1) * 18}"
    
    return all_listings

try:
    base_url = "https://www.airbnb.nl/s/Crete--Greece/homes?tab_id=home_tab&refinement_paths%5B%5D=%2Fhomes&flexible_trip_lengths%5B%5D=one_week&monthly_start_date=2025-01-01&monthly_length=3&monthly_end_date=2025-04-01&price_filter_input_type=0&channel=EXPLORE&query=Crete%2C%20Greece&place_id=ChIJg7ePxdcDmxQRmJlhKBGUMrs&date_picker_type=calendar&checkin=2025-01-01&checkout=2025-01-09&source=structured_search_input_header&search_type=filter_change&adults=2&search_mode=regular_search&price_filter_num_nights=8&selected_filter_order%5B%5D=price_min%3A303&price_min=303"
    
    print("Start met scrapen van Airbnb listings...")
    listings = scrape_multiple_pages(base_url)
    
    if listings:
        # Maak DataFrame en sla op als CSV
        df = pd.DataFrame(listings)
        output_file = 'crete_villas_airbnb.csv'
        df.to_csv(output_file, index=False)
        
        print(f"\nScraping voltooid!")
        print(f"Aantal gevonden listings: {len(listings)}")
        print(f"Data opgeslagen in: {output_file}")
        
        # Toon eerste paar resultaten
        print("\nVoorbeeld van gevonden data:")
        print(df.head())
    else:
        print("\nGeen listings gevonden. Mogelijk zijn er problemen met de toegang tot Airbnb.")

except Exception as e:
    print(f"Fout tijdens scraping: {str(e)}") 