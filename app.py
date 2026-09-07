import time
import io
from datetime import datetime
from fastapi import Depends, Header, HTTPException, UploadFile, File, Form
from pathlib import Path
from ingest import ingest_one
from rag.loader import ScanPDFError
from config import ACCESS_PASSWORD, DOCS_DIR, UPLOAD_MAX_BYTES
import json
from db import init_db, save_message, load_history, save_wrong_answer, list_wrong_answers
from logging_setup import setup_logging
import hmac, hashlib

setup_logging()

init_db()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agent import run_agent, run_agent_stream
from tools import make_quiz

class ChatRequest(BaseModel):
    question: str
    conversation_id: str = "default"


app = FastAPI(title="study-agent")
# 每个对话最近上传的文档（conversation_id -> 文件名），让"这内容"有指向
_recent_uploads = {}

# ---- 无状态签名令牌：服务器不存任何东西，重启后依然有效（迷你 JWT 思想）----
_TOKEN_TTL = 24 * 3600
_AUTH_SECRET = (ACCESS_PASSWORD or "study-agent-local").encode()

def _make_token() -> str:
    ts = str(int(time.time()))
    sig = hmac.new(_AUTH_SECRET, ts.encode(), hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"

def _check_token(token: str) -> bool:
    try:
        ts, sig = token.split(".")
    except ValueError:
        return False
    if time.time() - int(ts) > _TOKEN_TTL:
        return False
    expect = hmac.new(_AUTH_SECRET, ts.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expect)


def _require_auth(authorization: str = Header(None)):
    if not ACCESS_PASSWORD:
        return  # 没设密码 = 不启用访问控制
    if not authorization or not _check_token(authorization):
        raise HTTPException(status_code=401, detail="需要登录或令牌已过期")


class LoginRequest(BaseModel):
    password: str


class WrongAnswerIn(BaseModel):
    """存错题的请求体。options 是 dict（4 个选项）。"""
    device_id: str
    question: str
    options: dict
    your_answer: str
    correct_answer: str
    explain: str = ""


class QuizRequest(BaseModel):
    """点'出题'按钮时的请求体：只要主题。"""
    topic: str


@app.post("/api/login")
async def login(req: LoginRequest):
    if not ACCESS_PASSWORD or req.password == ACCESS_PASSWORD:
        return {"code": 200, "token": _make_token()}
    raise HTTPException(status_code=401, detail="密码错误")
@app.post("/api/upload")
async def upload(file: UploadFile = File(...), conversation_id: str = Form("default"), _: None = Depends(_require_auth)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="没有文件名")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pdf", ".doc", ".docx", ".txt", ".md"}:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {suffix}")

    # 流式读取并限制大小，避免超大文件一次性占满内存
    buf = io.BytesIO()
    total = 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > UPLOAD_MAX_BYTES:
            raise HTTPException(status_code=413, detail=f"文件太大，上限 {UPLOAD_MAX_BYTES // (1024*1024)}MB")
        buf.write(chunk)

    docs_dir = Path(DOCS_DIR)
    docs_dir.mkdir(exist_ok=True)
    safe_name = Path(file.filename).name          # 防路径穿越：只取文件名
    dest = docs_dir / safe_name
    # 同名文件自动重命名（追加时间戳），避免覆盖
    if dest.exists():
        stem = Path(safe_name).stem
        suffix = Path(safe_name).suffix
        safe_name = f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{suffix}"
        dest = docs_dir / safe_name
    dest.write_bytes(buf.getvalue())

    try:
        n = ingest_one(dest)
    except ScanPDFError as e:
        # 扫描版不是系统错误：文件保留在 docs/，但明确告知内容没进知识库
        return {"code": 200, "filename": safe_name, "chunks": 0, "warning": str(e)}
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
        # 先读旧历史，再存当前问题：避免把同一条问题同时通过 history 和 question 两次喂给模型
        history = load_history(req.conversation_id)
        save_message(req.conversation_id, "user", req.question)
        answer_parts = []
        gen = None
        try:
            recent = _recent_uploads.get(req.conversation_id)
            if recent:
                # 告诉模型"用户最近上传了这份文档"，让"这内容"有指向
                history = [
                    {"role": "system", "content": f"用户最近上传了文档「{recent}」。如果用户问'这内容/这份文档/刚上传的'，指的是这份文档。"}
                ] + history
            gen = run_agent_stream(req.question, history=history)
            for e in gen:
                if e["type"] == "token":
                    answer_parts.append(e["data"])
                yield "data: " + json.dumps(e, ensure_ascii=False) + "\n\n"
        except Exception as e:
            yield "data: " + json.dumps({"type": "error", "data": f"生成回答时出错: {e}"},
                                        ensure_ascii=False) + "\n\n"
        finally:
            # 客户端断开（点"停止"或关页面）时 Starlette close() 本生成器，
            # GeneratorExit 传到这里 → gen.close() 级联关掉 agent → llm → resp.close()
            if gen is not None:
                gen.close()
            if answer_parts:
                save_message(req.conversation_id, "assistant", "".join(answer_parts))

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/history")
async def history(conversation_id: str = "default", _: None = Depends(_require_auth)):
    return {"code": 200, "data": load_history(conversation_id, limit=100)}


@app.post("/api/wrong-answers")
async def add_wrong_answer(req: WrongAnswerIn, _: None = Depends(_require_auth)):
    """存一道错题（答错时前端自动调用）。"""
    try:
        rid = save_wrong_answer(
            req.device_id, req.question, req.options,
            req.your_answer, req.correct_answer, req.explain,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"存错题失败: {e}")
    return {"code": 200, "id": rid}


@app.get("/api/wrong-answers")
async def get_wrong_answers(device_id: str, _: None = Depends(_require_auth)):
    """取某设备的错题列表（最新在前）。"""
    return {"code": 200, "data": list_wrong_answers(device_id)}


@app.post("/api/quiz")
async def gen_quiz(req: QuizRequest, _: None = Depends(_require_auth)):
    """点'出题'按钮直连出题：不走 agent 工具调用，保证 100% 出题。"""
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="主题不能为空")
    try:
        raw = make_quiz(req.topic.strip())   # 返回 JSON 字符串（或出错信息）
        data = json.loads(raw)               # 解析成对象返回前端
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"出题失败：{raw[:200]}")
    return {"code": 200, "data": data}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8084)
