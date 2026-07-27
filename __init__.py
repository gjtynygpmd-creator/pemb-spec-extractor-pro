
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.session import Base, engine
from app.api.projects import router as projects_router
from app.api.uploads import router as uploads_router
from app.api.jobs import router as jobs_router
from app.api.fields import router as fields_router
from app.api.exports import router as exports_router
from app.models.project import Project, UploadedFile, ProcessingJob, ExtractedField, DocumentPage, ProcessingEvent

app = FastAPI(title="PEMB Spec Extractor Pro API", version="1.7.1")

# Always permit the production Netlify frontend and local development.
# Any additional origins supplied through CORS_ORIGINS are merged in rather
# than replacing these required defaults.
def _allowed_origins() -> list[str]:
    required = {
        "https://pemb-spec-extractor-pro.netlify.app",
        "http://localhost:8888",
        "http://localhost:3000",
        "http://127.0.0.1:8888",
    }
    configured = {
        origin.strip().rstrip("/")
        for origin in settings.cors_origins.split(",")
        if origin.strip()
    }
    return sorted(required | configured)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_origin_regex=r"https://.*--pemb-spec-extractor-pro\.netlify\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
    max_age=86400,
)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "storage_configured": bool(settings.s3_endpoint_url),
        "database_configured": bool(settings.database_url),
        "version": "1.7.1"
    }

app.include_router(projects_router)
app.include_router(uploads_router)
app.include_router(jobs_router)
app.include_router(fields_router)
app.include_router(exports_router)
