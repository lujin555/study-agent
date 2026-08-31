import secrets
from fastapi import Depends, Header, HTTPException, UploadFile, File, Form
from pathlib import Path
from ingest import ingest_one
from config import ACCESS_PASSWORD, DOCS_DIR
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
# 简单的内存令牌表（重启失效，够用；生产换数据库）
_tokens = set()
# 每个对话最近上传的文档（conversation_id -> 文件名），让"这内容"有指向
_recent_uploads = {}


def _require_auth(authorization: str = Header(None)):
    if not ACCESS_PASSWORD:
        return  # 没设密码 = 不启用访问控制
    if not authorization or authorization not in _tokens:
        raise HTTPException(status_code=401, detail="需要登录")


class LoginRequest(BaseModel):
    password: str


@app.post("/api/login")
async def login(req: LoginRequest):
    if not ACCESS_PASSWORD or req.password == ACCESS_PASSWORD:
        token = secrets.token_hex(16)
        _tokens.add(token)
        return {"code": 200, "token": token}
    raise HTTPException(status_code=401, detail="密码错误")
@app.post("/api/upload")
async def upload(file: UploadFile = File(...), conversation_id: str = Form("default"), _: None = Depends(_require_auth)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="没有文件名")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pdf", ".doc", ".docx", ".txt"}:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {suffix}")

    docs_dir = Path(DOCS_DIR)
    docs_dir.mkdir(exist_ok=True)
    safe_name = Path(file.filename).name          # 防路径穿越：只取文件名
    dest = docs_dir / safe_name
    content = await file.read()
    dest.write_bytes(content)

    try:
        n = ingest_one(dest)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"入库失败: {e}")
    _recent_uploads[conversation_id] = safe_name   # 记住"这个对话最近上传了谁"
    if n == 0:
        return {"code": 200, "filename": safe_name, "chunks": 0,
                "warning": "文件已上传，但没有提取到文字（可能是扫描版 PDF，没有文字层）。请换一份有文字的 PDF，或先做 OCR。"}
    return {"code": 200, "filename": safe_name, "chunks": n}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # 只允许本地前端
    allow_methods=["GET", "POST"],      # 只允许这两种方法
    allow_headers=["Content-Type", "Authorization"],     # 允许请求头和令牌头
)


@app.post("/api/chat")
async def chat(req: ChatRequest, _: None = Depends(_require_auth)):

    def event_stream():
        save_message(req.conversation_id, "user", req.question)
        answer_parts = []
        try:
            history = load_history(req.conversation_id)
            recent = _recent_uploads.get(req.conversation_id)
            if recent:
                # 告诉模型"用户最近上传了这份文档"，让"这内容/这份文档"有指向
                history = [
                    {"role": "system", "content": f"用户最近上传了文档「{recent}」。如果用户问'这内容/这份文档/刚上传的'，指的是这份文档。"}
                ] + history
            for e in run_agent_stream(req.question, history=history):
                if e["type"] == "token":
                    answer_parts.append(e["data"])
                yield "data: " + json.dumps(e, ensure_ascii=False) + "\n\n"
        except Exception as e:
            yield "data: " + json.dumps({"type": "error", "data": f"生成回答时出错: {e}"},
                                        ensure_ascii=False) + "\n\n"
        finally:
            if answer_parts:
                save_message(req.conversation_id, "assistant", "".join(answer_parts))

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/history")
async def history(conversation_id: str = "default", _: None = Depends(_require_auth)):
    return {"code": 200, "data": load_history(conversation_id, limit=100)}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8084)
