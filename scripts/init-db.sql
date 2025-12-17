-- Trybe Database Initialization Script

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgcrypto for encryption
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable pg_trgm for fuzzy text search
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set timezone
SET timezone = 'UTC';

-- Create custom types
DO $$ BEGIN
    CREATE TYPE user_type_enum AS ENUM ('professional', 'employer', 'company', 'admin');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE opportunity_status_enum AS ENUM ('open', 'closed', 'filled', 'archived');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE payment_status_enum AS ENUM ('proposed', 'counter_proposed', 'system_suggested', 'accepted', 'rejected', 'in_progress', 'completed', 'paid');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE opportunity_type_enum AS ENUM ('full_time', 'part_time', 'contract', 'freelance', 'gig', 'internship');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE experience_level_enum AS ENUM ('entry', 'junior', 'mid', 'senior', 'expert');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE swipe_action_enum AS ENUM ('like', 'pass', 'superlike');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE match_status_enum AS ENUM ('pending', 'accepted', 'rejected', 'expired');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE payment_type_enum AS ENUM ('hourly', 'fixed', 'milestone', 'commission');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE transaction_status_enum AS ENUM ('pending', 'processing', 'succeeded', 'failed', 'refunded', 'disputed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Trybe database initialized successfully';
END $$;
