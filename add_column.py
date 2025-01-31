import sqlite3

# Pad naar je databasebestand
db_file = '/Users/jovannitilborg/Desktop/Databases/Database_luxuryrentals.db'

# Verbinden met de database
connection = sqlite3.connect(db_file)
cursor = connection.cursor()

# SQL-query om de kolom toe te voegen
query = "ALTER TABLE leads ADD COLUMN email_opened DATETIME;"

try:
    cursor.execute(query)
    connection.commit()
    print("Kolom email_opened succesvol toegevoegd!")
except sqlite3.OperationalError as e:
    print(f"Fout: {e}")
finally:
    connection.close()