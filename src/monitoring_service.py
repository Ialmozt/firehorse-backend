"""
Monitoring Service для Firehorse MVP.
Отслеживает состояние системы, генерирует алерты и агрегирует метрики.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Уровни алертов."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class Alert:
    """Структура алерта."""
    level: AlertLevel
    message: str
    timestamp: datetime
    metric_name: Optional[str] = None
    value: Optional[float] = None
    threshold: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Преобразовать алерт в словарь."""
        return {
            "level": self.level.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "metric_name": self.metric_name,
            "value": self.value,
            "threshold": self.threshold
        }


class TimeWindow:
    """Окно времени для агрегации метрик."""
    
    def __init__(self, seconds: int):
        self.seconds = seconds
        self.data: List[Tuple[datetime, Dict]] = []
        self.lock = asyncio.Lock()
    
    async def add(self, timestamp: datetime, data: Dict):
        """Добавить данные в окно."""
        async with self.lock:
            self.data.append((timestamp, data))
            # Удалить старые данные
            cutoff = timestamp - timedelta(seconds=self.seconds)
            self.data = [(ts, d) for ts, d in self.data if ts >= cutoff]
    
    async def get_summary(self) -> Dict:
        """Получить агрегированные данные за окно."""
        async with self.lock:
            if not self.data:
                return {}
            
            # Агрегировать все метрики
            summary = {}
            for _, data in self.data:
                for key, value in data.items():
                    if isinstance(value, (int, float)):
                        if key not in summary:
                            summary[key] = []
                        summary[key].append(value)
            
            # Вычислить статистики
            result = {}
            for key, values in summary.items():
                if values:
                    result[f"{key}_count"] = len(values)
                    result[f"{key}_sum"] = sum(values)
                    result[f"{key}_avg"] = sum(values) / len(values)
                    result[f"{key}_min"] = min(values)
                    result[f"{key}_max"] = max(values)
                    # p95
                    sorted_values = sorted(values)
                    idx = int(len(sorted_values) * 0.95)
                    result[f"{key}_p95"] = sorted_values[idx] if idx < len(sorted_values) else sorted_values[-1]
            
            return result


