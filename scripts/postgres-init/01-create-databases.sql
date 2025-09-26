-- Initialize required databases for the Learning Agent stack
-- This file runs only on first initialization of the Postgres data volume.

-- Create databases if they don't already exist (entrypoint only runs once)
CREATE DATABASE learning_memories OWNER learning_agent;
CREATE DATABASE learning_agent OWNER learning_agent;

