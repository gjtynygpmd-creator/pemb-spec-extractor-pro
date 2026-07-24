# Deployment

## Frontend
Deploy `frontend/` to Netlify.

## Backend
Deploy `backend/` to Render using its Dockerfile or `render.yaml`.

## Required backend environment variables
- DATABASE_URL
- S3_ENDPOINT_URL
- S3_ACCESS_KEY_ID
- S3_SECRET_ACCESS_KEY
- S3_BUCKET
- S3_REGION
- CORS_ORIGINS
- OPENAI_API_KEY

Never commit actual credentials to GitHub.
