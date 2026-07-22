
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    s3_endpoint_url: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket: str = "pemb-project-files"
    s3_region: str = "auto"
    cors_origins: str = "http://localhost:8888"
    max_file_size_gb: int = 20
    upload_expiration_seconds: int = 3600
    openai_api_key: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
