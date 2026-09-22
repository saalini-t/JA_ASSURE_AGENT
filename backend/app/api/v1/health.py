from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.session import get_db
from app.config import settings
from app.services.llm_provider import llm_provider

router = APIRouter()

@router.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    # Verify DB connectivity
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "database_type": "postgresql" if "postgres" in settings.DATABASE_URL.lower() else "sqlite",
        "supabase_configured": bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY),
        "llm_provider": llm_provider.provider_name,
        "llm_model": llm_provider.model_name,
        "llm_mode": f"{llm_provider.provider_name.lower()}_live" if llm_provider.is_live else "demo_mock_mode",
        "supported_brands": settings.DEFAULT_BRANDS,
    }
