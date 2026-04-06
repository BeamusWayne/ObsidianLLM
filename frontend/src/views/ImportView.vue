<template>
  <div class="import-wrap">
    <div class="page-header">
      <h1 class="page-title">导入内容</h1>
      <p class="page-subtitle">粘贴链接或上传文件，AI 自动识别和整理</p>
    </div>

    <!-- Billing exhausted modal -->
    <div v-if="status.billing_needs_confirm" class="modal-overlay">
      <div class="modal-box">
        <div style="font-size:24px;text-align:center">⚠️</div>
        <div class="modal-title">所有 API 后端余额已耗尽</div>
        <p style="font-size:13px;color:var(--muted);line-height:1.6">{{ status.billing_confirm_msg || '链中所有 API 后端均余额不足，是否启用本地 Ollama 继续处理？' }}</p>
        <p style="font-size:12px;color:var(--muted)">选择「否」将跳过当前文件，队列中其余文件继续处理。</p>
        <div class="modal-actions">
          <button class="btn-primary" :disabled="confirmPending" @click="confirmOllama">
            <span v-if="confirmPending" class="spinner"></span>
            是，启用 Ollama
          </button>
          <button class="btn-ghost" :disabled="confirmPending" @click="rejectOllama">否，跳过</button>
        </div>
      </div>
    </div>

    <!-- Import tabs -->
    <div class="import-tabs">
      <button v-for="t in tabs" :key="t.value" class="import-tab" :class="{ active: activeTab === t.value }" @click="activeTab = t.value">
        <span>{{ t.icon }}</span> {{ t.label }}
      </button>
    </div>

    <!-- Tab: 链接 -->
    <div v-if="activeTab === 'url'" class="tab-content">
      <div class="card clip-card">
        <div class="clip-title">粘贴链接</div>
        <p class="clip-desc">支持文章、YouTube、Twitter、小红书、RSS — 自动识别</p>
        <div class="clip-input-row">
          <input v-model="url" placeholder="粘贴任意链接…" :disabled="clipping" @keyup.enter="doClip" />
          <button class="btn-primary" :disabled="clipping || !url.trim()" @click="doClip">
            <span v-if="clipping" class="spinner"></span>
            <span v-else>导入</span>
          </button>
        </div>
        <div v-if="clipping" class="clip-progress">
          <div class="progress-bar-indeterminate"></div>
          <span class="clip-stage">{{ clipStage }}</span>
        </div>
        <div v-if="clipResult" class="clip-result" :class="clipResult.error ? 'result-err' : 'result-ok'">
          <template v-if="clipResult.error">✗ {{ clipResult.error }}</template>
          <template v-else>✓ 已保存 <strong>{{ clipResult.title }}</strong>（{{ clipResult.images_saved }} 张图）</template>
        </div>
        <div class="src-badges">
          <span class="src-badge src-youtube">▶ YouTube</span>
          <span class="src-badge src-twitter">𝕏 Twitter / X</span>
          <span class="src-badge src-xiaohongshu">✿ 小红书</span>
          <span class="src-badge src-article">RSS</span>
          <span class="src-badge src-article">任意网页</span>
        </div>
      </div>
    </div>

    <!-- Tab: 上传文件 -->
    <div v-else-if="activeTab === 'file'" class="tab-content">
      <div class="card coming-soon">
        <div style="font-size:32px;margin-bottom:8px">📄</div>
        <div style="font-size:14px;font-weight:600">上传文件</div>
        <p style="font-size:13px;color:var(--muted);margin-top:6px">支持 .md、.txt、.pdf 文件，即将推出</p>
      </div>
    </div>

    <!-- Tab: 自动同步 -->
    <div v-else-if="activeTab === 'sync'" class="tab-content">
      <div class="card coming-soon">
        <div style="font-size:32px;margin-bottom:8px">🔄</div>
        <div style="font-size:14px;font-weight:600">自动同步</div>
        <p style="font-size:13px;color:var(--muted);margin-top:6px">RSS 订阅、定时抓取，即将推出</p>
      </div>
    </div>

    <!-- Tab: 手动 -->
    <div v-else-if="activeTab === 'manual'" class="tab-content">
      <div class="card coming-soon">
        <div style="font-size:32px;margin-bottom:8px">✏️</div>
        <div style="font-size:14px;font-weight:600">手动输入</div>
        <p style="font-size:13px;color:var(--muted);margin-top:6px">直接粘贴文字内容，即将推出</p>
      </div>
    </div>

    <!-- Ingest status -->
    <div class="card ingest-card" :class="{ running: status.running }">
      <div class="ingest-header">
        <span class="ingest-title">处理队列</span>
        <span class="ingest-badge" :class="status.running ? 'badge-running' : 'badge-idle'">
          <span v-if="status.running" class="spinner" style="width:8px;height:8px;border-width:1.5px"></span>
          {{ status.running ? '处理中' : '空闲' }}
        </span>
      </div>
      <div v-if="status.billing_fallback && !status.billing_needs_confirm" class="billing-warn">
        ⚠️ {{ status.billing_fallback_msg || 'LLM 余额不足，已切换到下一个后端' }}
        <button class="banner-close" @click="dismissBilling">✕</button>
      </div>
      <template v-if="status.running">
        <div class="ingest-current">
          <code>{{ status.current_file }}</code>
          <span class="elapsed">{{ elapsedStr }}</span>
        </div>
        <div v-if="status.queued > 0" class="ingest-queue">队列中还有 {{ status.queued }} 篇</div>
        <div v-if="status.log && status.log.length" class="ingest-log">
          <div v-for="(line, i) in status.log.slice(-5)" :key="i" class="log-line"
               :class="{ 'log-warn': line.includes('WARNING') || line.startsWith('ERROR') }">{{ line }}</div>
        </div>
      </template>
      <div v-else class="ingest-idle">
        <span v-if="status.last_error" style="color:var(--danger)">✗ {{ status.last_error }}</span>
        <span v-else-if="status.finished_at" style="color:var(--muted)">上次完成：{{ lastRunStr }} · 累计 {{ status.total_processed }} 篇</span>
        <span v-else style="color:var(--muted)">等待任务…</span>
      </div>
      <div class="ingest-footer">
        <button class="btn-ghost btn-sm" @click="doIngest" :disabled="status.running">处理所有未处理文件</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const activeTab = ref('url')
