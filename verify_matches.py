import pandas as pd

def clean_url(url):
    if not isinstance(url, str):
        return ''
    # Verwijder common prefixes en suffixes
    url = url.lower()
    for prefix in ['http://', 'https://', 'www.']:
        if url.startswith(prefix):
            url = url[len(prefix):]
    return url.split('/')[0]  # Alleen het domein deel

def get_domain_from_email(email):
    if not isinstance(email, str) or '@' not in email:
        return ''
    return email.split('@')[1].lower()

try:
    print("Bezig met inlezen van het bestand...")
    df = pd.read_csv('cleaned_instagram_data_met_emails.csv', sep=';')
    
    print("\nControleren van email matches met websites...")
    changes = 0
    
    for idx, row in df.iterrows():
        external_url = str(row['external_url'])
        email = str(row['Email'])
        
        if pd.isna(email) or email == '' or pd.isna(external_url) or external_url == '':
            continue
            
        # Haal de domeinnamen op
        website_domain = clean_url(external_url)
        email_domain = get_domain_from_email(email)
        
        # Check of het emailadres past bij de website
        match = False
        
        # Print debugging info
        print(f"\nControleren rij {idx + 1}:")
        print(f"Naam: {row['Name']}")
        print(f"Website: {external_url}")
        print(f"Email: {email}")
        print(f"Website domain: {website_domain}")
        print(f"Email domain: {email_domain}")
        
        # Check verschillende scenario's
        if website_domain in email_domain or email_domain in website_domain:
            match = True
        elif 'gmail.com' in email_domain and 'google' not in website_domain:
            # Gmail is acceptabel
            match = True
        
        if not match:
            print("✗ Geen match - email wordt verwijderd")
            df.at[idx, 'Email'] = ''
            changes += 1
        else:
            print("✓ Match gevonden - email wordt behouden")
    
    # Sla het gecontroleerde bestand op
    output_file = 'cleaned_instagram_data_geverifieerd.csv'
    df.to_csv(output_file, sep=';', index=False)
    
    print(f"\nVerificatie voltooid!")
    print(f"Aantal verwijderde emails: {changes}")
    print(f"Resultaat opgeslagen in '{output_file}'")

except FileNotFoundError:
    print("Fout: Kan het bestand 'cleaned_instagram_data_met_emails.csv' niet vinden")
except Exception as e:
    print(f"Fout: {str(e)}")