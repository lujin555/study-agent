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
          <button @click="openQuizBox" :disabled="loading || view !== 'chat'">出题</button>
          <button v-if="view === 'chat'" @click="openWrongBook">错题本{{ wrongList.length ? `(${wrongList.length})` : "" }}</button>
          <button v-else @click="goChat">← 返回聊天</button>
          <button v-if="view === 'chat'" @click="startNewChat">新对话</button>
        </div>
      </div>
      <template v-if="view === 'chat'">
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
        <input v-model="question" placeholder="输入学习问题，如：计算机网络第三章讲了什么重点？" :disabled="loading" />
        <button v-if="!loading" :disabled="!question.trim()">发送</button>
        <button v-else type="button" @click="stopGeneration" class="stop-btn">停止</button>
      </form>
      </template>

      <!-- 错题本独立界面 -->
      <div v-if="view === 'wrong'" class="wrongbook-page">
        <div class="wrongbook-head">
          <span>📚 错题本（{{ wrongList.length }} 道）</span>
          <button class="wrongbook-refresh" @click="loadWrongList" :disabled="wrongLoading">刷新</button>
        </div>
        <p v-if="wrongLoading" class="wrongbook-hint">加载中...</p>
        <p v-else-if="!wrongList.length" class="wrongbook-hint">还没有错题。答错的题会自动记到这里，方便复习。</p>
        <div v-for="w in wrongList" :key="w.id" class="wrong-item">
          <p class="wrong-q">{{ w.question }}</p>
          <div class="wrong-opts">
            <span v-for="(txt, k) in w.options" :key="k"
                  :class="['wrong-opt', k === w.correct_answer ? 'opt-correct' : '', k === w.your_answer && k !== w.correct_answer ? 'opt-wrong' : '']">
              {{ k }}. {{ txt }}
            </span>
          </div>
          <p class="wrong-result">你选了 {{ w.your_answer }}，正确答案 {{ w.correct_answer }}</p>
          <p v-if="w.explain" class="wrong-explain">📖 {{ w.explain }}</p>
        </div>
      </div>

      <!-- 出题主题弹框 -->
      <div v-if="showQuizBox" class="quiz-box-mask" @click.self="closeQuizBox">
        <div class="quiz-box">
          <h3>出题</h3>
          <p class="quiz-box-tip">输入想考的主题，如"C++ 多态"、"TCP 三次握手"</p>
          <input v-model="quizTopic" placeholder="输入出题主题" @keyup.enter="confirmQuiz" :disabled="quizLoading" />
          <div class="quiz-box-actions">
            <button @click="closeQuizBox" :disabled="quizLoading">取消</button>
            <button @click="confirmQuiz" :disabled="quizLoading || !quizTopic.trim()">
              {{ quizLoading ? "出题中..." : "出题" }}
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { askAgent, loadHistory, login, getToken, uploadDocument, saveWrongAnswer, fetchWrongAnswers, generateQuiz } from "./api.js";

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
const view = ref("chat");      // 当前视图：'chat'=聊天 | 'wrong'=错题本（独立界面）
const wrongList = ref([]);     // 错题列表
const wrongLoading = ref(false); // 拉取错题中
const showQuizBox = ref(false); // 出题主题弹框是否显示
const quizTopic = ref("");     // 出题弹框里输入的主题
const quizLoading = ref(false); // 出题请求中

