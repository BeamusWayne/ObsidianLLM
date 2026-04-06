<template>
  <nav class="sidebar" :class="{ collapsed: sidebarCollapsed }" :style="!sidebarCollapsed ? { width: sidebarW + 'px', minWidth: sidebarW + 'px' } : {}">
    <!-- Brand -->
    <div class="brand">
      <span class="brand-name" v-if="!sidebarCollapsed">Wiki KB</span>
      <button class="collapse-btn" @click="sidebarCollapsed = !sidebarCollapsed" :title="sidebarCollapsed ? '展开' : '收起'">
        <span class="collapse-icon">{{ sidebarCollapsed ? '›' : '‹' }}</span>
      </button>
    </div>

    <template v-if="!sidebarCollapsed">
      <!-- Core section -->
      <div class="nav-section-label">核心</div>
      <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }">
        <span class="nav-icon">○</span><span class="nav-label">首页</span>
      </router-link>
      <router-link to="/knowledge" class="nav-item" :class="{ active: $route.path === '/knowledge' }">
        <span class="nav-icon">○</span><span class="nav-label">知识库</span>
      </router-link>
      <router-link to="/import" class="nav-item" :class="{ active: $route.path === '/import' }">
        <span class="nav-icon">+</span><span class="nav-label">导入</span>
      </router-link>
      <router-link to="/review" class="nav-item" :class="{ active: $route.path === '/review' }">
        <span class="nav-icon">+</span><span class="nav-label">回顾</span>
      </router-link>
      <router-link to="/ideas" class="nav-item" :class="{ active: $route.path === '/ideas' }">
        <span class="nav-icon nav-moon">🌙</span><span class="nav-label">想法</span>
      </router-link>
      <router-link to="/growth" class="nav-item" :class="{ active: $route.path === '/growth' }">
        <span class="nav-icon">+</span><span class="nav-label">成长</span>
      </router-link>

      <!-- Collections section -->
      <div class="nav-section-label">
        <span>合集</span>
        <button class="section-add" @click="showNewCol = true" title="新建合集">+</button>
      </div>
      <div v-if="collections.length === 0" class="nav-empty">还没有合集</div>
      <router-link
        v-for="col in collections" :key="col.id"
        :to="`/collections/${col.id}`"
        class="nav-item nav-collection"
        :class="{ active: $route.params.id === col.id }"
      >
        <span class="col-dot"></span>
        <span class="nav-label">{{ col.name }}</span>
      </router-link>

      <!-- Admin section -->
      <div class="nav-section-label">管理</div>
      <router-link to="/settings" class="nav-item" :class="{ active: $route.path === '/settings' }">
        <span class="nav-icon">○</span><span class="nav-label">设置</span>
      </router-link>
      <router-link to="/graph" class="nav-item" :class="{ active: $route.path === '/graph' }">
        <span class="nav-icon">◎</span><span class="nav-label">图谱</span>
      </router-link>
    </template>
  </nav>

  <!-- Resize handle (only when not collapsed) -->
  <div v-if="!sidebarCollapsed" class="resize-handle" :class="{ active: dragging }" @mousedown="start"></div>

  <main class="main">
    <router-view />
  </main>

  <!-- New collection modal -->
  <div v-if="showNewCol" class="modal-overlay" @click.self="showNewCol = false">
    <div class="modal-box">
      <div class="modal-title">新建合集</div>
      <input v-model="newColName" placeholder="合集名称…" @keyup.enter="createCollection" autofocus />
      <div class="modal-actions">
        <button class="btn-primary" :disabled="!newColName.trim()" @click="createCollection">创建</button>
        <button class="btn-ghost" @click="showNewCol = false">取消</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useResizer } from './composables/useResizer.js'

const router = useRouter()
const sidebarCollapsed = ref(false)
const collections = ref([])
const showNewCol = ref(false)
const newColName = ref('')

const { size: sidebarW, dragging, start } = useResizer(200, { min: 160, max: 300 })

async function loadCollections() {
  collections.value = await fetch('/api/collections').then(r => r.json()).catch(() => [])
}

async function createCollection() {
  if (!newColName.value.trim()) return
  const col = await fetch('/api/collections', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: newColName.value.trim() }),
  }).then(r => r.json())
  collections.value = [...collections.value, col]
  showNewCol.value = false
  newColName.value = ''
  router.push(`/collections/${col.id}`)
}

onMounted(() => {
  const saved = localStorage.getItem('wiki-kb-theme') || 'light'
  document.documentElement.setAttribute('data-theme', saved)
  loadCollections()
})
</script>

<style scoped>
.sidebar {
  background: var(--bg);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0 0 16px;
  flex-shrink: 0;
  transition: background 0.2s;
  scrollbar-width: none;
}
.sidebar.collapsed { width: 44px !important; min-width: 44px !important; }
.sidebar::-webkit-scrollbar { display: none; }

.brand {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 14px 12px;
  min-height: 50px;
}
.brand-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: 0.3px;
}
.collapse-btn {
  background: none;
  border: none;
  padding: 2px 6px;
  color: var(--muted);
  font-size: 16px;
  cursor: pointer;
  line-height: 1;
  border-radius: 4px;
}
.collapse-btn:hover { color: var(--text); background: var(--surface2); }

.nav-section-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: var(--muted);
  padding: 14px 14px 5px;
  margin-top: 4px;
}
.section-add {
  background: none; border: none; color: var(--muted);
  font-size: 14px; cursor: pointer; padding: 0 2px;
  line-height: 1; border-radius: 4px;
}
.section-add:hover { color: var(--accent); background: var(--accent-light); }

.nav-item {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 14px; color: var(--muted);
  font-size: 13px; text-decoration: none;
  transition: color 0.12s, background 0.12s;
  white-space: nowrap;
}
.nav-item:hover { color: var(--text); background: var(--surface2); text-decoration: none; }
.nav-item.active { color: var(--accent); background: var(--accent-light); font-weight: 500; }
.nav-icon { font-size: 12px; width: 14px; text-align: center; flex-shrink: 0; color: inherit; }
.nav-moon { font-size: 10px; }
.nav-label { flex: 1; }

.nav-collection { padding-left: 16px; }
.col-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--border); flex-shrink: 0; }
.nav-item.active .col-dot { background: var(--accent); }
.nav-empty { font-size: 11px; color: var(--muted); padding: 4px 14px 8px; font-style: italic; }

.main { flex: 1; overflow: hidden; display: flex; flex-direction: column; min-width: 0; }

.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.25);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal-box {
  background: var(--surface); border-radius: 14px;
  padding: 24px; width: 320px; display: flex; flex-direction: column; gap: 14px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12);
}
.modal-title { font-size: 15px; font-weight: 700; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; }
</style>
