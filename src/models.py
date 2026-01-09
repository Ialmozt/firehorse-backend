# src/models.py
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class Order(BaseModel):
    """Kwork order model with validation"""
    
    id: str = Field(..., min_length=1, max_length=50, description="Kwork order ID")
    title: str = Field(..., min_length=1, max_length=500, description="Order title")
    price: float = Field(..., gt=0, le=1000000, description="Order price")
    description: Optional[str] = Field(None, max_length=5000, description="Order description")
    buyer_id: Optional[str] = Field(None, max_length=50, description="Kwork buyer ID")
    
    @validator('title')
    def title_no_injection(cls, v):
        """Prevent injection attacks in title"""
        if '<' in v or '>' in v or ';' in v:
            raise ValueError('Title contains invalid characters')
        return v
    
    @validator('price')
    def price_realistic(cls, v):
        """Ensure price is realistic"""
        if v < 0.01:
            raise ValueError('Price must be at least 0.01')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "id": "kwork_12345",
                "title": "Logo Design",
                "price": 150,
                "description": "Need professional logo",
                "buyer_id": "kwork_buyer_999"
            }
        }

class OrderResponse(BaseModel):
    """Response model for order creation"""
    status: str
    order_id: str
    request_id: str
    message: Optional[str] = None

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    message: str
    request_id: str