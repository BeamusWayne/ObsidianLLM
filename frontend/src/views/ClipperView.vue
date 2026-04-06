<template>
  <div class="clipper-wrap">
    <div class="panel">
      <h2 class="panel-title">Clip & Ingest</h2>

      <!-- Billing fallback info banner (silent switch already happened) -->
      <div v-if="status.billing_fallback && !status.billing_needs_confirm" class="billing-banner">
        <span>⚠️</span>
        <span>{{ status.billing_fallback_msg || 'LLM 余额不足，已切换到链中下一个后端继续处理' }}</span>
        <button class="banner-close" @click="dismissBilling">✕</button>
      </div>

      <!-- Billing exhausted — waiting for user confirmation -->
      <div v-if="status.billing_needs_confirm" class="billing-confirm-modal">
        <div class="billing-confirm-box">
          <div class="billing-confirm-icon">⚠️</div>
          <div class="billing-confirm-title">所有 API 后端余额已耗尽</div>
          <div class="billing-confirm-msg">{{ status.billing_confirm_msg || '链中所有 API 后端均余额不足，是否启用本地 Ollama 继续处理当前文件？' }}</div>
          <div class="billing-confirm-note">若选择「否」，当前文件将被跳过，队列中其余文件继续处理。</div>
          <div class="billing-confirm-actions">
            <button class="btn-confirm-yes" :disabled="confirmPending" @click="confirmOllama">
              <span v-if="confirmPending" class="btn-spinner"></span>
              {{ confirmPending ? '处理中…' : '是，启用本地 Ollama' }}
            </button>
            <button class="btn-confirm-no" :disabled="confirmPending" @click="rejectOllama">
              否，跳过此文件
            </button>
          </div>
        </div>
      </div>

      <!-- Clip URL -->
      <section class="card" :class="{ running: clipping }">
        <div class="card-header">
          <span class="card-title">Clip URL</span>
          <span v-if="clipping" class="stage-badge">
            <span class="spinner"></span> {{ clipStage }}
          </span>
        </div>
        <div class="progress-bar-wrap">
          <div v-if="clipping" class="progress-bar-indeterminate"></div>
        </div>
        <div class="row">
          <input v-model="url" placeholder="https://…" :disabled="clipping" @keyup.enter="doClip" />
          <button class="btn-primary" :disabled="clipping || !url.trim()" @click="doClip">
            <span v-if="clipping" class="btn-spinner"></span>
            {{ clipping ? 'Clipping…' : 'Clip' }}
          </button>
        </div>
        <div v-if="clipResult" class="result" :class="clipResult.error ? 'result-error' : 'result-ok'">
          <template v-if="clipResult.error">✗ {{ clipResult.error }}</template>
          <template v-else>
            ✓ 已保存 <strong>{{ clipResult.title }}</strong>
            ({{ clipResult.images_saved }} 张图)
            <span v-if="form.auto_ingest"> — 已加入处理队列</span>
            <span v-else> — 可在右侧选中后处理</span>
          </template>
        </div>
      </section>

      <!-- Model Selector -->
      <section class="card">
        <div class="card-header">
          <span class="card-title">处理模型</span>
          <span class="active-model-tag">{{ activeModelLabel }}</span>
        </div>

        <!-- Backend tabs -->
        <div class="backend-tabs">
          <button v-for="(b, i) in computedBackends" :key="b.id"
            class="backend-tab"
            :class="{
              active: activeTab === b.id,
              'preset-tab': b.isPreset,
              'drag-over': b.isPreset && presetDragOver === (i - STATIC_BACKENDS.length),
              'new-tab': b.id === '__new__',
            }"
            :draggable="b.isPreset"
            @click="switchBackend(b.id)"
            @dragstart="b.isPreset && onPresetDragStart(i - STATIC_BACKENDS.length, $event)"
            @dragover="b.isPreset && onPresetDragOver(i - STATIC_BACKENDS.length, $event)"
            @drop="b.isPreset && onPresetDrop(i - STATIC_BACKENDS.length)"
            @dragend="onPresetDragEnd">
            {{ b.label }}
          </button>
        </div>

        <!-- ── Ollama ── -->
        <div v-if="form.mode === 'ollama'" class="model-content">
          <div v-if="!ollamaAvailable" class="ollama-warn">
            ⚠ 无法连接 Ollama，请确认已启动：<code>ollama serve</code>
          </div>

          <div class="model-section-label">文字模型</div>
          <div class="model-grid">
            <div v-for="m in textModels" :key="m.name"
              class="model-item" :class="{ selected: form.ollama.text_model === m.name, installed: m.installed }"
              @click="m.installed ? selectModel('text', m.name) : null">
              <span class="mdot" :class="m.installed ? 'mdot-on' : 'mdot-off'"></span>
              <div class="minfo">
                <div class="mname">{{ m.name }}</div>
                <div class="mmeta">
                  <span v-if="m.installed">{{ m.size_str }}</span>
                  <span v-else class="mmeta-desc">{{ m.desc }}</span>
                </div>
              </div>
              <span v-if="form.ollama.text_model === m.name" class="mcheck">✓</span>
              <button v-else-if="!m.installed" class="pull-btn"
                :class="{ pulling: pullTarget === m.name }"
                :disabled="pulling"
                @click.stop="startPull(m.name)">
                <span v-if="pullTarget === m.name" class="spinner"></span>
                <span v-else>↓</span>
              </button>
            </div>
          </div>

          <div class="model-section-label">视觉模型</div>
          <div class="model-grid">
            <div v-for="m in visionModels" :key="m.name"
              class="model-item" :class="{ selected: form.ollama.vision_model === m.name, installed: m.installed }"
              @click="m.installed ? selectModel('vision', m.name) : null">
              <span class="mdot" :class="m.installed ? 'mdot-on' : 'mdot-off'"></span>
              <div class="minfo">
                <div class="mname">{{ m.name }}</div>
                <div class="mmeta">
                  <span v-if="m.installed">{{ m.size_str }}</span>
                  <span v-else class="mmeta-desc">{{ m.desc }}</span>
                </div>
              </div>
              <span v-if="form.ollama.vision_model === m.name" class="mcheck">✓</span>
              <button v-else-if="!m.installed" class="pull-btn"
                :class="{ pulling: pullTarget === m.name }"
                :disabled="pulling"
                @click.stop="startPull(m.name)">
                <span v-if="pullTarget === m.name" class="spinner"></span>
                <span v-else>↓</span>
              </button>
            </div>
          </div>

          <!-- Pull progress -->
          <div v-if="pulling" class="pull-progress">
            <div class="pull-header">
              <span class="spinner"></span>
              正在下载 <strong>{{ pullTarget }}</strong>
              <span class="pull-status-txt">{{ pullStatusText }}</span>
            </div>
            <div class="pull-track">
              <div class="pull-fill" :style="{ width: pullPct + '%' }"></div>
            </div>
            <div class="pull-pct">{{ pullPct }}%</div>
          </div>
        </div>

        <!-- ── Claude ── -->
        <div v-if="form.mode === 'claude'" class="model-content">
          <div class="model-grid">
            <div v-for="m in claudeModels" :key="m.id"
              class="model-item installed" :class="{ selected: form.claude.text_model === m.id }"
              @click="selectClaudeModel(m.id)">
              <span class="mdot mdot-cloud"></span>
              <div class="minfo">
                <div class="mname">{{ m.label }}</div>
                <div class="mmeta">
                  <span class="mmeta-desc">{{ m.desc }}</span>
                  <span class="mprice">{{ m.price }}</span>
                </div>
              </div>
              <span v-if="form.claude.text_model === m.id" class="mcheck">✓</span>
            </div>
          </div>
          <div class="api-key-row">
            <label>API Key</label>
            <input v-model="form.claude.api_key" type="password"
              placeholder="sk-ant-…" @change="saveSettings" />
          </div>
        </div>

        <!-- ── Active preset ── -->
        <div v-if="form.mode === 'custom' && activePresetName" class="model-content custom-fields">
          <div class="field">
            <label>Base URL</label>
            <input v-model="form.custom.base_url" placeholder="https://api.example.com/v1" @change="updatePreset" />
          </div>
          <div class="field">
            <label>API Key</label>
            <input v-model="form.custom.api_key" type="password" placeholder="sk-…" @change="updatePreset" />
          </div>
          <div class="field">
            <label>模型名称</label>
            <input v-model="form.custom.text_model" placeholder="gpt-4o" @change="updatePreset" />
          </div>
          <button class="btn-danger-ghost btn-sm" @click="deletePreset(activePresetName)">删除此预设</button>
        </div>

        <!-- ── New preset form ── -->
        <div v-if="form.mode === 'custom' && !activePresetName" class="model-content custom-fields">
          <div class="field">
            <label>Base URL</label>
            <input v-model="form.custom.base_url"
              placeholder="https://api.example.com/v1" @change="saveSettings" />
          </div>
          <div class="field">
            <label>API Key</label>
            <input v-model="form.custom.api_key" type="password"
              placeholder="sk-…" @change="saveSettings" />
          </div>
          <div class="field">
            <label>模型名称</label>
            <input v-model="form.custom.text_model"
              placeholder="gpt-4o" @change="saveSettings" />
          </div>
          <div class="preset-save-row">
            <input v-model="presetName" placeholder="预设名称（如：OpenAI GPT-4o）"
              @keyup.enter="savePreset" />
            <button class="btn-ghost btn-sm" :disabled="!presetName.trim() || !form.custom.base_url.trim()"
              @click="savePreset">保存为预设</button>
          </div>
        </div>
      </section>

      <!-- Background Ingest Status -->
      <section class="card" :class="{ running: status.running }">
        <div class="card-header">
          <span class="card-title">Background Ingest</span>
          <span class="ingest-model-hint">{{ currentIngestModels }}</span>
          <span class="status-badge" :class="statusClass">
            <span v-if="status.running" class="spinner"></span>
            <span v-else class="status-dot" :class="statusClass"></span>
            {{ statusLabel }}
          </span>
        </div>
        <div class="progress-bar-wrap">
          <div v-if="status.running" class="progress-bar-indeterminate"></div>
        </div>

        <template v-if="status.running">
          <div class="current-file">
            <code class="file-name">{{ status.current_file }}</code>
            <span class="elapsed-badge">{{ elapsedStr }}</span>
          </div>
          <div v-if="status.queued > 0" class="queue-hint muted">
            队列中还有 {{ status.queued }} 篇待处理
          </div>
        </template>

        <div v-if="llmThinking" class="llm-thinking">
          <span class="think-dots"><span></span><span></span><span></span></span>
          LLM 正在思考，请耐心等待…
        </div>

        <div v-if="status.log.length" class="log-box" ref="logBox">
          <div v-for="(line, i) in status.log" :key="i" class="log-line"
            :class="{
              'log-head':    line.startsWith('→'),
              'log-warn':    line.includes('WARNING') || line.startsWith('ERROR'),
              'log-current': status.running && i === status.log.length - 1,
            }">{{ line }}<span v-if="status.running && i === status.log.length - 1" class="cursor">▌</span>
          </div>
        </div>

        <div v-if="!status.running" class="idle-summary">
          <span v-if="status.last_error" class="error-hint">✗ {{ status.last_error }}</span>
          <span v-else-if="status.finished_at" class="muted">
            上次完成：{{ lastRunStr }} · 累计 {{ status.total_processed }} 篇
          </span>
          <span v-else class="muted">等待任务…</span>
        </div>

        <div class="card-footer">
          <span class="muted">Clip 后自动入队</span>
          <button class="btn-ghost btn-sm" @click="doIngest" :disabled="status.running">
            处理所有未处理文件
          </button>
        </div>
      </section>
    </div>

    <div class="resize-handle" :class="{ active: dragging }" @mousedown="start"></div>

    <!-- Raw files panel -->
    <div class="panel panel-right" :style="{ width: rightW + 'px', minWidth: rightW + 'px' }">

      <!-- Header -->
      <div class="raw-header">
        <div class="raw-title-row">
          <h2 class="panel-title">Raw Files</h2>
          <button class="btn-process-all" :disabled="status.running || pendingCount === 0"
            @click="doIngest" :title="pendingCount ? `处理全部 ${pendingCount} 个待处理文件` : '没有待处理文件'">
            <span v-if="status.running" class="btn-spinner"></span>
            <span v-else>▶</span>
            处理全部{{ pendingCount ? ` (${pendingCount})` : '' }}
          </button>
        </div>
        <div class="raw-header-row">
          <select class="sort-select" v-model="sortOrder">
            <option value="newest">最新在前</option>
            <option value="oldest">最旧在前</option>
            <option value="name">文件名</option>
          </select>
          <label class="auto-toggle" :class="{ on: form.auto_ingest }" title="Clip 后自动入队处理">
            <input type="checkbox" v-model="form.auto_ingest" @change="saveAutoIngest" />
            <span class="at-track"><span class="at-thumb"></span></span>
            <span class="at-label">自动</span>
          </label>
        </div>
      </div>

      <!-- Action bar -->
      <div v-if="selectedCount > 0" class="action-bar">
        <span class="sel-count">{{ selectedCount }} 已选</span>
        <button v-if="selStats.canProcess > 0"  class="act-btn act-process"  @click="ingestSelected">处理 {{ selStats.canProcess }}</button>
        <button v-if="selStats.canIgnore > 0"   class="act-btn act-ignore"   @click="ignoreSelected">忽略 {{ selStats.canIgnore }}</button>
        <button v-if="selStats.canUnignore > 0" class="act-btn act-unignore" @click="unignoreSelected">恢复 {{ selStats.canUnignore }}</button>
        <button class="act-clear" @click="clearSelection">✕</button>
      </div>

      <!-- Select-all + counts row -->
      <div class="select-all-row">
        <label class="cb-wrap">
          <input type="checkbox" :checked="allSelected" :indeterminate.prop="someSelected" @change="toggleSelectAll" />
          <span class="cb-box"></span>
        </label>
        <span class="select-all-label">全选</span>
        <span class="file-counts">
          <span class="cnt cnt-pending">{{ pendingCount }} 待处理</span>
          <span class="cnt cnt-done">{{ processedCount }} 已处理</span>
          <span v-if="ignoredCount" class="cnt cnt-ignored">{{ ignoredCount }} 已忽略</span>
        </span>
      </div>

      <div class="raw-body">
        <div v-if="!rawFiles.length" class="raw-empty">
          <div class="raw-empty-icon"></div>
          <div class="raw-empty-text">还没有文件</div>
          <div class="raw-empty-hint">先 Clip 一篇文章吧</div>
        </div>

        <!-- Articles -->
        <div v-if="sortedArticles.length" class="raw-section">
          <div class="section-hdr">
            <label class="cb-wrap" @click.stop>
              <input type="checkbox" :checked="sectionAllSelected('article')" @change="toggleSectionSelect('article')" />
              <span class="cb-box"></span>
            </label>
            <span class="section-title">文章</span>
            <span class="section-count">{{ sortedArticles.length }}</span>
          </div>

          <div v-for="f in sortedArticles" :key="f.path" class="raw-item-wrap">
            <div class="raw-item" :class="[fileStatus(f), { 'is-selected': isSelected(f.path) }]" :title="f.path">
              <label class="cb-wrap" @click.stop>
                <input type="checkbox" :checked="isSelected(f.path)" @change="toggleSelect(f.path)" />
                <span class="cb-box"></span>
              </label>
              <div class="file-icon file-icon-doc">
                <span v-if="f.active" class="spinner spinner-sm"></span>
                <span v-else class="file-ext-label">MD</span>
              </div>
              <div class="file-info">
                <span class="file-name">{{ displayName(f.name) }}</span>
                <button v-if="f.images && f.images.length" class="img-ref-chip"
                  @click.stop="toggleExpand(f.path)">
                  <span class="img-ref-count">{{ f.images.length }}</span>
                  <span class="img-ref-caret">{{ expandedArticles.has(f.path) ? '▴' : '▾' }}</span>
                </button>
              </div>
              <span class="status-dot" :class="`dot-${fileStatus(f)}`" :title="fileStatusLabel(f)"></span>
              <button v-if="!f.active" class="run-btn" :class="{ 'run-btn-redo': f.processed }"
                @click.stop="ingestSingle(f)" :title="f.processed ? '重新处理' : '处理'">
                <svg width="9" height="10" viewBox="0 0 9 10" fill="none">
                  <path d="M1.5 1.5L7.5 5L1.5 8.5V1.5Z" fill="currentColor"/>
                </svg>
              </button>
            </div>
            <div v-if="expandedArticles.has(f.path) && f.images && f.images.length" class="sub-images">
              <div v-for="imgPath in f.images" :key="imgPath" class="sub-img-item">
                <div class="sub-thumb-wrap">
                  <img v-if="getFile(imgPath)" :src="rawUrl(imgPath)" class="sub-thumb" loading="lazy" />
                  <span v-else class="sub-thumb sub-thumb-missing">?</span>
                </div>
                <span class="sub-name">{{ imgPath.split('/').pop() }}</span>
                <span v-if="getFile(imgPath)" class="status-dot" :class="`dot-${fileStatus(getFile(imgPath))}`" :title="fileStatusLabel(getFile(imgPath))"></span>
              </div>
            </div>
          </div>
        </div>

        <!-- Images -->
        <div v-if="sortedImages.length" class="raw-section">
          <div class="section-hdr">
            <label class="cb-wrap" @click.stop>
              <input type="checkbox" :checked="sectionAllSelected('image')" @change="toggleSectionSelect('image')" />
              <span class="cb-box"></span>
            </label>
            <span class="section-title">图片</span>
            <span class="section-count">{{ sortedImages.length }}</span>
          </div>
          <div v-for="f in sortedImages" :key="f.path"
            class="raw-item" :class="[fileStatus(f), { 'is-selected': isSelected(f.path) }]" :title="f.path">
            <label class="cb-wrap" @click.stop>
              <input type="checkbox" :checked="isSelected(f.path)" @change="toggleSelect(f.path)" />
              <span class="cb-box"></span>
            </label>
            <div class="img-thumb-wrap">
              <span v-if="f.active" class="spinner spinner-sm"></span>
              <img v-else :src="rawUrl(f.path)" class="img-thumb" loading="lazy" />
            </div>
            <div class="file-info">
              <span class="file-name">{{ f.name }}</span>
            </div>
            <span class="status-dot" :class="`dot-${fileStatus(f)}`" :title="fileStatusLabel(f)"></span>
            <button v-if="!f.active" class="run-btn" :class="{ 'run-btn-redo': f.processed }"
              @click.stop="ingestSingle(f)" :title="f.processed ? '重新处理' : '处理'">
              <svg width="9" height="10" viewBox="0 0 9 10" fill="none">
                <path d="M1.5 1.5L7.5 5L1.5 8.5V1.5Z" fill="currentColor"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Confirm dialog -->
    <div v-if="confirmDialog" class="dialog-overlay" @click.self="confirmDialog.reject()">
      <div class="dialog-box">
        <div class="dialog-msg">{{ confirmDialog.message }}</div>
        <div class="dialog-btns">
          <button class="btn-ghost" @click="confirmDialog.reject()">取消</button>
          <button class="btn-primary" @click="confirmDialog.resolve()">确定重新处理</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useResizer } from '../composables/useResizer.js'

