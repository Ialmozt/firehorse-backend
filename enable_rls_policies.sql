-- Enable Row Level Security (RLS) for Firehorse tables
-- Created: 2026-01-13 11:50 UTC

-- 1. Enable RLS on fh_orders table
ALTER TABLE fh_orders ENABLE ROW LEVEL SECURITY;

-- 2. Enable RLS on fh_order_events table
ALTER TABLE fh_order_events ENABLE ROW LEVEL SECURITY;

-- 3. Drop existing policies if they exist (idempotent)
DROP POLICY IF EXISTS "Service role full access to fh_orders" ON fh_orders;
DROP POLICY IF EXISTS "Authenticated users can read fh_orders" ON fh_orders;
DROP POLICY IF EXISTS "Service role full access to fh_order_events" ON fh_order_events;
DROP POLICY IF EXISTS "Authenticated users can read fh_order_events" ON fh_order_events;

-- 4. Create policies for fh_orders table

-- Policy 1: Service role (backend) has full access
CREATE POLICY "Service role full access to fh_orders"
ON fh_orders
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Policy 2: Authenticated users (frontend) can read only
CREATE POLICY "Authenticated users can read fh_orders"
ON fh_orders
FOR SELECT
TO authenticated
USING (true);

-- 5. Create policies for fh_order_events table

-- Policy 1: Service role (backend) has full access
CREATE POLICY "Service role full access to fh_order_events"
ON fh_order_events
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Policy 2: Authenticated users (frontend) can read only
CREATE POLICY "Authenticated users can read fh_order_events"
ON fh_order_events
FOR SELECT
TO authenticated
USING (true);

-- 6. Test the policies by checking RLS status
DO $$
DECLARE
    rls_enabled_orders BOOLEAN;
    rls_enabled_events BOOLEAN;
    policy_count_orders INTEGER;
    policy_count_events INTEGER;
BEGIN
    -- Check if RLS is enabled
    SELECT relrowsecurity INTO rls_enabled_orders
    FROM pg_class
    WHERE relname = 'fh_orders' AND relnamespace = 'public'::regnamespace;
    
    SELECT relrowsecurity INTO rls_enabled_events
    FROM pg_class
    WHERE relname = 'fh_order_events' AND relnamespace = 'public'::regnamespace;
    
    -- Count policies
    SELECT COUNT(*) INTO policy_count_orders
    FROM pg_policies
    WHERE tablename = 'fh_orders' AND schemaname = 'public';
    
    SELECT COUNT(*) INTO policy_count_events
    FROM pg_policies
    WHERE tablename = 'fh_order_events' AND schemaname = 'public';
    
    RAISE NOTICE 'RLS Status:';
    RAISE NOTICE '  fh_orders: RLS enabled = %, Policies = %', rls_enabled_orders, policy_count_orders;
    RAISE NOTICE '  fh_order_events: RLS enabled = %, Policies = %', rls_enabled_events, policy_count_events;
    
    IF rls_enabled_orders AND rls_enabled_events AND policy_count_orders >= 2 AND policy_count_events >= 2 THEN
        RAISE NOTICE '✅ RLS configuration successful!';
        RAISE NOTICE '   Service role: Full access (INSERT, SELECT, UPDATE, DELETE)';
        RAISE NOTICE '   Authenticated users: Read-only access (SELECT)';
        RAISE NOTICE '   Anonymous users: No access (blocked by RLS)';
    ELSE
        RAISE NOTICE '⚠️ RLS configuration incomplete. Check the setup.';
    END IF;
END $$;

-- 7. Verify with a test query (should work with service role, fail with anon)
-- Note: This is commented out as it requires specific role context
/*
-- Test as service role (should work):
SET ROLE service_role;
SELECT COUNT(*) FROM fh_orders;
RESET ROLE;

-- Test as authenticated (should work for SELECT):
SET ROLE authenticated;
SELECT COUNT(*) FROM fh_orders;
-- INSERT should fail:
-- INSERT INTO fh_orders (source_id, topic) VALUES ('test', 'test');
RESET ROLE;

-- Test as anon (should fail):
SET ROLE anon;
-- SELECT COUNT(*) FROM fh_orders; -- Should fail
RESET ROLE;
*/

-- 8. Important notes for application:
--    - Backend uses service_role key → Full access
--    - Frontend uses anon key → No access (needs authentication)
--    - For MVP, frontend uses anon key with RLS disabled or with read policies
--    - For production, implement proper authentication

COMMENT ON TABLE fh_orders IS 'Firehorse orders table with RLS enabled - service_role: full access, authenticated: read-only';
COMMENT ON TABLE fh_order_events IS 'Firehorse order events table with RLS enabled - service_role: full access, authenticated: read-only';