const url = ref('')
const clipping = ref(false)
const clipStage = ref('')
const clipResult = ref(null)
const confirmPending = ref(false)
const status = ref({ running: false, log: [], queued: 0, total_processed: 0 })
const startTime = ref(null)
const now = ref(Date.now())
let pollTimer = null
let clockTimer = null

const tabs = [
  { value: 'url',    label: '链接',    icon: '🔗' },
  { value: 'file',   label: '上传文件', icon: '📄' },
  { value: 'sync',   label: '自动同步', icon: '🔄' },
  { value: 'manual', label: '手动',    icon: '✏️' },
]

const elapsedStr = computed(() => {
  if (!startTime.value) return ''
  const s = Math.floor((now.value - startTime.value) / 1000)
  if (s < 60) return `${s}s`
  return `${Math.floor(s / 60)}m ${s % 60}s`
})

const lastRunStr = computed(() => {
  if (!status.value.finished_at) return ''
  return new Date(status.value.finished_at * 1000).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
})

async function doClip() {
  if (!url.value.trim() || clipping.value) return
  clipping.value = true
  clipResult.value = null
  clipStage.value = '正在抓取…'
  try {
    const res = await fetch('/api/clip', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url.value.trim() }),
    }).then(r => r.json())
    clipResult.value = res
    if (!res.error) { url.value = ''; await pollStatus() }
  } catch (e) {
    clipResult.value = { error: String(e) }
  } finally {
    clipping.value = false
    clipStage.value = ''
  }
}

