
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.session import Base, engine
from app.api.projects import router as projects_router
from app.api.uploads import router as uploads_router
from app.api.jobs import router as jobs_router
from app.models.project import Project, UploadedFile, ProcessingJob, ExtractedField

app = FastAPI(title="PEMB Spec Extractor Pro API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        "version": "1.1.0"
    }

app.include_router(projects_router)
app.include_router(uploads_router)
app.include_router(jobs_router)
