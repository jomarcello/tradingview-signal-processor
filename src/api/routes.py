from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.post("/api/v1/campaigns")
async def create_campaign(campaign_data: CampaignCreate):
    return campaign_service.create_campaign(**campaign_data.dict())

@app.post("/api/v1/campaigns/{campaign_id}/schedule")
async def schedule_campaign(campaign_id: str, schedule_data: ScheduleData):
    return campaign_service.schedule_campaign(campaign_id, schedule_data.schedule_time)
