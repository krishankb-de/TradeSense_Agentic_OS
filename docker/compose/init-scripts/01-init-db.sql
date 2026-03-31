-- Initialize TradeSense database schema
-- This script runs automatically when PostgreSQL container starts

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS tradesense;

-- Set search path
SET search_path TO tradesense, public;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA tradesense TO tradesense;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA tradesense TO tradesense;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA tradesense TO tradesense;

-- Create initial tables will be handled by Alembic migrations
-- This script just sets up the database structure
