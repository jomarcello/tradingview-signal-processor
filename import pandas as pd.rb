import pandas as pd

# Excel bestand inlezen
df = pd.read_excel('dataset_email-extractor_2024-11-28_15-39-54-899.xls')

# Kolommen A t/m F verwijderen
df = df.iloc[:, 6:]

# Bestand opslaan met nieuwe naam
df.to_excel('dataset_email-extractor_aangepast.xls', index=False)