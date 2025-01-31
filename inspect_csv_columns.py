import pandas as pd

# Path to the CSV file
CSV_FILE = "/Users/jovannitilborg/Desktop/Databases/cleaned_instagram_data 3(Werkblad 1 - cleaned_instagram_) 4.csv"

# Load and print column names
try:
    data = pd.read_csv(CSV_FILE)
    print("Columns in CSV:", data.columns.tolist())
except Exception as e:
    print(f"Error reading CSV file: {e}")