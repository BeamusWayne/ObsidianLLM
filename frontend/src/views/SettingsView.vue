<template>
  <div class="settings-wrap">
    <div class="settings-panel">
      <h2 class="panel-title">Settings</h2>

      <!-- Theme -->
      <section class="card">
        <div class="card-title">外观主题</div>
        <div class="theme-group">
          <button
            v-for="t in themes" :key="t.value"
            class="theme-btn"
            :class="{ active: currentTheme === t.value }"
            @click="setTheme(t.value)"
          >
            <span class="theme-icon">{{ t.icon }}</span>
            <span>{{ t.label }}</span>
          </button>
        </div>
      </section>

      <!-- LLM Backend -->
      <section class="card">
        <div class="card-title">LLM Backend</div>
        <div class="mode-group">
          <label v-for="m in modes" :key="m.value" class="mode-option"
                 :class="{ active: form.mode === m.value }"
                 @click="form.mode = m.value">
            <span class="mode-radio"></span>
            <div>
              <div class="mode-name">{{ m.label }}</div>
              <div class="mode-desc">{{ m.desc }}</div>
            </div>
          </label>
        </div>
      </section>

      <!-- Ollama -->
      <section v-if="form.mode === 'ollama'" class="card">
        <div class="card-title">Ollama Config</div>
        <div class="field">
          <label>Base URL</label>
          <input v-model="form.ollama.base_url" placeholder="http://localhost:11434" />
        </div>
        <div class="field">
          <label>Text Model</label>
          <input v-model="form.ollama.text_model" placeholder="qwen3.5:9b" />
        </div>
        <div class="field">
          <label>Vision Model</label>
          <input v-model="form.ollama.vision_model" placeholder="qwen3-vl:8b" />
        </div>
      </section>

      <!-- Claude -->
      <section v-if="form.mode === 'claude'" class="card">
        <div class="card-title">Claude API</div>
        <div class="field">
          <label>API Key</label>
          <input v-model="form.claude.api_key" type="password" placeholder="sk-ant-…" />
        </div>
        <div class="field">
          <label>Model</label>
          <input v-model="form.claude.text_model" placeholder="claude-sonnet-4-6" />
        </div>
      </section>

      <!-- Custom -->
      <section v-if="form.mode === 'custom'" class="card">
        <div class="card-title">Custom API (OpenAI-compatible)</div>
        <div class="field">
          <label>Base URL</label>
          <input v-model="form.custom.base_url" placeholder="https://api.example.com/v1" />
        </div>
        <div class="field">
          <label>API Key</label>
          <input v-model="form.custom.api_key" type="password" placeholder="sk-…" />
        </div>
        <div class="field">
          <label>Model Name</label>
          <input v-model="form.custom.text_model" placeholder="gpt-4o" />
        </div>
      </section>

      <!-- Auto Ingest -->
      <section class="card">
        <div class="card-title">Ingest 行为</div>
        <label class="toggle-row">
          <div>
            <div class="toggle-label">Clip 后自动入队处理</div>
            <div class="toggle-desc">关闭后，Clip 只保存原始文件，需要在 Clip & Ingest 页面手动选择处理</div>
          </div>
          <div class="toggle" :class="{ on: form.auto_ingest }" @click="form.auto_ingest = !form.auto_ingest">
            <div class="toggle-thumb"></div>
          </div>
        </label>
      </section>

      <!-- Fallback chain -->
      <section class="card">
        <div class="card-title">推理顺序</div>
        <div class="chain-desc">系统严格按此顺序使用后端。若余额不足且未配置 Ollama，会询问是否启用本地模型。拖拽可调整顺序。</div>

        <div class="chain-list">
          <div v-for="(id, i) in form.fallback_chain" :key="id"
            class="chain-item"
            :class="{ 'chain-drag-over': chainDragOver === i, 'chain-primary': i === 0 }"
            draggable="true"
            @dragstart="onChainDragStart(i, $event)"
            @dragover="onChainDragOver(i, $event)"
            @drop="onChainDrop(i)"
            @dragend="onChainDragEnd">
            <span class="chain-handle">⠿</span>
            <span class="chain-icon">{{ chainLabel(id).icon }}</span>
            <span class="chain-name">{{ chainLabel(id).label }}</span>
            <span class="chain-badge" :class="chainConfigOk(id) ? 'badge-ok' : 'badge-warn'">
              {{ chainConfigStatus(id) }}
            </span>
            <span v-if="i === 0" class="chain-primary-tag">主要</span>
            <button class="chain-test-btn"
              :class="testResultClass(id)"
              :disabled="testingId === id"
              @click.stop="testProvider(id)"
              title="测试连通性">
              <span v-if="testingId === id" class="test-spinner"></span>
              <span v-else-if="testResults[id]">{{ testResultLabel(id) }}</span>
              <span v-else>测试</span>
            </button>
            <button class="chain-remove" :disabled="form.fallback_chain.length <= 1"
              @click="removeFromChain(i)" title="从链中移除">✕</button>
          </div>
        </div>

        <div v-if="chainAvailable.length" class="chain-add-row">
          <span class="chain-add-label">添加到链：</span>
          <button v-for="b in chainAvailable" :key="b.id"
            class="chain-add-btn" @click="addToChain(b.id)">
            {{ b.icon }} {{ b.label }} +
          </button>
        </div>
      </section>

      <!-- Parallel Ingest -->
      <section class="card">
        <div class="card-title">并行 Ingest</div>
        <label class="toggle-row">
          <span class="toggle-label">启用并行处理</span>
          <div class="toggle" :class="{ on: form.parallel.enabled }" @click="form.parallel.enabled = !form.parallel.enabled">
            <div class="toggle-thumb"></div>
          </div>
        </label>
        <template v-if="form.parallel.enabled">
          <div class="field">
            <label>并发数（Workers）</label>
            <input v-model.number="form.parallel.workers" type="number" min="1" max="8" />
          </div>
          <div class="field">
            <label>大文件阈值（字符数）— 超过此值走大模型</label>
            <input v-model.number="form.parallel.size_threshold_chars" type="number" min="500" step="500" />
          </div>
          <div class="parallel-route">
            <div class="route-item">
              <span class="route-dot dot-small"></span>
              <span class="route-label">小文件 (&lt; {{ form.parallel.size_threshold_chars }} 字符)</span>
              <select v-model="form.parallel.small_backend" class="route-select">
                <option value="ollama">Ollama（本地）</option>
                <option value="claude">Claude API</option>
                <option value="custom">中转站</option>
              </select>
            </div>
            <div class="route-item">
              <span class="route-dot dot-large"></span>
              <span class="route-label">大文件 (≥ {{ form.parallel.size_threshold_chars }} 字符)</span>
              <select v-model="form.parallel.large_backend" class="route-select">
                <option value="claude">Claude API</option>
                <option value="ollama">Ollama（本地）</option>
                <option value="custom">中转站</option>
              </select>
            </div>
          </div>
        </template>
      </section>

      <div class="actions">
        <button class="btn-primary" :disabled="saving" @click="save">
          {{ saving ? 'Saving…' : 'Save' }}
        </button>
        <span v-if="saved" class="saved-msg">✓ Saved</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'

