from playwright.sync_api import sync_playwright
import pandas as pd
import re
import time
import random

def handle_cookies(page):
    try:
        # Wacht op de cookie prompt en klik 'Accept all'
        print("Wachten op cookie prompt...")
        accept_button = page.wait_for_selector('button:has-text("Accept all")', timeout=10000)
        if accept_button:
            accept_button.click()
            print("✓ Cookies geaccepteerd")
            time.sleep(2)  # Wacht tot de prompt verdwijnt
    except Exception as e:
        print(f"Geen cookie prompt gevonden of al geaccepteerd: {str(e)}")

def scrape_google_maps(playwright, num_scrolls=10):
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    )
    page = context.new_page()
    
    try:
        # Ga eerst naar Google voor de cookie prompt
        print("Navigeren naar Google...")
        page.goto("https://www.google.com")
        handle_cookies(page)
        
        # Dan naar Google Maps
        print("\nNavigeren naar Google Maps...")
        search_url = "https://www.google.com/maps/search/luxury+villas+in+crete+greece"
        page.goto(search_url)
        time.sleep(5)  # Wacht tot de pagina volledig geladen is
        
        # Wacht tot de resultaten zichtbaar zijn
        print("Wachten op zoekresultaten...")
        page.wait_for_selector("div[role='article']", timeout=30000)
        
        print("\nStart met scrapen...")
        villas_data = []
        
        # Scroll en verzamel resultaten
        for i in range(num_scrolls):
            print(f"\nScroll {i + 1}/{num_scrolls}")
            
            # Verzamel zichtbare resultaten
            listings = page.query_selector_all("div[role='article']")
            print(f"Gevonden listings: {len(listings)}")
            
            for idx, listing in enumerate(listings):
                try:
                    # Klik op listing voor details
                    listing.click()
                    time.sleep(2)
                    
                    # Haal naam op
                    name_element = page.query_selector("h1")
                    if not name_element:
                        continue
                    name = name_element.inner_text()
                    
                    # Haal website op
                    website = None
                    website_link = page.query_selector("a[data-item-id='authority']")
                    if website_link:
                        website = website_link.get_attribute("href")
                    
                    if website:
                        print(f"\nGevonden: {name}")
                        print(f"Website: {website}")
                        
                        # Zoek email op website
                        email = extract_email_from_website(page, website)
                        
                        if email:
                            print(f"✓ Email gevonden: {email}")
                            villas_data.append({
                                'name': name,
                                'website': website,
                                'email': email
                            })
                        else:
                            print("✗ Geen email gevonden")
                    
                except Exception as e:
                    print(f"Fout bij listing: {str(e)}")
                    continue
            
            # Scroll naar beneden
            try:
                page.evaluate("""
                    document.querySelector('div[role="feed"]').scrollBy(0, 1000);
                """)
                time.sleep(3)
            except Exception as e:
                print(f"Scroll fout: {str(e)}")
        
        return villas_data
        
    finally:
        browser.close()

def extract_email_from_website(page, url):
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        
        content = page.content()
        email_pattern = r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}'
        emails = re.findall(email_pattern, content)
        valid_emails = [email for email in emails if is_valid_email(email)]
        
        if not valid_emails:
            contact_paths = ['contact', 'contact-us', 'about', 'about-us']
            base_url = '/'.join(url.split('/')[:3])
            
            for path in contact_paths:
                try:
                    contact_url = f"{base_url}/{path}"
                    page.goto(contact_url, wait_until="networkidle", timeout=15000)
                    content = page.content()
                    emails = re.findall(email_pattern, content)
                    valid_emails.extend([email for email in emails if is_valid_email(email)])
                except:
                    continue
        
        if valid_emails:
            info_emails = [e for e in valid_emails if e.startswith('info@')]
            return info_emails[0] if info_emails else valid_emails[0]
            
        return None
        
    except Exception as e:
        print(f"Fout bij website {url}: {str(e)}")
        return None

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    invalid_patterns = ['example.com', 'test.com', 'domain.com']
    return (re.match(pattern, email) and 
            not any(p in email.lower() for p in invalid_patterns))

try:
    with sync_playwright() as playwright:
        villas_data = scrape_google_maps(playwright)
        
        if villas_data:
            df = pd.DataFrame(villas_data)
            output_file = 'crete_villas_data.csv'
            df.to_csv(output_file, index=False)
            
            print(f"\nScraping voltooid!")
            print(f"Aantal gevonden villa's: {len(villas_data)}")
            print(f"Data opgeslagen in: {output_file}")
            print("\nVoorbeeld van gevonden data:")
            print(df.head())
        else:
            print("\nGeen villa's gevonden.")

except Exception as e:
    print(f"Fout: {str(e)}") 