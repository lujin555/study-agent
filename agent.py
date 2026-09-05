import json
from llm import chat, chat_stream
from tools import search_notes, make_quiz

SYSTEM_PROMPT = (
    "你是学习助理。你的知识来源是用户上传的学习资料。"
    "只要问题可能涉及资料内容（人物、事件、名言、知识点等），就先调用 search_notes 查资料，再基于检索结果回答；"
    "资料里没有的内容，要明确说'资料里没有'，不要编造。"
    "**引用来源**：回答时凡引用资料内容，都用 `[来源：xxx]` 的格式标注来源文档名，方便用户溯源核查。"
    "来源名**原样照抄** search_notes 返回结果里括号内的文档名，不要改动后缀"
    "（例如 GPT123.md 就写 GPT123.md，笔记.txt 就写 笔记.txt）。"
    "只要用户要题目/练习题/出题/考考我（包括编程题，如'出一道C++题目'），必须调用 make_quiz 出题，"
    "绝不要自己直接编写题目内容。用中文。"
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_notes",
            "description": "从学习资料中检索相关内容，回答基于资料的学习问题时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词或问题"},
                    "top_k": {"type": "integer", "description": "返回片段数，默认 3"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "make_quiz",
            "description": "根据主题出一道单选题并返回 JSON（题目/4个选项/答案/解析）。只要用户表达出题意图（'出题/题目/练习题/考考我'，含编程题），必须调用本工具，不要自己写题",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "题目主题，如'TCP 三次握手'"},
                },
                "required": ["topic"],
            },
        },
    },
]

TOOL_IMPL = {"search_notes": search_notes, "make_quiz": make_quiz}


def call_tool(name: str, args: dict) -> str:
    """把模型想调的工具路由到真实函数。"""
    if name not in TOOL_IMPL:
        return f"未知工具: {name}"
    try:
        return TOOL_IMPL[name](**args)
    except Exception as e:
        return f"工具执行失败: {e}"


def run_agent(question: str, history: list = None, max_rounds: int = 5, max_history_items: int = 20) -> dict:
    """非流式版：收集流式事件，拼出完整结果。"""
    answer = ""
    trace = []
    for e in run_agent_stream(question, history, max_rounds, max_history_items):
        if e["type"] == "token":
            answer += e["data"]
        elif e["type"] == "trace":
            trace.append(e["data"])
        elif e["type"] == "error":
            answer = e["data"]
    return {"answer": answer, "trace": trace}


def run_agent_stream(question, history=None, max_rounds=5, max_history_items=20):
    """流式版 run_agent：唯一的真源。工具调用发 trace 事件，最终回答逐块吐 token。"""
    history = (history or [])[-max_history_items:]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    for _ in range(max_rounds):
        resp = chat(messages, tools=TOOLS)
        msg = resp["choices"][0]["message"]

        if msg.get("tool_calls"):
            messages.append(msg)
            for tc in msg["tool_calls"]:
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = call_tool(name, args)
                if name == "make_quiz":
                    # 出题结果（JSON 字符串）单独发给前端，渲染成可点的题目卡片
                    try:
                        yield {"type": "quiz", "data": json.loads(result)}
                        # 给模型看的工具结果换成中性提示：答案只进卡片，不经过模型的嘴
                        result = "题目已生成并展示给用户。请提示用户在题目卡片上作答，不要复述题目或选项，也不要提前透露答案。"
                    except Exception:
                        pass  # 不是合法 JSON（比如出错信息），照常走 trace 就行
                yield {"type": "trace", "data": {"tool": name, "arguments": args, "result_preview": result[:100]}}
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
            continue

        yield {"type": "answer_start"}
        for piece in chat_stream(messages):
            yield {"type": "token", "data": piece}
        yield {"type": "done"}
        return

    yield {"type": "error", "data": "已达到最大轮数，强制结束。"}
