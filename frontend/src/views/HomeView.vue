<template>
  <div class="home-wrap">
    <!-- Greeting -->
    <div class="greeting-header">
      <div class="greeting-text">{{ greeting }}</div>
      <div class="greeting-sub">{{ hasContent ? '你的知识库在等你' : '还没有内容' }}</div>
    </div>

    <!-- Echo chat widget -->
    <div class="echo-card card">
      <div class="echo-header">
        <span class="echo-avatar">🦇</span>
        <span class="echo-name">Echo <span class="echo-badge">AI</span></span>
      </div>

      <!-- Message history -->
      <div v-if="messages.length" class="echo-messages" ref="msgEl">
        <div v-for="(m, i) in messages" :key="i" class="echo-msg" :class="m.role">
          <div class="echo-msg-bubble">{{ m.content }}</div>
        </div>
        <div v-if="loading" class="echo-msg assistant">
          <div class="echo-msg-bubble thinking">
            <span class="dot-pulse"></span><span class="dot-pulse"></span><span class="dot-pulse"></span>
          </div>
        </div>
      </div>

      <!-- Welcome message when empty -->
      <div v-else class="echo-welcome">
        <p>嘿！我是 Echo，你的知识伙伴。把网上看到的好内容拉进来，我帮你整理、分析、串联。有什么想聊的？</p>
      </div>

      <!-- Suggested prompts -->
      <div v-if="!messages.length" class="echo-prompts">
        <button v-for="p in prompts" :key="p" class="prompt-chip" @click="sendPrompt(p)">{{ p }}</button>
      </div>

      <!-- Input -->
      <div class="echo-input-row">
        <input
          v-model="input"
          class="echo-input"
          placeholder="问 Echo 任何问题…"
          :disabled="loading"
          @keyup.enter="send"
        />
        <button class="echo-send" :disabled="loading || !input.trim()" @click="send">
          <span v-if="loading" class="spinner"></span>
          <span v-else>↑</span>
        </button>
      </div>
    </div>

    <!-- Quick actions -->
    <div class="quick-grid">
      <router-link to="/import" class="quick-card card">
        <span class="quick-icon">🔗</span>
        <div class="quick-title">粘贴链接</div>
        <div class="quick-desc">支持微博、X、YouTube 等</div>
      </router-link>
      <router-link to="/import" class="quick-card card">
        <span class="quick-icon">📄</span>
        <div class="quick-title">导入内容</div>
        <div class="quick-desc">上传文件、手动添加</div>
      </router-link>
    </div>

    <!-- Recent additions -->
    <div class="recent-section">
      <div class="recent-header">
        <span class="recent-title">最近添加</span>
        <router-link to="/knowledge" class="recent-more">查看全部 →</router-link>
      </div>
      <div v-if="recent.length === 0" class="recent-empty">
        <p>还没有内容，试试导入一些收藏？</p>
        <router-link to="/import" class="btn-primary" style="display:inline-block;margin-top:8px;text-decoration:none;padding:8px 18px;border-radius:8px">去导入 →</router-link>
      </div>
      <div v-else class="recent-grid">
        <router-link
          v-for="p in recent" :key="p.stem"
          :to="`/wiki/${encodeURIComponent(p.stem)}`"
          class="recent-card card"
        >
          <div class="recent-card-top">
            <span class="tag" :class="`tag-${p.type}`">{{ p.type }}</span>
            <span v-if="p.source_type !== 'article'" class="src-badge" :class="`src-${p.source_type}`">{{ srcLabel(p.source_type) }}</span>
          </div>
          <div class="recent-card-title">{{ p.title }}</div>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'

const input = ref('')
const messages = ref([])
const loading = ref(false)
const recent = ref([])
const msgEl = ref(null)

const prompts = ['帮我制定学习计划', '我的知识盲区在哪？', '推荐我该看什么']

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6)  return '夜深了'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const hasContent = computed(() => recent.value.length > 0)

function srcLabel(t) {
  return { youtube: 'YouTube', twitter: 'Twitter', xiaohongshu: '小红书' }[t] || t
}

async function send() {
  const text = input.value.trim()
  if (!text || loading.value) return
  messages.value = [...messages.value, { role: 'user', content: text }]
  input.value = ''
  loading.value = true
  await nextTick()
  if (msgEl.value) msgEl.value.scrollTop = msgEl.value.scrollHeight

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: messages.value.filter(m => m.role !== 'error'),
        context: 'free',
      }),
    }).then(r => r.json())
    messages.value = [...messages.value, { role: 'assistant', content: res.reply }]
  } catch {
    messages.value = [...messages.value, { role: 'assistant', content: '⚠️ 请检查 LLM 设置后重试' }]
  } finally {
    loading.value = false
    await nextTick()
    if (msgEl.value) msgEl.value.scrollTop = msgEl.value.scrollHeight
  }
}

