import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, redirect
import sqlite3

# App-specific password for email
SENDER_EMAIL = "contact@jomarcello.com"
SENDER_PASSWORD = "cikbwabaovzmpnzj"

# Flask app
app = Flask(__name__)

# Initialize database
conn = sqlite3.connect("email_tracking.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS email_tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        opened INTEGER DEFAULT 0,
        clicked INTEGER DEFAULT 0
    )
""")
conn.commit()

@app.route('/track/<int:email_id>')
def track_email(email_id):
    c.execute("UPDATE email_tracking SET opened = 1 WHERE id = ?", (email_id,))
    conn.commit()
    return "", 204

@app.route('/click/<int:email_id>')
def track_click(email_id):
    c.execute("UPDATE email_tracking SET clicked = 1 WHERE id = ?", (email_id,))
    conn.commit()
    # Redirect to a target page
    return redirect("https://www.your-redirect-link.com")

def send_email(subject, body, recipient, email_id):
    # Construct email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient

    # Include tracking pixel and clickable link
    tracking_pixel = f'<img src="http://127.0.0.1:5000/track/{email_id}" style="display:none" alt="tracker">'
    clickable_link = f'<a href="http://127.0.0.1:5000/click/{email_id}">Click here to visit our page</a>'
    html_content = f"""
    <html>
        <body>
            <p>Hello,</p>
            <p>This is a test email with tracking capabilities.</p>
            {tracking_pixel}
            <p>{clickable_link}</p>
        </body>
    </html>
    """
    msg.attach(MIMEText(html_content, "html"))

    # Send email
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, recipient, msg.as_string())

# Add email to database and send
def add_email_to_db_and_send(subject, body, recipient):
    c.execute("INSERT INTO email_tracking (email) VALUES (?)", (recipient,))
    conn.commit()
    email_id = c.lastrowid
    send_email(subject, body, recipient, email_id)

if __name__ == "__main__":
    # Example email sending
    recipient_email = "jovannimt@gmail.com"
    email_subject = "Test Email with Tracking"
    email_body = "This is a test email to track opens and clicks."

    add_email_to_db_and_send(email_subject, email_body, recipient_email)
    print("[INFO] Test email sent. Start Flask server for tracking.")

    # Start Flask server
    app.run(debug=True)