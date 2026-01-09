from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class OrderStatus(str, enum.Enum):
    RECEIVED = "received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Order(Base):
    """✅ VERIFIED: Production Order model"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Kwork data
    kwork_id = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    budget = Column(Float, nullable=True)
    
    # User
    user_id = Column(String(50), index=True)
    username = Column(String(100))
    
    # Processing
    status = Column(String(20), default=OrderStatus.RECEIVED)
    deepseek_response = Column(Text, nullable=True)
    
    # Metadata
    platform = Column(String(20), default="kwork")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_processed = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<Order(id={self.id}, kwork_id={self.kwork_id}, status={self.status})>"
