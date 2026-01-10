"""
Parser for Kwork webhook payloads.
Converts Kwork JSON to Firehorse order format.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class KworkParser:
    """Parser for Kwork webhook data"""
    
    @staticmethod
    def parse_webhook_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Kwork webhook payload to Firehorse order format.
        
        Args:
            payload: Raw JSON from Kwork webhook
            
        Returns:
            Dict with Firehorse order fields
        """
        try:
            # Extract basic order info
            order_id = str(payload.get("order_id", ""))
            user_id = str(payload.get("user_id", ""))
            title = payload.get("title", "")
            description = payload.get("description", "")
            status = payload.get("status", "pending")
            
            # Create source_id (unique identifier for Kwork order)
            source_id = f"kwork_{order_id}"
            
            # Extract topic from title or description
            topic = KworkParser._extract_topic(title, description)
            
            # Create metrics JSON
            metrics = {
                "source": "kwork",
                "order_id": order_id,
                "user_id": user_id,
                "title": title,
                "description_length": len(description) if description else 0,
                "parsed_at": datetime.utcnow().isoformat()
            }
            
            # Build Firehorse order
            firehorse_order = {
                "source_id": source_id,
                "topic": topic,
                "status": "queued",  # Always start as queued
                "attempts": 0,
                "final_text": None,
                "metrics": metrics,
                "last_error": None,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"✅ Parsed Kwork order {order_id} to Firehorse format")
            logger.debug(f"Parsed order: {firehorse_order}")
            
            return firehorse_order
            
        except Exception as e:
            logger.error(f"❌ Error parsing Kwork payload: {str(e)}")
            raise ValueError(f"Failed to parse Kwork payload: {str(e)}")
    
    @staticmethod
    def _extract_topic(title: str, description: str) -> str:
        """
        Extract topic from title and description.
        Uses simple keyword matching for common content types.
        """
        text = f"{title} {description}".lower()
        
        # Topic detection based on keywords
        topic_keywords = {
            "seo": ["seo", "поисковая", "оптимизация", "мета", "ключевые слова"],
            "article": ["статья", "article", "текст", "контент", "писать", "написать"],
            "translation": ["перевод", "translation", "перевести", "язык"],
            "copywriting": ["копирайтинг", "copywriting", "рекламный", "продающий"],
            "social": ["социальные", "social", "smm", "инстаграм", "telegram", "vk"],
            "design": ["дизайн", "design", "логотип", "баннер", "макет"],
            "programming": ["программирование", "programming", "код", "скрипт", "python", "javascript"],
            "video": ["видео", "video", "монтаж", "ролик", "youtube"],
            "audio": ["аудио", "audio", "озвучка", "подкаст", "запись"],
        }
        
        # Find matching topic
        for topic, keywords in topic_keywords.items():
            if any(keyword in text for keyword in keywords):
                return topic
        
        # Default topic
        return "general"
    
    @staticmethod
    def validate_payload(payload: Dict[str, Any]) -> bool:
        """
        Validate Kwork webhook payload structure.
        
        Args:
            payload: Raw JSON from Kwork webhook
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["order_id", "user_id", "title"]
        
        for field in required_fields:
            if field not in payload:
                logger.warning(f"Missing required field: {field}")
                return False
        
        # Validate field types
        if not isinstance(payload["order_id"], (int, str)):
            logger.warning(f"Invalid order_id type: {type(payload['order_id'])}")
            return False
        
        if not isinstance(payload["user_id"], (int, str)):
            logger.warning(f"Invalid user_id type: {type(payload['user_id'])}")
            return False
        
        if not isinstance(payload["title"], str):
            logger.warning(f"Invalid title type: {type(payload['title'])}")
            return False
        
        return True
    
    @staticmethod
    def create_webhook_response(order_id: str, firehorse_order_id: str) -> Dict[str, Any]:
        """
        Create standardized webhook response.
        
        Args:
            order_id: Original Kwork order ID
            firehorse_order_id: Generated Firehorse UUID
            
        Returns:
            Response dict
        """
        return {
            "status": "accepted",
            "message": f"Order {order_id} received and queued",
            "order_id": order_id,
            "firehorse_id": firehorse_order_id,
            "timestamp": datetime.utcnow().isoformat()
        }


# Convenience function for direct use
def parse_kwork_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to parse Kwork payload"""
    parser = KworkParser()
    return parser.parse_webhook_payload(payload)


def validate_kwork_payload(payload: Dict[str, Any]) -> bool:
    """Convenience function to validate Kwork payload"""
    parser = KworkParser()
    return parser.validate_payload(payload)
