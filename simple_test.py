print("=== Start Simple Test ===")

try:
    print("1. Import modules...")
    from dotenv import load_dotenv
    import os
    
    print("2. Load .env...")
    load_dotenv()
    
    print("3. Check environment variables...")
    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = os.getenv('SMTP_PORT')
    smtp_user = os.getenv('SMTP_USER')
    smtp_pass = os.getenv('SMTP_PASSWORD')
    
    print(f"""
    Configuratie gevonden:
    - SMTP Host: {smtp_host}
    - SMTP Port: {smtp_port}
    - SMTP User: {smtp_user}
    - SMTP Pass: {'*' * len(smtp_pass) if smtp_pass else 'Niet gevonden'}
    """)
    
except Exception as e:
    print(f"Error: {type(e).__name__}")
    print(f"Error bericht: {str(e)}") 