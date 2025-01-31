from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time
import random

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    return webdriver.Chrome(options=chrome_options)

def scrape_listings(url, num_pages=5):
    driver = setup_driver()
    listings = []
    
    try:
        print("Start met scrapen...")
        
        for page in range(num_pages):
            print(f"\nBezig met pagina {page + 1}/{num_pages}")
            
            # Laad de pagina
            current_url = url if page == 0 else f"{url}&items_offset={page * 18}"
            driver.get(current_url)
            
            # Wacht tot de listings geladen zijn
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[itemprop='itemListElement']"))
            )
            
            # Scroll om alle content te laden
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Vind alle listing elementen
            listing_elements = driver.find_elements(By.CSS_SELECTOR, "div[itemprop='itemListElement']")
            
            page_listings = []
            for element in listing_elements:
                try:
                    # Haal naam op
                    name = element.find_element(By.CSS_SELECTOR, "div[data-testid='listing-card-title']").text
                    
                    # Haal link op
                    link = element.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                    
                    # Haal prijs op
                    price = element.find_element(By.CSS_SELECTOR, "span[data-testid='price-and-discounted-price']").text
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
        driver.quit()
    
    return listings

try:
    # Installeer eerst Chrome WebDriver als je die nog niet hebt
    print("Controleer of je Chrome WebDriver hebt geïnstalleerd!")
    
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