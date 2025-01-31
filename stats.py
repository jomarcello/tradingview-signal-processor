from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import datetime
import os
import sys
import certifi

# Laad environment variables
load_dotenv()

# MongoDB setup
mongodb_uri = os.getenv('MONGODB_URI')
if not mongodb_uri:
    print("Error: Geen MONGODB_URI gevonden in .env bestand")
    sys.exit(1)

try:
    print("Verbinding maken met MongoDB...")
    client = MongoClient(
        mongodb_uri,
        server_api=ServerApi('1'),
        tlsCAFile=certifi.where()
    )
    # Test de connectie
    client.admin.command('ping')
    print("MongoDB connectie succesvol!")
except Exception as e:
    print(f"Error bij verbinden met MongoDB: {e}")
    sys.exit(1)

db = client['email_tracking']
email_events = db['events']

def get_email_stats(email_id=None):
    """Haal statistieken op voor één email of alle emails"""
    if email_id:
        query = {'email_id': email_id}
    else:
        query = {}
    
    emails = email_events.find(query)
    stats = {
        'total_sent': 0,
        'total_opens': 0,
        'total_clicks': 0,
        'emails': []
    }
    
    for email in emails:
        # Print document structuur voor debugging
        print(f"\nDocument in database: {email}")
        
        email_stats = {
            'email_id': email.get('email_id', 'Unknown ID'),
            'to': email.get('to', 'Unknown'),
            'subject': email.get('subject', 'No Subject'),
            'sent_at': email.get('sent_at', 'Unknown'),
            'opens': 0,
            'clicks': 0,
            'last_opened': None,
            'clicked_links': []
        }
        
        for event in email.get('events', []):
            if event['type'] == 'open':
                email_stats['opens'] += 1
                email_stats['last_opened'] = event['timestamp']
            elif event['type'] == 'click':
                email_stats['clicks'] += 1
                email_stats['clicked_links'].append({
                    'url': event.get('url'),
                    'timestamp': event['timestamp']
                })
        
        stats['total_sent'] += 1
        stats['total_opens'] += email_stats['opens']
        stats['total_clicks'] += email_stats['clicks']
        stats['emails'].append(email_stats)
    
    return stats

def print_stats(stats):
    """Print statistieken in leesbaar formaat"""
    print("\n=== Email Tracking Statistieken ===")
    print(f"Totaal verzonden: {stats['total_sent']}")
    print(f"Totaal geopend: {stats['total_opens']}")
    print(f"Totaal clicks: {stats['total_clicks']}")
    
    print("\n=== Per Email ===")
    for email in stats['emails']:
        print(f"\nEmail ID: {email['email_id']}")
        print(f"Verzonden aan: {email['to']}")
        print(f"Onderwerp: {email['subject']}")
        print(f"Verzonden op: {email['sent_at']}")
        print(f"Aantal opens: {email['opens']}")
        print(f"Laatste open: {email['last_opened']}")
        print(f"Aantal clicks: {email['clicks']}")
        
        if email['clicked_links']:
            print("\nGeklikte links:")
            for link in email['clicked_links']:
                print(f"- {link['url']} (geklikt op: {link['timestamp']})")
        print("-" * 50)

# Voeg deze functie toe om de database te inspecteren
def inspect_database():
    print("\n=== Database Inspectie ===")
    print("Collections in database:", db.list_collection_names())
    print("\nDocumenten in email_events collection:")
    for doc in email_events.find():
        print(f"\nDocument: {doc}")

def generate_detailed_report():
    print("\n=== Gedetailleerd Email Rapport ===")
    
    # Alleen echte emails (geen connection tests)
    email_query = {'email_id': {'$exists': True}}
    emails = email_events.find(email_query)
    
    total_emails = email_events.count_documents(email_query)
    print(f"\nTotaal aantal verstuurde emails: {total_emails}")
    
    for email in emails:
        print("\n-------------------")
        print(f"Email ID: {email.get('email_id')}")
        print(f"Verzonden aan: {email.get('to')}")
        print(f"Onderwerp: {email.get('subject')}")
        print(f"Verzonden op: {email.get('sent_at')}")
        
        events = email.get('events', [])
        opens = [e for e in events if e.get('type') == 'open']
        
        print(f"Aantal opens: {len(opens)}")
        
        if opens:
            print("\nOpen geschiedenis:")
            for open_event in opens:
                print(f"- Geopend op: {open_event.get('timestamp')}")
                print(f"  Browser: {open_event.get('user_agent')}")
        
        print("-------------------")

if __name__ == "__main__":
    print("Verbinding maken met MongoDB...")
    try:
        client.admin.command('ping')
        print("MongoDB connectie succesvol!")
        generate_detailed_report()
    except Exception as e:
        print(f"Error: {e}") 