const { size: rightW, dragging, start } = useResizer(320, { min: 260, max: 560, inverted: true })

// ── Constants ──────────────────────────────────────────────────────────────────
const TEXT_CATALOG = [
  { name: 'qwen3.5:9b',      desc: '中英双语，ingest 主力' },
  { name: 'qwen3:8b',        desc: '均衡选择' },
  { name: 'qwen3:4b',        desc: '轻量快速' },
  { name: 'deepseek-r1:7b',  desc: '推理增强' },
  { name: 'llama3.2:3b',     desc: '超轻量，英文好' },
  { name: 'gemma3:4b',       desc: 'Google 出品' },
  { name: 'mistral:7b',      desc: '欧洲开源，多语言' },
]
const VISION_CATALOG = [
  { name: 'qwen3-vl:8b',       desc: '中英双语视觉' },
  { name: 'llava:7b',          desc: '通用视觉理解' },
  { name: 'llava-phi3:latest', desc: '轻量视觉' },
  { name: 'moondream:latest',  desc: '超轻量视觉' },
  { name: 'minicpm-v:8b',      desc: '移动端视觉' },
]
const CLAUDE_MODELS = [
  { id: 'claude-haiku-4-5-20251001', label: 'Haiku 4.5',  desc: '最快 · 最省钱', price: '$0.8/MTok' },
  { id: 'claude-sonnet-4-6',         label: 'Sonnet 4.6', desc: '均衡 · 推荐',   price: '$3/MTok'   },
  { id: 'claude-opus-4-6',           label: 'Opus 4.6',   desc: '最强 · 最贵',   price: '$15/MTok'  },
]
const STATIC_BACKENDS = [
  { id: 'ollama', label: '🖥 Ollama' },
  { id: 'claude', label: '☁️ Claude' },
]

