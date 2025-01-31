from datetime import datetime
from app import db

class EmailTemplate(db.Model):
    __tablename__ = 'email_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    body_html = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relatie met back_populates
    campaigns = db.relationship('Campaign', back_populates='template')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'subject': self.subject,
            'body_html': self.body_html,
            'created_at': self.created_at.isoformat()
        }

class Campaign(db.Model):
    __tablename__ = 'campaigns'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('email_templates.id'))
    status = db.Column(db.String(50), default='draft')  # draft, active, completed, paused
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaties met back_populates in plaats van backref
    template = db.relationship('EmailTemplate', back_populates='campaigns')
    interactions = db.relationship('CampaignInteraction', back_populates='campaign')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'template_id': self.template_id,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }

class CampaignInteraction(db.Model):
    __tablename__ = 'campaign_interactions'
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    email_sent = db.Column(db.DateTime)
    email_opened = db.Column(db.DateTime)
    link_clicked = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaties met back_populates
    campaign = db.relationship('Campaign', back_populates='interactions')
    lead = db.relationship('Lead', back_populates='campaign_interactions')
    
    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'lead_id': self.lead_id,
            'email_sent': self.email_sent.isoformat() if self.email_sent else None,
            'email_opened': self.email_opened.isoformat() if self.email_opened else None,
            'link_clicked': self.link_clicked.isoformat() if self.link_clicked else None,
            'created_at': self.created_at.isoformat()
        }