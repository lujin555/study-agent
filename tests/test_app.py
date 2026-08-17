from fastapi.testclient import TestClient
import app


client = TestClient(app.app)


def test_chat_ok(monkeypatch):
    monkeypatch.setattr(app, "run_agent", lambda question: {
        "answer": "测试回答",
        "trace": [{"tool": "search_notes", "arguments": {"query": "x"}, "result_preview": "片段"}],
    })
    resp = client.post("/api/chat", json={"question": "测试"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["answer"] == "测试回答"
    assert data["trace"][0]["tool"] == "search_notes"