function isVision(name) {
  return /vl|vision|llava|moondream|minicpm-v|bakllava/i.test(name)
}

// ── Settings form ──────────────────────────────────────────────────────────────
const form = reactive({
  mode: 'ollama',
  auto_ingest: true,
  fallback_chain: ['claude', 'ollama'],
  ollama: { base_url: 'http://localhost:11434', text_model: 'qwen3.5:9b', vision_model: 'qwen3-vl:8b' },
  claude: { api_key: '', text_model: 'claude-haiku-4-5-20251001' },
  custom: { base_url: '', api_key: '', text_model: '' },
  custom_presets: [],
})

// Track which preset is active (by name)
const activePresetName = ref(null)

// Dynamic tabs: static + presets + new
const computedBackends = computed(() => [
  ...STATIC_BACKENDS,
  ...form.custom_presets.map(p => ({ id: `preset:${p.name}`, label: p.name, isPreset: true })),
  { id: '__new__', label: '＋ 新建' },
])

const activeTab = computed(() => {
  if (form.mode === 'ollama') return 'ollama'
  if (form.mode === 'claude') return 'claude'
  if (form.mode === 'custom') return activePresetName.value ? `preset:${activePresetName.value}` : '__new__'
  return 'ollama'
})

// ── Ollama installed models ────────────────────────────────────────────────────
const installedModels = ref([])
const ollamaAvailable = ref(true)

async function fetchInstalledModels() {
  const data = await fetch('/api/models').then(r => r.json()).catch(() => null)
  if (!data) return
  ollamaAvailable.value = data.available
  installedModels.value = data.installed || []
}

// Merge catalog with installed: installed models first, then catalog entries not yet installed
function mergeModels(catalog) {
  const installedNames = new Set(installedModels.value.map(m => m.name))
  const catalogNames   = new Set(catalog.map(m => m.name))

  // Installed models that match catalog or are of right type
  const installed = installedModels.value
    .filter(m => catalogNames.has(m.name))
    .map(m => ({ ...m, installed: true, desc: catalog.find(c => c.name === m.name)?.desc || '' }))

  // Installed models NOT in catalog but matching type (user pulled something custom)
  const installedExtra = installedModels.value
    .filter(m => !catalogNames.has(m.name))
    .map(m => ({ ...m, installed: true, desc: '' }))

  // Catalog entries not installed
  const available = catalog
    .filter(m => !installedNames.has(m.name))
    .map(m => ({ name: m.name, installed: false, size: 0, size_str: '', desc: m.desc }))

  return [...installed, ...installedExtra, ...available]
}

const textModels  = computed(() => mergeModels(TEXT_CATALOG.filter(m => !isVision(m.name))))
const visionModels = computed(() => {
  const installedVision = installedModels.value
    .filter(m => isVision(m.name) && !VISION_CATALOG.some(c => c.name === m.name))
    .map(m => ({ ...m, installed: true, desc: '' }))
  const catalog = mergeModels(VISION_CATALOG)
  return [...catalog.filter(m => m.installed && !installedVision.find(x => x.name === m.name)),
          ...installedVision,
          ...catalog.filter(m => !m.installed)]
})

