class TrackingService:
    def track_open(self, email_id: str, timestamp: datetime, metadata: Dict):
        return self.analytics_repository.record_event(
            event_type='email_open',
            email_id=email_id,
            timestamp=timestamp,
            metadata=metadata
        )
    
    def track_click(self, email_id: str, link_id: str, timestamp: datetime):
        return self.analytics_repository.record_event(
            event_type='link_click',
            email_id=email_id,
            link_id=link_id,
            timestamp=timestamp
        )
