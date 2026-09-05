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
export async function uploadDocument(file, conversationId) {
  const form = new FormData();
  form.append("file", file);
  form.append("conversation_id", conversationId);
  const res = await fetch(`${BASE_URL}/upload`, {
    method: "POST",
    headers: { "Authorization": getToken() },  // 注意：不手动设 Content-Type，浏览器会自动带 multipart 边界
    body: form,
  });
  if (res.status === 401) return { code: 401 };   // 令牌过期，交给页面处理
  return res.json();
}

// ===== 错题本相关 =====

// 生成/取固定的设备 ID：首次生成存 localStorage，之后每次读同一值 → "绑这台浏览器"
export function getDeviceId() {
  let id = localStorage.getItem("device_id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("device_id", id);
  }
  return id;
}

// 存一道错题（答错时调用）
export async function saveWrongAnswer(payload) {
  const res = await fetch(`${BASE_URL}/wrong-answers`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Authorization": getToken() },
    body: JSON.stringify({ device_id: getDeviceId(), ...payload }),
  });
  if (res.status === 401) return { code: 401 };
  return res.json();
}

// 查错题列表
export async function fetchWrongAnswers() {
  const res = await fetch(`${BASE_URL}/wrong-answers?device_id=${getDeviceId()}`, {
    headers: { "Authorization": getToken() },
  });
  if (res.status === 401) return { code: 401 };
  return res.json();
}
