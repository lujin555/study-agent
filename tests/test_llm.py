import llm


class FakeResp:
    def __init__(self, status_code, json_data, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        return self._json


def test_chat_sends_tools(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return FakeResp(200, {"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(llm.requests, "post", fake_post)
    result = llm.chat([{"role": "user", "content": "hi"}], tools=[{"type": "function"}])

    assert result["choices"][0]["message"]["content"] == "ok"
    assert captured["json"]["tools"] == [{"type": "function"}]


def test_chat_raises_on_error(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=None):
        return FakeResp(401, {}, text='{"error": "bad key"}')

    monkeypatch.setattr(llm.requests, "post", fake_post)
    try:
        llm.chat([{"role": "user", "content": "hi"}])
        assert False, "应该抛出 RuntimeError"
    except RuntimeError as e:
        assert "401" in str(e)
