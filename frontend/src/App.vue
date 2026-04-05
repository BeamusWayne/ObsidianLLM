<template>
  <nav class="sidebar" :style="{ width: sidebarW + 'px', minWidth: sidebarW + 'px' }">
    <div class="logo">Wiki KB</div>
    <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }">
      <span class="icon">◎</span> Graph
    </router-link>
    <router-link to="/clip" class="nav-item" :class="{ active: $route.path === '/clip' }">
      <span class="icon">⊕</span> Clip & Ingest
    </router-link>
    <div class="nav-section">Wiki</div>
    <router-link
      v-for="p in pages" :key="p.stem"
      :to="`/wiki/${encodeURIComponent(p.stem)}`"
      class="nav-item nav-wiki"
      :class="{ active: $route.params.path === p.stem }"
    >
      <span :class="`dot dot-${p.type}`"></span>
      {{ p.title }}
    </router-link>
    <div class="spacer"></div>
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
import { ref, onMounted } from 'vue'
import { useResizer } from './composables/useResizer.js'

const pages = ref([])
const THEME_KEY = 'wiki-kb-theme'

const { size: sidebarW, dragging, start } = useResizer(200, { min: 140, max: 360 })

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
  overflow-y: auto;
  padding: 0 0 12px;
  transition: background 0.2s;
  flex-shrink: 0;
}
.logo {
  font-size: clamp(13px, 1.1vw + 8px, 16px);
  font-weight: 700;
  color: var(--accent);
  padding: 16px 14px 12px;
  letter-spacing: 0.5px;
}
.nav-section {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--muted);
  padding: 12px 14px 4px;
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
.nav-wiki { font-size: clamp(10px, 0.8vw + 7px, 12px); padding: 4px 14px; }
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
