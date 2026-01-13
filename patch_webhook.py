import re

with open('src/main.py', 'r') as f:
    content = f.read()

# Replace the webhook function
new_webhook = '''@app.post("/webhook", response_model=OrderResponse)
@retry_with_backoff(supabase_retry_config)
async def webhook(order: Order, x_token: str = Header(None)):  # Pydantic validates automatically
    """
    Handle Kwork webhook with full validation and security

    Input validation by Pydantic:
    - order.kworkid: string 1-50 chars
    - order.topic: string 1-500 chars, no injection
    """
    # Check authentication
    INGRESS_SECRET = os.getenv("INGRESS_SECRET")
    if not INGRESS_SECRET:
        raise HTTPException(status_code=500, detail="Server configuration error")
    
    if x_token != INGRESS_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    request_id = get_request_id()
    start_time = time.time()

    try:
        logger.info(
            "kwork_webhook_received",
            extra={
                "request_id": request_id,
                "kworkid": order.kworkid,
                "topic": order.topic,
                "validated": True,  # Pydantic validated
            }
        )

        # Increment order created metric
        metrics_module.orders_created_total.inc()

        # Call Supabase RPC fh_ingress
        sb = get_supabase_client()
        result = sb.rpc('fh_ingress', {
            'p_kwork_order_id': int(order.kworkid) if order.kworkid.isdigit() else order.kworkid,
            'p_title': order.topic
        }).execute()
        
        rows = result.data or []
        if not rows:
            raise RuntimeError("fh_ingress returned empty result")
            
        row = rows[0]
        logger.info(f"Order {row['orderid']} from {order.kworkid}")
        
        # Log successful response
        logger.info(
            "webhook_response_success",
            extra={
                "request_id": request_id,
                "kworkid": order.kworkid,
                "supabase_id": row['orderid'],
                "status": "accepted" if row.get("created", True) else "exists",
            }
        )

        # At success, log metrics
        metrics_module.orders_completed_total.inc()
        duration = time.time() - start_time
        logger.info(f"Order {order.kworkid} processed in {duration:.2f}s")

        return OrderResponse(
            status="accepted" if row.get("created", True) else "exists",
            orderid=row['orderid'],
            request_id=request_id,
            message="Order processed successfully"
        )

    except HTTPException:
        # Re-raise HTTP exceptions (they already have proper status codes)
        raise
    except Exception as e:
        metrics_module.orders_failed_total.labels(reason=type(e).__name__).inc()
        metrics_module.external_api_errors_total.labels(
            api_name="supabase",
            error_type=type(e).__name__
        ).inc()

        logger.error(
            "webhook_processing_failed",
            extra={
                "request_id": request_id,
                "kworkid": order.kworkid,
                "error": str(e),
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))'''

# Find and replace the webhook function
pattern = r'@app\.post\("/webhook", response_model=OrderResponse\)[\s\S]*?raise HTTPException\(status_code=400, detail="Invalid request"\)'
content = re.sub(pattern, new_webhook, content, flags=re.DOTALL)

# Also need to add import for Header if not present
if 'from fastapi import FastAPI, HTTPException, Header' not in content:
    content = content.replace('from fastapi import FastAPI, HTTPException', 'from fastapi import FastAPI, HTTPException, Header')

with open('src/main.py', 'w') as f:
    f.write(content)

print("Webhook function updated")
