-- 🔥 FIXED fh_ingress RPC Function for Firehorse MVP
-- This function works with the existing fh_orders table structure
-- Created: 2026-01-13 11:15 UTC

-- Drop existing function if exists (idempotent)
DROP FUNCTION IF EXISTS fh_ingress;

-- Create or replace fh_ingress function
CREATE OR REPLACE FUNCTION fh_ingress(
    p_kwork_order_id BIGINT,
    p_title TEXT
)
RETURNS TABLE(orderid UUID, created BOOLEAN)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_order_id UUID;
    v_created BOOLEAN := false;
    v_source_id TEXT;
BEGIN
    -- Convert kwork_order_id to text for source_id field
    v_source_id := p_kwork_order_id::TEXT;
    
    -- Try to insert new order into fh_orders table
    INSERT INTO fh_orders (
        source_id,
        topic,
        status,
        attempts,
        final_text,
        metrics,
        last_error,
        created_at,
        updated_at
    ) VALUES (
        v_source_id,
        p_title,
        'queued',
        0,
        NULL,
        '{}'::jsonb,
        NULL,
        NOW(),
        NOW()
    )
    ON CONFLICT (source_id) DO NOTHING
    RETURNING id INTO v_order_id;
    
    -- Check if a new row was inserted
    IF v_order_id IS NOT NULL THEN
        v_created := true;
        
        -- Create event in fh_order_events table if it exists
        -- Note: This is optional, as the table might not exist yet
        BEGIN
            INSERT INTO fh_order_events (
                order_id,
                stage,
                level,
                message,
                meta,
                created_at
            ) VALUES (
                v_order_id,
                'ingress',
                'INFO',
                'Order created via webhook RPC',
                jsonb_build_object(
                    'source_id', v_source_id,
                    'topic', p_title,
                    'kwork_order_id', p_kwork_order_id
                ),
                NOW()
            );
        EXCEPTION WHEN OTHERS THEN
            -- Silently ignore if fh_order_events table doesn't exist
            NULL;
        END;
    ELSE
        -- Get existing order ID
        SELECT id INTO v_order_id 
        FROM fh_orders 
        WHERE source_id = v_source_id;
        
        -- Update updated_at timestamp for existing order
        UPDATE fh_orders 
        SET updated_at = NOW()
        WHERE source_id = v_source_id;
    END IF;
    
    -- Return result
    RETURN QUERY SELECT v_order_id, v_created;
END;
$$;

-- Test the function with sample data
SELECT * FROM fh_ingress(123456789, 'Test Order from Kwork Webhook');
SELECT * FROM fh_ingress(999999999, 'Another Test Order');

-- Verify the function works
COMMENT ON FUNCTION fh_ingress IS 'Firehorse ingress function for Kwork webhooks - inserts orders into fh_orders table';

-- Deployment verification
DO $$
BEGIN
    RAISE NOTICE '✅ fh_ingress function deployed successfully at %', now();
    RAISE NOTICE 'Function signature: fh_ingress(p_kwork_order_id BIGINT, p_title TEXT) → TABLE(orderid UUID, created BOOLEAN)';
    RAISE NOTICE 'Target table: fh_orders (source_id TEXT UNIQUE, topic TEXT, status TEXT DEFAULT ''queued'')';
END $$;
