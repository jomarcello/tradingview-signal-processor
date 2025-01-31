import pandas as pd

def clean_text(text):
    if not isinstance(text, str):
        return ''
    return text.lower().strip()

try:
    print("Bezig met inlezen van het bestand...")
    df = pd.read_csv('cleaned_instagram_data_met_emails.csv', sep=';')
    
    print("\nGedetailleerde analyse van matches:")
    
    for idx, row in df.iterrows():
        villa_name = str(row['Name'])
        email = str(row['Email'])
        
        if pd.isna(email) or email == '':
            continue
            
        # Originele waarden tonen
        print(f"\n{'='*50}")
        print(f"Rij {idx + 1}:")
        print(f"Villa naam: {villa_name}")
        print(f"Email: {email}")
        
        # Toon de externe URL ook
        print(f"Website: {row['external_url']}")
        
        # Behoud de email als:
        # 1. Het een algemeen contact email is (info@, contact@, etc.)
        # 2. De website naam in de email zit
        # 3. De villa naam (of deel ervan) in de email zit
        
        keep_email = False
        reason = []
        
        # Check voor algemene contact emails
        common_prefixes = ['info@', 'contact@', 'reservations@', 'booking@', 'villa@']
        if any(email.lower().startswith(prefix) for prefix in common_prefixes):
            keep_email = True
            reason.append("Algemeen contact email")
        
        # Check voor website match
        if 'external_url' in row and str(row['external_url']) != '':
            website = str(row['external_url']).lower()
            website_name = website.split('///')[-1].split('/')[0]
            if website_name in email.lower():
                keep_email = True
                reason.append("Website match")
        
        # Check voor villa naam match
        villa_words = villa_name.lower().split()
        if any(word in email.lower() for word in villa_words if len(word) > 3):
            keep_email = True
            reason.append("Villa naam match")
            
        # Speciale gevallen
        if '@gmail.com' in email.lower():
            keep_email = True
            reason.append("Gmail account")
        
        if keep_email:
            print("✓ Email wordt behouden")
            print(f"Reden: {', '.join(reason)}")
        else:
            print("✗ Email wordt verwijderd")
            print("Geen match gevonden met naam of website")
            df.at[idx, 'Email'] = ''
    
    # Sla het gecontroleerde bestand op
    output_file = 'villa_email_matches_revised.csv'
    df.to_csv(output_file, sep=';', index=False)
    
    # Toon statistieken
    remaining_emails = df['Email'].notna().sum()
    print(f"\nVerificatie voltooid!")
    print(f"Aantal behouden emails: {remaining_emails}")
    print(f"Aantal verwijderde emails: {len(df) - remaining_emails}")
    print(f"Resultaat opgeslagen in '{output_file}'")

except FileNotFoundError:
    print("Fout: Kan het bestand 'cleaned_instagram_data_met_emails.csv' niet vinden")
except Exception as e:
    print(f"Fout: {str(e)}") 