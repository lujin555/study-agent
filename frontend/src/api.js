const BASE_URL = "/api";

export async function askAgent(question, conversationId, handlers) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, conversation_id: conversationId }),
  });
  const reader = res.body.getReader();   // 拿到水管
  const decoder = new TextDecoder();     // 字节 → 文字的翻译官
  let buffer = "";                       // 攒残行的地方

  while (true) {
    const { done, value } = await reader.read();   // 读一节
    if (done) break;                               // 水管空了
    buffer += decoder.decode(value, { stream: true });  // 先攒进 buffer
    const lines = buffer.split("\n\n");            // 按消息边界切
    buffer = lines.pop() || "";                    // 残行留回 buffer
    for (const line of lines) {                    // 只处理完整的
      const evt = JSON.parse(line.replace(/^data: /, ""));  // 剥掉 data: 前缀
      handlers[evt.type]?.(evt.data ?? evt);       // 按类型分发给回调
    }
  }
}
