<template>
  <div class="app">
    <h2>学习助手 Agent</h2>
    <div class="messages">
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
    <form @submit.prevent="send">
      <input v-model="question" placeholder="输入学习问题，如：计算机网络第三章讲了什么重点？" />
      <button :disabled="loading || !question.trim()">发送</button>
    </form>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { askAgent } from "./api.js";

const question = ref("");
const messages = ref([]);
const loading = ref(false);
const conversationId = ref("default");   // 当前对话的 id
const status = ref("");       // "正在查资料…"之类的过程提示

// ===== 打字机：队列 + 定时器 =====
const queue = ref([]);        // 排队等待显示的字
let timer = null;             // 定时器 id
let currentMsg = null;        // 正在"打字"的那条消息

function startTypewriter() {
  currentMsg = { role: "assistant", content: "" };
  messages.value.push(currentMsg);
  queue.value = [];
  timer = setInterval(() => {
    const ch = queue.value.shift();       // 从队头取一个字
    if (ch) currentMsg.content += ch;     // 拼到消息上
  }, 50);                                 // 每 50ms 一个
}

function flushQueue() {
  // done 来了：队列里剩下的字一次全显示，停表
  if (currentMsg) {
    currentMsg.content += queue.value.join("");
    queue.value = [];
  }
  clearInterval(timer);
  timer = null;
}

async function send() {
  const q = question.value.trim();
  if (!q || loading.value) return;
  loading.value = true;
  messages.value.push({ role: "user", content: q });
  question.value = "";
  try {
        await askAgent(q, conversationId.value, {
      answer_start() { startTypewriter(); },          // 开始打字
      token(data) { queue.value.push(data); },        // 来的字进队列
      trace(data) {
        status.value = "正在调用工具: " + data.tool_calls.map(t => t.name).join("、");
      },
      done() { flushQueue(); status.value = ""; loading.value = false; },
      error(data) {
        flushQueue(); status.value = "";
        if (currentMsg) currentMsg.content = data;
        loading.value = false;
      },
    });
  } catch (e) {
    flushQueue(); status.value = "";
    messages.value.push({ role: "assistant", content: "请求失败，请确认后端已启动" });
    loading.value = false;
  }
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: system-ui, sans-serif; background: #f5f6f8; }
.app { max-width: 720px; margin: 24px auto; padding: 16px; background: #fff; border-radius: 10px; }
h2 { margin-bottom: 12px; font-size: 18px; }
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
