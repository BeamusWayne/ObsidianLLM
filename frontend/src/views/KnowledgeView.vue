<template>
  <div class="kb-wrap">
    <div class="kb-header">
      <h1 class="page-title">我的知识库</h1>
    </div>

    <!-- Search + semantic search -->
    <div class="search-row">
      <div class="search-input-wrap">
        <span class="search-icon">⌕</span>
        <input v-model="query" class="kb-search" placeholder="搜索知识库…" />
      </div>
      <button class="btn-ghost btn-sm echo-search-btn" @click="showOriSearch = !showOriSearch" title="语义搜索 (Echo)">
        🦇 语义搜索
      </button>
    </div>

    <!-- Echo semantic search panel -->
    <div v-if="showOriSearch" class="echo-search-panel card">
      <div class="echo-search-header">
        <span class="echo-avatar">🦇</span>
        <span style="font-size:13px;font-weight:600">Echo 语义搜索</span>
        <span style="font-size:11px;color:var(--muted);margin-left:4px">— 用自然语言找任何内容</span>
      </div>
      <div class="echo-search-input-row">
        <input v-model="oriQuery" placeholder="问 Echo：这个概念和什么有关？" @keyup.enter="oriSearch" />
        <button class="btn-primary btn-sm" :disabled="oriLoading || !oriQuery.trim()" @click="oriSearch">
          <span v-if="oriLoading" class="spinner"></span>
          <span v-else>搜索</span>
        </button>
      </div>
      <div v-if="oriAnswer" class="echo-answer">{{ oriAnswer }}</div>
    </div>

    <!-- Source type filter tabs -->
    <div class="filter-tabs">
      <button
        v-for="tab in sourceTabs" :key="tab.value"
        class="filter-tab"
        :class="{ active: sourceFilter === tab.value }"
        @click="sourceFilter = tab.value"
      >{{ tab.label }}</button>
    </div>

    <!-- Knowledge type filter (concept/entity/topic) -->
    <div class="type-filters">
      <button
        v-for="t in typeTabs" :key="t.value"
        class="type-chip"
        :class="{ active: typeFilter === t.value }"
        @click="typeFilter = t.value === typeFilter ? '' : t.value"
      >{{ t.label }}</button>
    </div>

    <!-- Count -->
    <div class="kb-count">{{ filtered.length }} 条内容</div>

    <!-- Empty state -->
    <div v-if="filtered.length === 0" class="kb-empty">
      <div v-if="pages.length === 0">
        <p>还没有内容</p>
        <p>从 Twitter 或 YouTube 导入你的收藏</p>
        <router-link to="/import" class="btn-primary" style="display:inline-block;margin-top:12px;text-decoration:none;padding:8px 18px;border-radius:8px">去导入</router-link>
      </div>
      <p v-else>没有匹配的内容</p>
    </div>

    <!-- Card grid -->
    <div v-else class="kb-grid">
      <router-link
        v-for="p in filtered" :key="p.stem"
        :to="`/wiki/${encodeURIComponent(p.stem)}`"
        class="kb-card card"
      >
        <div class="kb-card-meta">
          <span class="tag" :class="`tag-${p.type}`">{{ p.type }}</span>
          <span v-if="p.source_type && p.source_type !== 'article'" class="src-badge" :class="`src-${p.source_type}`">{{ srcLabel(p.source_type) }}</span>
        </div>
        <div class="kb-card-title">{{ p.title }}</div>
        <div class="kb-card-stem">{{ p.stem }}</div>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const pages = ref([])
const query = ref('')
const sourceFilter = ref('all')
const typeFilter = ref('')
const showOriSearch = ref(false)
const oriQuery = ref('')
const oriAnswer = ref('')
const oriLoading = ref(false)

const sourceTabs = [
  { value: 'all',          label: '全部' },
  { value: 'twitter',      label: 'Twitter' },
  { value: 'youtube',      label: 'YouTube' },
  { value: 'article',      label: '文章' },
  { value: 'xiaohongshu',  label: '小红书' },
]

const typeTabs = [
  { value: 'concept', label: '概念' },
  { value: 'entity',  label: '实体' },
  { value: 'topic',   label: '主题' },
]

