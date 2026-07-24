services:
  - type: web
    name: pemb-spec-extractor-api
    runtime: docker
    plan: starter
    dockerfilePath: ./Dockerfile
    healthCheckPath: /health
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: S3_ENDPOINT_URL
        sync: false
      - key: S3_ACCESS_KEY_ID
        sync: false
      - key: S3_SECRET_ACCESS_KEY
        sync: false
      - key: S3_BUCKET
        value: pemb-project-files
      - key: S3_REGION
        value: auto
      - key: CORS_ORIGINS
        sync: false

  - type: worker
    name: pemb-spec-extractor-worker
    runtime: docker
    plan: starter
    dockerfilePath: ./Dockerfile
    dockerCommand: python -m app.worker
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: S3_ENDPOINT_URL
        sync: false
      - key: S3_ACCESS_KEY_ID
        sync: false
      - key: S3_SECRET_ACCESS_KEY
        sync: false
      - key: S3_BUCKET
        value: pemb-project-files
      - key: S3_REGION
        value: auto
      - key: WORKER_POLL_SECONDS
        value: 8
      # v1.9.x vision extraction (drawings + scanned pages), provider-agnostic
      - key: VISION_PROVIDER
        value: openai
      - key: VISION_EXTRACTION_ENABLED
        value: "true"
      - key: OPENAI_API_KEY
        sync: false
      - key: VISION_MODEL_OPENAI
        value: gpt-4o
      # Only needed if VISION_PROVIDER is switched to "anthropic"
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: VISION_MODEL_ANTHROPIC
        value: claude-opus-4-8
      - key: VISION_DPI
        value: "200"
      - key: TEXT_LAYER_MIN_CHARS
        value: "200"
      - key: TEXT_LAYER_MIN_LABELS
        value: "3"
