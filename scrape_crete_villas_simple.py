import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import random

def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

def extract_email_from_website(url):
    try:
        print(f"\nControleren website: {url}")
        response = requests.get(url, headers=get_headers(), timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Zoek emails in de tekst
        email_pattern = r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}'
        emails = re.findall(email_pattern, response.text)
        valid_emails = [email for email in emails if is_valid_email(email)]
        
        # Check contact pagina's als geen email gevonden
        if not valid_emails:
            contact_paths = ['contact', 'contact-us', 'about', 'about-us']
            base_url = '/'.join(url.split('/')[:3])
            
            for path in contact_paths:
                try:
                    contact_url = f"{base_url}/{path}"
                    print(f"Controleren: {contact_url}")
                    response = requests.get(contact_url, headers=get_headers(), timeout=10)
                    emails = re.findall(email_pattern, response.text)
                    valid_emails.extend([email for email in emails if is_valid_email(email)])
                except:
                    continue
        
        # Filter en kies beste email
        if valid_emails:
            # Prefereer info@ emails
            info_emails = [e for e in valid_emails if e.startswith('info@')]
            if info_emails:
                return info_emails[0]
            # Anders, neem eerste geldige email
            return valid_emails[0]
        
        return None
        
    except Exception as e:
        print(f"Fout bij website {url}: {str(e)}")
        return None

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    invalid_patterns = ['example.com', 'test.com', 'domain.com']
    
    if not isinstance(email, str):
        return False
    
    return (re.match(pattern, email) and 
            not any(p in email.lower() for p in invalid_patterns))

def scrape_villas():
    # Lijst met bekende villa websites in Kreta
    villa_urls = [
        'https://www.luxuryvillascrete.com',
        'https://www.cretevillas.gr',
        'https://www.cretanvillas.com',
        'https://www.villaincrete.com',
        'https://www.cretanvillas.gr',
        'https://www.cretevillas4u.com',
        'https://www.cretanvilla.com',
        'https://www.villasincretegreece.com',
        # Voeg hier meer URLs toe
    ]
    
    villas_data = []
    
    for url in villa_urls:
        try:
            print(f"\nVerwerken van: {url}")
            response = requests.get(url, headers=get_headers(), timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Zoek villa listings
            villa_elements = soup.find_all(['div', 'article'], class_=lambda x: x and ('villa' in x.lower() or 'property' in x.lower()))
            
            for element in villa_elements:
                try:
                    # Probeer villa naam te vinden
                    name = element.find(['h1', 'h2', 'h3', 'h4'])
                    if name:
                        name = name.text.strip()
                    else:
                        continue
                    
                    # Zoek link naar villa pagina
                    villa_link = element.find('a')
                    if villa_link:
                        villa_url = villa_link.get('href')
                        if not villa_url.startswith('http'):
                            villa_url = url + villa_url
                        
                        print(f"\nGevonden villa: {name}")
                        print(f"URL: {villa_url}")
                        
                        # Zoek email
                        email = extract_email_from_website(villa_url)
                        
                        if email:
                            print(f"✓ Email gevonden: {email}")
                            villas_data.append({
                                'name': name,
                                'website': villa_url,
                                'email': email
                            })
                        else:
                            print("✗ Geen email gevonden")
                    
                except Exception as e:
                    print(f"Fout bij villa element: {str(e)}")
                    continue
                
                # Wacht tussen requests
                time.sleep(random.uniform(2, 4))
            
        except Exception as e:
            print(f"Fout bij URL {url}: {str(e)}")
            continue
        
        # Wacht tussen websites
        time.sleep(random.uniform(5, 8))
    
    return villas_data

try:
    print("Start met scrapen van villa websites...")
    villas_data = scrape_villas()
    
    if villas_data:
        # Maak DataFrame en sla op
        df = pd.DataFrame(villas_data)
        output_file = 'crete_villas_data.csv'
        df.to_csv(output_file, index=False)
        
        print(f"\nScraping voltooid!")
        print(f"Aantal gevonden villa's: {len(villas_data)}")
        print(f"Data opgeslagen in: {output_file}")
        
        # Toon voorbeeld
        print("\nVoorbeeld van gevonden data:")
        print(df.head())
    else:
        print("\nGeen villa's gevonden.")

except Exception as e:
    print(f"Fout: {str(e)}") 