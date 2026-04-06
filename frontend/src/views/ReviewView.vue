<template>
  <div class="review-wrap">
    <div class="review-top-bar">
      <div class="page-header">
        <h1 class="page-title">回顾</h1>
        <p class="page-subtitle">AI 从你的知识库中发现主题和洞察</p>
      </div>
      <button class="btn-primary" :disabled="generatingWeekly" @click="generateWeekly">
        <span v-if="generatingWeekly" class="spinner"></span>
        <span v-else>生成本周回顾</span>
      </button>
    </div>

    <!-- Topic research -->
    <div class="card topic-card">
      <div class="topic-header">
        <span class="topic-icon">◆</span>
        <span class="topic-label">主题研究</span>
      </div>
      <div class="topic-input-row">
        <input v-model="topicInput" placeholder='输入一个主题，如 "AI Agent"、"产品设计"…' @keyup.enter="researchTopic" />
        <button class="btn-primary btn-sm" :disabled="generatingTopic || !topicInput.trim()" @click="researchTopic">
          <span v-if="generatingTopic" class="spinner"></span>
          <span v-else>分析</span>
        </button>
      </div>
    </div>

    <!-- Past reviews -->
    <div v-if="reviews.length === 0 && !generatingWeekly && !generatingTopic" class="review-empty">
      <p>还没有回顾</p>
      <p style="font-size:12px;margin-top:4px">收藏一些内容后，生成你的第一份知识回顾。</p>
      <button class="btn-primary" style="margin-top:14px" @click="generateWeekly">生成回顾</button>
    </div>

    <!-- Generating spinner -->
    <div v-if="generatingWeekly || generatingTopic" class="review-generating card">
      <span class="spinner"></span>
      <span>{{ generatingWeekly ? 'Echo 正在分析本周知识…' : `Echo 正在研究主题：${currentTopic}` }}</span>
    </div>

    <!-- Review list -->
    <div v-if="reviews.length" class="review-list">
      <div v-for="r in reviews" :key="r.id" class="review-item card" :class="{ expanded: expandedId === r.id }">
        <div class="review-item-header" @click="expandedId = expandedId === r.id ? null : r.id">
          <span class="review-type-badge" :class="r.type">{{ r.type === 'weekly' ? '周回顾' : '主题研究' }}</span>
          <span class="review-item-title">{{ r.title }}</span>
          <span class="review-item-date">{{ formatDate(r.created_at) }}</span>
          <span class="review-chevron">{{ expandedId === r.id ? '▲' : '▼' }}</span>
        </div>
        <div v-if="expandedId === r.id" class="review-content" v-html="renderMarkdown(r.content)"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { marked } from 'marked'

const reviews = ref([])
const topicInput = ref('')
const currentTopic = ref('')
const generatingWeekly = ref(false)
const generatingTopic = ref(false)
const expandedId = ref(null)

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function renderMarkdown(text) {
  return marked(text || '')
}

async function loadReviews() {
  reviews.value = await fetch('/api/review').then(r => r.json()).catch(() => [])
}

async function generateWeekly() {
  generatingWeekly.value = true
  try {
    const r = await fetch('/api/review/weekly', { method: 'POST' }).then(res => res.json())
    reviews.value = [r, ...reviews.value]
    expandedId.value = r.id
  } catch {
    alert('生成失败，请检查 LLM 设置')
  } finally {
    generatingWeekly.value = false
  }
}

async function researchTopic() {
  if (!topicInput.value.trim() || generatingTopic.value) return
  currentTopic.value = topicInput.value.trim()
  generatingTopic.value = true
  try {
    const r = await fetch('/api/review/topic', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic: currentTopic.value }),
    }).then(res => res.json())
    reviews.value = [r, ...reviews.value]
    expandedId.value = r.id
    topicInput.value = ''
  } catch {
    alert('分析失败，请检查 LLM 设置')
  } finally {
    generatingTopic.value = false
  }
}

onMounted(loadReviews)
</script>

<style scoped>
.review-wrap {
  height: 100%; overflow-y: auto;
  padding: 28px 32px;
  display: flex; flex-direction: column; gap: 16px;
  max-width: 800px;
}
.review-top-bar {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 16px;
}
.review-top-bar .page-header { flex: 1; }

.topic-card { display: flex; flex-direction: column; gap: 10px; }
.topic-header { display: flex; align-items: center; gap: 6px; }
.topic-icon { color: var(--accent); font-size: 12px; }
.topic-label { font-size: 13px; font-weight: 600; }
.topic-input-row { display: flex; gap: 8px; }
.topic-input-row input { flex: 1; }

.review-empty { text-align: center; padding: 40px 20px; color: var(--muted); font-size: 14px; }

.review-generating {
  display: flex; align-items: center; gap: 10px;
  font-size: 13px; color: var(--muted); background: var(--accent-light);
}

.review-list { display: flex; flex-direction: column; gap: 10px; }
.review-item { }
.review-item-header {
  display: flex; align-items: center; gap: 10px; cursor: pointer;
  user-select: none;
}
.review-type-badge {
  font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 10px;
  flex-shrink: 0;
}
.review-type-badge.weekly { background: var(--accent-light); color: var(--accent); }
.review-type-badge.topic { background: var(--tag-concept-bg); color: var(--concept); }
.review-item-title { flex: 1; font-size: 13px; font-weight: 500; }
.review-item-date { font-size: 11px; color: var(--muted); flex-shrink: 0; }
.review-chevron { font-size: 10px; color: var(--muted); flex-shrink: 0; }

.review-content {
  margin-top: 12px; padding-top: 12px;
  border-top: 1px solid var(--border);
  font-size: 13px; line-height: 1.75; color: var(--text);
}
</style>

<style>
.review-content h1,.review-content h2,.review-content h3 { font-weight: 600; margin: 14px 0 8px; }
.review-content h1 { font-size: 16px; }
.review-content h2 { font-size: 14px; }
.review-content h3 { font-size: 13px; color: var(--muted); }
.review-content p { margin-bottom: 10px; }
.review-content ul,.review-content ol { padding-left: 18px; margin-bottom: 10px; }
.review-content li { margin-bottom: 4px; }
.review-content strong { font-weight: 600; }
.review-content code { background: var(--surface2); border-radius: 3px; padding: 1px 4px; font-size: 0.85em; }
</style>