// ── Raw files — selection / sort / expand ──────────────────────────────────────
const sortOrder         = ref('newest')
const selected          = reactive(new Set())
const expandedArticles  = reactive(new Set())
const confirmDialog     = ref(null)  // { message, resolve, reject }

const fileMap = computed(() => {
  const m = {}
  for (const f of rawFiles.value) m[f.path] = f
  return m
})
function getFile(path) { return fileMap.value[path] }

function rawUrl(path) {
  // path like "raw/images/Image 6.jpg" → "/raw-files/images/Image%206.jpg"
  const rel = path.replace(/^raw\//, '')
  return '/raw-files/' + rel.split('/').map(encodeURIComponent).join('/')
}

function fileStatus(f) {
  if (!f) return 'pending'
  if (f.active)    return 'active'
  if (f.ignored)   return 'ignored'
  if (f.processed) return 'processed'
  return 'pending'
}

function fileStatusLabel(f) {
  if (!f) return '待处理'
  if (f.active)    return '处理中'
  if (f.ignored)   return '已忽略'
  if (f.processed) return '已处理'
  return '待处理'
}

function displayName(name) {
  return name.replace(/\.md$/i, '')
}

function sortFiles(files) {
  return [...files].sort((a, b) => {
    if (sortOrder.value === 'newest') return b.mtime - a.mtime
    if (sortOrder.value === 'oldest') return a.mtime - b.mtime
    return a.name.localeCompare(b.name)
  })
}

const articles     = computed(() => rawFiles.value.filter(f => f.type === 'article'))
const images       = computed(() => rawFiles.value.filter(f => f.type === 'image'))
const sortedArticles = computed(() => sortFiles(articles.value))
const sortedImages   = computed(() => sortFiles(images.value))

const pendingCount   = computed(() => rawFiles.value.filter(f => !f.processed && !f.ignored && !f.active).length)
const processedCount = computed(() => rawFiles.value.filter(f => f.processed).length)
const ignoredCount   = computed(() => rawFiles.value.filter(f => f.ignored).length)
const selectedCount  = computed(() => selected.size)

const allSelected  = computed(() => rawFiles.value.length > 0 && rawFiles.value.every(f => selected.has(f.path)))
const someSelected = computed(() => selected.size > 0 && !allSelected.value)

const selStats = computed(() => {
  const files = rawFiles.value.filter(f => selected.has(f.path))
  return {
    canProcess:  files.filter(f => !f.active).length,
    canIgnore:   files.filter(f => !f.ignored).length,
    canUnignore: files.filter(f => f.ignored).length,
    alreadyProcessed: files.filter(f => f.processed && !f.ignored).length,
  }
})

function isSelected(path) { return selected.has(path) }

function toggleSelect(path) {
  if (selected.has(path)) selected.delete(path)
  else selected.add(path)
}

function toggleSelectAll() {
  if (allSelected.value) {
    selected.clear()
  } else {
    rawFiles.value.forEach(f => selected.add(f.path))
  }
}

function sectionAllSelected(type) {
  const files = rawFiles.value.filter(f => f.type === type)
  return files.length > 0 && files.every(f => selected.has(f.path))
}

function toggleSectionSelect(type) {
  const files = rawFiles.value.filter(f => f.type === type)
  if (sectionAllSelected(type)) files.forEach(f => selected.delete(f.path))
  else files.forEach(f => selected.add(f.path))
}

function clearSelection() { selected.clear() }

function toggleExpand(path) {
  if (expandedArticles.has(path)) expandedArticles.delete(path)
  else expandedArticles.add(path)
}

function showConfirm(message) {
  return new Promise((resolve, reject) => {
    confirmDialog.value = {
      message,
      resolve: () => { confirmDialog.value = null; resolve(true) },
      reject:  () => { confirmDialog.value = null; reject(false) },
    }
  })
}

async function ingestSingle(f) {
  if (f.active) return
  if (f.processed) {
    try { await showConfirm(`"${f.name}" 已处理过，确定重新处理？`) }
    catch { return }
  }
  if (f.ignored) {
    await fetch('/api/raw/unignore', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paths: [f.path] }),
    })
  }
  await fetch('/api/ingest', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ files: [f.path] }),
  })
  await loadRaw()
  setTimeout(fetchStatus, 300)
}

async function ingestSelected() {
  const paths = [...selected].filter(p => {
    const f = fileMap.value[p]
    return f && !f.active
  })
  if (!paths.length) return

  // Warn if any already-processed files included
  if (selStats.value.alreadyProcessed > 0) {
    try {
      await showConfirm(`${selStats.value.alreadyProcessed} 个文件已处理过，确定重新处理？`)
    } catch { return }
  }

  // Unignore any ignored files in selection first
  const toUnignore = paths.filter(p => fileMap.value[p]?.ignored)
  if (toUnignore.length) {
    await fetch('/api/raw/unignore', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paths: toUnignore }),
    })
  }

  await fetch('/api/ingest', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ files: paths }),
  })
  clearSelection()
  await loadRaw()
  setTimeout(fetchStatus, 300)
}

async function ignoreSelected() {
  const paths = [...selected].filter(p => !fileMap.value[p]?.ignored)
  if (!paths.length) return
  await fetch('/api/raw/ignore', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paths }),
  })
  clearSelection()
  await loadRaw()
}

async function unignoreSelected() {
  const paths = [...selected].filter(p => fileMap.value[p]?.ignored)
  if (!paths.length) return
  await fetch('/api/raw/unignore', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paths }),
  })
  clearSelection()
  await loadRaw()
}

async function saveAutoIngest() {
  await saveSettings()
  if (form.auto_ingest) await doIngest()
}

// ── Pull state ─────────────────────────────────────────────────────────────────
const pulling         = ref(false)
const pullTarget      = ref('')
const pullStatusText  = ref('')
const pullPct         = ref(0)

async function startPull(name) {
  if (pulling.value) return
  pulling.value    = true
  pullTarget.value = name
  pullPct.value    = 0
  pullStatusText.value = '连接中…'

  const res = await fetch('/api/models/pull', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  const reader  = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const parts = buf.split('\n\n')
    buf = parts.pop()
    for (const part of parts) {
      const line = part.replace(/^data: /, '').trim()
      if (!line) continue
      try {
        const ev = JSON.parse(line)
        if (ev.status === 'done') break
        if (ev.error) { pullStatusText.value = ev.error; break }
        pullStatusText.value = ev.status || ''
        if (ev.total > 0) {
          pullPct.value = Math.round((ev.completed / ev.total) * 100)
        }
      } catch {}
    }
  }

  pulling.value = false
  pullPct.value = 100
  await fetchInstalledModels()
  // Auto-select the newly pulled model
  if (isVision(name)) {
    form.ollama.vision_model = name
  } else {
    form.ollama.text_model = name
  }
  await saveSettings()
}

// ── Model selection ────────────────────────────────────────────────────────────
const claudeModels = CLAUDE_MODELS

const activeModelLabel = computed(() => {
  if (form.mode === 'ollama') return form.ollama.text_model
  if (form.mode === 'claude') {
    const m = CLAUDE_MODELS.find(m => m.id === form.claude.text_model)
    return m ? m.label : form.claude.text_model
  }
  if (activePresetName.value) return activePresetName.value
  return form.custom.text_model || '自定义'
})

const currentIngestModels = computed(() => {
  const chain = form.fallback_chain || [form.mode || 'ollama']
  return chain.map(b => {
    if (b === 'ollama') return 'Ollama'
    if (b === 'claude') return 'Claude'
    return activePresetName.value || form.custom.text_model || '自定义'
  }).join(' → ')
})

async function switchBackend(id) {
  if (id === 'ollama') {
    form.mode = 'ollama'; activePresetName.value = null
    await saveSettings(); fetchInstalledModels()
  } else if (id === 'claude') {
    form.mode = 'claude'; activePresetName.value = null
    await saveSettings()
  } else if (id === '__new__') {
    form.mode = 'custom'; activePresetName.value = null
    await saveSettings()
  } else if (id.startsWith('preset:')) {
    const name = id.slice(7)
    const p = form.custom_presets.find(x => x.name === name)
    if (p) {
      form.custom.base_url   = p.base_url
      form.custom.api_key    = p.api_key
      form.custom.text_model = p.text_model
      form.mode = 'custom'; activePresetName.value = name
      await saveSettings()
    }
  }
}

