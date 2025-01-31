import pandas as pd
from difflib import SequenceMatcher

def similar(a, b):
    if not isinstance(a, str) or not isinstance(b, str):
        return 0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

try:
    # Lees beide bestanden
    print("Bezig met inlezen van bestanden...")
    emails_df = pd.read_excel('dataset_email-extractor_resultaat.xlsx')
    villas_df = pd.read_csv('cleaned_instagram_data 3(Werkblad 1 - cleaned_instagram_) 4.csv', sep=';')
    
    print(f"\nAantal gevonden villa's: {len(villas_df)}")
    print(f"Aantal websites met emails: {len(emails_df)}")
    
    # Voor elke villa, zoek de beste match
    matches_found = 0
    for idx, villa_row in villas_df.iterrows():
        villa_name = villa_row['Name']  # Nu gebruiken we de correcte kolomnaam 'Name'
        print(f"\nZoeken naar match voor: {villa_name}")
        
        best_match_score = 0
        best_match_email = None
        best_match_website = None
        
        for _, email_row in emails_df.iterrows():
            website = email_row['Website']
            email = email_row['Email']
            
            if pd.isna(email) or email == '':
                continue
            
            # Verwijder 'http://', 'https://', 'www.' en '.com' voor betere matching
            clean_website = website.lower()
            for prefix in ['http://', 'https://', 'www.']:
                if clean_website.startswith(prefix):
                    clean_website = clean_website[len(prefix):]
            clean_website = clean_website.split('.com')[0]
            
            # Check overeenkomst tussen villa naam en website
            match_score = similar(str(villa_name).lower(), clean_website)
            
            if match_score > best_match_score and match_score > 0.5:  # 50% overeenkomst minimum
                best_match_score = match_score
                best_match_email = email
                best_match_website = website
        
        if best_match_email:
            villas_df.at[idx, 'Email'] = best_match_email
            matches_found += 1
            print(f"✓ Match gevonden ({best_match_score:.2%}):")
            print(f"  Villa: {villa_name}")
            print(f"  Website: {best_match_website}")
            print(f"  Email: {best_match_email}")
        else:
            print("✗ Geen match gevonden")
    
    # Sla het bijgewerkte bestand op
    output_file = 'cleaned_instagram_data_met_emails.csv'
    villas_df.to_csv(output_file, sep=';', index=False)
    
    print("\nKoppeling voltooid!")
    print(f"Aantal villa's met gekoppelde email: {matches_found}")
    print(f"Resultaat opgeslagen in '{output_file}'")

except FileNotFoundError as e:
    print(f"Fout: Bestand niet gevonden - {str(e)}")
    print("\nControleer of deze bestanden aanwezig zijn:")
    print("- dataset_email-extractor_resultaat.xlsx")
    print("- cleaned_instagram_data 3(Werkblad 1 - cleaned_instagram_) 4.csv")
except Exception as e:
    print(f"Fout: {str(e)}")