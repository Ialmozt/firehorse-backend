from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from app.config import settings
from app.routes import health, webhook

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORS
origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "https://barsk.online",
    "https://www.barsk.online",
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация при старте приложения"""
    logger.info("🚀 FIREHORSE API starting...")
    yield
    logger.info("🛑 FIREHORSE API shutting down...")

# Создание приложения
app = FastAPI(
    title="FIREHORSE API",
    description="FastAPI backend для Kwork + DeepSeek автоматизации",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роуты
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(webhook.router, prefix="/api", tags=["webhook"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "FIREHORSE API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/health",
            "kwork_webhook": "/api/webhook/kwork",
            "webhook_test": "/api/webhook/kwork/test (dev only)",
            "info": "/api/info"
        }
    }

@app.get("/api/info")
async def info():
    return {
        "service": "FIREHORSE",
        "version": "1.0.0",
        "environment": "production" if not settings.DEBUG else "development",
        "endpoints": {
            "health": "/api/health",
            "kwork_webhook": {
                "path": "/api/webhook/kwork",
                "method": "POST",
                "description": "Accept Kwork webhook, save to Supabase, create PGMQ job"
            },
            "webhook_test": "/api/webhook/kwork/test (development only)",
            "webhook_simulate": "/api/webhook/kwork/simulate (development only)"
        },
        "features": {
            "kwork_integration": True,
            "supabase_storage": True,
            "pgmq_job_queue": True,
            "deepseek_ai": True
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
