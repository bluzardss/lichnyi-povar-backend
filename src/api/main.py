from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from src.api.routes import recipes, user, images
from src.db.models import Base
from src.db.session import engine, SessionLocal
from src.config import config
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Личный Повар API",
    description="API для Telegram Mini App «Личный Повар»",
    version="0.1.0",
)

# Debug middleware to log all requests
async def log_requests(request: Request, call_next):
    print(f"DEBUG: Request: {request.method} {request.url.path}", flush=True)
    response = await call_next(request)
    print(f"DEBUG: Response: {response.status_code} for {request.method} {request.url.path}", flush=True)
    return response

app.add_middleware(BaseHTTPMiddleware, dispatch=log_requests)

# CORS настройки для разрешения запросов от Telegram Web App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене стоит указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(recipes.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(images.router, prefix="/api")

# Dependency для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Создаем таблицы при старте приложения (если они не существуют)
@app.on_event("startup")
async def on_startup():
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")
    # Debug: print middleware stack
    print(f"DEBUG STARTUP: Middleware count: {len(app.user_middleware)}", flush=True)
    for m in app.user_middleware:
        print(f"DEBUG STARTUP: Middleware: {m}", flush=True)
    # Debug: print routes
    print(f"DEBUG STARTUP: Routes count: {len(app.routes)}", flush=True)
    for r in app.routes:
        if hasattr(r, 'methods'):
            print(f"DEBUG STARTUP: Route: {r.path} - {r.methods}", flush=True)

@app.get("/")
async def root():
    return {"message": "Личный Повар API работает"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Debug endpoint to check middleware stack
@app.get("/debug/middleware")
async def debug_middleware(request: Request):
    return {
        "middleware_count": len(app.user_middleware),
        "middleware": [str(m) for m in app.user_middleware],
        "routes": [{"path": r.path, "methods": list(r.methods)} for r in app.routes if hasattr(r, "methods")],
    }
