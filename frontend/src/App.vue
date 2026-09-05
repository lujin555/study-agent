<template>
  <div class="app">
    <div v-if="!authed" class="login">
      <h2>学习助手 Agent</h2>
      <p class="login-hint">请输入访问密码</p>
      <input v-model="password" type="password" placeholder="访问密码" @keyup.enter="doLogin" />
      <button @click="doLogin" :disabled="!password.trim()">登录</button>
      <p v-if="loginError" class="error">{{ loginError }}</p>
    </div>
    <template v-else>
            <div class="header">
        <h2>学习助手 Agent</h2>
        <div class="header-actions">
          <input ref="fileInput" type="file" accept=".pdf,.docx,.txt,.md" style="display:none" @change="onFileSelected" />
          <button @click="fileInput.click()" :disabled="loading">上传资料</button>
          <button @click="startNewChat">新对话</button>
        </div>
      </div>
      <p v-if="uploadStatus" class="upload-status">{{ uploadStatus }}</p>
      <div ref="messagesBox" class="messages">
        <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]">
          <div class="bubble">{{ m.content }}</div>
          <details v-if="m.trace && m.trace.length" class="trace">
            <summary>Agent 过程（{{ m.trace.length }} 步）</summary>
            <div v-for="(t, j) in m.trace" :key="j" class="step">
              <code>调用了 {{ t.tool }}({{ JSON.stringify(t.arguments) }})</code>
              <p>结果：{{ t.result_preview }}</p>
            </div>
          </details>
        </div>
        <div v-if="status" class="msg assistant">
          <div class="bubble">{{ status }}</div>
        </div>
      <div v-if="loading" class="msg assistant">
          <div class="bubble">思考中...</div>
        </div>
      </div>
      <div v-if="quiz" class="quiz-card">
        <p class="quiz-question">{{ quiz.question }}</p>
        <button v-for="(opt, key) in quiz.options" :key="key" class="quiz-option"
                :class="{ selected: selected === key, correct: answered && key === quiz.answer, wrong: answered && selected === key && key !== quiz.answer }"
                :disabled="answered"
                @click="chooseOption(key)">
          {{ key }}. {{ opt }}
        </button>
        <p v-if="answered" class="quiz-feedback">
          <template v-if="selected === quiz.answer">✅ 答对了！</template>
          <template v-else>❌ 答错了，正确答案是 {{ quiz.answer }}</template>
        </p>
        <p v-if="answered && quiz.explain" class="quiz-explain">📖 {{ quiz.explain }}</p>
      </div>
      <form @submit.prevent="send">
        <input v-model="question" placeholder="输入学习问题，如：计算机网络第三章讲了什么重点？" />
        <button :disabled="loading || !question.trim()">发送</button>
      </form>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { askAgent, loadHistory, login, getToken, uploadDocument } from "./api.js";

const question = ref("");
const messages = ref([]);
const loading = ref(false);
const conversationId = ref(localStorage.getItem("conversation_id") || crypto.randomUUID());
localStorage.setItem("conversation_id", conversationId.value);
const status = ref("");       // "正在查资料…"之类的过程提示
const authed = ref(!!getToken());   // 有没有登录令牌
const password = ref("");
const loginError = ref("");
const fileInput = ref(null);
const uploadStatus = ref("");
const quiz = ref(null);        // 当前显示的题目卡片
const selected = ref(null);    // 用户选中的选项（A/B/C/D）
const answered = ref(false);   // 是否已作答（true=交卷：锁定按钮+显示判定）

// ===== 打字机：队列 + 定时器 =====
const queue = ref([]);        // 排队等待显示的字
let timer = null;             // 定时器 id
let currentMsg = null;        // 正在"打字"的那条消息

function flushQueue() {
  // done 来了：队列里剩下的字一次全显示，停表
  if (currentMsg) {
    currentMsg.content += queue.value.join("");
    queue.value = [];
  }
  clearInterval(timer);
  timer = null;
}

const messagesBox = ref(null);   // 消息容器的引用
function startTypewriter() {
  currentMsg = { role: "assistant", content: "" };   // 创建气泡（丢了）
  messages.value.push(currentMsg);                   // 挂到消息列表（丢了）
  queue.value = [];                                  // 清队列（丢了）
  clearInterval(timer);                              // 防重复开表（建议加）
  timer = setInterval(() => {
    const pending = queue.value.length;
    if (pending > 0) {
      const take = Math.max(1, Math.ceil(pending / 10));
      currentMsg.content += queue.value.splice(0, take).join("");
      scrollToBottom();
    }
  }, 50);
}

