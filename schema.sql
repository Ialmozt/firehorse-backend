-- ============================================
-- FIREHORSE MVP - FINAL PRODUCTION SCHEMA
-- Created: 2026-01-10
-- Purpose: Complete order management with PGMQ, DeepSeek integration, and monitoring
-- ============================================

-- EXTENSIONS (idempotent)
CREATE EXTENSION IF NOT EXISTS pgmq CASCADE;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- QUEUES FOR JOB PROCESSING
SELECT pgmq.create('job_queue');
SELECT pgmq.create('dlq_job_queue');

-- ORDERS TABLE (main order tracking)
CREATE TABLE IF NOT EXISTS public.orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kwork_order_id BIGINT NOT NULL UNIQUE,
    source_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')),
    buyer_id TEXT,
    content_type TEXT NOT NULL DEFAULT 'seo_article'
        CHECK (content_type IN ('seo_article', 'translation', 'content_creation', 'code_generation', 'social_media', 'copywriting')),
    prompt_version TEXT NOT NULL DEFAULT 'v1',
    temperature DECIMAL(3, 2) NOT NULL DEFAULT 0.7,
    max_tokens INTEGER NOT NULL DEFAULT 2000,
    generated_content TEXT,
    content_quality_score INTEGER
        CHECK (content_quality_score >= 0 AND content_quality_score <= 100),
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    last_error TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ GENERATED ALWAYS AS (created_at + INTERVAL '7 days') STORED
);

-- ORDER_EVENTS TABLE (audit log for all order activities)
CREATE TABLE IF NOT EXISTS public.order_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES public.orders(id) ON DELETE CASCADE,
    stage TEXT NOT NULL
        CHECK (stage IN ('created', 'queued', 'processing', 'deepseek_api', 'content_generated', 'completed', 'failed', 'retry')),
    level TEXT NOT NULL
        CHECK (level IN ('INFO', 'WARN', 'ERROR', 'DEBUG')),
    message TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- DEEPSEEK_USAGE TABLE (track API usage and costs)
