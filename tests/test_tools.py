import tools


def test_search_notes_ok(monkeypatch):
    def fake_query(collection_name, question, top_k=3, persist_path=None):
        return {
            "documents": [["三次握手是 TCP 建立连接的过程"]],
            "metadatas": [[{"source": "data/test.pdf"}]],
        }

    monkeypatch.setattr(tools, "hybrid_query", fake_query)
    result = tools.search_notes("三次握手")
    assert "三次握手" in result
    assert "test.pdf" in result


def test_search_notes_empty(monkeypatch):
    def fake_query(collection_name, question, top_k=3, persist_path=None):
        return None  # 向量库为空

    monkeypatch.setattr(tools, "hybrid_query", fake_query)
    assert tools.search_notes("不存在的内容") == "向量库还没有内容。请先把资料拖进 docs/ 文件夹，再运行 ingest.py。"


def test_search_notes_error(monkeypatch):
    def fake_query(collection_name, question, top_k=3, persist_path=None):
        raise ConnectionError("backend down")

    monkeypatch.setattr(tools, "hybrid_query", fake_query)
    assert "检索失败" in tools.search_notes("xxx")


def test_make_quiz(monkeypatch):
    def fake_chat(messages, tools=None):
        return {"choices": [{"message": {"content": '{"question": "三次握手有几步？", "options": {"A": "1", "B": "2", "C": "3", "D": "4"}, "answer": "C", "explain": "三次握手共三步"}'}}]}

    monkeypatch.setattr(tools, "chat", fake_chat)
    result = tools.make_quiz("TCP 三次握手")
    assert "三次握手" in result
