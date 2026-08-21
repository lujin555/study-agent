import json
from llm import chat, chat_stream
from tools import search_notes, make_quiz

SYSTEM_PROMPT = (
    "你是学习助理。回答基于资料的学习问题前，先调用 search_notes 查资料；"
    "用户要练习题时，调用 make_quiz。其他情况直接回答。用中文。"
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
            "description": "根据主题生成一道练习题，含题目、答案和解析",
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
    """手写 agent loop。messages 是状态，贯穿整个循环。"""
    history = (history or [])[-max_history_items:]  # 口袋最多 20 条，超了挤掉最旧的
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    if history:
        messages.extend(history)                     # 之前的对话按时间顺序放进来
    messages.append({"role": "user", "content": question})  # 当前问题放最后
    trace = []

    for _ in range(max_rounds):
        resp = chat(messages, tools=TOOLS)
        msg = resp["choices"][0]["message"]

        if msg.get("tool_calls"):
            messages.append(msg)  # 模型消息（含调用意图）进状态
            for tc in msg["tool_calls"]:
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = call_tool(name, args)
                trace.append({"tool": name, "arguments": args, "result_preview": result[:100]})
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
            continue

        return {"answer": msg["content"], "trace": trace}

    return {"answer": "已达到最大轮数，强制结束。", "trace": trace}
def run_agent_stream(question, history=None, max_rounds=5, max_history_items=20):
    """流式版 run_agent：工具调用发 trace 事件，最终回答逐块吐 token。"""
    history = (history or [])[-max_history_items:]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})
    trace = []

    for _ in range(max_rounds):
        resp = chat(messages, tools=TOOLS)
        msg = resp["choices"][0]["message"]

        if msg.get("tool_calls"):
            yield {"type": "trace", "data": {"tool_calls": [
                {"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]}
                for tc in msg["tool_calls"]
            ]}}
            messages.append(msg)
            for tc in msg["tool_calls"]:
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = call_tool(name, args)
                trace.append({"tool": name, "arguments": args, "result_preview": result[:100]})
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
            continue

        yield {"type": "answer_start"}
        for piece in chat_stream(messages):
            yield {"type": "token", "data": piece}
        yield {"type": "done"}
        return

    yield {"type": "error", "data": "达到最大轮数，强制结束。"}
