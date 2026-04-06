<template>
  <div class="col-wrap">
    <div class="col-top-bar">
      <div class="page-header">
        <h1 class="page-title">{{ collection ? collection.name : '合集' }}</h1>
        <p class="page-subtitle" v-if="collection">{{ collection.items.length }} 个条目</p>
      </div>
      <div class="col-actions" v-if="collection">
        <button class="btn-ghost btn-sm" @click="showAddItem = true">+ 添加条目</button>
        <button class="btn-ghost btn-sm danger-btn" @click="deleteCollection">删除合集</button>
      </div>
    </div>

    <!-- No collection selected -->
    <div v-if="!collection" class="col-empty">
      <p>合集未找到</p>
    </div>

    <!-- Empty collection -->
    <div v-else-if="collection.items.length === 0" class="col-empty">
      <p>此合集还没有内容</p>
      <button class="btn-primary" style="margin-top:12px" @click="showAddItem = true">+ 添加条目</button>
    </div>

    <!-- Items grid -->
    <div v-else class="col-grid">
      <div v-for="stem in collection.items" :key="stem" class="col-item card">
        <div class="col-item-meta">
          <span class="tag" :class="`tag-${pageMap[stem]?.type || 'unknown'}`">{{ pageMap[stem]?.type || 'unknown' }}</span>
        </div>
        <router-link :to="`/wiki/${encodeURIComponent(stem)}`" class="col-item-title">
          {{ pageMap[stem]?.title || stem }}
        </router-link>
        <button class="col-remove" @click="removeItem(stem)" title="从合集移除">✕</button>
      </div>
    </div>

    <!-- Add item modal -->
    <div v-if="showAddItem" class="modal-overlay" @click.self="showAddItem = false">
      <div class="modal-box">
        <div class="modal-title">添加到合集</div>
        <input v-model="itemSearch" placeholder="搜索知识页面…" />
        <div class="item-picker">
          <div
            v-for="p in filteredPages" :key="p.stem"
            class="item-option"
            :class="{ selected: collection.items.includes(p.stem) }"
            @click="toggleItem(p.stem)"
          >
            <span class="tag tag-sm" :class="`tag-${p.type}`">{{ p.type }}</span>
            <span class="item-option-title">{{ p.title }}</span>
            <span v-if="collection.items.includes(p.stem)" class="item-check">✓</span>
          </div>
          <div v-if="filteredPages.length === 0" class="item-empty">没有匹配的页面</div>
        </div>
        <div class="modal-actions">
          <button class="btn-primary" @click="showAddItem = false">完成</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const collection = ref(null)
const allPages = ref([])
const showAddItem = ref(false)
const itemSearch = ref('')

const pageMap = computed(() => {
  const map = {}
  allPages.value.forEach(p => { map[p.stem] = p })
  return map
})

const filteredPages = computed(() => {
  const q = itemSearch.value.trim().toLowerCase()
  if (!q) return allPages.value.slice(0, 30)
  return allPages.value.filter(p =>
    p.title.toLowerCase().includes(q) || p.stem.toLowerCase().includes(q)
  ).slice(0, 30)
})

async function loadCollection() {
  const id = route.params.id
  const cols = await fetch('/api/collections').then(r => r.json()).catch(() => [])
  collection.value = cols.find(c => c.id === id) || null
}

async function removeItem(stem) {
  if (!collection.value) return
  await fetch(`/api/collections/${collection.value.id}/items/${encodeURIComponent(stem)}`, { method: 'DELETE' })
  collection.value = { ...collection.value, items: collection.value.items.filter(s => s !== stem) }
}

async function toggleItem(stem) {
  if (!collection.value) return
  if (collection.value.items.includes(stem)) {
    await removeItem(stem)
  } else {
    const res = await fetch(`/api/collections/${collection.value.id}/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stem }),
    }).then(r => r.json())
    collection.value = res
  }
}

async function deleteCollection() {
  if (!collection.value) return
  if (!confirm(`确认删除合集「${collection.value.name}」？`)) return
  await fetch(`/api/collections/${collection.value.id}`, { method: 'DELETE' })
  router.push('/')
}

watch(() => route.params.id, loadCollection)

onMounted(async () => {
  await loadCollection()
  allPages.value = await fetch('/api/wiki').then(r => r.json()).catch(() => [])
})
</script>

<style scoped>
.col-wrap {
  height: 100%; overflow-y: auto;
  padding: 28px 32px;
  display: flex; flex-direction: column; gap: 16px;
}
.col-top-bar { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.col-actions { display: flex; gap: 8px; flex-shrink: 0; }
.danger-btn:hover { border-color: var(--danger) !important; color: var(--danger) !important; }

.col-empty { text-align: center; padding: 60px 20px; color: var(--muted); font-size: 14px; }

.col-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
.col-item { display: flex; flex-direction: column; gap: 8px; position: relative; }
.col-item-meta { }
.col-item-title {
  font-size: 13px; font-weight: 500; color: var(--text); text-decoration: none; line-height: 1.4;
}
.col-item-title:hover { color: var(--accent); }
.col-remove {
  position: absolute; top: 10px; right: 10px;
  background: none; border: none; color: var(--muted);
  font-size: 11px; cursor: pointer; opacity: 0;
  padding: 2px 5px; border-radius: 4px; transition: opacity 0.15s, color 0.15s;
}
.col-item:hover .col-remove { opacity: 1; }
.col-remove:hover { color: var(--danger); background: var(--result-err-bg); }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.25);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal-box {
  background: var(--surface); border-radius: 14px;
  padding: 24px; width: 420px; display: flex; flex-direction: column; gap: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12); max-height: 70vh;
}
.modal-title { font-size: 15px; font-weight: 700; }
.item-picker { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 4px; min-height: 0; max-height: 300px; }
.item-option {
  display: flex; align-items: center; gap: 8px; padding: 8px 10px;
  border-radius: 8px; cursor: pointer; transition: background 0.12s;
}
.item-option:hover { background: var(--surface2); }
.item-option.selected { background: var(--accent-light); }
.tag-sm { font-size: 9px; padding: 1px 6px; }
.item-option-title { flex: 1; font-size: 12px; color: var(--text); }
.item-check { font-size: 12px; color: var(--accent); font-weight: 700; }
.item-empty { font-size: 12px; color: var(--muted); text-align: center; padding: 16px; }
.modal-actions { display: flex; justify-content: flex-end; }
</style>
