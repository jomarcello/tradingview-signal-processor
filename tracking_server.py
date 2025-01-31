from flask import Flask, redirect
import sqlite3

app = Flask(__name__)

def get_lead_id(email):
    conn = sqlite3.connect("/Users/jovannitilborg/Desktop/Databases/Database_luxuryrentals.db")
    c = conn.cursor()
    c.execute("SELECT id FROM leads WHERE email = ?", (email,))
    lead_id = c.fetchone()[0]
    conn.close()
    return lead_id

LEAD_EMAIL = "adobejovanni@gmail.com"
LEAD_ID = get_lead_id(LEAD_EMAIL)

@app.route(f'/track/{LEAD_ID}')
def track_open():
    conn = sqlite3.connect("/Users/jovannitilborg/Desktop/Databases/Database_luxuryrentals.db")
    c = conn.cursor()
    c.execute("UPDATE leads SET email_opened = email_opened + 1 WHERE id = ?", (LEAD_ID,))
    conn.commit()
    conn.close()
    return "", 204

@app.route(f'/click/{LEAD_ID}')
def track_click():
    conn = sqlite3.connect("/Users/jovannitilborg/Desktop/Databases/Database_luxuryrentals.db")
    c = conn.cursor()
    c.execute("UPDATE leads SET link_clicked = link_clicked + 1 WHERE id = ?", (LEAD_ID,))
    conn.commit()
    conn.close()
    return redirect("https://jomarcello.com")

if __name__ == "__main__":
    print(f"Tracking server started for lead ID: {LEAD_ID}")
    app.run(port=5001, debug=True)  # Using port 5001 instead of 5000    app.run(debug=True)