function sendPrompt(p) {
  input.value = p
  send()
}

onMounted(async () => {
  const pages = await fetch('/api/wiki').then(r => r.json()).catch(() => [])
  recent.value = pages.slice(0, 6)
})
</script>

<style scoped>
.home-wrap {
  height: 100%;
  overflow-y: auto;
  padding: 28px 32px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 720px;
}

.greeting-header { }
.greeting-text { font-size: 22px; font-weight: 700; }
.greeting-sub { font-size: 13px; color: var(--muted); margin-top: 2px; }

/* Ori card */
.echo-card { display: flex; flex-direction: column; gap: 12px; }
.echo-header { display: flex; align-items: center; gap: 8px; }
.echo-avatar { font-size: 20px; }
.echo-name { font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 6px; }
.echo-badge {
  font-size: 9px; font-weight: 700; letter-spacing: 0.5px;
  background: var(--accent); color: #fff;
  padding: 1px 5px; border-radius: 4px;
}

.echo-messages {
  max-height: 280px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 4px 0;
}
.echo-msg { display: flex; }
.echo-msg.user { justify-content: flex-end; }
.echo-msg.assistant { justify-content: flex-start; }
.echo-msg-bubble {
  max-width: 85%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
}
.echo-msg.user .echo-msg-bubble {
  background: var(--accent);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.echo-msg.assistant .echo-msg-bubble {
  background: var(--surface2);
  color: var(--text);
  border-bottom-left-radius: 4px;
}
.thinking { display: flex; align-items: center; gap: 4px; padding: 12px 14px; }
.dot-pulse {
  width: 6px; height: 6px; border-radius: 50%; background: var(--muted);
  animation: pulse 1.2s ease-in-out infinite;
}
.dot-pulse:nth-child(2) { animation-delay: 0.2s; }
.dot-pulse:nth-child(3) { animation-delay: 0.4s; }
@keyframes pulse { 0%,80%,100% { opacity: 0.3 } 40% { opacity: 1 } }

.echo-welcome { font-size: 13px; color: var(--text); line-height: 1.6; }
.echo-prompts { display: flex; flex-wrap: wrap; gap: 8px; }
.prompt-chip {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 20px; padding: 5px 12px; font-size: 12px; color: var(--muted);
  cursor: pointer; transition: all 0.15s;
}
.prompt-chip:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-light); }

.echo-input-row { display: flex; gap: 8px; align-items: center; }
.echo-input {
  flex: 1; background: var(--surface2); border: 1px solid var(--border);
  border-radius: 20px; padding: 9px 16px; font-size: 13px;
}
.echo-input:focus { border-color: var(--accent); }
.echo-send {
  width: 34px; height: 34px; border-radius: 50%;
  background: var(--accent); color: #fff; border: none;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; flex-shrink: 0;
}
.echo-send:disabled { opacity: 0.4; }
.echo-send:not(:disabled):hover { filter: brightness(1.1); }

/* Quick actions */
.quick-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.quick-card {
  display: flex; flex-direction: column; gap: 6px;
  padding: 16px; text-decoration: none; color: var(--text);
  transition: border-color 0.15s, box-shadow 0.15s;
}
.quick-card:hover { border-color: var(--accent); box-shadow: 0 2px 12px rgba(0,0,0,0.06); text-decoration: none; }
.quick-icon { font-size: 20px; }
.quick-title { font-size: 13px; font-weight: 600; }
.quick-desc { font-size: 11px; color: var(--muted); }

/* Recent */
.recent-section { }
.recent-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.recent-title { font-size: 14px; font-weight: 600; }
.recent-more { font-size: 12px; color: var(--accent); }
.recent-empty { text-align: center; padding: 24px; color: var(--muted); font-size: 13px; }
.recent-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
.recent-card {
  display: flex; flex-direction: column; gap: 8px;
  text-decoration: none; color: var(--text); padding: 14px;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.recent-card:hover { border-color: var(--accent); box-shadow: 0 2px 8px rgba(0,0,0,0.06); text-decoration: none; }
.recent-card-top { display: flex; gap: 6px; flex-wrap: wrap; }
.recent-card-title { font-size: 12px; font-weight: 500; line-height: 1.4; color: var(--text); }
</style>
