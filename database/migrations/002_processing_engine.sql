-- v1.2 Processing Engine
ALTER TABLE processing_jobs ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE processing_jobs ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE processing_jobs ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
ALTER TABLE processing_jobs ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS ix_processing_jobs_status ON processing_jobs(status);

CREATE TABLE IF NOT EXISTS document_pages (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    uploaded_file_id VARCHAR(36) NOT NULL REFERENCES uploaded_files(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    sheet_number VARCHAR(80),
    sheet_title VARCHAR(255),
    page_type VARCHAR(80) NOT NULL DEFAULT 'unclassified',
    spec_division VARCHAR(20),
    searchable_text BOOLEAN NOT NULL DEFAULT FALSE,
    ocr_required BOOLEAN NOT NULL DEFAULT FALSE,
    text_length INTEGER NOT NULL DEFAULT 0,
    text_excerpt TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_document_pages_project_id ON document_pages(project_id);
CREATE INDEX IF NOT EXISTS ix_document_pages_uploaded_file_id ON document_pages(uploaded_file_id);

CREATE TABLE IF NOT EXISTS processing_events (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    job_id VARCHAR(36) NOT NULL REFERENCES processing_jobs(id) ON DELETE CASCADE,
    stage VARCHAR(80) NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_processing_events_project_id ON processing_events(project_id);
CREATE INDEX IF NOT EXISTS ix_processing_events_job_id ON processing_events(job_id);
