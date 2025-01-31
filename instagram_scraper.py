import time
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth

def configure_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    service = Service('/usr/local/bin/chromedriver')  # Pas dit pad aan als nodig
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def search_and_scrape(driver, query):
    """Search for a query on Instagram and scrape profile data."""
    try:
        print(f"[INFO] Starting scrape for: {query}")
        
        # Klik op het zoekicoon
        search_icon = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//svg[@aria-label='Zoeken']"))
        )
        search_icon.click()
        print("[DEBUG] Zoekicoon aangeklikt.")

        # Zoekveld invullen
        input_search = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='Zoeken']"))
        )
        input_search.send_keys(query)
        time.sleep(2)

        # Druk op 'Enter' om de zoekresultaten te verkrijgen
        input_search.send_keys(Keys.RETURN)
        time.sleep(2)
        input_search.send_keys(Keys.RETURN)  # Bevestig zoeken
        print(f"[INFO] Searching for '{query}'...")

        # Zoekresultaten ophalen
        time.sleep(5)

        # Profielen scrapen
        results = driver.find_elements(By.XPATH, "//div[@class='x9f619']//a")
        print(f"[DEBUG] Aantal gevonden resultaten: {len(results)}")
        
        profiles = []
        for result in results:
            profile_url = result.get_attribute("href")
            print(f"[DEBUG] Profiel gevonden: {profile_url}")
            if profile_url:
                profiles.append(profile_url)

        return profiles

    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")
        return []

def save_profiles_to_csv(profiles, filename="profiles.csv"):
    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Profile URL"])
            for profile in profiles:
                writer.writerow([profile])
        print(f"[INFO] Profiles saved to {filename}.")
    except Exception as e:
        print(f"[ERROR] Could not save profiles to CSV: {e}")

def main():
    query = "villa crete"  # Zoekterm aanpassen indien nodig
    print("[INFO] Navigate to Instagram homepage and log in manually.")
    
    driver = configure_driver()
    driver.get("https://www.instagram.com")
    
    # Log in handmatig
    input("Log in manually and press ENTER once logged in...")
    
    # Zoek en scrape profielen
    profiles = search_and_scrape(driver, query)
    
    # Profielen opslaan in CSV
    if profiles:
        save_profiles_to_csv(profiles)
    else:
        print("[INFO] Geen profielen gevonden.")

    # Sluit de browser
    driver.quit()
    print("[INFO] Browser closed.")

if __name__ == "__main__":
    main()