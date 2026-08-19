# my_agent.py —— 你亲手写的最小 Agent（重写挑战）
# 规则：逻辑全部由你填，卡住可以问我提示，我不会替你写

print("开始")
# ① 工具的说明书（TOOLS）
# 工具名: calculator
# 参数: expression (string)，比如 "1+2"
TOOLS = [
    # 在这里写 calculator 的说明书
 # 参考结构：{"type": "function", "function": {"name": ..., "description": ..., "pa # rameters": ...}}
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "算数学表达式",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "要计算的数学表达式，比如 2+2"},
                },
                "required": ["expression"],
            },
        },
    },







]


# ② 工具实现
def calculator(expression: str) -> str:
    # 把 "1+2" 算成 "3" 并返回字符串
    # 提示：第一版只处理加法就行，比如 expression.split("+") 再转 int 相加
    parts = expression.split("+")
    a = int(parts[0])
    b = int(parts[1])
    return str(a + b)
    pass


# ③ 通讯录：字符串名字 → 函数本人
TOOL_IMPL = {
     "calculator": calculator,
}


# ④ 接单员：按名字找到函数并执行
def call_tool(name: str, args: dict) -> str:
    if name not in TOOL_IMPL:
        return f"未知工具: {name}"
    try:
        return TOOL_IMPL[name](**args)
    except Exception as e:
        return f"工具执行失败: {e}"

    pass


# ⑤ 假 chat（先不接真 API，模拟模型回复）
# 第一次调用：返回"我要调 calculator，参数 expression=1+2"（tool_calls 形态）
# 第二次调用：返回"结果是 3。"（content 形态，没有 tool_calls）
def fake_chat(messages, tools=None):      # 第 0 层
    for m in messages:                    # 第 1 层（4 空格）
        if m.get("role") == "tool":       # 第 2 层（8 空格）
            return {"content": "结果是 3。"}  # 第 3 层（12 空格）
    return {"tool_calls":[{"name": "calculator", "arguments": {"expression": "1+2"}}]}          # 回第 1 层（4 空格，跟 for 平级）



# ⑥ 主循环（最多 3 轮）
def run_agent(question: str, max_rounds: int = 3) -> dict:
    messages = [
        {"role": "system", "content": "你是计算助手"},
        {"role": "user", "content": question},
    ]
    trace = []
    for round_no in range(max_rounds):
        response = fake_chat(messages, tools=TOOLS)
        if "tool_calls" in response:                        # ① 怎么判断"有 tool_calls"？
            call = response["tool_calls"][0]
            result = call_tool(call["name"], call["arguments"])
            trace.append(f"第{round_no + 1}轮：调 {call['name']} → 得到 {result}")
            messages.append({"role": "tool", "name": call["name"], "content": result})       # ② 把工具结果塞回消息（role 用 "tool"）
        else:
            return {"answer": response["content"], "trace": trace}
    return {"answer": "轮数用完", "trace": trace}


# ⑦ 跑起来
if __name__ == "__main__":
    result = run_agent("3+5 等于几？")
    print("答案:", result["answer"])
    print("过程:", result["trace"])
