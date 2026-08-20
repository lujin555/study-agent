from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import run_agent


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

    return {"code": 200, "data": run_agent(req.question, history=req.history)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8084)