const THEME_KEY = 'wiki-kb-theme'
const saving = ref(false)
const saved = ref(false)
const currentTheme = ref(localStorage.getItem(THEME_KEY) || 'light')

const themes = [
  { value: 'light',  icon: '☀️', label: '浅色' },
  { value: 'dark',   icon: '🌙', label: '深色' },
  { value: 'system', icon: '💻', label: '跟随系统' },
]

function setTheme(value) {
  currentTheme.value = value
  localStorage.setItem(THEME_KEY, value)
  document.documentElement.setAttribute('data-theme', value)
}

const form = reactive({
  mode: 'ollama',
  auto_ingest: true,
  fallback_chain: ['claude', 'ollama'],
  ollama: { base_url: 'http://localhost:11434', text_model: 'qwen3.5:9b', vision_model: 'qwen3-vl:8b' },
  claude: { api_key: '', text_model: 'claude-sonnet-4-6' },
  custom: { base_url: '', api_key: '', text_model: '' },
  custom_presets: [],
  parallel: { enabled: false, workers: 3, size_threshold_chars: 3000, small_backend: 'ollama', large_backend: 'claude' },
})

// ── Fallback chain helpers ────────────────────────────────────────────────────
const STATIC_CHAIN_BACKENDS = [
  { id: 'claude', label: 'Claude API', icon: '☁️' },
  { id: 'ollama', label: 'Ollama',     icon: '🖥' },
]

