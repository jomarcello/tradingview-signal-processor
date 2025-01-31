from datetime import datetime
from typing import List, Dict

class CampaignService:
    def create_campaign(self, name: str, template_id: str, segment_ids: List[str]):
        return {
            'id': generate_uuid(),
            'name': name,
            'template_id': template_id,
            'segments': segment_ids,
            'status': 'draft',
            'created_at': datetime.utcnow()
        }
    
    def schedule_campaign(self, campaign_id: str, schedule_time: datetime):
        return self.scheduler.schedule(campaign_id, schedule_time)
