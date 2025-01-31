import pandas as pd
import sqlite3

# Step 1: Load the CSV file into a Pandas DataFrame
csv_file = "/Users/jovannitilborg/Desktop/Databases/cleaned_instagram_data 3(Werkblad 1 - cleaned_instagram_) 4.csv"
df = pd.read_csv(csv_file, sep=";")

# Step 2: Rename columns to match the SQLite table structure
df.columns = ['name', 'instagram_username', 'instagram_url', 'external_url', 'email']

# Step 3: Connect to the SQLite Database
db_file = "/Users/jovannitilborg/Desktop/Databases/Database_luxuryrentals.db"
connection = sqlite3.connect(db_file)

# Step 4: Write the DataFrame to the "leads" table
df.to_sql('leads', connection, if_exists='append', index=False)

# Step 5: Close the connection
connection.close()

print("Data imported successfully!")