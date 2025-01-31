from datetime import datetime
from app import db

class Activity(db.Model):
    __tablename__ = 'activities'
    
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # email_sent, email_opened, link_clicked, status_changed, etc.
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow) 
    
    # Relatie toevoegen
    lead = db.relationship('Lead', back_populates='activities')