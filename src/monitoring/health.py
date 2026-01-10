"""
Health checks for Firehorse components.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import httpx
import psutil

from app.config import settings
from app.services.supabase_client import SupabaseClient
from src.services.deepseek_client_v2 import AdvancedDeepSeekClient

logger = logging.getLogger(__name__)


class HealthChecker:
    """Health checker for Firehorse components"""
    
    def __init__(self):
        self.checks: List[Dict[str, Any]] = []
        self.last_check_time: Optional[datetime] = None
        self.check_results: Dict[str, Dict[str, Any]] = {}
        
    def register_check(self, name: str, check_func, interval_seconds: int = 30):
        """Register a health check"""
        self.checks.append({
            "name": name,
            "func": check_func,
            "interval": interval_seconds,
            "last_run": None,
            "result": None
        })
    
    async def run_check(self, check: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single health check"""
        try:
            start_time = datetime.now()
            result = await check["func"]()
            duration = (datetime.now() - start_time).total_seconds()
            
            check_result = {
                "name": check["name"],
                "status": result.get("status", "unknown"),
                "healthy": result.get("healthy", False),
                "message": result.get("message", ""),
                "details": result.get("details", {}),
                "duration": duration,
                "timestamp": datetime.now().isoformat(),
                "error": None
            }
            
            check["last_run"] = datetime.now()
            check["result"] = check_result
            
            # Store in results
            self.check_results[check["name"]] = check_result
            
            return check_result
            
        except Exception as e:
            logger.error(f"Health check '{check['name']}' failed: {e}")
            
            check_result = {
                "name": check["name"],
                "status": "error",
                "healthy": False,
                "message": f"Check failed: {str(e)}",
                "details": {},
                "duration": 0,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
            
            check["last_run"] = datetime.now()
            check["result"] = check_result
            
            self.check_results[check["name"]] = check_result
            
            return check_result
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all registered health checks"""
        self.last_check_time = datetime.now()
        
        tasks = []
        for check in self.checks:
            # Check if enough time has passed since last run
            if (check["last_run"] is None or 
                (datetime.now() - check["last_run"]).total_seconds() >= check["interval"]):
                tasks.append(self.run_check(check))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Health check task failed: {result}")
        
        return self.get_overall_health()
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall health status"""
        if not self.check_results:
            return {
                "status": "unknown",
                "healthy": False,
                "message": "No health checks have been run",
                "checks": {},
                "timestamp": datetime.now().isoformat()
            }
        
        # Calculate overall status
        total_checks = len(self.check_results)
        healthy_checks = sum(1 for r in self.check_results.values() if r["healthy"])
        
        if total_checks == 0:
            overall_healthy = False
            overall_status = "unknown"
        elif healthy_checks == total_checks:
            overall_healthy = True
            overall_status = "healthy"
        elif healthy_checks == 0:
            overall_healthy = False
            overall_status = "critical"
        else:
            overall_healthy = False
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "healthy": overall_healthy,
            "message": f"{healthy_checks}/{total_checks} checks healthy",
            "checks": self.check_results,
            "timestamp": datetime.now().isoformat(),
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None
        }
    
    async def start_periodic_checks(self, interval_seconds: int = 30):
        """Start periodic health checks"""
        logger.info(f"Starting periodic health checks every {interval_seconds} seconds")
        
        while True:
            try:
                await self.run_all_checks()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                logger.info("Periodic health checks cancelled")
                break
            except Exception as e:
                logger.error(f"Periodic health check failed: {e}")
                await asyncio.sleep(interval_seconds)


