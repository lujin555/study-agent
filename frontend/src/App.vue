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

async function send() {
  const q = question.value.trim();
  if (!q || loading.value) return;
  loading.value = true;
  const history = messages.value
    .filter(m => m.role === "user" || m.role === "assistant")
    .map(m => ({ role: m.role, content: m.content }));
  messages.value.push({ role: "user", content: q });
  question.value = "";
  try {
    const res = await askAgent(q, history);
    if (res.code === 200) {
      messages.value.push({ role: "assistant", content: res.data.answer, trace: res.data.trace });
    } else {
      messages.value.push({ role: "assistant", content: res.detail || "出错了" });
    }
  } catch (e) {
    messages.value.push({ role: "assistant", content: "请求失败，请确认后端已启动" });
  }
  loading.value = false;
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
