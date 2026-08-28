import agent


def fake_response(content=None, tool_calls=None):
    message = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {"choices": [{"message": message}]}


def make_tool_call(tool_id, name, args_json):
    return {
        "id": tool_id,
        "type": "function",
        "function": {"name": name, "arguments": args_json},
    }


def test_agent_calls_tool_then_answers(monkeypatch):
    calls = {"n": 0}

    def fake_chat(messages, tools=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return fake_response(tool_calls=[make_tool_call("call_1", "search_notes", '{"query": "三次握手"}')])
        return fake_response(content="忽略，答案由 chat_stream 给")

    def fake_chat_stream(messages, tools=None):
        yield "三次握手是"
        yield " TCP 建立连接的过程。"

    monkeypatch.setattr(agent, "chat", fake_chat)
    monkeypatch.setattr(agent, "chat_stream", fake_chat_stream)
    result = agent.run_agent("三次握手是什么？")

    assert "三次握手" in result["answer"]
    assert len(result["trace"]) == 1
    assert result["trace"][0]["tool"] == "search_notes"
    assert result["trace"][0]["arguments"] == {"query": "三次握手"}


def test_agent_no_tool_when_not_needed(monkeypatch):
    def fake_chat(messages, tools=None):
        return fake_response(content="你好！有什么可以帮你？")

    def fake_chat_stream(messages, tools=None):
        yield "你好！有什么可以帮你？"

    monkeypatch.setattr(agent, "chat", fake_chat)
    monkeypatch.setattr(agent, "chat_stream", fake_chat_stream)
    result = agent.run_agent("你好")

    assert result["answer"] == "你好！有什么可以帮你？"
    assert result["trace"] == []


def test_agent_max_rounds(monkeypatch):
    def fake_chat(messages, tools=None):
        return fake_response(tool_calls=[make_tool_call("call_x", "make_quiz", '{"topic": "TCP"}')])

    monkeypatch.setattr(agent, "chat", fake_chat)
    result = agent.run_agent("一直调工具", max_rounds=2)

    assert "最大轮数" in result["answer"]
    assert len(result["trace"]) == 2


def test_agent_bad_arguments_json(monkeypatch):
    calls = {"n": 0}

    def fake_chat(messages, tools=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return fake_response(tool_calls=[make_tool_call("call_1", "search_notes", "not-json")])
        return fake_response(content="忽略，答案由 chat_stream 给")

    def fake_chat_stream(messages, tools=None):
        yield "我换个方式回答。"

    monkeypatch.setattr(agent, "chat", fake_chat)
    monkeypatch.setattr(agent, "chat_stream", fake_chat_stream)
    result = agent.run_agent("查一下")

    assert len(result["trace"]) == 1
    assert "工具执行失败" in result["trace"][0]["result_preview"]
