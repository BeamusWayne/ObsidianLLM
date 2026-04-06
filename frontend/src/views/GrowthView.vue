<template>
  <div class="growth-wrap">
    <div class="page-header">
      <h1 class="page-title">知识档案</h1>
      <p class="page-subtitle">你的知识版图：主题分布、增长趋势和学习轨迹。</p>
    </div>

    <!-- Health check -->
    <div class="card health-card">
      <div class="card-title">知识健康检查</div>
      <p class="health-desc">AI 分析你的知识库，找出优势、薄弱领域和隐藏的知识关联。</p>
      <button class="btn-primary" style="align-self:flex-start" :disabled="checking" @click="runHealthCheck">
        <span v-if="checking" class="spinner"></span>
        <span v-else>运行知识健康检查</span>
      </button>
      <div v-if="healthResult" class="health-result" v-html="healthHtml"></div>
    </div>

    <!-- Stats row -->
    <div v-if="stats" class="stats-row">
      <div class="stat-card card">
        <div class="stat-label">总收藏数</div>
        <div class="stat-value">{{ stats.total }}</div>
      </div>
      <div class="stat-card card">
        <div class="stat-label">本周新增</div>
        <div class="stat-value">{{ stats.weekly_new }}</div>
      </div>
      <div class="stat-card card">
        <div class="stat-label">相比上周</div>
        <div class="stat-value" :class="stats.weekly_delta_pct >= 0 ? 'delta-pos' : 'delta-neg'">
          {{ stats.weekly_delta_pct >= 0 ? '+' : '' }}{{ stats.weekly_delta_pct }}%
        </div>
        <div class="stat-sub">+{{ stats.weekly_new - stats.weekly_prev }}，上周为 {{ stats.weekly_prev }}</div>
      </div>
    </div>

    <!-- Growth chart -->
    <div v-if="stats" class="card chart-card">
      <div class="card-title">收藏增长</div>
      <div class="chart-wrap">
        <svg :viewBox="`0 0 ${chartW} ${chartH}`" class="chart-svg" preserveAspectRatio="none">
          <path :d="chartPath" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path :d="chartAreaPath" fill="url(#grad)" opacity="0.15"/>
          <defs>
            <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.6"/>
              <stop offset="100%" stop-color="var(--accent)" stop-opacity="0"/>
            </linearGradient>
          </defs>
        </svg>
        <div class="chart-labels">
          <span v-for="(label, i) in chartLabels" :key="i" class="chart-label">{{ label }}</span>
        </div>
      </div>
    </div>

    <!-- Distribution + Tags -->
    <div v-if="stats" class="dist-row">
      <div class="card dist-card">
        <div class="card-title">分类分布</div>
        <div v-if="Object.keys(stats.source_dist).length === 0" class="dist-empty">还没有分类数据</div>
        <div v-else class="dist-bars">
          <div v-for="(count, type) in stats.source_dist" :key="type" class="dist-item">
            <div class="dist-label-row">
              <span class="src-badge" :class="`src-${type}`">{{ srcLabel(type) }}</span>
              <span class="dist-count">{{ count }}</span>
            </div>
            <div class="dist-track">
              <div class="dist-fill" :style="{ width: (count / stats.total * 100) + '%' }"></div>
            </div>
          </div>
        </div>
      </div>
      <div class="card tags-card">
        <div class="card-title">热门标签</div>
        <div v-if="stats.top_tags.length === 0" class="dist-empty">还没有标签数据</div>
        <div v-else class="tags-cloud">
          <span
            v-for="[tag, count] in stats.top_tags" :key="tag"
            class="tag-cloud-item"
            :style="{ fontSize: tagSize(count) + 'px' }"
          >{{ tag }}</span>
        </div>
      </div>
    </div>

    <!-- Activity heatmap -->
    <div v-if="stats" class="card heatmap-card">
      <div class="heatmap-header">
        <div class="card-title" style="margin:0">活跃度热力图</div>
        <div class="heatmap-legend">
          <span style="font-size:10px;color:var(--muted)">少</span>
          <span v-for="l in 5" :key="l" class="heat-cell" :class="`heat-${l-1}`"></span>
          <span style="font-size:10px;color:var(--muted)">多</span>
        </div>
      </div>
      <div class="heatmap-grid">
        <div
          v-for="(day, i) in heatmapDays"
          :key="i"
          class="heat-cell"
          :class="`heat-${day.level}`"
          :title="day.date + (day.count ? `：${day.count} 条` : '')"
        ></div>
      </div>
    </div>

    <div v-if="!stats && loading" class="loading-state">
      <span class="spinner"></span> 加载中…
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { marked } from 'marked'

