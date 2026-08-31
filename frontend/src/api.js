const BASE_URL = "/api";

export function getToken() {
  return localStorage.getItem("access_token") || "";
}

export async function login(password) {
  const res = await fetch(`${BASE_URL}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  return res.json();
}

export async function askAgent(question, conversationId, handlers) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Authorization": getToken() },
    body: JSON.stringify({ question, conversation_id: conversationId }),
  });
  if (res.status === 401) {
    handlers.unauthorized?.();
    return;
  }
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
export async function loadHistory(conversationId) {
  const res = await fetch(`${BASE_URL}/history?conversation_id=${conversationId}`, {
    headers: { "Authorization": getToken() },
  });
  return res.json();
}
export async function uploadDocument(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE_URL}/upload`, {
    method: "POST",
    headers: { "Authorization": getToken() },  // 注意：不手动设 Content-Type，浏览器会自动带 multipart 边界
    body: form,
  });
  return res.json();
}