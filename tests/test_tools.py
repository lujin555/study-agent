import tools


class FakeResp:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json = json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json


def test_search_notes_ok(monkeypatch):
    def fake_post(url, json=None, timeout=None):
        return FakeResp(200, {"code": 200, "data": [
            {"content": "三次握手是 TCP 建立连接的过程", "source": "data/test.pdf"},
        ]})

    monkeypatch.setattr(tools.requests, "post", fake_post)
    result = tools.search_notes("三次握手")
    assert "三次握手" in result
    assert "data/test.pdf" in result


def test_search_notes_empty(monkeypatch):
    def fake_post(url, json=None, timeout=None):
        return FakeResp(200, {"code": 200, "data": []})

    monkeypatch.setattr(tools.requests, "post", fake_post)
    assert tools.search_notes("不存在的内容") == "没有检索到相关内容。"


def test_search_notes_error(monkeypatch):
    def fake_post(url, json=None, timeout=None):
        raise ConnectionError("backend down")

    monkeypatch.setattr(tools.requests, "post", fake_post)
    assert "检索失败" in tools.search_notes("xxx")


def test_make_quiz(monkeypatch):
    def fake_chat(messages, tools=None):
        return {"choices": [{"message": {"content": '{"question": "三次握手有几步？"}'}}]}

    monkeypatch.setattr(tools, "chat", fake_chat)
    result = tools.make_quiz("TCP 三次握手")
    assert "三次握手" in result
