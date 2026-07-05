from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.routes import admin, auth, chat, conversations, datasources, evals, feedback, health, history, ingest
from app.core.config import settings
from app.db.session import Base, engine, ensure_runtime_schema_updates
from app.observability import setup_logging, setup_tracing

setup_logging()

app = FastAPI(title=settings.app_name)
setup_tracing(app)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
ensure_runtime_schema_updates()

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
app.include_router(chat.router, prefix=settings.api_prefix)
app.include_router(history.router, prefix=settings.api_prefix)
app.include_router(conversations.router, prefix=settings.api_prefix)
app.include_router(feedback.router, prefix=settings.api_prefix)
app.include_router(ingest.router, prefix=settings.api_prefix)
app.include_router(datasources.router, prefix=settings.api_prefix)
app.include_router(evals.router, prefix=settings.api_prefix)