async function selectModel(type, name) {
  if (type === 'text')   form.ollama.text_model   = name
  if (type === 'vision') form.ollama.vision_model = name
  await saveSettings()
}

async function selectClaudeModel(id) {
  form.claude.text_model = id
  await saveSettings()
}

// ── Custom presets ─────────────────────────────────────────────────────────────
const presetName = ref('')

async function savePreset() {
  const name = presetName.value.trim()
  if (!name) return
  const idx = form.custom_presets.findIndex(p => p.name === name)
  const entry = {
    name,
    base_url:   form.custom.base_url,
    api_key:    form.custom.api_key,
    text_model: form.custom.text_model,
  }
  if (idx >= 0) form.custom_presets[idx] = entry
  else form.custom_presets.push(entry)
  activePresetName.value = name
  presetName.value = ''
  await saveSettings()
}

async function updatePreset() {
  const name = activePresetName.value
  if (!name) return
  const idx = form.custom_presets.findIndex(p => p.name === name)
  if (idx < 0) return
  form.custom_presets[idx] = {
    name,
    base_url:   form.custom.base_url,
    api_key:    form.custom.api_key,
    text_model: form.custom.text_model,
  }
  await saveSettings()
}

async function deletePreset(name) {
  const idx = form.custom_presets.findIndex(p => p.name === name)
  if (idx < 0) return
  form.custom_presets.splice(idx, 1)
  if (activePresetName.value === name) {
    activePresetName.value = null
    form.mode = form.custom_presets.length ? 'custom' : 'ollama'
    if (form.mode === 'ollama') { form.custom.base_url = ''; form.custom.text_model = '' }
  }
  await saveSettings()
}

// ── Preset tab drag-to-reorder ─────────────────────────────────────────────────
const presetDragIdx = ref(null)
const presetDragOver = ref(null)

function onPresetDragStart(i, evt) {
  presetDragIdx.value = i
  evt.dataTransfer.effectAllowed = 'move'
}
function onPresetDragOver(i, evt) {
  evt.preventDefault()
  presetDragOver.value = i
}
function onPresetDrop(i) {
  const from = presetDragIdx.value
  presetDragOver.value = null
  presetDragIdx.value = null
  if (from === null || from === i) return
  const arr = [...form.custom_presets]
  const [item] = arr.splice(from, 1)
  arr.splice(i, 0, item)
  form.custom_presets.splice(0, form.custom_presets.length, ...arr)
  saveSettings()
}
function onPresetDragEnd() {
  presetDragIdx.value = null
  presetDragOver.value = null
}

async function saveSettings() {
  await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...form }),
  })
}

// ── Clip state ─────────────────────────────────────────────────────────────────
const url        = ref('')
const clipping   = ref(false)
const clipResult = ref(null)
const clipStage  = ref('')
let   clipTimer  = null

const clipStages = ['Fetching page…', 'Extracting content…', 'Downloading images…']

async function doClip() {
  if (!url.value.trim()) return
  clipping.value   = true
  clipResult.value = null
  let stageIdx = 0
  clipStage.value = clipStages[0]
  clipTimer = setInterval(() => {
    stageIdx = Math.min(stageIdx + 1, clipStages.length - 1)
    clipStage.value = clipStages[stageIdx]
  }, 3500)
  try {
    const res  = await fetch('/api/clip', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url.value.trim() }),
    })
    const data = await res.json()
    clipResult.value = res.ok ? data : { error: data.detail || 'Error' }
    if (res.ok) { url.value = ''; loadRaw(); setTimeout(fetchStatus, 500) }
  } catch (e) {
    clipResult.value = { error: e.message }
  } finally {
    clearInterval(clipTimer)
    clipping.value = false
  }
}

// ── Ingest status polling ──────────────────────────────────────────────────────
const status = ref({
  running: false, current_file: null, queued: 0,
  log: [], started_at: null, finished_at: null,
  total_processed: 0, last_error: null,
  billing_fallback: false, billing_fallback_msg: '',
  billing_needs_confirm: false, billing_confirm_msg: '',
})
const confirmPending = ref(false)
const logBox  = ref(null)
const rawFiles = ref([])
const now      = ref(Date.now())
let pollTimer  = null
let nowTimer   = null

async function fetchStatus() {
  const s = await fetch('/api/ingest/status').then(r => r.json()).catch(() => null)
  if (s) {
    const wasRunning = status.value.running
    status.value = s
    if (wasRunning && !s.running) loadRaw()
  }
}

async function loadRaw() {
  rawFiles.value = await fetch('/api/raw').then(r => r.json()).catch(() => [])
}

watch(() => status.value.log.length, async () => {
  await nextTick()
  logBox.value?.scrollTo({ top: logBox.value.scrollHeight, behavior: 'smooth' })
})