// All addable chain entries: static backends + one slot per preset
const chainAvailable = computed(() => {
  const inChain = new Set(form.fallback_chain)
  const statics = STATIC_CHAIN_BACKENDS.filter(b => !inChain.has(b.id))
  const presets = (form.custom_presets || [])
    .map(p => ({ id: `preset:${p.name}`, label: p.name, icon: '🔗' }))
    .filter(b => !inChain.has(b.id))
  return [...statics, ...presets]
})

function chainLabel(id) {
  if (id === 'claude') return { icon: '☁️', label: 'Claude API' }
  if (id === 'ollama') return { icon: '🖥', label: 'Ollama' }
  if (id === 'custom') return { icon: '🔗', label: '自定义' }  // legacy
  if (id.startsWith('preset:')) return { icon: '🔗', label: id.slice(7) }
  return { icon: '🔗', label: id }
}

function chainConfigStatus(id) {
  if (id === 'claude') return form.claude.api_key ? '已配置' : '未设置 Key'
  if (id === 'ollama') return '本地'
  if (id === 'custom') return form.custom.base_url ? '已配置' : '未配置'
  if (id.startsWith('preset:')) {
    const name = id.slice(7)
    const p = (form.custom_presets || []).find(p => p.name === name)
    return p ? p.text_model : '未找到'
  }
  return ''
}

function chainConfigOk(id) {
  if (id === 'claude') return !!form.claude.api_key
  if (id === 'ollama') return true
  if (id === 'custom') return !!(form.custom.base_url && form.custom.text_model)
  if (id.startsWith('preset:')) {
    const name = id.slice(7)
    const p = (form.custom_presets || []).find(p => p.name === name)
    return !!(p?.base_url && p?.text_model)
  }
  return false
}

function addToChain(id) {
  form.fallback_chain.push(id)
}

function removeFromChain(idx) {
  if (form.fallback_chain.length <= 1) return
  form.fallback_chain.splice(idx, 1)
}

// Drag-to-reorder for chain
const chainDragIdx = ref(null)
const chainDragOver = ref(null)

function onChainDragStart(i, evt) {
  chainDragIdx.value = i
  evt.dataTransfer.effectAllowed = 'move'
}
function onChainDragOver(i, evt) {
  evt.preventDefault()
  chainDragOver.value = i
}
function onChainDrop(i) {
  const from = chainDragIdx.value
  chainDragOver.value = null
  chainDragIdx.value  = null
  if (from === null || from === i) return
  const arr = [...form.fallback_chain]
  const [item] = arr.splice(from, 1)
  arr.splice(i, 0, item)
  form.fallback_chain.splice(0, form.fallback_chain.length, ...arr)
}
function onChainDragEnd() {
  chainDragIdx.value  = null
  chainDragOver.value = null
}

const modes = [
  { value: 'ollama', label: 'Ollama (本地)', desc: '全程数据不离本机' },
  { value: 'claude', label: 'Claude API',   desc: 'Anthropic — 需要 API Key' },
  { value: 'custom', label: '中转站 / 自定义', desc: 'OpenAI 兼容接口' },
]

// ── Provider connectivity test ────────────────────────────────────────────────
const testingId = ref(null)
const testResults = ref({})  // id → { ok, latency_ms, error }

