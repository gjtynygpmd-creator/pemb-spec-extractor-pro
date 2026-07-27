-- Reference schema. The v1 backend also creates these tables automatically on startup.
CREATE TABLE IF NOT EXISTS projects (
  id varchar(36) PRIMARY KEY,
  name varchar(255) NOT NULL,
  customer varchar(255),
  address text,
  bid_due timestamptz,
  status varchar(40) NOT NULL DEFAULT 'draft',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
