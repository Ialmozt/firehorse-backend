-- Drop existing function if exists
DROP FUNCTION IF EXISTS fh_ingress;

-- Create fh_ingress function that works with fh_orders table
CREATE OR REPLACE FUNCTION fh_ingress(p_kwork_order_id BIGINT, p_title TEXT)
RETURNS TABLE(order_id UUID, created BOOLEAN) 
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE 
    v_order_id UUID;
    v_created BOOLEAN := false;
BEGIN
    -- Try to insert new order
    INSERT INTO fh_orders (source_id, topic, status, created_at, updated_at)
    VALUES (p_kwork_order_id::TEXT, p_title, 'queued', NOW(), NOW())
    ON CONFLICT (source_id) DO NOTHING
    RETURNING id INTO v_order_id;
    
    -- Check if inserted
    IF v_order_id IS NOT NULL THEN
        v_created := true;
        
        -- Create event in fh_order_events
        INSERT INTO fh_order_events (order_id, stage, level, message, meta, created_at)
        VALUES (v_order_id, 'ingress', 'INFO', 'Order created via webhook', 
                jsonb_build_object('source_id', p_kwork_order_id::TEXT, 'topic', p_title), NOW());
    ELSE
        -- Get existing order ID
        SELECT id INTO v_order_id 
        FROM fh_orders 
        WHERE source_id = p_kwork_order_id::TEXT;
    END IF;
    
    -- Return result
    RETURN QUERY SELECT v_order_id, v_created;
END;
$$;

-- Test the function
SELECT * FROM fh_ingress(123456, 'Test Order from Kwork');
