<template>
  <div class="wiki-wrap">
    <div v-if="loading" class="center-msg">Loading…</div>
    <div v-else-if="error" class="center-msg error">{{ error }}</div>
    <div v-else class="wiki-layout">
      <article class="wiki-body">
        <div class="wiki-content" v-html="rendered"></div>
      </article>

      <div class="resize-handle" :class="{ active: dragging }" @mousedown="start"></div>

      <aside class="wiki-side" :style="{ width: sideW + 'px', minWidth: sideW + 'px' }">
        <div v-if="page.backlinks.length" class="side-section">
          <div class="side-title">Backlinks</div>
          <router-link
            v-for="b in page.backlinks" :key="b.stem"
            :to="`/wiki/${encodeURIComponent(b.stem)}`"
            class="backlink"
          >← {{ b.label }}</router-link>
        </div>
        <div class="side-section">
          <div class="side-title">Path</div>
          <div class="side-path">{{ page.path }}</div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { marked } from 'marked'
import { useResizer } from '../composables/useResizer.js'

const route = useRoute()
const page = ref(null)
const rendered = ref('')
const loading = ref(true)
const error = ref(null)

const { size: sideW, dragging, start } = useResizer(200, { min: 120, max: 400, inverted: true })

function renderMarkdown(content) {
  const processed = content.replace(
    /\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]/g,
    (_, target, label) => {
      const display = label || target.replace(/-/g, ' ')
      const href = `#/wiki/${encodeURIComponent(target.trim())}`
      return `[${display}](${href})`
    }
  )
  return marked(processed)
}

async function load(path) {
  loading.value = true
  error.value = null
  try {
    const data = await fetch(`/api/wiki/${encodeURIComponent(path)}`).then(r => {
      if (!r.ok) throw new Error('Page not found')
      return r.json()
    })
    page.value = data
    rendered.value = renderMarkdown(data.content)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(() => load(route.params.path))
watch(() => route.params.path, p => p && load(p))
</script>

<style scoped>
.wiki-wrap    { height: 100%; overflow: hidden; display: flex; }
.center-msg   { margin: auto; color: var(--muted); }
.center-msg.error { color: var(--danger); }

.wiki-layout  { display: flex; width: 100%; height: 100%; overflow: hidden; }

.wiki-body {
  flex: 1;
  overflow-y: auto;
  padding: clamp(20px, 3vw, 40px) clamp(20px, 4vw, 48px);
  min-width: 0;
}

.resize-handle {
  width: 4px;
  flex-shrink: 0;
  cursor: col-resize;
  background: var(--border);
  transition: background 0.15s;
}
.resize-handle:hover,
.resize-handle.active { background: var(--accent); opacity: 0.6; }

.wiki-side {
  border-left: none;
  padding: 24px 16px;
  overflow-y: auto;
  flex-shrink: 0;
  background: var(--surface);
}

.side-section { margin-bottom: 20px; }
.side-title {
  font-size: 10px; font-weight: 700;
  letter-spacing: 1px; text-transform: uppercase;
  color: var(--muted); margin-bottom: 8px;
}
.backlink {
  display: block; font-size: clamp(11px, 0.9vw + 7px, 13px);
  color: var(--accent); padding: 3px 0; text-decoration: none;
}
.backlink:hover { text-decoration: underline; }
.side-path { font-size: 11px; color: var(--muted); word-break: break-all; }
</style>

<style>
/* Unscoped: rendered markdown styles */
.wiki-content h1 { font-size: clamp(18px, 1.6vw + 10px, 24px); font-weight: 700; margin-bottom: 18px; }
.wiki-content h2 { font-size: clamp(15px, 1.2vw + 9px, 18px); font-weight: 600; margin: 24px 0 10px; }
.wiki-content h3 { font-size: clamp(13px, 1vw + 8px, 15px); font-weight: 600; margin: 18px 0 8px; color: var(--muted); }
.wiki-content p  { line-height: 1.75; margin-bottom: 12px; color: var(--text); font-size: clamp(13px, 1vw + 8px, 15px); }
.wiki-content ul, .wiki-content ol { padding-left: 20px; margin-bottom: 12px; }
.wiki-content li { line-height: 1.7; color: var(--text); margin-bottom: 3px; font-size: clamp(13px, 1vw + 8px, 15px); }
.wiki-content code {
  background: var(--surface2); border-radius: 4px;
  padding: 1px 5px; font-size: 0.85em; font-family: 'SF Mono', 'Fira Code', monospace;
  color: var(--text);
}
.wiki-content pre {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 8px; padding: 14px; overflow-x: auto; margin-bottom: 14px;
}
.wiki-content pre code { background: none; padding: 0; font-size: clamp(11px, 0.8vw + 8px, 13px); }
.wiki-content a { color: var(--accent); }
.wiki-content strong { color: var(--text); font-weight: 600; }
.wiki-content hr { border: none; border-top: 1px solid var(--border); margin: 20px 0; }
.wiki-content blockquote {
  border-left: 3px solid var(--accent); padding-left: 14px;
  color: var(--muted); margin-bottom: 12px;
}
</style>
