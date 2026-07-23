import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_production_netlify_preflight_is_allowed():
    response = client.options(
        "/projects",
        headers={
            "Origin": "https://pemb-spec-extractor-pro.netlify.app",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://pemb-spec-extractor-pro.netlify.app"
    assert "GET" in response.headers["access-control-allow-methods"]
