import os
import sys
# Voeg de parent directory toe aan sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Lead, EmailTemplate, Campaign
from datetime import datetime, timedelta

app = create_app()

with app.app_context():
    try:
        # Verwijder bestaande data
        db.session.query(Lead).delete()
        db.session.query(EmailTemplate).delete()
        db.session.query(Campaign).delete()
        
        # Voeg test leads toe
        leads = [
            Lead(
                name='John Doe',
                email='john@example.com',
                instagram='@johndoe',
                source_url='https://example.com/listing1'
            ),
            Lead(
                name='Jane Smith',
                email='jane@example.com',
                instagram='@janesmith',
                source_url='https://example.com/listing2'
            )
        ]
        db.session.add_all(leads)
        
        # Voeg test email template toe
        template = EmailTemplate(
            name='Welkom Template',
            subject='Welkom bij Luxury Rentals',
            body_html='''
            <h1>Welkom!</h1>
            <p>Bedankt voor je interesse in onze luxe accommodaties.</p>
            <p>We nemen binnenkort contact met je op.</p>
            '''
        )
        db.session.add(template)
        
        # Voeg test campagne toe
        campaign = Campaign(
            name='Welkom Campagne',
            status='draft',
            scheduled_at=datetime.utcnow() + timedelta(days=1)
        )
        db.session.add(campaign)
        
        db.session.commit()
        print("Test data succesvol toegevoegd!")
        
    except Exception as e:
        print(f"Error bij toevoegen test data: {str(e)}")
        db.session.rollback() 