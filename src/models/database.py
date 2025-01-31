from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Campaign(Base):
    __tablename__ = 'campaigns'
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    
class EmailEvent(Base):
    __tablename__ = 'email_events'
    
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey('campaigns.id'))
    event_type = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
