import json
from fastapi.testclient import TestClient
import app

client = TestClient(app.app)


def fake_stream(question, history=None, max_rounds=5, max_history_items=20):
    """假的 run_agent_stream：固定吐出几个事件，不碰真模型。"""
    yield {"type": "answer_start"}
    yield {"type": "token", "data": "测试"}
    yield {"type": "token", "data": "回答"}
    yield {"type": "done"}


def parse_sse(text):
    """把 SSE 文本切成事件列表（buffer 切分的测试版）。"""
    events = []
    for line in text.split("\n\n"):
        line = line.strip()
        if not line or not line.startswith("data: "):
            continue
        events.append(json.loads(line[len("data: "):]))
    return events


def test_chat_stream_ok(monkeypatch):
    monkeypatch.setattr(app, "run_agent_stream", fake_stream)
    resp = client.post("/api/chat", json={"question": "测试"})
    assert resp.status_code == 200

    events = parse_sse(resp.text)
    types = [e["type"] for e in events]
    assert types == ["answer_start", "token", "token", "done"]

    tokens = "".join(e["data"] for e in events if e["type"] == "token")
    assert tokens == "测试回答"