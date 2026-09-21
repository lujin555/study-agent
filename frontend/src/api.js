const BASE_URL = "/api";

export function getToken() {
  return localStorage.getItem("access_token") || "";
}

// 判断 token 是否存在且未过期。
// token 格式是 "签发秒级时间戳.签名"，后端 _TOKEN_TTL = 24*3600（校验 now - ts > TTL 即过期），
// 前端照同一规则本地预判 → 避免"token 已过期但页面还以为登录着"。
// 注意：24h 这个数目前和后端各写一份（两处硬编码）；以后优化方向是登录响应带 expires_in。
export function isTokenValid() {
  const token = getToken();
  if (!token || !token.includes(".")) return false;
  const issued = Number(token.split(".")[0]);
  if (!Number.isFinite(issued)) return false;
  return Date.now() / 1000 - issued < 24 * 3600;
}

export async function login(password) {
  const res = await fetch(`${BASE_URL}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  return res.json();
}

export async function askAgent(question, conversationId, handlers, signal) {
  let res;
  try {
    res = await fetch(`${BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": getToken() },
      body: JSON.stringify({ question, conversation_id: conversationId }),
      signal,                  // 前端点"停止"时 abort() → 切断 SSE → 后端级联关闭 DeepSeek 流
    });
  } catch (e) {
    if (e.name === "AbortError") { handlers.aborted?.(); return; }
    throw e;
  }
  if (res.status === 401) {
    handlers.unauthorized?.();
    return;
  }
  const reader = res.body.getReader();   // 拿到水管
  const decoder = new TextDecoder();     // 字节 → 文字的翻译官
  let buffer = "";                       // 攒残行的地方

  try {
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
  } catch (e) {
    if (e.name === "AbortError") { handlers.aborted?.(); return; }
    throw e;
  }
}
export async function loadHistory(conversationId) {
  const res = await fetch(`${BASE_URL}/history?conversation_id=${conversationId}`, {
    headers: { "Authorization": getToken() },
  });
  if (res.status === 401) return { code: 401 };   // 令牌过期 → 交给页面跳登录（之前漏了这行，401 被静默吞掉）
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

// ===== 直连出题（点"出题"按钮）=====
export async function generateQuiz(topic) {
  const res = await fetch(`${BASE_URL}/quiz`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Authorization": getToken() },
    body: JSON.stringify({ topic }),
  });
  if (res.status === 401) return { code: 401 };
  return res.json();
}
