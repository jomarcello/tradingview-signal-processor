import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import random

def extract_email_from_url(url, timeout=20):
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url.strip()
        
        print(f"\nBezoeken van: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        response = requests.get(url, headers=headers, timeout=timeout)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        emails = set()
        
        # 1. Zoek in tekst
        text_content = soup.get_text()
        email_pattern = r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}'
        found_emails = re.findall(email_pattern, text_content)
        emails.update(found_emails)
        
        # 2. Zoek in mailto links
        mailto_links = soup.select('a[href^="mailto:"]')
        for link in mailto_links:
            email = link['href'].replace('mailto:', '').strip()
            emails.add(email)
        
        # 3. Check contact pagina
        contact_paths = ['contact', 'contact-us', 'about', 'about-us']
        base_url = '/'.join(url.split('/')[:3])
        
        for path in contact_paths:
            try:
                contact_url = f"{base_url}/{path}"
                contact_response = requests.get(contact_url, headers=headers, timeout=timeout)
                contact_soup = BeautifulSoup(contact_response.text, 'html.parser')
                contact_emails = re.findall(email_pattern, contact_soup.get_text())
                emails.update(contact_emails)
                time.sleep(1)
            except:
                continue
        
        valid_emails = []
        for email in emails:
            if is_valid_email(email):
                valid_emails.append(email)
        
        if valid_emails:
            # Prefereer info@ emails
            info_emails = [e for e in valid_emails if e.startswith('info@')]
            if info_emails:
                return info_emails[0]
            return valid_emails[0]
            
        return None
            
    except Exception as e:
        print(f"Fout bij URL {url}: {str(e)}")
        return None

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Z|a-z]{2,}$'
    
    if not re.match(pattern, str(email)):
        return False
    
    invalid_patterns = [
        'example.com',
        'test.com',
        'domain.com',
        '..',
        ' '
    ]
    
    return not any(pattern in str(email).lower() for pattern in invalid_patterns)

def extract_villa_name(url):
    try:
        clean_url = url.lower()
        for prefix in ['http://', 'https://', 'www.']:
            if clean_url.startswith(prefix):
                clean_url = clean_url[len(prefix):]
        
        parts = re.split('[/.]', clean_url)
        
        for part in parts:
            if 'villa' in part or 'mykonos' in part:
                words = part.split('-')
                return ' '.join(word.capitalize() for word in words)
        
        return parts[0].capitalize()
    except:
        return ''

try:
    print("Bezig met inlezen van het bestand...")
    # Lees het bestand en gebruik de eerste kolom als websites
    df = pd.read_excel('dataset_email-extractor_met_emails.xlsx')
    
    # Controleer de kolomnamen
    print("\nBeschikbare kolommen:")
    print(df.columns.tolist())
    
    # Gebruik de eerste kolom als website kolom
    websites = df.iloc[:, 0]  # Eerste kolom
    
    # Maak nieuwe dataframe met gewenste kolommen
    new_data = []
    
    print(f"\nVerwerken van {len(websites)} websites...")
    
    for idx, url in enumerate(websites):
        print(f"\nVerwerken {idx + 1}/{len(websites)}: {url}")
        
        # Haal email op
        email = extract_email_from_url(url)
        
        if email:
            # Haal villa naam op
            villa_name = extract_villa_name(url)
            
            # Voeg toe aan nieuwe data
            new_data.append({
                'Villa Name': villa_name,
                'Website': url,
                'Email': email
            })
            
            print(f"✓ Gevonden: {villa_name} - {email}")
        else:
            print("✗ Geen email gevonden - rij wordt overgeslagen")
        
        # Wacht tussen requests
        time.sleep(random.uniform(2, 4))
    
    # Maak nieuwe dataframe
    new_df = pd.DataFrame(new_data)
    
    # Sla op
    output_file = 'villa_data_compleet.xlsx'
    new_df.to_excel(output_file, index=False)
    
    print(f"\nVerwerking voltooid!")
    print(f"Aantal verwerkte websites: {len(websites)}")
    print(f"Aantal gevonden emails: {len(new_data)}")
    print(f"Resultaat opgeslagen in '{output_file}'")

except FileNotFoundError:
    print("Fout: Kan het bronbestand niet vinden")
except Exception as e:
    print(f"Fout: {str(e)}")
    print("\nProbeer de kolomnamen te controleren in het bronbestand")