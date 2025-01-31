from main import send_tracked_email
import requests
import time
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

def print_env_settings():
    """Print alle relevante instellingen"""
    print("\n=== Email Instellingen ===")
    print(f"SMTP Host: {os.getenv('SMTP_HOST')}")
    print(f"SMTP Port: {os.getenv('SMTP_PORT')}")
    print(f"SMTP User: {os.getenv('SMTP_USER')}")
    print(f"SMTP Pass: {'*' * len(os.getenv('SMTP_PASSWORD', ''))} ({len(os.getenv('SMTP_PASSWORD', ''))} karakters)")
    print(f"Tracking Domain: {os.getenv('TRACKING_DOMAIN')}")

def send_test_emails():
    current_time = datetime.now().strftime("%H:%M:%S")
    subject = f"Test Email [{current_time}]"
    
    email_html = f"""
    <html>
        <body>
            <h1>Test Email</h1>
            <p>Dit is een test email verzonden om {current_time}</p>
            <p>Als je deze email kunt lezen, werkt het verzendproces.</p>
            <hr>
            <p><small>Email tracking test</small></p>
        </body>
    </html>
    """
    
    print(f"\nVerstuur test email met onderwerp: {subject}")
    return send_tracked_email(
        to_email="jovannimt@gmail.com",
        subject=subject,
        body=email_html
    )

if __name__ == "__main__":
    print("=== Email Test Systeem Start ===")
    
    # Print instellingen
    print_env_settings()
    
    # Verstuur test email
    email_id = send_test_emails()
    
    if email_id:
        print("\nWacht 5 seconden...")
        time.sleep(5)
        
        print("\nStatistieken ophalen...")
        from stats import get_email_stats, print_stats
        
        try:
            stats = get_email_stats(email_id)
            print_stats(stats)
        except Exception as e:
            print(f"Error bij ophalen statistieken: {e}")
    else:
        print("\nTest gefaald: kon geen email versturen") 