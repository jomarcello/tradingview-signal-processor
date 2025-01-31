from datetime import datetime
from app import db

class Lead(db.Model):
    __tablename__ = 'leads'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    instagram_username = db.Column(db.String(100), nullable=False)
    instagram_url = db.Column(db.String(500), nullable=False)
    external_url = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(50), default='new')
    engagement_score = db.Column(db.Integer, default=0)
    last_email_sent = db.Column(db.DateTime)
    last_email_opened = db.Column(db.DateTime)
    last_link_clicked = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaties worden later toegevoegd via back_populates
    activities = db.relationship('Activity', back_populates='lead', lazy='dynamic')
    comments = db.relationship('Comment', back_populates='lead', lazy='dynamic')
    campaign_interactions = db.relationship('CampaignInteraction', back_populates='lead', lazy='dynamic')

    def calculate_engagement_score(self):
        score = 0
        if self.last_email_opened:
            score += 1
        if self.last_link_clicked:
            score += 2
        return score

    def update_engagement(self):
        self.engagement_score = self.calculate_engagement_score()
        
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'instagram_username': self.instagram_username,
            'instagram_url': self.instagram_url,
            'external_url': self.external_url,
            'status': self.status,
            'engagement_score': self.engagement_score,
            'last_email_sent': self.last_email_sent.isoformat() if self.last_email_sent else None,
            'last_email_opened': self.last_email_opened.isoformat() if self.last_email_opened else None,
            'last_link_clicked': self.last_link_clicked.isoformat() if self.last_link_clicked else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 