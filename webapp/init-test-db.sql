-- Initialize test database with required extensions
-- Create extensions schema for security (extensions should not be in public)
CREATE SCHEMA IF NOT EXISTS extensions;

-- Create pg_trgm extension in extensions schema
CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA extensions;

-- Set search_path at database level so all connections include extensions schema
-- This is required for gin_trgm_ops operator class to be found
ALTER DATABASE seatsteal_test SET search_path = public, extensions;