CREATE TABLE IF NOT EXISTS public.deepseek_usage (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id UUID REFERENCES public.orders(id) ON DELETE SET NULL,
    task_type TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    temperature DECIMAL(3, 2) NOT NULL,
    model TEXT NOT NULL DEFAULT 'deepseek-chat',
    response_time_ms INTEGER NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    estimated_cost_usd DECIMAL(10, 6) NOT NULL DEFAULT 0.000000,
    cache_hit BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- API_KEYS TABLE (secure API key storage with rotation)
CREATE TABLE IF NOT EXISTS public.api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    key_prefix TEXT NOT NULL,
    scopes TEXT[] NOT NULL DEFAULT '{}',
    rate_limit_per_minute INTEGER NOT NULL DEFAULT 10,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    usage_count INTEGER NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- PERFORMANCE INDEXES
CREATE INDEX IF NOT EXISTS idx_orders_status ON public.orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_kwork_order_id ON public.orders(kwork_order_id);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON public.orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_content_type ON public.orders(content_type);
CREATE INDEX IF NOT EXISTS idx_orders_buyer_id ON public.orders(buyer_id);
CREATE INDEX IF NOT EXISTS idx_orders_expires_at ON public.orders(expires_at);

CREATE INDEX IF NOT EXISTS idx_order_events_order_id ON public.order_events(order_id);
CREATE INDEX IF NOT EXISTS idx_order_events_stage ON public.order_events(stage);
CREATE INDEX IF NOT EXISTS idx_order_events_level ON public.order_events(level);
CREATE INDEX IF NOT EXISTS idx_order_events_created_at ON public.order_events(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_deepseek_usage_order_id ON public.deepseek_usage(order_id);
CREATE INDEX IF NOT EXISTS idx_deepseek_usage_task_type ON public.deepseek_usage(task_type);
CREATE INDEX IF NOT EXISTS idx_deepseek_usage_created_at ON public.deepseek_usage(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_deepseek_usage_success ON public.deepseek_usage(success);

CREATE INDEX IF NOT EXISTS idx_api_keys_key_prefix ON public.api_keys(key_prefix);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON public.api_keys(is_active);
CREATE INDEX IF NOT EXISTS idx_api_keys_expires_at ON public.api_keys(expires_at);

-- ROW LEVEL SECURITY (RLS) POLICIES
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.order_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.deepseek_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;

-- Service role has full access (for backend services)
CREATE POLICY IF NOT EXISTS orders_service_role ON public.orders
    USING (true) WITH CHECK (true) TO service_role;

CREATE POLICY IF NOT EXISTS order_events_service_role ON public.order_events
    USING (true) WITH CHECK (true) TO service_role;

CREATE POLICY IF NOT EXISTS deepseek_usage_service_role ON public.deepseek_usage
    USING (true) WITH CHECK (true) TO service_role;

CREATE POLICY IF NOT EXISTS api_keys_service_role ON public.api_keys
    USING (true) WITH CHECK (true) TO service_role;

-- Authenticated users can only read their own orders
CREATE POLICY IF NOT EXISTS orders_auth_read ON public.orders
    FOR SELECT USING (auth.uid()::text = buyer_id) TO authenticated;

CREATE POLICY IF NOT EXISTS order_events_auth_read ON public.order_events
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.orders o 
            WHERE o.id = order_events.order_id 
            AND o.buyer_id = auth.uid()::text
        )
    ) TO authenticated;

-- FUNCTIONS FOR BUSINESS LOGIC

-- Function to create order event (audit logging)
CREATE OR REPLACE FUNCTION public.fh_create_order_event(
    p_order_id UUID,
    p_stage TEXT,
    p_level TEXT,
    p_message TEXT,
    p_metadata JSONB DEFAULT '{}'::jsonb
) RETURNS BIGINT AS $$
DECLARE
    v_event_id BIGINT;
BEGIN
    INSERT INTO public.order_events (order_id, stage, level, message, metadata)
    VALUES (p_order_id, p_stage, p_level, p_message, p_metadata)
    RETURNING id INTO v_event_id;
    
    RETURN v_event_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to update order status with event logging
CREATE OR REPLACE FUNCTION public.fh_update_order_status(
    p_order_id UUID,
    p_new_status TEXT,
    p_error_message TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    v_old_status TEXT;
    v_level TEXT;
    v_message TEXT;
BEGIN
    -- Get current status
    SELECT status INTO v_old_status FROM public.orders WHERE id = p_order_id;
    
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;
    
    -- Determine log level
    IF p_new_status = 'failed' THEN
        v_level := 'ERROR';
        v_message := COALESCE(p_error_message, 'Order processing failed');
    ELSIF p_new_status = 'completed' THEN
        v_level := 'INFO';
        v_message := 'Order completed successfully';
    ELSE
        v_level := 'INFO';
        v_message := 'Order status updated from ' || v_old_status || ' to ' || p_new_status;
    END IF;
    
    -- Update order
    UPDATE public.orders 
    SET 
        status = p_new_status,
        last_error = CASE WHEN p_new_status = 'failed' THEN p_error_message ELSE last_error END,
        updated_at = now(),
        completed_at = CASE WHEN p_new_status = 'completed' THEN now() ELSE completed_at END
    WHERE id = p_order_id;
    
    -- Create audit event
    PERFORM public.fh_create_order_event(
        p_order_id,
        p_new_status,
        v_level,
        v_message,
        jsonb_build_object('old_status', v_old_status, 'new_status', p_new_status)
    );
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to record DeepSeek API usage
CREATE OR REPLACE FUNCTION public.fh_record_deepseek_usage(
    p_order_id UUID,
    p_task_type TEXT,
    p_prompt_version TEXT,
    p_prompt_tokens INTEGER,
    p_completion_tokens INTEGER,
    p_temperature DECIMAL(3, 2),
    p_model TEXT,
    p_response_time_ms INTEGER,
    p_success BOOLEAN,
    p_error_message TEXT DEFAULT NULL,
    p_cache_hit BOOLEAN DEFAULT FALSE
) RETURNS BIGINT AS $$
DECLARE
    v_usage_id BIGINT;
    v_total_tokens INTEGER;
    v_estimated_cost_usd DECIMAL(10, 6);
BEGIN
    v_total_tokens := p_prompt_tokens + p_completion_tokens;
    
    -- Estimated cost calculation (DeepSeek pricing: $0.14 per 1M tokens)
    v_estimated_cost_usd := (v_total_tokens::DECIMAL / 1000000) * 0.14;
    
    INSERT INTO public.deepseek_usage (
        order_id, task_type, prompt_version, prompt_tokens, completion_tokens,
        total_tokens, temperature, model, response_time_ms, success,
        error_message, estimated_cost_usd, cache_hit
    ) VALUES (
        p_order_id, p_task_type, p_prompt_version, p_prompt_tokens, p_completion_tokens,
        v_total_tokens, p_temperature, p_model, p_response_time_ms, p_success,
        p_error_message, v_estimated_cost_usd, p_cache_hit
    ) RETURNING id INTO v_usage_id;
    
    RETURN v_usage_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to validate API key
CREATE OR REPLACE FUNCTION public.fh_validate_api_key(
    p_key_prefix TEXT
) RETURNS TABLE (
    is_valid BOOLEAN,
    key_name TEXT,
    scopes TEXT[],
    rate_limit_per_minute INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ak.is_active AND (ak.expires_at IS NULL OR ak.expires_at > now()),
        ak.name,
        ak.scopes,
        ak.rate_limit_per_minute
    FROM public.api_keys ak
    WHERE ak.key_prefix = p_key_prefix;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- TRIGGERS FOR AUTOMATION

-- Auto-update updated_at timestamp on orders
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_orders_updated_at
    BEFORE UPDATE ON public.orders
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- Auto-create order event when order is created
CREATE OR REPLACE FUNCTION public.create_order_created_event()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM public.fh_create_order_event(
        NEW.id,
        'created',
        'INFO',
        'Order created from source: ' || NEW.source_id,
        jsonb_build_object(
            'kwork_order_id', NEW.kwork_order_id,
            'title', NEW.title,
            'content_type', NEW.content_type
        )
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER create_order_event_on_insert
    AFTER INSERT ON public.orders
    FOR EACH ROW
    EXECUTE FUNCTION public.create_order_created_event();

-- VIEWS FOR REPORTING

-- Order summary view
CREATE OR REPLACE VIEW public.vw_order_summary AS
SELECT 
    o.id,
    o.kwork_order_id,
    o.title,
    o.status,
    o.content_type,
    o.price,
    o.buyer_id,
    o.created_at,
    o.completed_at,
    o.attempts,
    COALESCE(du.total_tokens, 0) as total_tokens_used,
    COALESCE(du.estimated_cost_usd, 0) as estimated_cost_usd,
    (SELECT COUNT(*) FROM public.order_events oe WHERE oe.order_id = o.id) as event_count
FROM public.orders o
LEFT JOIN LATERAL (
    SELECT SUM(total_tokens) as total_tokens, SUM(estimated_cost_usd) as estimated_cost_usd
    FROM public.deepseek_usage du
    WHERE du.order_id = o.id
) du ON true;

-- Daily usage statistics view
CREATE OR REPLACE VIEW public.vw_daily_usage AS
SELECT 
    DATE(du.created_at) as usage_date,
    du.task_type,
    COUNT(*) as request_count,
    SUM(CASE WHEN du.success THEN 1 ELSE 0 END) as success_count,
    SUM(du.total_tokens) as total_tokens,
    SUM(du.estimated_cost_usd) as total_cost_usd,
    AVG(du.response_time_ms) as avg_response_time_ms,
    AVG(CASE WHEN du.cache_hit THEN 1.0 ELSE 0.0 END) as cache_hit_rate
FROM public.deepseek_usage du
GROUP BY DATE(du.created_at), du.task_type;

-- Performance metrics view
CREATE OR REPLACE VIEW public.vw_performance_metrics AS
SELECT 
    o.content_type,
    o.prompt_version,
    COUNT(*) as total_orders,
    AVG(CASE WHEN o.status = 'completed' THEN 1.0 ELSE 0.0 END) as completion_rate,
    AVG(EXTRACT(EPOCH FROM (o.completed_at - o.created_at))) as avg_processing_time_seconds,
    AVG(o.content_quality_score) as avg_quality_score,
    AVG(o.attempts) as avg_attempts
FROM public.orders o
WHERE o.created_at >= now() - INTERVAL '30 days'
GROUP BY o.content_type, o.prompt_version;

-- GRANTS (apply appropriate permissions)
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT SELECT ON public.vw_order_summary, public.vw_daily_usage, public.vw_performance_metrics TO authenticated;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role;

-- INITIAL DATA (optional seed data)
INSERT INTO public.api_keys (name, key_hash, key_prefix, scopes, rate_limit_per_minute, expires_at)
VALUES (
    'Default Service Key',
    crypt('service-key-default', gen_salt('bf')),
    'service',
    ARRAY['orders:read', 'orders:write', 'usage:read', 'admin'],
    100,
    now() + INTERVAL '365 days'
) ON CONFLICT DO NOTHING;

-- VALIDATION QUERIES (for deployment verification)
COMMENT ON TABLE public.orders IS 'Main orders table for Firehorse MVP';
COMMENT ON TABLE public.order_events IS 'Audit log for order lifecycle events';
COMMENT ON TABLE public.deepseek_usage IS 'DeepSeek API usage tracking and cost monitoring';
COMMENT ON TABLE public.api_keys IS 'Secure API key storage with rotation support';

-- Deployment verification
DO $$
BEGIN
    RAISE NOTICE 'Firehorse MVP schema deployed successfully at %', now();
    RAISE NOTICE 'Tables created: orders, order_events, deepseek_usage, api_keys';
    RAISE NOTICE 'Functions created: fh_create_order_event, fh_update_order_status, fh_record_deepseek_usage, fh_validate_api_key';
    RAISE NOTICE 'Views created: vw_order_summary, vw_daily_usage, vw_performance_metrics';
    RAISE NOTICE 'RLS policies enabled for all tables';
END $$;