async function doIngest() {
  await fetch('/api/ingest', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
  await pollStatus()
}

async function pollStatus() {
  const data = await fetch('/api/ingest/status').then(r => r.json()).catch(() => null)
  if (!data) return
  if (data.running && !startTime.value) startTime.value = Date.now()
  if (!data.running) startTime.value = null
  status.value = data
}

async function confirmOllama() {
  confirmPending.value = true
  await fetch('/api/ingest/confirm-ollama', { method: 'POST' })
  confirmPending.value = false
}
async function rejectOllama() {
  await fetch('/api/ingest/reject-ollama', { method: 'POST' })
}
async function dismissBilling() {
  await fetch('/api/ingest/dismiss-billing', { method: 'POST' })
  status.value = { ...status.value, billing_fallback: false }
}

onMounted(() => {
  pollStatus()
  pollTimer = setInterval(pollStatus, 2000)
  clockTimer = setInterval(() => { now.value = Date.now() }, 1000)
})
onUnmounted(() => {
  clearInterval(pollTimer)
  clearInterval(clockTimer)
})
</script>

<style scoped>
.import-wrap {
  height: 100%; overflow-y: auto;
  padding: 28px 32px;
  display: flex; flex-direction: column; gap: 16px;
  max-width: 640px;
}

.import-tabs { display: flex; gap: 6px; }
.import-tab {
  display: flex; align-items: center; gap: 5px;
  padding: 7px 14px; border-radius: 20px; font-size: 12px;
  border: 1px solid var(--border); background: var(--surface);
  color: var(--muted); cursor: pointer; transition: all 0.15s;
}
.import-tab:hover { border-color: var(--accent); color: var(--accent); }
.import-tab.active { background: var(--accent); color: #fff; border-color: var(--accent); font-weight: 600; }

.tab-content { }
.clip-card { display: flex; flex-direction: column; gap: 12px; }
.clip-title { font-size: 14px; font-weight: 600; }
.clip-desc { font-size: 12px; color: var(--muted); }
.clip-input-row { display: flex; gap: 8px; }
.clip-input-row input { flex: 1; }
.clip-progress {
  display: flex; flex-direction: column; gap: 6px;
}
.progress-bar-indeterminate {
  height: 3px; border-radius: 2px; background: var(--surface2);
  position: relative; overflow: hidden;
}
.progress-bar-indeterminate::after {
  content: ''; position: absolute; height: 100%;
  width: 40%; background: var(--accent);
  animation: slide 1.2s ease-in-out infinite;
}
@keyframes slide { 0% { left: -40% } 100% { left: 100% } }
.clip-stage { font-size: 12px; color: var(--muted); }
.clip-result { font-size: 13px; padding: 8px 12px; border-radius: 8px; }
.result-ok { background: var(--result-ok-bg); color: var(--result-ok-text); }
.result-err { background: var(--result-err-bg); color: var(--result-err-text); }
.src-badges { display: flex; flex-wrap: wrap; gap: 6px; }

.coming-soon {
  text-align: center; padding: 40px 20px;
  background: var(--surface2); border-style: dashed;
}

/* Ingest status */
.ingest-card { display: flex; flex-direction: column; gap: 10px; }
.ingest-card.running { border-color: color-mix(in srgb, var(--accent) 40%, transparent); }
.ingest-header { display: flex; align-items: center; justify-content: space-between; }
.ingest-title { font-size: 13px; font-weight: 600; }
.ingest-badge {
  font-size: 11px; padding: 2px 8px; border-radius: 10px;
  display: flex; align-items: center; gap: 4px;
}
.badge-running { background: var(--accent-light); color: var(--accent); }
.badge-idle { background: var(--surface2); color: var(--muted); }
.billing-warn {
  font-size: 12px; color: var(--topic); background: #fff7ed;
  border-radius: 6px; padding: 7px 10px;
  display: flex; align-items: center; justify-content: space-between;
}
.banner-close { background: none; border: none; cursor: pointer; color: var(--muted); font-size: 12px; padding: 0; }
.ingest-current { display: flex; align-items: center; justify-content: space-between; font-size: 12px; }
.ingest-current code { font-size: 11px; color: var(--muted); background: var(--surface2); padding: 2px 6px; border-radius: 4px; }
.elapsed { font-size: 11px; color: var(--muted); }
.ingest-queue { font-size: 12px; color: var(--muted); }
.ingest-log { font-size: 11px; background: var(--surface2); border-radius: 6px; padding: 8px; max-height: 100px; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }
.log-line { font-family: monospace; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.log-warn { color: var(--topic); }
.ingest-idle { font-size: 12px; }
.ingest-footer { display: flex; justify-content: flex-end; }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.3);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal-box {
  background: var(--surface); border-radius: 14px;
  padding: 24px; width: 360px; display: flex; flex-direction: column; gap: 14px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.15);
}
.modal-title { font-size: 15px; font-weight: 700; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; }
</style>
