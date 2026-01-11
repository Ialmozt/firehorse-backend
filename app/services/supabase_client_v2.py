"""
Supabase Client v2 - использует httpx напрямую для работы с REST API Supabase.
Поддерживает SOCKS5 прокси через httpx[socks].
"""
import logging
import httpx
import json
from datetime import datetime
import uuid
from typing import Dict, Any, Optional, List
from app.config import settings

logger = logging.getLogger(__name__)


class SupabaseClientV2:
    """Клиент для работы с Supabase через REST API с поддержкой прокси"""
    
    def __init__(self):
        self.base_url = settings.SUPABASE_URL
        self.api_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "apikey": settings.SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        # Создаем HTTP клиент с прокси
        if settings.USE_PROXY and settings.proxy_url:
            logger.info(f"🔗 Using {settings.PROXY_TYPE} proxy: {settings.proxy_url}")
            self.http_client = httpx.Client(
                proxies=settings.proxy_url,
                timeout=30.0
            )
        else:
            logger.info("🔗 Direct connection (no proxy)")
            self.http_client = httpx.Client(timeout=30.0)
        
        logger.info("✅ Supabase REST client initialized")
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Выполнить HTTP запрос к Supabase REST API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                response = self.http_client.get(url, headers=self.headers, params=data)
            elif method == "POST":
                response = self.http_client.post(url, headers=self.headers, json=data)
            elif method == "PUT":
                response = self.http_client.put(url, headers=self.headers, json=data)
            elif method == "PATCH":
                response = self.http_client.patch(url, headers=self.headers, json=data)
            elif method == "DELETE":
                response = self.http_client.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            if response.status_code == 204:  # No Content
                return None
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"❌ Request error: {str(e)}")
            raise
    
    def save_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Сохранить заказ в таблице orders"""
        try:
            order_uuid = str(uuid.uuid4())
            data = {
                "id": order_uuid,
                "source_id": order_data["source_id"],
                "topic": order_data["topic"],
                "status": order_data["status"],
                "attempts": order_data["attempts"],
                "final_text": order_data["final_text"],
                "metrics": order_data["metrics"],
                "last_error": order_data["last_error"],
                "created_at": order_data["created_at"],
                "updated_at": order_data["updated_at"]
            }
            
            result = self._make_request("POST", "/rest/v1/orders", data)
            
            if result and len(result) > 0:
                saved_order = result[0]
                logger.info(f"✅ Order saved: {order_data['source_id']} (UUID: {order_uuid})")
                saved_order["firehorse_id"] = order_uuid
                return saved_order
            else:
                raise Exception("No data returned from Supabase")
                
        except Exception as e:
            logger.error(f"❌ Error saving order: {str(e)}")
            raise
    
    def get_order_by_source_id(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Получить заказ по source_id"""
        try:
            params = {"source_id": f"eq.{source_id}"}
            result = self._make_request("GET", "/rest/v1/orders", params)
            
            if result and len(result) > 0:
                logger.info(f"✅ Retrieved order: {source_id}")
                return result[0]
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting order: {str(e)}")
            return None
    
    def update_order_status(self, order_uuid: str, status: str, error_message: Optional[str] = None) -> Dict[str, Any]:
        """Обновить статус заказа"""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if error_message:
                update_data["last_error"] = error_message
            
            # Используем PATCH для обновления
            endpoint = f"/rest/v1/orders?id=eq.{order_uuid}"
            result = self._make_request("PATCH", endpoint, update_data)
            
            if result and len(result) > 0:
                logger.info(f"✅ Order {order_uuid} status updated to {status}")
                return result[0]
            else:
                return update_data
                
        except Exception as e:
            logger.error(f"❌ Error updating order status: {str(e)}")
            raise
    
    def create_order_event(self, order_uuid: str, stage: str, level: str, 
                          message: str, meta: Optional[Dict] = None) -> Dict[str, Any]:
        """Создать событие для заказа"""
        try:
            event_data = {
                "order_id": order_uuid,
                "stage": stage,
                "level": level,
                "message": message,
                "meta": meta or {},
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = self._make_request("POST", "/rest/v1/order_events", event_data)
            
            if result and len(result) > 0:
                logger.info(f"✅ Order event created: {stage} - {level}")
                return result[0]
            else:
                return event_data
                
        except Exception as e:
            logger.error(f"❌ Error creating order event: {str(e)}")
            raise
    
    def update_order_with_content(self, order_uuid: str, content: str, 
                                 usage_metrics: Optional[Dict] = None) -> Dict[str, Any]:
        """Обновить заказ сгенерированным контентом"""
        try:
            update_data = {
                "final_text": content,
                "status": "completed",
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if usage_metrics:
                # Получаем текущие метрики
                params = {"id": f"eq.{order_uuid}"}
                current_order = self._make_request("GET", "/rest/v1/orders", params)
                
                if current_order and len(current_order) > 0:
                    current_metrics = current_order[0].get("metrics", {})
                    current_metrics["deepseek_usage"] = usage_metrics
                    update_data["metrics"] = current_metrics
            
            endpoint = f"/rest/v1/orders?id=eq.{order_uuid}"
            result = self._make_request("PATCH", endpoint, update_data)
            
            if result and len(result) > 0:
                logger.info(f"✅ Order {order_uuid} updated with content ({len(content)} chars)")
                return result[0]
            else:
                return update_data
                
        except Exception as e:
            logger.error(f"❌ Error updating order with content: {str(e)}")
            raise
    
    def test_connection(self) -> bool:
        """Тестирование подключения к Supabase"""
        try:
            result = self._make_request("GET", "/rest/v1/orders?limit=1")
            if result is not None:
                logger.info("✅ Supabase connection test passed")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Supabase connection test failed: {str(e)}")
            return False


# Синглтон экземпляр
_supabase_client_v2 = None

def get_supabase_client() -> SupabaseClientV2:
    """Получение экземпляра Supabase клиента"""
    global _supabase_client_v2
    if _supabase_client_v2 is None:
        _supabase_client_v2 = SupabaseClientV2()
    return _supabase_client_v2
