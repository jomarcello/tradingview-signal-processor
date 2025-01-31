import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, redirect
import sqlite3
from datetime import datetime

# Configuration
SENDER_EMAIL = "contact@jomarcello.com"
SENDER_PASSWORD = "CIKBWABAOVZMPNZJ"
DOMAIN = "http://127.0.0.1:5000"
DB_PATH = "/Users/jovannitilborg/Desktop/Databases/Database_luxuryrentals.db"

app = Flask(__name__)

def send_tracked_email(recipient, subject, body, lead_id):
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

@app.route('/track/<int:lead_id>')
def track_open(lead_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE leads SET emails_opened = emails_opened + 1 WHERE id = ?", (lead_id,))
    conn.commit()
    conn.close()
    return "", 204

@app.route('/click/<int:lead_id>')
def track_click(lead_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE leads SET link_clicked = link_clicked + 1 WHERE id = ?", (lead_id,))
    conn.commit()
    conn.close()
    return redirect("https://jomarcello.com")

def check_tracking_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, email, emails_opened, link_clicked FROM leads")
    stats = c.fetchall()
    conn.close()
    return stats

if __name__ == "__main__":
    # Example usage
    lead_id = 1  # Replace with actual lead ID
    send_tracked_email(
        "jovannimt@gmail.com",
        "Welcome to Jomarcello",
        "<h1>Hello!</h1><p>Welcome to our luxury rentals!</p>",
        lead_id
    )
    
    # Start tracking server
    app.run(debug=True)