const stats = ref(null)
const loading = ref(true)
const checking = ref(false)
const healthResult = ref('')

const chartW = 600
const chartH = 80

function srcLabel(t) {
  return { youtube: 'YouTube', twitter: 'Twitter', xiaohongshu: '小红书', article: '文章' }[t] || t
}

const healthHtml = computed(() => marked(healthResult.value || ''))

// ── Chart ──────────────────────────────────────────────────────────────────
const chartPoints = computed(() => {
  if (!stats.value) return []
  const daily = stats.value.daily_counts
  // Build 12-week windows (aggregated weekly)
  const weeks = []
  const now = new Date()
  for (let w = 11; w >= 0; w--) {
    let count = 0
    for (let d = 0; d < 7; d++) {
      const date = new Date(now)
      date.setDate(date.getDate() - w * 7 - d)
      const key = date.toISOString().split('T')[0]
      count += daily[key] || 0
    }
    weeks.push(count)
  }
  return weeks
})

const chartLabels = computed(() => {
  const labels = []
  const now = new Date()
  for (let w = 11; w >= 0; w--) {
    const d = new Date(now)
    d.setDate(d.getDate() - w * 7)
    if (w % 3 === 0) labels.push(`${d.getMonth()+1}/${d.getDate()}`)
    else labels.push('')
  }
  return labels
})

