import sqlite3
import pandas as pd

# Path to the CSV file
CSV_FILE = "/Users/jovannitilborg/Desktop/Databases/cleaned_instagram_data 3(Werkblad 1 - cleaned_instagram_) 4.csv"

# Path to the SQLite database
DB_FILE = "/Users/jovannitilborg/Desktop/Databases/Database_luxuryrentals.db"

def recreate_table(cursor):
    """Recreate the 'leads' table with the correct schema."""
    cursor.execute("DROP TABLE IF EXISTS leads")
    cursor.execute("""
    CREATE TABLE leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        instagram_username TEXT,
        instagram_url TEXT,
        external_url TEXT,
        email TEXT
    )
    """)

def inspect_and_import_csv():
    """Inspect CSV and import data into the database."""
    conn = None
    try:
        # Read the CSV with the semicolon delimiter
        data = pd.read_csv(CSV_FILE, delimiter=';', encoding='utf-8')

        # Print the detected column headers
        print("Columns detected in the CSV:", data.columns.tolist())

        # Clean column names (strip extra spaces and standardize to lowercase)
        data.columns = data.columns.str.strip().str.lower()
        print("Standardized column names:", data.columns.tolist())

        # Check for required columns
        required_columns = ['name', 'instagram_username', 'instagram_url', 'external_url', 'email']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise ValueError(f"The CSV file is missing these columns: {missing_columns}")

        # Connect to the SQLite database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Recreate the table with the correct schema if necessary
        recreate_table(cursor)
        conn.commit()

        # Insert data into the database
        for _, row in data.iterrows():
            cursor.execute("""
            INSERT INTO leads (name, instagram_username, instagram_url, external_url, email)
            VALUES (?, ?, ?, ?, ?)
            """, (
                row['name'],
                row['instagram_username'],
                row['instagram_url'],
                row['external_url'],
                row['email']
            ))
        
        conn.commit()
        print("Data imported successfully!")

    except FileNotFoundError:
        print("CSV file not found. Please check the file path.")
    except ValueError as ve:
        print(f"Error reading CSV file: {ve}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    inspect_and_import_csv()