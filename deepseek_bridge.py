import uvicorn
import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

# БЕРЁМ КЛЮЧ ИЗ WINDOWS
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
REAL_MODEL = "deepseek-chat"

app = FastAPI()

@app.post("/v1/chat/completions")
async def proxy(request: Request):
    if not DEEPSEEK_API_KEY:
        return {"error": "DEEPSEEK_API_KEY not set in environment"}
    
    body = await request.json()
    print(f"🔄 Cursor sent model: {body.get('model')} -> Swapping to: {REAL_MODEL}")
    body["model"] = REAL_MODEL
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    async def stream():
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("POST", "https://api.deepseek.com/chat/completions", json=body, headers=headers) as r:
                async for chunk in r.aiter_bytes():
                    yield chunk
    
    return StreamingResponse(stream(), media_type="text/event-stream")

if __name__ == "__main__":
    print(f"🚀 DeepSeek Bridge running on http://127.0.0.1:5000")
    print(f"🔑 Key: {DEEPSEEK_API_KEY[:10]}..." if DEEPSEEK_API_KEY else "❌ NO KEY SET")
    uvicorn.run(app, host="127.0.0.1", port=5000)