class MonitoringService:
    """
    Сервис мониторинга для отслеживания состояния системы.
    
    Отслеживает:
    - Запросы и ошибки
    - Производительность API
    - Состояние очередей
    - Здоровье системы
    """
    
    def __init__(self):
        self.windows = {
            "5min": TimeWindow(300),  # 5 минут
            "1hr": TimeWindow(3600),  # 1 час
            "24hr": TimeWindow(86400),  # 24 часа
        }
        
        self.alerts: List[Alert] = []
        self.alert_lock = asyncio.Lock()
        
        # Состояние системы
        self.system_start_time = datetime.utcnow()
        self.last_error_time: Optional[datetime] = None
        self.error_counts: Dict[str, int] = {}
        
        logger.info("MonitoringService initialized")
    
    async def record_request(self, endpoint: str, status_code: int, duration: float):
        """
        Записать информацию о запросе.
        
        Args:
            endpoint: Путь эндпоинта
            status_code: HTTP статус код
            duration: Длительность запроса в секундах
        """
        timestamp = datetime.utcnow()
        data = {
            "request_duration": duration,
            "status_code": status_code,
        }
        
        # Добавить во все окна
        for window in self.windows.values():
            await window.add(timestamp, data)
        
        # Проверить на алерты
        if duration > 5.0:  # Запрос длится более 5 секунд
            await self._add_alert(
                AlertLevel.WARNING,
                f"Slow request detected: {endpoint} took {duration:.2f}s",
                metric_name="request_duration",
                value=duration,
                threshold=5.0
            )
        
        if status_code >= 500:
            await self._add_alert(
                AlertLevel.CRITICAL,
                f"Server error on {endpoint}: {status_code}",
                metric_name="status_code",
                value=status_code,
                threshold=500
            )
    
    async def record_error(self, endpoint: str, error_type: str):
        """
        Записать информацию об ошибке.
        
        Args:
            endpoint: Путь эндпоинта
            error_type: Тип ошибки
        """
        timestamp = datetime.utcnow()
        self.last_error_time = timestamp
        
        # Обновить счетчик ошибок
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        data = {
            "error_count": 1,
        }
        
        for window in self.windows.values():
            await window.add(timestamp, data)
        
        # Проверить частоту ошибок
        error_rate = await self._calculate_error_rate()
        if error_rate > 10.0:  # Более 10% ошибок
            await self._add_alert(
                AlertLevel.CRITICAL,
                f"High error rate detected: {error_rate:.1f}%",
                metric_name="error_rate",
                value=error_rate,
                threshold=10.0
            )
    
    async def record_api_call(self, api_name: str, status_code: int, duration: float):
        """
        Записать информацию о вызове внешнего API.
        
        Args:
            api_name: Название API (deepseek, kwork, etc.)
            status_code: HTTP статус код
            duration: Длительность вызова в секундах
        """
        timestamp = datetime.utcnow()
        data = {
            f"api_{api_name}_duration": duration,
            f"api_{api_name}_status": status_code,
        }
        
        for window in self.windows.values():
            await window.add(timestamp, data)
        
        # Проверить на алерты
        if duration > 30.0:  # API вызов длится более 30 секунд
            await self._add_alert(
                AlertLevel.WARNING,
                f"Slow API call: {api_name} took {duration:.2f}s",
                metric_name=f"api_{api_name}_duration",
                value=duration,
                threshold=30.0
            )
        
        if status_code >= 400:
            await self._add_alert(
                AlertLevel.WARNING,
                f"API error: {api_name} returned {status_code}",
                metric_name=f"api_{api_name}_status",
                value=status_code,
                threshold=400
            )
    
    async def get_health_status(self) -> Dict:
        """
        Получить статус здоровья системы.
        
        Returns:
            Словарь с информацией о здоровье системы
        """
        error_rate = await self._calculate_error_rate()
        uptime = (datetime.utcnow() - self.system_start_time).total_seconds()
        
        # Получить агрегированные метрики
        metrics_5min = await self.windows["5min"].get_summary()
        metrics_1hr = await self.windows["1hr"].get_summary()
        
        # Определить общий статус
        if error_rate > 20.0:
            overall_status = "CRITICAL"
        elif error_rate > 5.0:
            overall_status = "WARNING"
        else:
            overall_status = "HEALTHY"
        
        return {
            "status": overall_status,
            "uptime_seconds": uptime,
            "error_rate_percent": error_rate,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "error_counts": self.error_counts,
            "metrics_5min": metrics_5min,
            "metrics_1hr": metrics_1hr,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    async def get_alerts(self, level: Optional[AlertLevel] = None) -> List[Alert]:
        """
        Получить алерты.
        
        Args:
            level: Фильтр по уровню алерта
            
        Returns:
            Список алертов
        """
        async with self.alert_lock:
            if level:
                return [alert for alert in self.alerts if alert.level == level]
            return self.alerts.copy()
    
    async def get_performance_summary(self) -> Dict:
        """
        Получить сводку по производительности.
        
        Returns:
            Словарь с метриками производительности
        """
        metrics_5min = await self.windows["5min"].get_summary()
        metrics_1hr = await self.windows["1hr"].get_summary()
        metrics_24hr = await self.windows["24hr"].get_summary()
        
        # Вычислить производные метрики
        summary = {
            "time_windows": {
                "5min": metrics_5min,
                "1hr": metrics_1hr,
                "24hr": metrics_24hr,
            },
            "derived_metrics": {},
        }
        
        # Вычислить процент ошибок
        if "error_count_sum" in metrics_5min and "request_duration_count" in metrics_5min:
            error_count = metrics_5min.get("error_count_sum", 0)
            request_count = metrics_5min.get("request_duration_count", 0)
            if request_count > 0:
                summary["derived_metrics"]["error_rate_5min_percent"] = (error_count / request_count) * 100
        
        # Вычислить среднее время ответа
        if "request_duration_avg" in metrics_5min:
            summary["derived_metrics"]["avg_response_time_5min_seconds"] = metrics_5min["request_duration_avg"]
        
        if "request_duration_p95" in metrics_5min:
            summary["derived_metrics"]["p95_response_time_5min_seconds"] = metrics_5min["request_duration_p95"]
        
        return summary
    
    async def cleanup(self):
        """Очистить старые данные."""
        # Удалить алерты старше 24 часов
        cutoff = datetime.utcnow() - timedelta(hours=24)
        async with self.alert_lock:
            self.alerts = [alert for alert in self.alerts if alert.timestamp >= cutoff]
        
        logger.debug("MonitoringService cleanup completed")
    
    async def _calculate_error_rate(self) -> float:
        """Вычислить процент ошибок за последние 5 минут."""
        metrics = await self.windows["5min"].get_summary()
        
        error_count = metrics.get("error_count_sum", 0)
        request_count = metrics.get("request_duration_count", 0)
        
        if request_count == 0:
            return 0.0
        
        return (error_count / request_count) * 100
    
    async def _add_alert(self, level: AlertLevel, message: str, 
                         metric_name: Optional[str] = None, 
                         value: Optional[float] = None,
                         threshold: Optional[float] = None):
        """Добавить алерт."""
        alert = Alert(
            level=level,
            message=message,
            timestamp=datetime.utcnow(),
            metric_name=metric_name,
            value=value,
            threshold=threshold
        )
        
        async with self.alert_lock:
            self.alerts.append(alert)
        
        # Логировать алерт
        log_method = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.CRITICAL: logger.error,
        }[level]
        
        log_method(f"Alert: {message}")


# Глобальный экземпляр сервиса мониторинга
_monitoring_service: Optional[MonitoringService] = None


def get_monitoring_service() -> MonitoringService:
    """
    Получить глобальный экземпляр MonitoringService.
    
    Returns:
        Экземпляр MonitoringService
    """
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service


async def start_monitoring_cleanup_task():
    """Запустить задачу периодической очистки."""
    service = get_monitoring_service()
    
    while True:
        try:
            await asyncio.sleep(300)  # Каждые 5 минут
            await service.cleanup()
        except Exception as e:
            logger.error(f"Monitoring cleanup task failed: {e}")
            await asyncio.sleep(60)  # Подождать минуту перед повторной попыткой