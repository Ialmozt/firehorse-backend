-- Create or replace fh_ingress function for existing fh_orders table
CREATE OR REPLACE FUNCTION fh_ingress(p_kwork_order_id BIGINT, p_title TEXT)
RETURNS TABLE(order_id UUID, created BOOLEAN) AS $$
DECLARE 
    vid UUID; 
    vcreated BOOLEAN := false;
BEGIN
    -- UPSERT into fh_orders table (idempotent)
    INSERT INTO fh_orders(source_id, topic, status) 
    VALUES(p_kwork_order_id::TEXT, p_title, 'queued')
    ON CONFLICT(source_id) DO NOTHING 
    RETURNING id INTO vid;
    
    IF NOT FOUND THEN 
        -- Already exists
        SELECT id INTO vid FROM fh_orders WHERE source_id = p_kwork_order_id::TEXT;
    ELSE 
        vcreated := true; 
        
        -- Create event in fh_order_events
        INSERT INTO fh_order_events(order_id, stage, level, message, meta)
        VALUES (vid, 'ingress', 'INFO', 'Order created via webhook', 
                jsonb_build_object('source_id', p_kwork_order_id::TEXT, 'topic', p_title));
    END IF;
    
    RETURN QUERY SELECT vid, vcreated;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Test the function
SELECT * FROM fh_ingress(999999, 'Cline RPC Test');
