import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# Verbind met de database
db_file = "/Users/jovannitilborg/Desktop/Databases/Database_luxuryrentals.db"
connection = sqlite3.connect(db_file)

# SQL-query
query = """
SELECT country, COUNT(*) as lead_count
FROM leads
GROUP BY country
ORDER BY lead_count DESC;
"""
df = pd.read_sql_query(query, connection)

# Maak een grafiek
plt.figure(figsize=(10, 6))
plt.bar(df['country'], df['lead_count'], color='skyblue')
plt.xlabel('Land')
plt.ylabel('Aantal Leads')
plt.title('Aantal Leads per Land')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Sluit de database
connection.close()