function scrollToBottom() {
  if (messagesBox.value) {
    messagesBox.value.scrollTop = messagesBox.value.scrollHeight;
  }
}
function startNewChat() {
  if (loading.value) return;    // 正在回答时禁止切换，防止流写进已清空的列表
  conversationId.value = crypto.randomUUID();
  localStorage.setItem("conversation_id", conversationId.value);
  messages.value = [];          // 清屏
  quiz.value = null;            // 清掉题目卡片
  selected.value = null;
  answered.value = false;       // 重置作答态
}
function chooseOption(key) {
  if (answered.value) return;   // 已交卷则忽略（双重保险，disabled 已挡一层）
  selected.value = key;         // 记录选中的选项
  answered.value = true;        // 标记已作答 → 触发判定 + 锁定
}
async function onFileSelected(event) {
  const file = event.target.files[0];
  if (!file) return;
  uploadStatus.value = `正在上传 ${file.name}...`;
  try {
    const res = await uploadDocument(file, conversationId.value);
    if (res.code === 401) { onUnauthorized(); return; }
    if (res.code === 200) {
      uploadStatus.value = `${res.filename} 已入库 ${res.chunks} 块`;
      if (res.warning) {
        uploadStatus.value += "。⚠️ " + res.warning;
      }
    } else {
      uploadStatus.value = res.detail || "上传失败";
    }
  } catch (e) {
    uploadStatus.value = "上传失败：请确认后端已启动";
  }
  event.target.value = "";   // 清空 input，允许重复选同一文件
}
async function send() {
  const q = question.value.trim();
  if (!q || loading.value) return;
  loading.value = true;
  messages.value.push({ role: "user", content: q });
  scrollToBottom();
  question.value = "";
  try {
    const traces = [];                                  // 攒工具过程
    await askAgent(q, conversationId.value, {
      answer_start() { startTypewriter(); },          // 开始打字
      token(data) { queue.value.push(data); },        // 来的字进队列
      unauthorized() { onUnauthorized(); },           // 令牌失效 → 回登录页
      quiz(data) { quiz.value = data; selected.value = null; answered.value = false; },  // 收到题目 → 显示卡片（重置作答态）
      trace(data) {
        traces.push(data);                            // 攒起来，done 时挂到消息上
        status.value = "正在调用工具: " + data.tool;
      },
      done() {
        flushQueue();
        if (currentMsg) currentMsg.trace = traces;     // 面板复活的关键
        scrollToBottom();
        status.value = "";
        loading.value = false;
      },
      error(data) {
        flushQueue(); status.value = "";
        if (currentMsg) {
          currentMsg.content = data;
          currentMsg.trace = traces;
        }
        loading.value = false;
      },
    });
  } catch (e) {
    flushQueue(); status.value = "";
    messages.value.push({ role: "assistant", content: "请求失败，请确认后端已启动" });
    loading.value = false;
  }
}
async function doLogin() {
  loginError.value = "";
  const res = await login(password.value);
  if (res.code === 200) {
    localStorage.setItem("access_token", res.token);
    authed.value = true;
    password.value = "";
    loadHistoryAndShow();
  } else {
    loginError.value = res.detail || "密码错误";
  }
}

function onUnauthorized() {
  localStorage.removeItem("access_token");
  authed.value = false;
  loginError.value = "登录已过期，请重新输入密码";
}

async function loadHistoryAndShow() {
  try {
    const res = await loadHistory(conversationId.value);
    if (res.code === 401) { onUnauthorized(); return; }
    if (res.code === 200) {
      messages.value = res.data.map(m => ({ role: m.role, content: m.content }));
      scrollToBottom();
    }
  } catch (e) {
    // 加载失败就空着，不阻塞聊天
  }
}

onMounted(() => {
  if (authed.value) loadHistoryAndShow();
});
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: system-ui, sans-serif; background: #f5f6f8; }
.app { max-width: 720px; margin: 24px auto; padding: 16px; background: #fff; border-radius: 10px; }
h2 { margin-bottom: 12px; font-size: 18px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.header h2 { margin-bottom: 0; }
.login { text-align: center; padding: 40px 20px; }
.login-hint { color: #888; margin-bottom: 12px; }
.login input { max-width: 260px; margin: 0 auto 12px; display: block; }
.error { color: #d33; margin-top: 10px; font-size: 14px; }
.quiz-card { border: 1px solid #e0e0e0; border-radius: 10px; padding: 14px; margin-bottom: 12px; background: #fafcff; color: #222 !important; }
.quiz-question { font-weight: 600; margin-bottom: 10px; line-height: 1.5; color: #111 !important; }
.quiz-option { display: block; width: 100%; text-align: left; margin-bottom: 8px; padding: 10px 12px; border: 1px solid #ddd; border-radius: 8px; background: #fff; cursor: pointer; color: #222 !important; }
.quiz-option:hover { border-color: #4a90d9; }
.quiz-option.selected { border-color: #4a90d9; background: #d6e6fa; color: #0a3a6b !important; }
.quiz-option:disabled { cursor: not-allowed; opacity: 0.6; }
.quiz-option.correct:disabled { background: #e6f6e6; border-color: #2e8b57; color: #1d5c39 !important; opacity: 1; }
.quiz-option.wrong:disabled { background: #fdecea; border-color: #d93025; color: #8a1a11 !important; opacity: 1; }
.quiz-feedback { margin-top: 10px; font-weight: 600; color: #222 !important; }
.quiz-explain { margin-top: 6px; padding: 8px 10px; background: #f0f4f8; border-radius: 6px; font-size: 14px; line-height: 1.6; color: #333 !important; }
.messages { min-height: 320px; max-height: 60vh; overflow-y: auto; border: 1px solid #eee; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
.msg { margin-bottom: 10px; }
.bubble { padding: 8px 12px; border-radius: 8px; line-height: 1.6; white-space: pre-wrap; }
.msg.user .bubble { background: #4a90d9; color: #fff; }
.msg.assistant .bubble { background: #f0f0f0; }
.trace { margin-top: 6px; font-size: 12px; color: #666; }
.step { margin: 4px 0; padding: 6px 8px; background: #fafafa; border-radius: 6px; }
.step p { margin-top: 2px; }
form { display: flex; gap: 8px; }
input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 6px; }
button { padding: 10px 18px; border: none; background: #4a90d9; color: #fff; border-radius: 6px; cursor: pointer; }
button:disabled { opacity: 0.5; }
</style>
