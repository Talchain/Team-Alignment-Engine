-- ============================================
-- OLUMI SUPABASE DATABASE DIAGNOSTIC
-- ============================================
-- Purpose: Assess current database state before TAE integration
-- Run this in Supabase SQL Editor and share results with workstream leads
-- ============================================

-- 1. ALL EXISTING TABLES
-- Shows every table currently in the database
SELECT
    schemaname AS schema,
    tablename AS table_name,
    tableowner AS owner
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema', 'auth', 'storage', 'extensions', 'graphql', 'graphql_public', 'net', 'pgbouncer', 'pgsodium', 'realtime', 'supabase_functions', 'vault')
ORDER BY schemaname, tablename;

-- 2. TABLE COLUMN DETAILS
-- Shows all columns for user-created tables
SELECT
    table_schema AS schema,
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default,
    character_maximum_length
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;

-- 3. FOREIGN KEY RELATIONSHIPS
-- Shows how tables reference each other
SELECT
    tc.table_name AS "from_table",
    kcu.column_name AS "from_column",
    ccu.table_name AS "to_table",
    ccu.column_name AS "to_column",
    tc.constraint_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema = 'public'
ORDER BY tc.table_name;

-- 4. POTENTIAL NAME CONFLICTS
-- Checks if common table names already exist
SELECT
    'CONFLICT' AS status,
    table_name,
    table_schema
FROM information_schema.tables
WHERE table_schema = 'public'
    AND table_name IN (
        -- Core platform tables
        'users', 'organizations', 'teams', 'workspaces',

        -- TAE proposed table names (would conflict if exist)
        'sessions', 'profiles', 'options', 'validations',
        'fits', 'concerns', 'decision_briefs',

        -- TAE deliberation tables
        'deliberation_sessions', 'deliberation_rounds',
        'deliberation_submissions', 'deliberation_votes',
        'deliberation_conflicts',

        -- TAE aggregation tables
        'user_accuracy_history', 'user_domain_expertise',

        -- TAE organizational tables
        'decision_dependencies', 'pattern_analysis_cache',
        'coordination_groups', 'detected_conflicts',
        'analytics_cache', 'assumption_validations',
        'decision_retrospectives'
    )
ORDER BY table_name;

-- 5. ROW COUNTS (Data Volume)
-- Shows how much data is in each table
SELECT
    schemaname,
    relname AS table_name,
    n_live_tup AS row_count,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||relname)) AS total_size
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_live_tup DESC;

-- 6. EXISTING SCHEMAS
-- Shows if any workstreams already use schema isolation
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'auth', 'storage', 'extensions', 'graphql', 'graphql_public', 'net', 'pgbouncer', 'pgsodium', 'realtime', 'supabase_functions', 'vault')
ORDER BY schema_name;

-- 7. RLS (Row Level Security) STATUS
-- Shows which tables have RLS enabled
SELECT
    schemaname,
    tablename,
    rowsecurity AS rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- 8. EXISTING INDEXES
-- Shows current indexing strategy
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
