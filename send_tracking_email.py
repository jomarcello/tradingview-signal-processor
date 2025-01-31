import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SENDER_EMAIL = "contact@jomarcello.com"
SENDER_PASSWORD = "CIKBWABAOVZMPNZJ"
DOMAIN = "https://3f6c-77-164-37-158.ngrok.io"  # Your ngrok URL
LEAD_ID = 62

msg = MIMEMultipart("alternative")
msg["Subject"] = "Welcome to Jomarcello Luxury Rentals"
msg["From"] = SENDER_EMAIL
msg["To"] = "adobejovanni@gmail.com"

tracking_pixel = f'<img src="{DOMAIN}/track/{LEAD_ID}" width="1" height="1" />'
tracked_link = f'<a href="{DOMAIN}/click/{LEAD_ID}">View Our Luxury Properties</a>'

html_content = f"""
<html>
<body>
    <h1>Welcome to Jomarcello Luxury Rentals!</h1>
    <p>Thank you for your interest in our exclusive properties.</p>
    <p>{tracked_link}</p>
    {tracking_pixel}
</body>
</html>
"""

msg.attach(MIMEText(html_content, "html"))

with smtplib.SMTP("smtp.gmail.com", 587) as server:
    server.set_debuglevel(1)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.sendmail(SENDER_EMAIL, "adobejovanni@gmail.com", msg.as_string())

print("Tracking email sent successfully!")