async def check_database_health() -> Dict[str, Any]:
    """Check database health"""
    try:
        supabase = SupabaseClient(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Test connection with a simple query
        start_time = datetime.now()
        result = await supabase.test_connection()
        duration = (datetime.now() - start_time).total_seconds()
        
        if result:
            return {
                "status": "healthy",
                "healthy": True,
                "message": "Database connection successful",
                "details": {
                    "connection_time": duration,
                    "database": "Supabase PostgreSQL"
                }
            }
        else:
            return {
                "status": "unhealthy",
                "healthy": False,
                "message": "Database connection failed",
                "details": {
                    "connection_time": duration
                }
            }
            
    except Exception as e:
        return {
            "status": "error",
            "healthy": False,
            "message": f"Database check failed: {str(e)}",
            "details": {
                "error": str(e)
            }
        }


async def check_deepseek_health() -> Dict[str, Any]:
    """Check DeepSeek API health"""
    try:
        deepseek = AdvancedDeepSeekClient()
        
        # Test connection
        start_time = datetime.now()
        connected = await deepseek.test_connection()
        duration = (datetime.now() - start_time).total_seconds()
        
        if connected:
            return {
                "status": "healthy",
                "healthy": True,
                "message": "DeepSeek API connection successful",
                "details": {
                    "connection_time": duration,
                    "api_key_configured": bool(settings.DEEPSEEK_API_KEY)
                }
            }
        else:
            return {
                "status": "unhealthy",
                "healthy": False,
                "message": "DeepSeek API connection failed",
                "details": {
                    "connection_time": duration,
                    "api_key_configured": bool(settings.DEEPSEEK_API_KEY)
                }
            }
            
    except Exception as e:
        return {
            "status": "error",
            "healthy": False,
            "message": f"DeepSeek check failed: {str(e)}",
            "details": {
                "error": str(e)
            }
        }


async def check_vpn_health() -> Dict[str, Any]:
    """Check VPN connection health"""
    try:
        # Test VPN connectivity by trying to connect to a known endpoint
        # through the VPN proxy
        vpn_port = getattr(settings, 'VPN_HTTP_PORT', 7890)
        proxy_url = f"http://127.0.0.1:{vpn_port}"
        
        async with httpx.AsyncClient(
            timeout=10.0,
            proxies={"http://": proxy_url, "https://": proxy_url}
        ) as client:
            start_time = datetime.now()
            
            # Try to connect to a test endpoint
            response = await client.get("http://httpbin.org/ip", timeout=5.0)
            duration = (datetime.now() - start_time).total_seconds()
            
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "healthy": True,
                    "message": "VPN connection successful",
                    "details": {
                        "connection_time": duration,
                        "proxy_port": vpn_port,
                        "response_ip": response.json().get("origin", "unknown")
                    }
                }
            else:
                return {
                    "status": "unhealthy",
                    "healthy": False,
                    "message": f"VPN connection failed with status {response.status_code}",
                    "details": {
                        "connection_time": duration,
                        "status_code": response.status_code
                    }
                }
                
    except Exception as e:
        vpn_port = getattr(settings, 'VPN_HTTP_PORT', 7890)
        return {
            "status": "error",
            "healthy": False,
            "message": f"VPN check failed: {str(e)}",
            "details": {
                "error": str(e),
                "proxy_port": vpn_port
            }
        }


async def check_system_health() -> Dict[str, Any]:
    """Check system health (CPU, memory, disk)"""
    try:
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Get memory usage
        memory = psutil.virtual_memory()
        
        # Get disk usage
        disk = psutil.disk_usage("/")
        
        # Determine health status
        healthy = True
        issues = []
        
        if cpu_percent > 90:
            healthy = False
            issues.append(f"High CPU usage: {cpu_percent}%")
        
        if memory.percent > 90:
            healthy = False
            issues.append(f"High memory usage: {memory.percent}%")
        
        if disk.percent > 90:
            healthy = False
            issues.append(f"High disk usage: {disk.percent}%")
        
        status = "healthy" if healthy else "degraded"
        message = "System resources OK" if healthy else f"Issues: {', '.join(issues)}"
        
        return {
            "status": status,
            "healthy": healthy,
            "message": message,
            "details": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3)
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "healthy": False,
            "message": f"System check failed: {str(e)}",
            "details": {
                "error": str(e)
            }
        }


async def check_queue_health() -> Dict[str, Any]:
    """Check queue health"""
    try:
        supabase = SupabaseClient(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Get queue depth
        queue_depth = await supabase.get_queue_depth()
        
        # Determine health status
        healthy = True
        message = "Queue depth normal"
        
        if queue_depth > 100:
            healthy = False
            message = f"High queue depth: {queue_depth}"
        elif queue_depth > 50:
            message = f"Moderate queue depth: {queue_depth}"
        
        return {
            "status": "healthy" if healthy else "degraded",
            "healthy": healthy,
            "message": message,
            "details": {
                "queue_depth": queue_depth,
                "threshold_warning": 50,
                "threshold_critical": 100
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "healthy": False,
            "message": f"Queue check failed: {str(e)}",
            "details": {
                "error": str(e)
            }
        }


async def perform_health_check() -> Dict[str, Any]:
    """Perform comprehensive health check"""
    health_checker = HealthChecker()
    
    # Register all checks
    health_checker.register_check("database", check_database_health)
    health_checker.register_check("deepseek", check_deepseek_health)
    health_checker.register_check("vpn", check_vpn_health)
    health_checker.register_check("system", check_system_health)
    health_checker.register_check("queue", check_queue_health)
    
    # Run all checks
    return await health_checker.run_all_checks()


# Create global health checker instance
_global_health_checker = HealthChecker()


def get_global_health_checker() -> HealthChecker:
    """Get global health checker instance"""
    return _global_health_checker


async def setup_health_checks():
    """Setup health checks"""
    global _global_health_checker
    
    # Register checks
    _global_health_checker.register_check("database", check_database_health)
    _global_health_checker.register_check("deepseek", check_deepseek_health)
    _global_health_checker.register_check("vpn", check_vpn_health)
    _global_health_checker.register_check("system", check_system_health)
    _global_health_checker.register_check("queue", check_queue_health)
    
    logger.info("Health checks setup complete")
    return _global_health_checker