// ===== 打字机：队列 + 定时器 =====
const queue = ref([]);        // 排队等待显示的字
let timer = null;             // 定时器 id
let currentMsg = null;        // 正在"打字"的那条消息
let abortController = null;   // SSE 中断控制器（点"停止"时 abort）

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
function scrollToTop() {
  window.scrollTo(0, 0);   // 切视图时回到页面顶部
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
function stopGeneration() {
  if (abortController) {
    abortController.abort();     // 切断 SSE → 后端级联关闭 DeepSeek 流
    abortController = null;
  }
}
function chooseOption(key) {
  if (answered.value) return;   // 已交卷则忽略（双重保险，disabled 已挡一层）
  selected.value = key;         // 记录选中的选项
  answered.value = true;        // 标记已作答 → 触发判定 + 锁定
  if (key !== quiz.value.answer) {
    // 答错了 → 自动存进错题本（方便复习）；异步进行，不阻塞界面
    saveWrongAnswer({
      question: quiz.value.question,
      options: quiz.value.options,
      your_answer: key,
      correct_answer: quiz.value.answer,
      explain: quiz.value.explain || "",
    }).then((res) => { if (res && res.code === 200) loadWrongList(); });
  }
}
async function openWrongBook() {
  view.value = "wrong";          // 切到错题本整页视图
  if (!wrongList.value.length) loadWrongList();   // 首次进入拉一次
  scrollToTop();
}
function goChat() {
  view.value = "chat";           // 返回聊天视图
}
function openQuizBox() {
  quizTopic.value = "";
  showQuizBox.value = true;      // 弹出出题主题输入框
}
function closeQuizBox() {
  if (quizLoading.value) return; // 出题中禁止关闭
  showQuizBox.value = false;
}
async function confirmQuiz() {
  const topic = quizTopic.value.trim();
  if (!topic || quizLoading.value) return;
  quizLoading.value = true;
  try {
    const res = await generateQuiz(topic);
    if (res && res.code === 401) { onUnauthorized(); return; }
    if (res && res.code === 200 && res.data) {
      showQuizBox.value = false;
      quiz.value = res.data;            // 直接渲染成题目卡片
      selected.value = null;
      answered.value = false;
      view.value = "chat";              // 回到聊天视图看题
      scrollToBottom();
    } else {
      alert(res?.detail || "出题失败，请稍后再试");
    }
  } catch (e) {
    alert("出题失败：" + e.message);
  } finally {
    quizLoading.value = false;
  }
}
async function loadWrongList() {
  wrongLoading.value = true;
  try {
    const res = await fetchWrongAnswers();
    if (res && res.code === 200) wrongList.value = res.data;
  } finally {
    wrongLoading.value = false;
  }
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
  abortController = new AbortController();
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
      aborted() {                                     // 用户点"停止" → 保留已生成的部分
        flushQueue();
        if (currentMsg) currentMsg.trace = traces;
        status.value = "";
        loading.value = false;
      },
    }, abortController.signal);
  } catch (e) {
    flushQueue(); status.value = "";
    messages.value.push({ role: "assistant", content: "请求失败，请确认后端已启动" });
    loading.value = false;
  } finally {
    abortController = null;
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

.wrongbook-page { padding: 4px 2px; color: #222 !important; }
.wrongbook-page .wrongbook-head { font-size: 18px; padding: 8px 0 14px; border-bottom: 1px solid #eee; }
.wrongbook-head { display: flex; justify-content: space-between; align-items: center; font-weight: 600; margin-bottom: 10px; }
.wrongbook-refresh { font-size: 13px; padding: 4px 10px; }
.wrongbook-hint { color: #555 !important; font-size: 14px; padding: 8px 0; }
.wrong-item { border-bottom: 1px solid #eee; padding: 14px 0; }
.wrong-q { font-weight: 600; margin-bottom: 6px; line-height: 1.5; color: #111 !important; }
.wrong-opts { display: flex; flex-direction: column; gap: 4px; margin-bottom: 6px; }
.wrong-opt { padding: 5px 8px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; color: #333 !important; }
.wrong-opt.opt-correct { background: #e6f6e6; border-color: #2e8b57; color: #1d5c39 !important; }
.wrong-opt.opt-wrong { background: #fdecea; border-color: #d93025; color: #8a1a11 !important; }
.wrong-result { font-size: 14px; font-weight: 600; color: #222 !important; }
.wrong-explain { margin-top: 5px; padding: 6px 8px; background: #f0f4f8; border-radius: 6px; font-size: 13px; line-height: 1.5; color: #333 !important; }
.quiz-box-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.quiz-box { background: #fff; border-radius: 10px; padding: 20px; width: 340px; max-width: 90vw; box-shadow: 0 8px 30px rgba(0,0,0,0.2); color: #222 !important; }
.quiz-box h3 { margin-bottom: 8px; color: #111 !important; }
.quiz-box-tip { font-size: 13px; color: #555 !important; margin-bottom: 10px; }
.quiz-box input { width: 100%; padding: 8px 10px; border: 1px solid #ccc; border-radius: 6px; font-size: 14px; margin-bottom: 14px; color: #222 !important; }
.quiz-box-actions { display: flex; justify-content: flex-end; gap: 8px; }
.quiz-box-actions button { padding: 6px 14px; }
.quiz-box-actions button:first-child { background: #eee; color: #333; }
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
.stop-btn { background: #e74c3c; }
.stop-btn:hover { background: #c0392b; }
</style>