const chartPath = computed(() => {
  const pts = chartPoints.value
  if (!pts.length) return ''
  const max = Math.max(...pts, 1)
  const pad = 10
  return pts.map((v, i) => {
    const x = (i / (pts.length - 1)) * chartW
    const y = chartH - pad - (v / max) * (chartH - pad * 2)
    return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`
  }).join(' ')
})

const chartAreaPath = computed(() => {
  const pts = chartPoints.value
  if (!pts.length) return ''
  const max = Math.max(...pts, 1)
  const pad = 10
  const line = pts.map((v, i) => {
    const x = (i / (pts.length - 1)) * chartW
    const y = chartH - pad - (v / max) * (chartH - pad * 2)
    return `${x.toFixed(1)} ${y.toFixed(1)}`
  })
  return `M ${line.join(' L ')} L ${chartW} ${chartH} L 0 ${chartH} Z`
})

// ── Heatmap ────────────────────────────────────────────────────────────────
const heatmapDays = computed(() => {
  if (!stats.value) return []
  const daily = stats.value.daily_counts
  const days = []
  const now = new Date()
  const max = Math.max(...Object.values(daily), 1)
  for (let i = 364; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(d.getDate() - i)
    const key = d.toISOString().split('T')[0]
    const count = daily[key] || 0
    const level = count === 0 ? 0 : Math.min(4, Math.ceil((count / max) * 4))
    days.push({ date: key, count, level })
  }
  return days
})

function tagSize(count) {
  const max = stats.value?.top_tags?.[0]?.[1] || 1
  return 11 + Math.floor((count / max) * 8)
}

async function runHealthCheck() {
  checking.value = true
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: [{ role: 'user', content: '请分析我的知识库，做一次知识健康检查：找出优势领域、薄弱领域、以及知识关联机会。' }],
        context: 'wiki',
      }),
    }).then(r => r.json())
    healthResult.value = res.reply
  } catch {
    healthResult.value = '⚠️ 检查失败，请确认 LLM 已配置'
  } finally {
    checking.value = false
  }
}

onMounted(async () => {
  stats.value = await fetch('/api/stats').then(r => r.json()).catch(() => null)
  loading.value = false
})
</script>

<style scoped>
.growth-wrap {
  height: 100%; overflow-y: auto;
  padding: 28px 32px;
  display: flex; flex-direction: column; gap: 16px;
  max-width: 900px;
}

/* Health */
.health-card { display: flex; flex-direction: column; gap: 10px; }
.health-desc { font-size: 13px; color: var(--muted); }
.health-result {
  font-size: 13px; line-height: 1.7; margin-top: 4px;
  padding: 12px; background: var(--accent-light); border-radius: 8px;
}

/* Stats row */
.stats-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.stat-card { display: flex; flex-direction: column; gap: 4px; }
.stat-label { font-size: 11px; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
.stat-value { font-size: 28px; font-weight: 700; color: var(--text); }
.delta-pos { color: #16a34a; }
.delta-neg { color: var(--danger); }
.stat-sub { font-size: 11px; color: var(--muted); }

/* Chart */
.chart-card { }
.chart-wrap { }
.chart-svg { width: 100%; height: 80px; display: block; }
.chart-labels {
  display: flex; justify-content: space-between;
  font-size: 10px; color: var(--muted); margin-top: 4px;
}
.chart-label { text-align: center; }

/* Distribution + Tags */
.dist-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.dist-card,.tags-card { display: flex; flex-direction: column; gap: 10px; }
.dist-empty { font-size: 12px; color: var(--muted); }
.dist-bars { display: flex; flex-direction: column; gap: 8px; }
.dist-item { display: flex; flex-direction: column; gap: 4px; }
.dist-label-row { display: flex; align-items: center; justify-content: space-between; }
.dist-count { font-size: 11px; color: var(--muted); font-weight: 600; }
.dist-track { height: 5px; background: var(--surface2); border-radius: 3px; overflow: hidden; }
.dist-fill { height: 100%; background: var(--accent); border-radius: 3px; transition: width 0.5s; }

.tags-cloud { display: flex; flex-wrap: wrap; gap: 6px; align-items: baseline; }
.tag-cloud-item {
  color: var(--accent); font-weight: 500;
  opacity: 0.75; transition: opacity 0.15s;
  cursor: default;
}
.tag-cloud-item:hover { opacity: 1; }

/* Heatmap */
.heatmap-card { display: flex; flex-direction: column; gap: 10px; }
.heatmap-header { display: flex; align-items: center; justify-content: space-between; }
.heatmap-legend { display: flex; align-items: center; gap: 3px; }
.heatmap-grid {
  display: grid;
  grid-template-rows: repeat(7, 12px);
  grid-auto-flow: column;
  gap: 2px;
  overflow-x: auto;
}
.heat-cell {
  width: 12px; height: 12px; border-radius: 2px;
  background: var(--surface2);
  transition: background 0.15s;
}
.heat-0 { background: var(--surface2); }
.heat-1 { background: color-mix(in srgb, var(--accent) 25%, var(--surface2)); }
.heat-2 { background: color-mix(in srgb, var(--accent) 45%, var(--surface2)); }
.heat-3 { background: color-mix(in srgb, var(--accent) 65%, var(--surface2)); }
.heat-4 { background: var(--accent); }

.loading-state { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 13px; }
</style>

<style>
.health-result h1,.health-result h2,.health-result h3 { font-weight:600; margin:12px 0 6px; }
.health-result h2 { font-size:14px; }
.health-result p { margin-bottom:8px; }
.health-result ul,.health-result ol { padding-left:18px; margin-bottom:8px; }
.health-result li { margin-bottom:3px; }
</style>
