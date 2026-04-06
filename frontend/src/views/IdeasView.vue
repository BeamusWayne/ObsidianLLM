<template>
  <div class="ideas-wrap">
    <div class="page-header">
      <h1 class="page-title">想法</h1>
    </div>

    <!-- Empty state -->
    <div v-if="ideas.length === 0" class="ideas-empty">
      <p>还没有想法</p>
      <p style="font-size:12px;margin-top:4px">点击右下角的按钮记录你的第一个想法</p>
    </div>

    <!-- Ideas grid -->
    <div v-else class="ideas-grid">
      <div v-for="idea in ideas" :key="idea.id" class="idea-card card">
        <div class="idea-content">{{ idea.content }}</div>

        <!-- AI expanded -->
        <div v-if="idea.ai_expanded" class="idea-expanded">
          <div class="expanded-label">🦇 Echo 的展开</div>
          <div class="expanded-text">{{ idea.ai_expanded }}</div>
        </div>

        <!-- Expanding spinner -->
        <div v-if="expandingId === idea.id" class="idea-expanding">
          <span class="spinner"></span> Echo 正在思考…
        </div>

        <div class="idea-footer">
          <span class="idea-time">{{ formatTime(idea.created_at) }}</span>
          <div class="idea-actions">
            <button
              v-if="!idea.ai_expanded"
              class="idea-btn"
              :disabled="expandingId === idea.id"
              @click="expandIdea(idea)"
              title="AI 展开"
            >🦇 展开</button>
            <button class="idea-btn idea-del" @click="deleteIdea(idea.id)" title="删除">✕</button>
          </div>
        </div>
      </div>
    </div>

    <!-- FAB: Add new idea -->
    <button class="fab" @click="showAdd = true" title="记录新想法">+</button>

    <!-- Add idea modal -->
    <div v-if="showAdd" class="modal-overlay" @click.self="showAdd = false">
      <div class="modal-box">
        <div class="modal-title">记录想法</div>
        <textarea
          v-model="newContent"
          placeholder="写下你的想法…"
          rows="4"
          style="resize:vertical"
          autofocus
        ></textarea>
        <div class="modal-actions">
          <button class="btn-primary" :disabled="!newContent.trim() || saving" @click="createIdea">
            <span v-if="saving" class="spinner"></span>
            <span v-else>保存</span>
          </button>
          <button class="btn-ghost" @click="showAdd = false">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const ideas = ref([])
const showAdd = ref(false)
const newContent = ref('')
const saving = ref(false)
const expandingId = ref(null)

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

async function loadIdeas() {
  ideas.value = await fetch('/api/ideas').then(r => r.json()).catch(() => [])
}

async function createIdea() {
  if (!newContent.value.trim()) return
  saving.value = true
  try {
    const idea = await fetch('/api/ideas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: newContent.value.trim() }),
    }).then(r => r.json())
    ideas.value = [idea, ...ideas.value]
    newContent.value = ''
    showAdd.value = false
  } finally {
    saving.value = false
  }
}

async function deleteIdea(id) {
  await fetch(`/api/ideas/${id}`, { method: 'DELETE' })
  ideas.value = ideas.value.filter(i => i.id !== id)
}

async function expandIdea(idea) {
  expandingId.value = idea.id
  try {
    const res = await fetch(`/api/ideas/${idea.id}/expand`, { method: 'POST' }).then(r => r.json())
    ideas.value = ideas.value.map(i => i.id === idea.id ? res : i)
  } finally {
    expandingId.value = null
  }
}

onMounted(loadIdeas)
</script>

<style scoped>
.ideas-wrap {
  height: 100%; overflow-y: auto;
  padding: 28px 32px;
  display: flex; flex-direction: column; gap: 16px;
  position: relative;
}
.ideas-empty {
  text-align: center; padding: 60px 20px; color: var(--muted); font-size: 14px;
}
.ideas-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
  align-items: start;
}
.idea-card { display: flex; flex-direction: column; gap: 10px; }
.idea-content { font-size: 14px; line-height: 1.6; color: var(--text); white-space: pre-wrap; }

.idea-expanded {
  background: var(--accent-light);
  border-radius: 8px; padding: 10px 12px;
  border-left: 3px solid var(--accent);
}
.expanded-label { font-size: 11px; font-weight: 600; color: var(--accent); margin-bottom: 5px; }
.expanded-text { font-size: 12px; line-height: 1.7; color: var(--text); white-space: pre-wrap; }

.idea-expanding { font-size: 12px; color: var(--muted); display: flex; align-items: center; gap: 6px; }

.idea-footer {
  display: flex; align-items: center; justify-content: space-between;
  padding-top: 6px; border-top: 1px solid var(--border);
}
.idea-time { font-size: 11px; color: var(--muted); }
.idea-actions { display: flex; gap: 6px; }
.idea-btn {
  font-size: 11px; padding: 3px 9px; border-radius: 6px;
  border: 1px solid var(--border); background: transparent;
  color: var(--muted); cursor: pointer; transition: all 0.15s;
}
.idea-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.idea-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.idea-del:hover { border-color: var(--danger) !important; color: var(--danger) !important; }

/* FAB */
.fab {
  position: fixed; bottom: 28px; right: 28px;
  width: 48px; height: 48px; border-radius: 50%;
  background: var(--accent); color: #fff;
  border: none; font-size: 24px; font-weight: 300;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  cursor: pointer; transition: filter 0.15s;
  z-index: 50;
}
.fab:hover { filter: brightness(1.1); }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.25);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal-box {
  background: var(--surface); border-radius: 14px;
  padding: 24px; width: 400px; display: flex; flex-direction: column; gap: 14px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12);
}
.modal-title { font-size: 15px; font-weight: 700; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; }
</style>
