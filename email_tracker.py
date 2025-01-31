import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, redirect
import sqlite3
from datetime import datetime

# Email configuration
SENDER_EMAIL = "contact@jomarcello.com"
SENDER_PASSWORD = "CIKBWABAOVZMPNZJ"
DOMAIN = "http://127.0.0.1:5000"

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect("jomarcello.db")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        opened INTEGER DEFAULT 0,
        clicked INTEGER DEFAULT 0,
        last_opened DATETIME,
        last_clicked DATETIME,
        status TEXT DEFAULT 'sent',
        campaign TEXT
    )
    """)
    conn.commit()
    return conn, c

@app.route('/track/<int:lead_id>')
def track_open(lead_id):
    conn = sqlite3.connect("/Users/jovannitilborg/Desktop/Databases/Database_luxuryrentals.db")
    c = conn.cursor()
    c.execute("UPDATE leads SET emails_opened = emails_opened + 1 WHERE id = ?", (lead_id,))
    conn.commit()
    conn.close()
    return "", 204

@app.route('/click/<int:lead_id>')
def track_click(lead_id):
    conn = sqlite3.connect("/Users/jovannitilborg/Desktop/Databases/Database_luxuryrentals.db")
    c = conn.cursor()
    c.execute("UPDATE leads SET link_clicked = link_clicked + 1 WHERE id = ?", (lead_id,))
    conn.commit()
    conn.close()
    return redirect("https://jomarcello.com")

def send_tracked_email(recipient, subject, body, campaign_name):
    conn, c = init_db()
    c.execute("INSERT INTO leads (email, campaign) VALUES (?, ?)", (recipient, campaign_name))
    conn.commit()
    lead_id = c.lastrowid

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient

    tracking_pixel = f'<img src="{DOMAIN}/track/{lead_id}" width="1" height="1" />'
    tracked_link = f'<a href="{DOMAIN}/click/{lead_id}">Visit Jomarcello</a>'
    
    html_content = f"""
    <html>
    <body>
        {body}
        <p>{tracked_link}</p>
        {tracking_pixel}
    </body>
    </html>
    """
    
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, recipient, msg.as_string())

    return lead_id

if __name__ == "__main__":
    # Example usage
    send_tracked_email(
        "jovannimt@gmail.com",
        "Welcome to Jomarcello",
        "<h1>Hello!</h1><p>Thanks for joining Jomarcello.</p>",
        "welcome_campaign"
    )
    app.run(debug=True)