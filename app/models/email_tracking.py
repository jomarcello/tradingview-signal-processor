from datetime import datetime
from app import db

class EmailTracking(db.Model):
    __tablename__ = 'email_tracking'
    
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    email_id = db.Column(db.String(36), unique=True, nullable=False)
    subject = db.Column(db.String(200))
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    opened_at = db.Column(db.DateTime)
    clicked_at = db.Column(db.DateTime)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'email_id': self.email_id,
            'subject': self.subject,
            'sent_at': self.sent_at.isoformat(),
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'clicked_at': self.clicked_at.isoformat() if self.clicked_at else None,
            'campaign_id': self.campaign_id
        } 