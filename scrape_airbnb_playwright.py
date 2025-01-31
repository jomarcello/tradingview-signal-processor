from playwright.sync_api import sync_playwright
import pandas as pd
import time
import random

def scrape_listings(url, num_pages=5):
    listings = []
    
    with sync_playwright() as p:
        # Start browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        try:
            print("Start met scrapen...")
            
            for page_num in range(num_pages):
                print(f"\nBezig met pagina {page_num + 1}/{num_pages}")
                
                # Laad de pagina
                current_url = url if page_num == 0 else f"{url}&items_offset={page_num * 18}"
                page.goto(current_url, wait_until="networkidle")
                
                # Wacht tot listings geladen zijn
                page.wait_for_selector("div[itemprop='itemListElement']", timeout=10000)
                
                # Scroll om alle content te laden
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                
                # Vind alle listings
                listing_elements = page.query_selector_all("div[itemprop='itemListElement']")
                
                page_listings = []
                for element in listing_elements:
                    try:
                        # Haal naam op
                        name = element.query_selector("div[data-testid='listing-card-title']").inner_text()
                        
                        # Haal link op
                        link = element.query_selector("a").get_attribute("href")
                        if not link.startswith("http"):
                            link = "https://www.airbnb.nl" + link
                        
                        # Haal prijs op
                        price_element = element.query_selector("span[data-testid='price-and-discounted-price']")
                        price = price_element.inner_text() if price_element else ""
                        price = price.split('€')[1].split(' ')[0] if '€' in price else ''
                        
                        page_listings.append({
                            'name': name,
                            'url': link,
                            'price_per_night': price
                        })
                        
                    except Exception as e:
                        print(f"Fout bij listing: {str(e)}")
                        continue
                
                listings.extend(page_listings)
                print(f"✓ {len(page_listings)} listings gevonden op deze pagina")
                
                # Wacht tussen pagina's
                time.sleep(random.uniform(2, 4))
        
        except Exception as e:
            print(f"Fout tijdens scrapen: {str(e)}")
        
        finally:
            browser.close()
    
    return listings

try:
    # Installeer eerst Playwright als je die nog niet hebt
    print("Controleer of je Playwright hebt geïnstalleerd!")
    
    base_url = "https://www.airbnb.nl/s/Crete--Greece/homes?tab_id=home_tab&refinement_paths%5B%5D=%2Fhomes&flexible_trip_lengths%5B%5D=one_week&monthly_start_date=2025-01-01&monthly_length=3&monthly_end_date=2025-04-01&price_filter_input_type=0&channel=EXPLORE&query=Crete%2C%20Greece&place_id=ChIJg7ePxdcDmxQRmJlhKBGUMrs&date_picker_type=calendar&checkin=2025-01-01&checkout=2025-01-09&source=structured_search_input_header&search_type=filter_change&adults=2&search_mode=regular_search&price_filter_num_nights=8&selected_filter_order%5B%5D=price_min%3A303&price_min=303"
    
    listings = scrape_listings(base_url)
    
    if listings:
        # Maak DataFrame en sla op
        df = pd.DataFrame(listings)
        output_file = 'crete_villas_airbnb.csv'
        df.to_csv(output_file, index=False)
        
        print(f"\nScraping voltooid!")
        print(f"Aantal gevonden listings: {len(listings)}")
        print(f"Data opgeslagen in: {output_file}")
        
        # Toon voorbeeld
        print("\nVoorbeeld van gevonden data:")
        print(df.head())
    else:
        print("\nGeen listings gevonden.")

except Exception as e:
    print(f"Fout: {str(e)}") 