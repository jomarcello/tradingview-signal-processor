import sqlite3
import time

while True:
    conn = sqlite3.connect("/Users/jovannitilborg/Desktop/Databases/Database_luxuryrentals.db")
    c = conn.cursor()
    c.execute("SELECT id, email, email_opened, link_clicked FROM leads WHERE id=62")
    lead = c.fetchone()
    print(f"\rID: {lead[0]} | Opens: {lead[2]} | Clicks: {lead[3]}", end="")
    conn.close()
    time.sleep(1)
