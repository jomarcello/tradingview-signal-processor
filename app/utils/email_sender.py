import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import uuid
from datetime import datetime
from app import db
from app.models.email_tracking import EmailTracking

def create_tracking_pixel(email_id):
    tracking_domain = os.getenv('TRACKING_DOMAIN', 'localhost:5000')
    return f"""
    <img src='http://{tracking_domain}/pixel/{email_id}' 
         width='1' 
         height='1' 
         style='display:none'
    />
    """

def send_tracked_email(to_email, subject, body, campaign_id=None, lead_id=None):
    try:
        # Genereer uniek email ID
        email_id = str(uuid.uuid4())
        
        # Voeg tracking pixel toe
        tracked_body = f"{body}{create_tracking_pixel(email_id)}"
        
        # Maak email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = os.getenv('SMTP_USER')
        msg['To'] = to_email
        msg.attach(MIMEText(tracked_body, 'html'))
        
        # Verstuur email
        with smtplib.SMTP(os.getenv('SMTP_HOST'), int(os.getenv('SMTP_PORT'))) as server:
            server.starttls()
            server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD'))
            server.send_message(msg)
        
        # Log in database
        if lead_id:
            tracking = EmailTracking(
                lead_id=lead_id,
                email_id=email_id,
                subject=subject,
                sent_at=datetime.utcnow()
            )
            db.session.add(tracking)
            db.session.commit()
        
        return email_id
        
    except Exception as e:
        print(f"Error bij versturen email: {str(e)}")
        return None 