function srcLabel(t) {
  return { youtube: 'YouTube', twitter: 'Twitter', xiaohongshu: '小红书' }[t] || t
}

const filtered = computed(() => {
  let list = pages.value
  if (sourceFilter.value !== 'all') {
    list = list.filter(p => p.source_type === sourceFilter.value)
  }
  if (typeFilter.value) {
    list = list.filter(p => p.type === typeFilter.value)
  }
  if (query.value.trim()) {
    const q = query.value.trim().toLowerCase()
    list = list.filter(p =>
      p.title.toLowerCase().includes(q) || p.stem.toLowerCase().includes(q)
    )
  }
  return list
})

async function oriSearch() {
  if (!oriQuery.value.trim() || oriLoading.value) return
  oriLoading.value = true
  oriAnswer.value = ''
  try {
    const res = await fetch('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: oriQuery.value }),
    }).then(r => r.json())
    oriAnswer.value = res.answer
  } catch {
    oriAnswer.value = '⚠️ 搜索失败，请检查 LLM 设置'
  } finally {
    oriLoading.value = false
  }
}

onMounted(async () => {
  pages.value = await fetch('/api/wiki').then(r => r.json()).catch(() => [])
})
</script>

<style scoped>
.kb-wrap {
  height: 100%; overflow-y: auto;
  padding: 28px 32px;
  display: flex; flex-direction: column; gap: 14px;
}
.kb-header { }

.search-row { display: flex; gap: 10px; align-items: center; }
.search-input-wrap { flex: 1; position: relative; }
.search-icon {
  position: absolute; left: 12px; top: 50%; transform: translateY(-50%);
  color: var(--muted); font-size: 15px; pointer-events: none;
}
.kb-search {
  padding-left: 34px;
  background: var(--surface);
}
.echo-search-btn { white-space: nowrap; border-color: var(--border); }
.echo-search-btn:hover { border-color: var(--accent); color: var(--accent); }

.echo-search-panel {
  display: flex; flex-direction: column; gap: 10px;
  background: var(--accent-light); border-color: color-mix(in srgb, var(--accent) 20%, transparent);
}
.echo-search-header { display: flex; align-items: center; gap: 6px; }
.echo-avatar { font-size: 16px; }
.echo-search-input-row { display: flex; gap: 8px; }
.echo-search-input-row input { flex: 1; }
.echo-answer {
  font-size: 13px; line-height: 1.7; color: var(--text);
  background: var(--surface); border-radius: 8px; padding: 12px;
  white-space: pre-wrap;
}

.filter-tabs { display: flex; gap: 6px; flex-wrap: wrap; }
.filter-tab {
  padding: 5px 14px; border-radius: 20px; font-size: 12px;
  border: 1px solid var(--border); background: var(--surface);
  color: var(--muted); cursor: pointer; transition: all 0.15s;
}
.filter-tab:hover { border-color: var(--accent); color: var(--accent); }
.filter-tab.active {
  background: var(--accent); color: #fff; border-color: var(--accent); font-weight: 600;
}

.type-filters { display: flex; gap: 6px; }
.type-chip {
  padding: 3px 10px; border-radius: 12px; font-size: 11px;
  border: 1px solid var(--border); background: transparent;
  color: var(--muted); cursor: pointer; transition: all 0.15s;
}
.type-chip:hover { border-color: var(--accent); color: var(--accent); }
.type-chip.active { background: var(--surface2); color: var(--text); border-color: var(--text); font-weight: 600; }

.kb-count { font-size: 12px; color: var(--muted); }
.kb-empty { text-align: center; padding: 40px 20px; color: var(--muted); font-size: 13px; line-height: 1.7; }

.kb-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.kb-card {
  display: flex; flex-direction: column; gap: 8px;
  text-decoration: none; color: var(--text); padding: 14px;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.kb-card:hover { border-color: var(--accent); box-shadow: 0 2px 10px rgba(0,0,0,0.06); text-decoration: none; }
.kb-card-meta { display: flex; gap: 5px; flex-wrap: wrap; }
.kb-card-title { font-size: 13px; font-weight: 500; line-height: 1.4; }
.kb-card-stem { font-size: 11px; color: var(--muted); font-family: monospace; }
</style>