async function testProvider(id) {
  testingId.value = id
  testResults.value = { ...testResults.value, [id]: null }
  try {
    const res = await fetch('/api/test-provider', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ backend: id }),
    }).then(r => r.json())
    testResults.value = { ...testResults.value, [id]: res }
  } catch (e) {
    testResults.value = { ...testResults.value, [id]: { ok: false, error: String(e) } }
  } finally {
    testingId.value = null
  }
}

function testResultLabel(id) {
  const r = testResults.value[id]
  if (!r) return '测试'
  if (r.ok) return `✓ ${r.latency_ms}ms`
  return '✗ 失败'
}

function testResultClass(id) {
  const r = testResults.value[id]
  if (!r) return ''
  return r.ok ? 'test-ok' : 'test-fail'
}

onMounted(async () => {
  const data = await fetch('/api/settings').then(r => r.json()).catch(() => null)
  if (data) Object.assign(form, data)
})

async function save() {
  saving.value = true
  saved.value = false
  await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...form }),
  })
  saving.value = false
  saved.value = true
  setTimeout(() => { saved.value = false }, 2000)
}
</script>

<style scoped>
.settings-wrap  { height: 100%; overflow-y: auto; padding: 28px 32px; }
.settings-panel { max-width: 520px; display: flex; flex-direction: column; gap: 18px; }
.panel-title    { font-size: 17px; font-weight: 700; }

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px 18px;
  display: flex; flex-direction: column; gap: 12px;
  transition: background 0.2s, border-color 0.2s;
}
.card-title { font-size: 13px; font-weight: 600; color: var(--muted); margin-bottom: 2px; }

/* Theme buttons */
.theme-group { display: flex; gap: 8px; }
.theme-btn {
  flex: 1; display: flex; flex-direction: column; align-items: center; gap: 5px;
  padding: 10px 8px; border-radius: 8px; border: 1px solid var(--border);
  cursor: pointer; font-size: 12px; color: var(--muted);
  transition: border-color 0.15s, background 0.15s, color 0.15s;
}
.theme-btn:hover { background: var(--surface2); color: var(--text); }
.theme-btn.active {
  border-color: var(--accent);
  background: var(--active-bg);
  color: var(--accent);
  font-weight: 600;
}
.theme-icon { font-size: 18px; }

/* LLM mode */
.mode-group  { display: flex; flex-direction: column; gap: 8px; }
.mode-option {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 10px 12px; border-radius: 8px; cursor: pointer;
  border: 1px solid var(--border);
  transition: border-color 0.15s, background 0.15s;
}
.mode-option:hover  { background: var(--surface2); }
.mode-option.active { border-color: var(--accent); background: var(--active-bg); }
.mode-radio {
  width: 14px; height: 14px; border-radius: 50%;
  border: 2px solid var(--border); margin-top: 2px; flex-shrink: 0;
  transition: border-color 0.15s, background 0.15s;
}
.mode-option.active .mode-radio { border-color: var(--accent); background: var(--accent); }
.mode-name { font-size: 13px; font-weight: 600; }
.mode-desc { font-size: 11px; color: var(--muted); margin-top: 2px; }

.field { display: flex; flex-direction: column; gap: 5px; }
.field label { font-size: 12px; color: var(--muted); }
.actions { display: flex; align-items: center; gap: 12px; }
.saved-msg { font-size: 12px; color: var(--entity); }

/* Toggle switch */
.toggle-row {
  display: flex; align-items: center; justify-content: space-between;
  cursor: pointer; user-select: none;
}
.toggle-label { font-size: 13px; }
.toggle-desc  { font-size: 11px; color: var(--muted); margin-top: 2px; }

