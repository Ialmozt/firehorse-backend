"""
PGMQ REST Client - взаимодействие с PGMQ через Supabase REST API.
"""
import logging
import httpx
from typing import Dict, Any, Optional, List
from app.config import settings

logger = logging.getLogger(__name__)


class PGMQRESTClient:
    """Клиент для работы с PGMQ через REST API Supabase"""
    
    def __init__(self):
        self.base_url = settings.SUPABASE_URL
        self.api_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "apikey": settings.SUPABASE_ANON_KEY,
            "Content-Type": "application/json"
        }
        
        # Настройка HTTP клиента с прокси
        if settings.USE_PROXY and settings.proxy_url:
            logger.info(f"🔗 PGMQ REST client using proxy: {settings.proxy_url}")
            self.http_client = httpx.Client(
                proxies=settings.proxy_url,
                timeout=30.0
            )
        else:
            logger.info("🔗 PGMQ REST client direct connection")
            self.http_client = httpx.Client(timeout=30.0)
    
    def read_job(self, queue_name: str = "job_queue", num_messages: int = 1, 
                 visibility_timeout: int = 300) -> Optional[Dict[str, Any]]:
        """
        Чтение сообщения из очереди PGMQ через REST API.
        
        Args:
            queue_name: Имя очереди
            num_messages: Количество сообщений для чтения
            visibility_timeout: Таймаут видимости в секундах
            
        Returns:
            Сообщение или None если очередь пуста
        """
        try:
            # Вызов RPC функции pgmq.read через REST API
            url = f"{self.base_url}/rest/v1/rpc/pgmq_read"
            payload = {
                "queue_name": queue_name,
                "vt": visibility_timeout,
                "qty": num_messages
            }
            
            response = self.http_client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            if data and len(data) > 0:
                job = data[0]
                logger.info(f"📥 Read job from {queue_name}: {job.get('msg_id')}")
                return job
            
            return None
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Функция не найдена - возможно PGMQ не установлен
                logger.warning(f"⚠️ PGMQ extension not available: {e}")
                return None
            logger.error(f"❌ HTTP error reading job: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error reading job: {str(e)}")
            return None
    
    def delete_job(self, queue_name: str, msg_id: int) -> bool:
        """
        Удаление сообщения из очереди (acknowledge).
        
        Args:
            queue_name: Имя очереди
            msg_id: ID сообщения
            
        Returns:
            True если успешно, False в противном случае
        """
        try:
            url = f"{self.base_url}/rest/v1/rpc/pgmq_delete"
            payload = {
                "queue_name": queue_name,
                "msg_id": msg_id
            }
            
            response = self.http_client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            logger.debug(f"✅ Deleted job {msg_id} from {queue_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting job {msg_id}: {str(e)}")
            return False
    
    def send_job(self, queue_name: str, message: Dict[str, Any]) -> Optional[int]:
        """
        Отправка сообщения в очередь.
        
        Args:
            queue_name: Имя очереди
            message: Сообщение для отправки
            
        Returns:
            ID сообщения или None в случае ошибки
        """
        try:
            url = f"{self.base_url}/rest/v1/rpc/pgmq_send"
            payload = {
                "queue_name": queue_name,
                "msg": message
            }
            
            response = self.http_client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            msg_id = response.json()
            logger.info(f"📤 Sent job to {queue_name}: {msg_id}")
            return msg_id
            
        except Exception as e:
            logger.error(f"❌ Error sending job to {queue_name}: {str(e)}")
            return None
    
    def archive_job(self, queue_name: str, msg_id: int) -> bool:
        """
        Архивирование сообщения (перемещение в архивную очередь).
        
        Args:
            queue_name: Имя очереди
            msg_id: ID сообщения
            
        Returns:
            True если успешно, False в противном случае
        """
        try:
            url = f"{self.base_url}/rest/v1/rpc/pgmq_archive"
            payload = {
                "queue_name": queue_name,
                "msg_id": msg_id
            }
            
            response = self.http_client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            logger.debug(f"📦 Archived job {msg_id} from {queue_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error archiving job {msg_id}: {str(e)}")
            return False
    
    def list_queues(self) -> List[str]:
        """
        Получение списка очередей.
        
        Returns:
            Список имен очередей
        """
        try:
            url = f"{self.base_url}/rest/v1/rpc/pgmq_list_queues"
            response = self.http_client.post(url, headers=self.headers)
            response.raise_for_status()
            
            queues = response.json()
            logger.info(f"📋 Found {len(queues)} queues")
            return queues
            
        except Exception as e:
            logger.error(f"❌ Error listing queues: {str(e)}")
            return []
    
    def test_connection(self) -> bool:
        """Тестирование подключения к PGMQ через REST API"""
        try:
            queues = self.list_queues()
            if queues is not None:
                logger.info("✅ PGMQ REST connection test passed")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ PGMQ REST connection test failed: {str(e)}")
            return False


# Синглтон экземпляр
_pgmq_client = None

def get_pgmq_client() -> PGMQRESTClient:
    """Получение экземпляра PGMQ REST клиента"""
    global _pgmq_client
    if _pgmq_client is None:
        _pgmq_client = PGMQRESTClient()
    return _pgmq_client
