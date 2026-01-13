-- Create fh_ingress_v2 function for testing
-- This is a temporary function to test the logic before replacing the main function

CREATE OR REPLACE FUNCTION fh_ingress_v2(
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
        
        -- Try to create event in fh_order_events table if it exists
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
                'Order created via webhook RPC v2',
                jsonb_build_object(
                    'source_id', v_source_id,
                    'topic', p_title,
                    'kwork_order_id', p_kwork_order_id
                ),
                NOW()
            );
        EXCEPTION WHEN OTHERS THEN
            -- Silently ignore if fh_order_events table doesn't exist or has errors
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
    
    -- Return result - ensure we always return something
    IF v_order_id IS NOT NULL THEN
        RETURN QUERY SELECT v_order_id, v_created;
    ELSE
        -- This should not happen, but just in case
        RETURN QUERY SELECT NULL::UUID, false;
    END IF;
END;
$$;

-- Test the function
SELECT * FROM fh_ingress_v2(111222333, 'Test Order v2');
SELECT * FROM fh_ingress_v2(444555666, 'Another Test v2');

-- Check what was inserted
SELECT * FROM fh_orders WHERE source_id IN ('111222333', '444555666') ORDER BY created_at DESC;