/* Fallback chain */
.chain-desc { font-size: 12px; color: var(--muted); }
.chain-list { display: flex; flex-direction: column; gap: 6px; }
.chain-item {
  display: flex; align-items: center; gap: 8px;
  padding: 9px 12px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--bg);
  cursor: grab; user-select: none; transition: border-color 0.15s, background 0.15s;
}
.chain-item:active { cursor: grabbing; }
.chain-item.chain-primary { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 5%, transparent); }
.chain-item.chain-drag-over { border-color: var(--accent); border-style: dashed; }
.chain-handle { color: var(--muted); font-size: 14px; flex-shrink: 0; }
.chain-icon   { font-size: 14px; flex-shrink: 0; }
.chain-name   { font-size: 13px; font-weight: 500; flex: 1; }
.chain-badge  {
  font-size: 10px; padding: 1px 6px; border-radius: 4px;
  font-weight: 600; letter-spacing: 0.3px;
}
.badge-ok   { background: color-mix(in srgb, var(--entity) 14%, transparent); color: var(--entity); }
.badge-warn { background: color-mix(in srgb, var(--topic) 14%, transparent); color: var(--topic); }
.chain-primary-tag {
  font-size: 9px; font-weight: 700; letter-spacing: 0.5px;
  background: var(--accent); color: #fff; padding: 1px 5px; border-radius: 3px;
}
.chain-test-btn {
  font-size: 10px; padding: 2px 7px; border-radius: 4px; flex-shrink: 0;
  border: 1px solid var(--border); background: transparent; cursor: pointer;
  color: var(--muted); transition: border-color 0.15s, color 0.15s, background 0.15s;
  white-space: nowrap; min-width: 42px; text-align: center;
}
.chain-test-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.chain-test-btn.test-ok  { border-color: var(--entity); color: var(--entity); background: color-mix(in srgb, var(--entity) 8%, transparent); }
.chain-test-btn.test-fail { border-color: var(--topic); color: var(--topic); background: color-mix(in srgb, var(--topic) 8%, transparent); }
.chain-test-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.test-spinner {
  display: inline-block; width: 8px; height: 8px; border-radius: 50%;
  border: 1.5px solid var(--border); border-top-color: var(--accent);
  animation: spin 0.6s linear infinite; vertical-align: middle;
}
@keyframes spin { to { transform: rotate(360deg); } }

.chain-remove {
  background: none; border: none; cursor: pointer; color: var(--muted);
  font-size: 12px; padding: 2px 4px; border-radius: 4px; opacity: 0;
  transition: opacity 0.15s, color 0.15s; flex-shrink: 0;
}
.chain-item:hover .chain-remove { opacity: 1; }
.chain-remove:hover { color: var(--danger); }
.chain-remove:disabled { opacity: 0.2 !important; cursor: not-allowed; }

.chain-add-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.chain-add-label { font-size: 12px; color: var(--muted); }
.chain-add-btn {
  font-size: 11px; padding: 3px 10px; border-radius: 6px;
  border: 1px dashed var(--border); background: transparent; cursor: pointer;
  color: var(--muted); transition: border-color 0.15s, color 0.15s;
}
.chain-add-btn:hover { border-color: var(--accent); color: var(--accent); }
.toggle {
  width: 36px; height: 20px; border-radius: 10px; background: var(--border);
  position: relative; transition: background 0.2s; flex-shrink: 0;
}
.toggle.on { background: var(--accent); }
.toggle-thumb {
  position: absolute; top: 3px; left: 3px;
  width: 14px; height: 14px; border-radius: 50%; background: #fff;
  transition: transform 0.2s;
}
.toggle.on .toggle-thumb { transform: translateX(16px); }

/* Parallel routing */
.parallel-route { display: flex; flex-direction: column; gap: 8px; }
.route-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; border-radius: 8px; background: var(--surface2);
}
.route-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dot-small { background: var(--entity); }
.dot-large { background: var(--accent); }
.route-label { flex: 1; font-size: 12px; color: var(--muted); }
.route-select {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 6px; color: var(--text); font-size: 12px;
  padding: 4px 8px; outline: none; cursor: pointer;
}
.route-select:focus { border-color: var(--accent); }
</style>
