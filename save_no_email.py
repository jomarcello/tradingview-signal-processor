import pandas as pd

try:
    # Probeer verschillende mogelijke bestandsnamen
    possible_files = [
        'dataset_email-extractor_hersteld.xlsx',
        'dataset_email-extractor_resultaat.xlsx',
        'dataset_email-extractor_2024-11-28_15-39-54-899.xlsx'
    ]
    
    df = None
    used_file = None
    
    for file in possible_files:
        try:
            print(f"Probeer bestand te openen: {file}")
            df = pd.read_excel(file)
            used_file = file
            break
        except:
            continue
    
    if df is None:
        raise FileNotFoundError("Geen van de Excel bestanden kon worden gevonden")
    
    print(f"\nBestand succesvol geopend: {used_file}")
    
    # Filter websites zonder email
    no_email_df = df[df['Email'].isna() | (df['Email'] == '')]
    
    # Sla op als CSV
    no_email_df.to_csv('websites_zonder_email.csv', index=False)
    
    print(f"\nWebsites zonder email zijn opgeslagen in 'websites_zonder_email.csv'")
    print(f"Aantal websites zonder email: {len(no_email_df)}")
    print("Websites zonder email:")
    for website in no_email_df['Website']:
        print(f"- {website}")

except Exception as e:
    print(f"Fout: {str(e)}")
    print("\nControleer of een van deze bestanden aanwezig is in de huidige map:")
    for file in possible_files:
        print(f"- {file}") 