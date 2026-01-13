
-- 🔥 FIREHORSE COMPLETE SCHEMA (from 02-ROADMAP)
-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS pgmq SCHEMA public CASCADE;
CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA public CASCADE;

-- 2. TABLES
CREATE TABLE IF NOT EXISTS public.orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sourceid TEXT UNIQUE NOT NULL,
    topic TEXT NOT NULL,
    finaltext TEXT,
    status TEXT CHECK (status IN ('queued', 'processing', 'completed', 'failed')) DEFAULT 'queued',
    attempts INT DEFAULT 0,
    lasterror TEXT,
    metrics JSONB DEFAULT '{}',
    createdat TIMESTAMPTZ DEFAULT now(),
    updatedat TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_orders_status ON public.orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_sourceid ON public.orders(sourceid);
CREATE INDEX IF NOT EXISTS idx_orders_createdat ON public.orders(createdat DESC);

CREATE TABLE IF NOT EXISTS public.orderevents (
    id BIGSERIAL PRIMARY KEY,
    orderid UUID REFERENCES public.orders(id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    level TEXT CHECK (level IN ('INFO', 'WARN', 'ERROR')) DEFAULT 'INFO',
    message TEXT,
    meta JSONB DEFAULT '{}',
    createdat TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_orderevents_orderid ON public.orderevents(orderid);
CREATE INDEX IF NOT EXISTS idx_orderevents_level ON public.orderevents(level);
CREATE INDEX IF NOT EXISTS idx_orderevents_createdat ON public.orderevents(createdat);

-- 3. RLS (Service Role bypass)
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orderevents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access" ON public.orders
FOR ALL USING (true) WITH CHECK (true) TO service_role;

CREATE POLICY "Service role full access events" ON public.orderevents  
FOR ALL USING (true) WITH CHECK (true) TO service_role;

-- 4. PGMQ QUEUE
SELECT pgmq.create('jobqueue');

-- 5. CRITICAL RPCs
CREATE OR REPLACE FUNCTION public.fhingress(psourceid TEXT, ptopic TEXT)
RETURNS TABLE (orderid UUID, created BOOLEAN) AS $$
DECLARE
    vid UUID;
BEGIN
    -- UPSERT order (idempotent)
    INSERT INTO public.orders (sourceid, topic, status)
    VALUES (psourceid, ptopic, 'queued')
    ON CONFLICT (sourceid) DO NOTHING
    RETURNING id INTO vid;

    IF NOT FOUND THEN
        -- Already exists
        SELECT id INTO vid FROM public.orders WHERE sourceid = psourceid;
        INSERT INTO public.orderevents (orderid, stage, level, message)
        VALUES (vid, 'ingress', 'INFO', 'Order exists');
        RETURN QUERY SELECT vid, false;
        RETURN;
    END IF;

    -- Queue message
    PERFORM pgmq.send(
        'jobqueue',
        jsonb_build_object('orderid', vid::TEXT)
    );

    -- Log event
    INSERT INTO public.orderevents (orderid, stage, level, message, meta)
    VALUES (vid, 'ingress', 'INFO', 'Enqueued', jsonb_build_object('sourceid', psourceid));

    RETURN QUERY SELECT vid, true;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Test RPC
SELECT * FROM public.fhingress('test-123', 'Test Topic');
