import sqlite3

conn = sqlite3.connect("/Users/jovannitilborg/Desktop/Databases/Database_luxuryrentals.db")
c = conn.cursor()

# Show current tracking status
print("\n=== CURRENT TRACKING STATUS ===")
c.execute("SELECT id, email, email_opened, link_clicked FROM leads WHERE email='adobejovanni@gmail.com'")
lead = c.fetchone()
print(f"""
Lead ID: {lead[0]}
Email: {lead[1]}
Opens: {lead[2]}
Clicks: {lead[3]}
""")

conn.close()