const statusClass = computed(() => {
  if (status.value.running)    return 'badge-running'
  if (status.value.last_error) return 'badge-error'
  return 'badge-idle'
})
const statusLabel = computed(() => {
  if (status.value.running)      return '运行中'
  if (status.value.last_error)   return '出错'
  if (status.value.queued > 0)   return `队列中 ${status.value.queued}`
  return '空闲'
})
const elapsedStr = computed(() => {
  if (!status.value.running || !status.value.started_at) return ''
  const s = Math.floor((now.value - new Date(status.value.started_at)) / 1000)
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`
})
const lastRunStr = computed(() => {
  if (!status.value.finished_at) return ''
  return new Date(status.value.finished_at)
    .toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
})
const llmThinking = computed(() => {
  if (!status.value.running) return false
  return (status.value.log[status.value.log.length - 1] || '').includes('calling LLM')
})

async function doIngest() {
  await fetch('/api/ingest', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ files: [] }),
  })
  setTimeout(fetchStatus, 300)
}

async function dismissBilling() {
  await fetch('/api/ingest/dismiss-billing', { method: 'POST' }).catch(() => {})
  status.value = { ...status.value, billing_fallback: false, billing_fallback_msg: '' }
}

async function confirmOllama() {
  confirmPending.value = true
  await fetch('/api/ingest/confirm-ollama', { method: 'POST' }).catch(() => {})
  status.value = { ...status.value, billing_needs_confirm: false, billing_confirm_msg: '' }
  confirmPending.value = false
}

async function rejectOllama() {
  confirmPending.value = true
  await fetch('/api/ingest/reject-ollama', { method: 'POST' }).catch(() => {})
  status.value = { ...status.value, billing_needs_confirm: false, billing_confirm_msg: '' }
  confirmPending.value = false
}

// ── Lifecycle ──────────────────────────────────────────────────────────────────
onMounted(async () => {
  const data = await fetch('/api/settings').then(r => r.json()).catch(() => null)
  if (data) {
    Object.assign(form, data)
    // Restore activePresetName: find preset whose values match current custom config
    if (form.mode === 'custom' && form.custom_presets?.length) {
      const match = form.custom_presets.find(p =>
        p.base_url === form.custom.base_url && p.text_model === form.custom.text_model)
      if (match) activePresetName.value = match.name
    }
  }
  loadRaw()
  fetchInstalledModels()
  fetchStatus()
  pollTimer = setInterval(fetchStatus, 3000)
  nowTimer  = setInterval(() => { now.value = Date.now() }, 1000)
})

onUnmounted(() => {
  clearInterval(pollTimer)
  clearInterval(nowTimer)
  clearInterval(clipTimer)
})
</script>

<style scoped>
/* ── Layout ──────────────────────────────────────────────────────────────────── */
.clipper-wrap { display: flex; height: 100%; overflow: hidden; }
.panel {
  flex: 1; padding: clamp(16px, 2.5vw, 28px);
  overflow-y: auto; display: flex; flex-direction: column; gap: 18px; min-width: 0;
}
.panel-right {
  display: flex; flex-direction: column; overflow: hidden;
  flex-shrink: 0; background: var(--surface);
}
.panel-title { font-size: clamp(14px, 1.3vw + 8px, 18px); font-weight: 700; margin-bottom: 4px; }
.resize-handle {
  width: 4px; flex-shrink: 0; cursor: col-resize;
  background: var(--border); transition: background 0.15s;
}
.resize-handle:hover, .resize-handle.active { background: var(--accent); opacity: 0.6; }

/* ── Billing banner ──────────────────────────────────────────────────────────── */
.billing-banner {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding: 10px 14px; border-radius: 8px;
  background: color-mix(in srgb, var(--topic) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--topic) 30%, transparent);
  font-size: 13px; animation: fade-in 0.3s ease;
}
.billing-banner span:nth-child(2) { flex: 1; }
.banner-close { background: none; border: none; cursor: pointer; color: var(--muted); }

/* ── Billing confirm modal ───────────────────────────────────────────────────── */
.billing-confirm-modal {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.45);
  display: flex; align-items: center; justify-content: center;
  animation: fade-in 0.2s ease;
}
.billing-confirm-box {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 14px; padding: 28px 28px 22px;
  max-width: 400px; width: 90%; display: flex; flex-direction: column; gap: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.25);
}
.billing-confirm-icon  { font-size: 28px; text-align: center; }
.billing-confirm-title { font-size: 15px; font-weight: 700; text-align: center; }
.billing-confirm-msg   { font-size: 13px; color: var(--text); line-height: 1.5; }
.billing-confirm-note  { font-size: 11px; color: var(--muted); line-height: 1.4; }
.billing-confirm-actions {
  display: flex; flex-direction: column; gap: 8px; margin-top: 4px;
}
.btn-confirm-yes {
  padding: 10px; border-radius: 8px; font-size: 13px; font-weight: 600;
  background: var(--accent); color: #fff; border: none; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 6px;
  transition: opacity 0.15s;
}
.btn-confirm-yes:hover:not(:disabled) { opacity: 0.88; }
.btn-confirm-yes:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-confirm-no {
  padding: 10px; border-radius: 8px; font-size: 13px;
  background: var(--surface2); color: var(--text);
  border: 1px solid var(--border); cursor: pointer; transition: background 0.15s;
}
.btn-confirm-no:hover:not(:disabled) { background: var(--active-bg); }
.btn-confirm-no:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── Card ────────────────────────────────────────────────────────────────────── */
.card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; padding: 0;
  display: flex; flex-direction: column; gap: 0;
  overflow: hidden; transition: border-color 0.2s, box-shadow 0.2s;
}
.card.running {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 12%, transparent);
}
.card-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px 0;
}
.card-title { font-size: 13px; font-weight: 600; color: var(--muted); }
.card > .row,
.card > .result,
.card > .log-box,
.card > .llm-thinking,
.card > .current-file,
.card > .queue-hint,
.card > .idle-summary,
.card > .card-footer { padding: 0 18px; }
.card > .row        { padding-top: 12px; }
.card > .current-file { padding-top: 12px; }
.card > .card-footer  { padding-top: 10px; padding-bottom: 16px; }
.card > *:last-child  { padding-bottom: 16px; }

/* ── Progress bar ────────────────────────────────────────────────────────────── */
.progress-bar-wrap { height: 3px; background: transparent; margin: 8px 0 0; overflow: hidden; }
.progress-bar-indeterminate {
  height: 100%; width: 35%; background: var(--accent); border-radius: 2px;
  animation: slide 1.6s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

/* ── Clip stage badge ────────────────────────────────────────────────────────── */
.stage-badge {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: var(--accent); animation: fade-in 0.3s ease;
}

/* ── Spinners ────────────────────────────────────────────────────────────────── */
.spinner, .btn-spinner {
  display: inline-block; width: 12px; height: 12px;
  border: 2px solid color-mix(in srgb, var(--accent) 30%, transparent);
  border-top-color: var(--accent); border-radius: 50%;
  animation: spin 0.75s linear infinite; vertical-align: middle; flex-shrink: 0;
}
.btn-spinner { margin-right: 5px; width: 11px; height: 11px; border-width: 1.5px; }

/* ── Model selector card ─────────────────────────────────────────────────────── */
.active-model-tag {
  font-size: 11px; color: var(--accent);
  background: color-mix(in srgb, var(--accent) 10%, transparent);
  border-radius: 10px; padding: 2px 8px; max-width: 180px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* Backend tabs */
.backend-tabs {
  display: flex; gap: 6px; padding: 12px 18px 0; flex-wrap: wrap;
}
.backend-tab {
  padding: 5px 12px; border-radius: 6px; border: 1px solid var(--border);
  font-size: 12px; background: transparent; color: var(--muted); cursor: pointer;
  transition: all 0.15s; white-space: nowrap; user-select: none;
}
.backend-tab:hover  { background: var(--surface2); color: var(--text); }
.backend-tab.active { background: var(--active-bg); border-color: var(--accent); color: var(--accent); font-weight: 600; }
.backend-tab.preset-tab { cursor: grab; }
.backend-tab.preset-tab:active { cursor: grabbing; }
.backend-tab.drag-over { border-color: var(--accent); border-style: dashed; }
.backend-tab.new-tab { color: var(--muted); font-style: normal; }
.backend-tab.new-tab:hover { color: var(--accent); border-color: var(--accent); }

/* Model content area */
.model-content { padding: 12px 18px 16px; display: flex; flex-direction: column; gap: 8px; }

.model-section-label {
  font-size: 10px; font-weight: 700; letter-spacing: 0.8px;
  text-transform: uppercase; color: var(--muted); margin-top: 4px;
}

/* Model grid */
.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 6px;
}

.model-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--surface2);
  cursor: default; transition: border-color 0.15s, background 0.15s;
  min-width: 0;
}
.model-item.installed { cursor: pointer; }
.model-item.installed:hover { background: var(--active-bg); border-color: var(--accent); }
.model-item.selected  { background: var(--active-bg); border-color: var(--accent); }

.mdot {
  width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
}
.mdot-on    { background: var(--entity); }
.mdot-off   { background: var(--border); }
.mdot-cloud { background: var(--accent); }

.minfo  { flex: 1; min-width: 0; }
.mname  { font-size: 12px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mmeta  { font-size: 10px; color: var(--muted); margin-top: 1px; display: flex; gap: 5px; align-items: center; }
.mmeta-desc { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mprice { color: var(--topic); font-size: 10px; flex-shrink: 0; }

.mcheck { font-size: 11px; color: var(--accent); flex-shrink: 0; font-weight: 700; }

.pull-btn {
  width: 22px; height: 22px; border-radius: 4px; flex-shrink: 0;
  border: 1px solid var(--border); background: var(--surface);
  font-size: 11px; cursor: pointer; display: flex; align-items: center; justify-content: center;
  color: var(--accent); padding: 0; transition: background 0.15s;
}
.pull-btn:hover    { background: var(--active-bg); }
.pull-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.pull-btn.pulling  { background: var(--active-bg); }

/* Pull progress */
.pull-progress {
  background: var(--surface2); border-radius: 8px; padding: 10px 12px;
  display: flex; flex-direction: column; gap: 6px;
  animation: fade-in 0.3s ease;
}
.pull-header { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.pull-status-txt { color: var(--muted); font-size: 11px; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pull-track  { height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; }
.pull-fill   { height: 100%; background: var(--accent); border-radius: 2px; transition: width 0.3s ease; }
.pull-pct    { font-size: 11px; color: var(--accent); text-align: right; }

/* Ollama warning */
.ollama-warn {
  font-size: 12px; color: var(--topic); padding: 6px 0;
}
.ollama-warn code { font-size: 11px; background: var(--surface2); padding: 1px 5px; border-radius: 3px; }

/* API key row */
.api-key-row {
  display: flex; align-items: center; gap: 10px; margin-top: 8px;
}
.api-key-row label { font-size: 12px; color: var(--muted); flex-shrink: 0; }
.api-key-row input { flex: 1; }

/* Custom fields */
.custom-fields { gap: 10px; }
.field { display: flex; flex-direction: column; gap: 4px; }
.field label { font-size: 12px; color: var(--muted); }

/* Presets */
.preset-save-row {
  display: flex; gap: 8px; align-items: center; margin-top: 4px;
}
.preset-save-row input { flex: 1; }
.btn-danger-ghost {
  background: none; border: 1px solid color-mix(in srgb, var(--danger) 40%, transparent);
  color: var(--danger); cursor: pointer; border-radius: 6px; padding: 5px 12px;
  font-size: 12px; transition: background 0.15s;
}
.btn-danger-ghost:hover { background: color-mix(in srgb, var(--danger) 10%, transparent); }

/* Ingest model hint */
.ingest-model-hint {
  font-size: 11px; color: var(--accent);
  background: color-mix(in srgb, var(--accent) 8%, transparent);
  border-radius: 10px; padding: 2px 8px; flex: 1;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin: 0 8px;
}

/* ── Status badge ────────────────────────────────────────────────────────────── */
.status-badge {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 500; animation: fade-in 0.3s ease;
}
.badge-running { color: var(--accent); }
.badge-idle    { color: var(--muted); }
.badge-error   { color: var(--danger); }
.status-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.badge-idle .status-dot  { background: var(--muted); }
.badge-error .status-dot { background: var(--danger); }

/* ── Current file ────────────────────────────────────────────────────────────── */
.current-file { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.file-name {
  font-size: 11px; background: var(--surface2); border-radius: 4px; padding: 2px 6px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 280px;
}
.elapsed-badge {
  font-size: 11px; color: var(--accent);
  background: color-mix(in srgb, var(--accent) 10%, transparent);
  border-radius: 10px; padding: 1px 7px;
}
.queue-hint { font-size: 12px; padding-top: 4px !important; }

/* ── LLM thinking ────────────────────────────────────────────────────────────── */
.llm-thinking {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 18px !important; font-size: 12px; color: var(--accent);
  background: color-mix(in srgb, var(--accent) 8%, transparent);
  border-top: 1px solid color-mix(in srgb, var(--accent) 20%, transparent);
  border-bottom: 1px solid color-mix(in srgb, var(--accent) 20%, transparent);
  animation: fade-in 0.4s ease;
}
.think-dots { display: flex; gap: 3px; align-items: center; }
.think-dots span {
  width: 5px; height: 5px; border-radius: 50%; background: var(--accent);
  animation: bounce 1.2s ease-in-out infinite;
}
.think-dots span:nth-child(2) { animation-delay: 0.2s; }
.think-dots span:nth-child(3) { animation-delay: 0.4s; }

/* ── Log ─────────────────────────────────────────────────────────────────────── */
.log-box {
  background: var(--bg); border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);
  padding: 10px 18px !important; max-height: 220px; overflow-y: auto;
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: clamp(10px, 0.7vw + 8px, 12px); margin: 8px 0 0 !important;
}
.log-line    { color: var(--muted); line-height: 1.9; white-space: pre-wrap; }
.log-head    { color: var(--accent); font-weight: 600; margin-top: 4px; }
.log-warn    { color: var(--danger); }
.log-current { color: var(--text); }
.cursor { color: var(--accent); margin-left: 1px; animation: blink 1s step-end infinite; }

/* ── Idle / footer ───────────────────────────────────────────────────────────── */
.idle-summary { font-size: 12px; padding-top: 12px !important; }
.error-hint   { color: var(--danger); }
.card-footer  {
  display: flex; align-items: center; justify-content: space-between;
  border-top: 1px solid var(--border); margin-top: 10px;
  padding-top: 10px !important;
}
.btn-sm { font-size: 12px; padding: 5px 12px; }

/* ── Row / inputs ────────────────────────────────────────────────────────────── */
.row { display: flex; gap: 10px; align-items: center; padding-top: 12px; }
.row input { flex: 1; }
.result {
  font-size: 12px; padding: 8px 10px !important;
  border-radius: 6px; margin: 8px 0 0 !important;
}
.result-ok    { background: var(--result-ok-bg);  color: var(--result-ok-text); }
.result-error { background: var(--result-err-bg); color: var(--result-err-text); }
.muted { color: var(--muted); font-size: 13px; }

/* ── Raw files panel ─────────────────────────────────────────────────────────── */
.raw-header {
  padding: 16px 16px 10px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.raw-title-row {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
}
.raw-title-row .panel-title { margin-bottom: 0; }
.btn-process-all {
  display: flex; align-items: center; gap: 5px;
  font-size: 11px; font-weight: 600; padding: 5px 12px; border-radius: 20px;
  border: 1.5px solid var(--accent); color: var(--accent); background: transparent;
  cursor: pointer; transition: all 0.15s; white-space: nowrap; flex-shrink: 0;
  letter-spacing: 0.1px;
}
.btn-process-all:hover:not(:disabled) { background: var(--accent); color: #fff; }
.btn-process-all:disabled { opacity: 0.35; cursor: default; }
.raw-header-row {
  display: flex; align-items: center; gap: 8px; margin-top: 10px;
}
.sort-select {
  flex: 1; font-size: 11px; padding: 5px 8px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--surface2); color: var(--text);
  cursor: pointer; outline: none; transition: border-color 0.15s;
  appearance: none; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%236b7280' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat; background-position: right 8px center; padding-right: 24px;
}
.sort-select:focus { border-color: var(--accent); }

/* Auto-ingest toggle */
.auto-toggle { display: flex; align-items: center; gap: 5px; cursor: pointer; user-select: none; }
.auto-toggle input { display: none; }
.at-track {
  width: 30px; height: 17px; border-radius: 9px; background: var(--border);
  position: relative; transition: background 0.2s; flex-shrink: 0;
}
.at-thumb {
  position: absolute; top: 2px; left: 2px;
  width: 13px; height: 13px; border-radius: 50%; background: #fff;
  transition: transform 0.2s; box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}
.auto-toggle.on .at-track { background: var(--accent); }
.auto-toggle.on .at-thumb { transform: translateX(13px); }
.at-label { font-size: 11px; color: var(--muted); white-space: nowrap; }
.auto-toggle.on .at-label { color: var(--accent); }

/* Action bar */
.action-bar {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  padding: 6px 12px;
  background: color-mix(in srgb, var(--accent) 5%, transparent);
  border-bottom: 1px solid color-mix(in srgb, var(--accent) 12%, transparent);
  flex-shrink: 0;
}
.sel-count {
  font-size: 11px; font-weight: 700; color: var(--accent);
  padding: 2px 8px; border-radius: 20px;
  background: color-mix(in srgb, var(--accent) 12%, transparent);
  margin-right: 2px;
}
.act-btn {
  font-size: 11px; font-weight: 500; padding: 3px 10px; border-radius: 20px;
  cursor: pointer; border: 1px solid; transition: all 0.15s;
}
.act-process  { border-color: var(--accent); color: var(--accent); background: transparent; }
.act-process:hover { background: var(--accent); color: #fff; }
.act-ignore   { border-color: var(--border); color: var(--muted); background: transparent; }
.act-ignore:hover { background: var(--surface2); color: var(--text); border-color: var(--muted); }
.act-unignore { border-color: var(--entity); color: var(--entity); background: transparent; }
.act-unignore:hover { background: var(--entity); color: #fff; }
.act-clear {
  background: none; border: none; cursor: pointer; color: var(--muted);
  margin-left: auto; font-size: 15px; line-height: 1; padding: 2px 4px;
  border-radius: 4px; transition: color 0.12s;
}
.act-clear:hover { color: var(--text); }

/* Select-all bar */
.select-all-row {
  display: flex; align-items: center; gap: 8px;
  padding: 5px 14px; border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.select-all-label { font-size: 11px; color: var(--muted); }
.file-counts { display: flex; gap: 5px; margin-left: auto; align-items: center; }
.cnt {
  font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 20px; letter-spacing: 0.1px;
}
.cnt-pending  { background: color-mix(in srgb, var(--accent) 10%, transparent); color: var(--accent); }
.cnt-done     { background: color-mix(in srgb, var(--entity) 10%, transparent); color: var(--entity); }
.cnt-ignored  { background: var(--surface2); color: var(--muted); }

/* Custom checkbox */
.cb-wrap { display: flex; align-items: center; cursor: pointer; flex-shrink: 0; }
.cb-wrap input[type="checkbox"] { position: absolute; opacity: 0; width: 0; height: 0; pointer-events: none; }
.cb-box {
  width: 14px; height: 14px; border-radius: 4px; flex-shrink: 0;
  border: 1.5px solid var(--border); background: var(--surface);
  transition: all 0.12s; position: relative;
}
.cb-wrap:hover .cb-box { border-color: var(--accent); }
.cb-wrap input:checked ~ .cb-box {
  background: var(--accent); border-color: var(--accent);
}
.cb-wrap input:checked ~ .cb-box::after {
  content: '';
  position: absolute; top: 1px; left: 4px;
  width: 4px; height: 7px;
  border: 1.5px solid #fff; border-top: none; border-left: none;
  transform: rotate(45deg);
}
.cb-wrap input:indeterminate ~ .cb-box {
  background: var(--accent); border-color: var(--accent);
}
.cb-wrap input:indeterminate ~ .cb-box::after {
  content: '';
  position: absolute; top: 5px; left: 2px; right: 2px;
  height: 1.5px; background: #fff; border: none; transform: none;
}

/* File list body */
.raw-body { flex: 1; overflow-y: auto; }

/* Empty state */
.raw-empty { display: flex; flex-direction: column; align-items: center; padding: 48px 24px; gap: 8px; }
.raw-empty-icon {
  width: 36px; height: 40px; position: relative; margin-bottom: 4px;
  background: var(--surface2); border-radius: 4px 10px 4px 4px; border: 1.5px solid var(--border);
}
.raw-empty-icon::before {
  content: ''; position: absolute; top: -1px; right: -1px;
  width: 10px; height: 10px; background: var(--surface);
  border-radius: 0 0 0 4px; border-bottom: 1.5px solid var(--border); border-left: 1.5px solid var(--border);
}
.raw-empty-text { font-size: 13px; font-weight: 600; color: var(--text); }
.raw-empty-hint { font-size: 12px; color: var(--muted); }

/* Section */
.raw-section { margin-bottom: 4px; }
.section-hdr {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px 4px;
}
.section-title {
  font-size: 10px; font-weight: 700; letter-spacing: 0.8px;
  text-transform: uppercase; color: var(--muted); flex-shrink: 0;
}
.section-count {
  font-size: 10px; font-weight: 600; color: var(--muted);
  background: var(--surface2); border-radius: 20px;
  padding: 0px 6px; min-width: 18px; text-align: center;
}
.section-hdr::after { content: ''; flex: 1; height: 1px; background: var(--border); }

/* File rows */
.raw-item-wrap { display: flex; flex-direction: column; }
.raw-item {
  display: flex; align-items: center; gap: 8px;
  padding: 0 12px 0 14px; height: 42px;
  border-left: 2px solid transparent;
  transition: background 0.1s, border-color 0.1s;
  cursor: default; position: relative;
}
.raw-item:hover { background: var(--surface2); border-left-color: color-mix(in srgb, var(--accent) 40%, transparent); }
.raw-item.is-selected { background: color-mix(in srgb, var(--accent) 5%, transparent); }
.raw-item.active { border-left-color: var(--accent); background: color-mix(in srgb, var(--accent) 6%, transparent); }
.raw-item.ignored { opacity: 0.4; }
.raw-item.processed .file-name { color: var(--muted); }

/* Doc icon */
.file-icon-doc {
  width: 22px; height: 26px; flex-shrink: 0; position: relative;
  background: color-mix(in srgb, var(--accent) 12%, transparent);
  border-radius: 3px 7px 3px 3px;
  display: flex; align-items: center; justify-content: center;
}
.file-icon-doc::before {
  content: ''; position: absolute; top: 0; right: 0;
  width: 7px; height: 7px; background: var(--surface);
  border-radius: 0 0 0 3px;
  box-shadow: -1px 1px 0 color-mix(in srgb, var(--accent) 20%, transparent);
}
.file-ext-label {
  font-size: 7px; font-weight: 800; color: var(--accent);
  letter-spacing: 0.3px; margin-top: 4px;
}
.spinner-sm { width: 12px; height: 12px; }

/* Image thumbnail */
.img-thumb-wrap {
  width: 32px; height: 32px; border-radius: 6px; overflow: hidden; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--surface2); border: 1px solid var(--border);
}
.img-thumb { width: 100%; height: 100%; object-fit: cover; display: block; }

/* File info */
.file-info {
  flex: 1; min-width: 0; display: flex; align-items: center; gap: 6px; overflow: hidden;
}
.file-name {
  font-size: 12px; font-weight: 500; overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; color: var(--text); flex: 1; min-width: 0;
}

/* Image ref chip (article expand toggle) */
.img-ref-chip {
  display: inline-flex; align-items: center; gap: 3px; flex-shrink: 0;
  font-size: 10px; font-weight: 600;
  padding: 2px 6px; border-radius: 20px;
  background: var(--surface2); border: 1px solid var(--border);
  color: var(--muted); cursor: pointer;
  transition: all 0.12s;
}
.img-ref-chip:hover { border-color: var(--accent); color: var(--accent); }
.img-ref-count { font-size: 10px; }
.img-ref-caret { font-size: 8px; }

/* Status dot */
.status-dot {
  width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
  transition: opacity 0.15s;
}
.dot-pending  { background: var(--accent); opacity: 0.5; }
.dot-active   { background: var(--accent); opacity: 1; box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 25%, transparent); }
.dot-processed { background: var(--entity); opacity: 0.7; }
.dot-ignored  { background: var(--border); opacity: 1; }

/* Run button (per-item process) */
.run-btn {
  width: 26px; height: 26px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  border: 1.5px solid var(--accent); color: var(--accent); background: transparent;
  cursor: pointer; transition: all 0.15s;
  opacity: 0; pointer-events: none;
}
.run-btn.run-btn-redo { border-color: var(--border); color: var(--muted); }
.raw-item:hover .run-btn { opacity: 1; pointer-events: auto; }
.run-btn:hover { background: var(--accent); color: #fff; border-color: var(--accent); }
.run-btn.run-btn-redo:hover { background: var(--surface2); color: var(--text); border-color: var(--muted); }

/* Sub-images (article expansion) */
.sub-images {
  display: flex; flex-direction: column;
  margin-left: 44px; margin-bottom: 2px;
  border-left: 1.5px solid var(--border);
  border-radius: 0 0 4px 4px;
}
.sub-img-item {
  display: flex; align-items: center; gap: 8px;
  padding: 5px 12px; min-height: 38px;
}
.sub-thumb-wrap {
  width: 26px; height: 26px; border-radius: 4px; overflow: hidden; flex-shrink: 0;
  border: 1px solid var(--border); background: var(--surface2);
}
.sub-thumb { width: 100%; height: 100%; object-fit: cover; display: block; }
.sub-thumb-missing {
  display: flex; align-items: center; justify-content: center;
  width: 100%; height: 100%; color: var(--muted); font-size: 10px;
}
.sub-name {
  flex: 1; min-width: 0; font-size: 11px; color: var(--muted);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* Confirm dialog */
.dialog-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.35);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.dialog-box {
  background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
  padding: 24px 28px; min-width: 280px; max-width: 380px;
  display: flex; flex-direction: column; gap: 18px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.2); animation: fade-in 0.15s ease;
}
.dialog-msg  { font-size: 14px; line-height: 1.5; }
.dialog-btns { display: flex; gap: 10px; justify-content: flex-end; }
/* ── Keyframes ───────────────────────────────────────────────────────────────── */
@keyframes slide {
  0% { transform: translateX(-100%); } 100% { transform: translateX(350%); }
}
@keyframes spin    { to { transform: rotate(360deg); } }
@keyframes bounce  {
  0%, 60%, 100% { transform: translateY(0); }
  30%           { transform: translateY(-4px); }
}
@keyframes blink   { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
@keyframes fade-in {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}
</style>
