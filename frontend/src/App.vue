<template>
  <nav class="sidebar" :style="{ width: sidebarW + 'px', minWidth: sidebarW + 'px' }">
    <div class="logo">Wiki KB</div>
    <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }">
      <span class="icon">◎</span> Graph
    </router-link>
    <router-link to="/clip" class="nav-item" :class="{ active: $route.path === '/clip' }">
      <span class="icon">⊕</span> Clip & Ingest
    </router-link>
    <div class="search-wrap">
      <input v-model="query" class="search-input" placeholder="Search…" />
    </div>
    <div class="nav-groups">
      <div
        v-for="g in grouped" :key="g.type"
        class="nav-group"
        :style="collapsed[g.type] ? {} : { flex: g.items.length }"
      >
        <button class="nav-section nav-group-toggle" @click="toggle(g.type)">
          <span>{{ g.label }} <em class="count">{{ g.items.length }}</em></span>
          <span class="chevron" :class="{ open: !collapsed[g.type] }">›</span>
        </button>
        <div v-if="!collapsed[g.type]" class="nav-group-items">
          <router-link
            v-for="p in g.items" :key="p.stem"
            :to="`/wiki/${encodeURIComponent(p.stem)}`"
            class="nav-item nav-wiki"
            :class="{ active: $route.params.path === p.stem }"
          >
            <span :class="`dot dot-${p.type}`"></span>
            {{ p.title }}
          </router-link>
        </div>
      </div>
    </div>
    <router-link to="/settings" class="nav-item" :class="{ active: $route.path === '/settings' }">
      <span class="icon">⚙</span> Settings
    </router-link>
  </nav>

  <div class="resize-handle" :class="{ active: dragging }" @mousedown="start"></div>

  <main class="main">
    <router-view />
  </main>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useResizer } from './composables/useResizer.js'

const pages = ref([])
const query = ref('')
const THEME_KEY = 'wiki-kb-theme'
const collapsed = ref({})

const { size: sidebarW, dragging, start } = useResizer(200, { min: 140, max: 360 })

const TYPE_ORDER = ['concept', 'entity', 'topic', 'unknown']
const TYPE_LABEL = { concept: 'Concepts', entity: 'Entities', topic: 'Topics', unknown: 'Other' }

const grouped = computed(() => {
  const q = query.value.trim().toLowerCase()
  const filtered = q ? pages.value.filter(p => p.title.toLowerCase().includes(q)) : pages.value
  return TYPE_ORDER
    .map(type => ({ type, label: TYPE_LABEL[type], items: filtered.filter(p => p.type === type) }))
    .filter(g => g.items.length > 0)
})

function toggle(type) {
  const isOpen = !collapsed.value[type]
  // collapse all, then toggle target (accordion)
  const allTypes = ['concept', 'entity', 'topic', 'unknown']
  allTypes.forEach(t => { collapsed.value[t] = true })
  collapsed.value[type] = isOpen
}

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY) || 'light'
  document.documentElement.setAttribute('data-theme', saved)
}

onMounted(async () => {
  initTheme()
  const data = await fetch('/api/wiki').then(r => r.json()).catch(() => [])
  pages.value = data
})
</script>

<style scoped>
.sidebar {
  background: var(--surface);
  border-right: none;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0 0 12px;
  transition: background 0.2s;
  flex-shrink: 0;
}

.nav-groups {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}
.nav-group {
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 0 0 auto;
}
.logo {
  font-size: clamp(13px, 1.1vw + 8px, 16px);
  font-weight: 700;
  color: var(--accent);
  padding: 16px 14px 12px;
  letter-spacing: 0.5px;
}
.search-wrap {
  padding: 8px 10px 4px;
}
.search-input {
  width: 100%;
  box-sizing: border-box;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 8px;
  font-size: 11px;
  color: var(--text);
  outline: none;
}
.search-input:focus { border-color: var(--accent); }
.search-input::placeholder { color: var(--muted); }

.nav-section {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--muted);
  padding: 12px 14px 4px;
}
.nav-group-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  background: none;
  border: none;
  cursor: pointer;
  padding: 14px 14px 5px;
  margin-top: 4px;
}
.nav-group-toggle:hover { color: var(--text); }
.chevron {
  font-size: 14px;
  line-height: 1;
  transform: rotate(0deg);
  transition: transform 0.15s;
  display: inline-block;
}
.chevron.open { transform: rotate(90deg); }

.count {
  font-style: normal;
  font-weight: 400;
  font-size: 9px;
  background: var(--surface2);
  color: var(--muted);
  border-radius: 8px;
  padding: 1px 5px;
  margin-left: 4px;
  vertical-align: middle;
  letter-spacing: 0;
}

.nav-group-items {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 6px 14px;
  color: var(--muted);
  font-size: clamp(11px, 0.9vw + 7px, 13px);
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 0.1s, background 0.1s;
}
.nav-item:hover  { color: var(--text); background: var(--surface2); text-decoration: none; }
.nav-item.active { color: var(--accent); background: var(--active-bg); font-weight: 500; }
.nav-wiki {
  font-size: clamp(11px, 0.85vw + 7px, 13px);
  padding: 6px 14px 6px 24px;
  line-height: 1.4;
  white-space: normal;
}
.icon { font-size: 12px; }
.dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.dot-concept { background: var(--concept); }
.dot-entity  { background: var(--entity); }
.dot-topic   { background: var(--topic); }
.dot-unknown { background: var(--muted); }
.spacer { flex: 1; }
.main { flex: 1; overflow: hidden; display: flex; flex-direction: column; min-width: 0; }

.resize-handle {
  width: 4px;
  flex-shrink: 0;
  cursor: col-resize;
  background: var(--border);
  transition: background 0.15s;
  z-index: 20;
}
.resize-handle:hover,
.resize-handle.active { background: var(--accent); opacity: 0.6; }
</style>
