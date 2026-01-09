from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Firehorse API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class KworkWebhookPayload(BaseModel):
    order_id: int
    title: str
    description: str
    deadline: Optional[str] = None
    category: Optional[str] = None

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "1.0.0",
        "postgres": "connected",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/webhook/kwork")
async def kwork_webhook(payload: KworkWebhookPayload):
    """Kwork webhook - receives new orders"""
    logger.info(f"Kwork webhook: order {payload.order_id}")
    
    # Validation
    if not payload.title.strip():
        raise HTTPException(400, "Title required")
    
    # TODO: Save to DB + Queue (Итерация 3)
    logger.info(f"Order {payload.order_id} queued: {payload.title[:50]}...")
    
    return {
        "status": "accepted",
        "order_id": payload.order_id,
        "message": "Queued for AI processing"
    }

@app.get("/")
async def root():
    return {"message": "Firehorse API ready"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
