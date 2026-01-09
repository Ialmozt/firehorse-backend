-- ============================================
-- FIREHORSE MVP - PostgreSQL Schema
-- Created: 2026-01-09
-- Purpose: PGMQ job queues + order management
-- ============================================

-- EXTENSIONS
CREATE EXTENSION IF NOT EXISTS pgmq;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- QUEUES
SELECT pgmq.create_job_queue('job_queue');
SELECT pgmq.create_dlq_job_queue('dlq_job_queue');

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
id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
order_id UUID REFERENCES public.orders(id) ON DELETE CASCADE,
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

-- ROW LEVEL SECURITY
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.order_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS orders_service_role ON public.orders
USING (true) WITH CHECK (true) TO service_role;
CREATE POLICY IF NOT EXISTS order_events_service_role ON public.order_events
USING (true) WITH CHECK (true) TO service_role;
