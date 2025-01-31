import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Instellingen voor de SMTP-server
smtp_server = "smtp.gmail.com"
smtp_port = 587
email_address = "contact@jomarcello.com"  # Jouw e-mailadres
email_password = "cikbwabaovzmpnzj"  # App-specifiek wachtwoord

# Tracking-pixel server URL
tracking_server_url = "http://127.0.0.1:5000/tracking_pixel"

# Verstuur e-mail functie
def send_email(to_email):
    # Tracking-pixel-URL met e-mailadres als queryparameter
    tracking_pixel_url = f"{tracking_server_url}?email={to_email}"

    # HTML-inhoud van de e-mail
    html_content = f"""
    <html>
        <body>
            <p>Hallo,</p>
            <p>Dit is een test e-mail met een tracking pixel. Wanneer deze e-mail wordt geopend, wordt dit bijgehouden in onze database.</p>
            <img src="{tracking_pixel_url}" alt="" width="1" height="1" style="display: none;">
        </body>
    </html>
    """

    # Maak de e-mail aan
    msg = MIMEMultipart()
    msg['From'] = email_address
    msg['To'] = to_email
    msg['Subject'] = "Test E-mail met Tracking Pixel"
    msg.attach(MIMEText(html_content, "html"))

    # Verstuur de e-mail
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Activeer encryptie
        server.login(email_address, email_password)
        server.send_message(msg)
        print(f"E-mail succesvol verzonden naar {to_email}!")
        server.quit()
    except Exception as e:
        print(f"Fout bij het verzenden van e-mail naar {to_email}: {e}")

# Test e-mail verzenden
if __name__ == "__main__":
    # Pas dit aan naar de ontvanger
    recipient_email = "jovannimt@gmail.com"
    send_email(recipient_email)