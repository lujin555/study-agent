import json
from db import init_db, save_message, load_history

init_db()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agent import run_agent, run_agent_stream

class ChatRequest(BaseModel):
    question: str
    conversation_id: str = "default"


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
        save_message(req.conversation_id, "user", req.question)   # 问题先存库
        answer_parts = []
        for e in run_agent_stream(req.question, history=load_history(req.conversation_id)):
            if e["type"] == "token":
                answer_parts.append(e["data"])
            yield "data: " + json.dumps(e, ensure_ascii=False) + "\n\n"
        save_message(req.conversation_id, "assistant", "".join(answer_parts)) # 答案存库

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/history")
async def history(conversation_id: str = "default"):
    return {"code": 200, "data": load_history(conversation_id, limit=100)}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8084)
