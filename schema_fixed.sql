-- ============================================
-- FIREHORSE MVP - PostgreSQL Schema (FIXED)
-- Created: 2026-01-09
-- Purpose: PGMQ job queues + order management
-- ============================================

-- EXTENSIONS
CREATE EXTENSION IF NOT EXISTS pgmq CASCADE;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- QUEUES (using correct PGMQ functions)
SELECT pgmq.create('job_queue');
SELECT pgmq.create('dlq_job_queue');

-- ORDERS TABLE
CREATE TABLE IF NOT EXISTS public.orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id TEXT NOT NULL UNIQUE,
    topic TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
    attempts INT NOT NULL DEFAULT 0,
    final_text TEXT,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ORDER_EVENTS TABLE (AUDIT LOG)
CREATE TABLE IF NOT EXISTS public.order_events (
    id BIGSERIAL PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES public.orders(id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    level TEXT NOT NULL CHECK (level IN ('INFO', 'WARN', 'ERROR')),
    message TEXT,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- INDEXES
CREATE INDEX IF NOT EXISTS idx_orders_status ON public.orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_source_id ON public.orders(source_id);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON public.orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_order_events_order_id ON public.order_events(order_id);
CREATE INDEX IF NOT EXISTS idx_order_events_level ON public.order_events(level);
CREATE INDEX IF NOT EXISTS idx_order_events_created_at ON public.order_events(created_at DESC);

-- ROW LEVEL SECURITY (PostgreSQL 17 compatible)
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.order_events ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DO $$ 
BEGIN
    DROP POLICY IF EXISTS orders_service_role ON public.orders;
    DROP POLICY IF EXISTS order_events_service_role ON public.order_events;
EXCEPTION
    WHEN undefined_object THEN NULL;
END $$;

-- Create new policies
CREATE POLICY orders_service_role ON public.orders
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY order_events_service_role ON public.order_events
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- GRANT permissions
GRANT ALL ON public.orders TO service_role;
GRANT ALL ON public.order_events TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.order_events_id_seq TO service_role;

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for orders table
DROP TRIGGER IF EXISTS update_orders_updated_at ON public.orders;
CREATE TRIGGER update_orders_updated_at
    BEFORE UPDATE ON public.orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Verification queries
COMMENT ON TABLE public.orders IS 'Firehorse orders table for Kwork content processing';
COMMENT ON TABLE public.order_events IS 'Firehorse order events audit log';