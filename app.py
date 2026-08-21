import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agent import run_agent, run_agent_stream

class ChatRequest(BaseModel):
    question: str
    history: list = []  # 新增：前端传来的历史对话


app = FastAPI(title="study-agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/chat")
async def chat(req: ChatRequest):
    def event_stream():
        for e in run_agent_stream(req.question, history=req.history):
            yield "data: " + json.dumps(e, ensure_ascii=False) + "\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8084)
