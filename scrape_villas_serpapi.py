from serpapi import GoogleSearch
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
        'Accept-Language': 'en-US,en;q=0.5'
    }

def search_villas():
    params = {
        "api_key": "a2a4572bfa3691a56a3514934922e3a9421dfdd1f774ef89c3cc3970ae2265fa",
        "engine": "google",
        "q": "villa rental crete contact email",
        "google_domain": "google.com",
        "gl": "gr",
        "hl": "en",
        "num": 100,
        "location": "Crete, Greece"
    }

    try:
        print("Uitvoeren Google zoekopdracht via SerpApi...")
        search = GoogleSearch(params)
        results = search.get_dict()
        
        websites = []
        
        if "organic_results" in results:
            for result in results["organic_results"]:
                if "link" in result and not any(domain in result["link"].lower() for domain in ['booking.com', 'airbnb.com', 'tripadvisor.com']):
                    websites.append({
                        'title': result.get('title', ''),
                        'url': result['link']
                    })
        
        return websites
        
    except Exception as e:
        print(f"Zoekfout: {str(e)}")
        return []

def extract_email_from_website(url):
    try:
        print(f"\nControleren website: {url}")
        response = requests.get(url, headers=get_headers(), timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        email_pattern = r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}'
        emails = re.findall(email_pattern, response.text)
        valid_emails = [email for email in emails if is_valid_email(email)]
        
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
    return (re.match(pattern, str(email)) and 
            not any(p in str(email).lower() for p in invalid_patterns))

try:
    print("Start met zoeken van villa websites...")
    websites = search_villas()
    
    if websites:
        print(f"\nGevonden websites: {len(websites)}")
        villas_data = []
        
        for site in websites:
            try:
                email = extract_email_from_website(site['url'])
                
                if email:
                    print(f"\n✓ Gevonden voor {site['title']}:")
                    print(f"Website: {site['url']}")
                    print(f"Email: {email}")
                    
                    villas_data.append({
                        'name': site['title'],
                        'website': site['url'],
                        'email': email
                    })
                else:
                    print(f"\n✗ Geen email gevonden voor: {site['title']}")
                
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                print(f"Fout bij website {site['url']}: {str(e)}")
                continue
        
        if villas_data:
            df = pd.DataFrame(villas_data)
            output_file = 'crete_villas_data.csv'
            df.to_csv(output_file, index=False)
            
            print(f"\nScraping voltooid!")
            print(f"Aantal gevonden villa's met email: {len(villas_data)}")
            print(f"Data opgeslagen in: {output_file}")
            print("\nVoorbeeld van gevonden data:")
            print(df.head())
        else:
            print("\nGeen villa's met emails gevonden.")
    else:
        print("\nGeen websites gevonden in zoekresultaten.")

except Exception as e:
    print(f"Fout: {str(e)}")