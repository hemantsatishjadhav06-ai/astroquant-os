-- 001_extensions.sql — run once on a fresh database (before migrations).
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS vector;        -- pgvector (knowledge/discoveries/patterns)
