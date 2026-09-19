-- Initialize the competitive pricing database
-- This file runs automatically when the PostgreSQL container starts

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- The actual tables will be created by Alembic migrations
-- This file just ensures the database is ready for connections