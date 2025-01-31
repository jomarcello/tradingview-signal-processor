import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import random

def extract_email_from_url(url, timeout=30):
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url.strip()
        
        print(f"\nBezoeken van: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        # Probeer eerst de hoofdpagina
        response = requests.get(url, headers=headers, timeout=timeout)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Verschillende methoden om emails te vinden
        emails = set()
        
        # 1. Zoek in de tekst
        text_content = soup.get_text()
        email_pattern = r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}'
        found_emails = re.findall(email_pattern, text_content)
        emails.update(found_emails)
        
        # 2. Zoek in mailto links
        mailto_links = soup.select('a[href^="mailto:"]')
        for link in mailto_links:
            email = link['href'].replace('mailto:', '').strip()
            emails.add(email)
        
        # 3. Zoek in contact pagina als die bestaat
        contact_urls = [
            url + '/contact',
            url + '/contact-us',
            url + '/contact.html',
            url + '/about-us',
            url + '/about'
        ]
        
        for contact_url in contact_urls:
            try:
                contact_response = requests.get(contact_url, headers=headers, timeout=timeout)
                contact_soup = BeautifulSoup(contact_response.text, 'html.parser')
                contact_emails = re.findall(email_pattern, contact_soup.get_text())
                emails.update(contact_emails)
                time.sleep(2)  # Wacht tussen requests
            except:
                continue
        
        # Filter en valideer gevonden emails
        valid_emails = []
        for email in emails:
            if is_valid_email(email):
                valid_emails.append(email)
        
        if valid_emails:
            print(f"Gevonden email(s): {valid_emails[0]}")
            return valid_emails[0]
        else:
            print("Geen geldig emailadres gevonden")
            return None
            
    except Exception as e:
        print(f"Fout bij URL {url}: {str(e)}")
        return None

def is_valid_email(email):
    # Basis email patroon
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Z|a-z]{2,}$'
    
    # Check basis formaat
    if not re.match(pattern, str(email)):
        return False
    
    # Check voor ongeldige patronen
    invalid_patterns = [
        'example.com',
        'test.com',
        'domain.com',
        '..',
        ' '
    ]
    
    return not any(pattern in str(email).lower() for pattern in invalid_patterns)

try:
    print("Bezig met inlezen van het bestand...")
    df = pd.read_excel('dataset_email-extractor_hersteld.xlsx')
    
    print("\nControleren op lege email velden...")
    empty_rows = df[df['Email'].isna() | (df['Email'] == '')].index
    total_empty = len(empty_rows)
    
    print(f"Aantal lege email velden gevonden: {total_empty}")
    
    for idx in empty_rows:
        url = df.loc[idx, 'Website']
        print(f"\nVerwerken van rij {idx + 1}/{len(df)}")
        
        email = extract_email_from_url(url)
        if email:
            df.at[idx, 'Email'] = email
            # Direct opslaan na elke vondst
            df.to_excel('dataset_email-extractor_final.xlsx', index=False)
        
        # Random wachttijd tussen 3 en 7 seconden
        time.sleep(random.uniform(3, 7))
    
    print("\nBezig met opslaan...")
    df.to_excel('dataset_email-extractor_final.xlsx', index=False)
    
    # Statistieken
    filled_emails = df['Email'].notna().sum()
    still_empty = len(df) - filled_emails
    
    print(f"\nScraping voltooid!")
    print(f"Totaal aantal rijen: {len(df)}")
    print(f"Aantal gevulde emails: {filled_emails}")
    print(f"Aantal nog leeg: {still_empty}")
    print("\nHet nieuwe bestand is opgeslagen als 'dataset_email-extractor_final.xlsx'")

except Exception as e:
    print(f"Er is een fout opgetreden: {str(e)}")

print("\nScript voltooid.") 