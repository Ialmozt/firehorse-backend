# src/models.py
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class Order(BaseModel):
    """Kwork order model with validation"""

    kworkid: str = Field(..., min_length=1, max_length=50, description="Kwork order ID")
    topic: str = Field(..., min_length=1, max_length=500, description="Order topic")

    @validator('topic')
    def topic_no_injection(cls, v):
        """Prevent injection attacks in topic"""
        if '<' in v or '>' in v or ';' in v:
            raise ValueError('Topic contains invalid characters')
        return v

    class Config:
        schema_extra = {
            "example": {
                "kworkid": "123456",
                "topic": "SEO Article about AI"
            }
        }

class OrderResponse(BaseModel):
    """Response model for order creation"""
    status: str
    orderid: str
    request_id: str
    message: Optional[str] = None

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    message: str
    request_id: str
