<template>
  <div class="graph-wrap">
    <svg ref="svgRef" class="graph-svg" @click.self="selected = null"></svg>

    <!-- Minimal top bar -->
    <div class="topbar">
      <div class="legend">
        <span class="leg-dot" style="background:#4a9eff"></span><span class="leg-label">concept</span>
        <span class="leg-dot" style="background:#4ade80"></span><span class="leg-label">entity</span>
        <span class="leg-dot" style="background:#fb923c"></span><span class="leg-label">topic</span>
      </div>
      <span class="node-count">{{ visibleNodeCount }} 页 · {{ visibleLinkCount }} 链接</span>
    </div>

    <!-- Node info card -->
    <Transition name="fade">
      <div v-if="selected" class="info-card" @click.stop>
        <button class="info-close" @click="selected = null">✕</button>
        <div class="info-title">{{ selected.label }}</div>
        <span :class="`tag tag-${selected.type}`">{{ selected.type }}</span>
        <div class="info-stat">{{ selected.linkCount }} 条入链</div>
        <div class="info-actions">
          <router-link v-if="!selected.isOrphan"
            :to="`/wiki/${encodeURIComponent(selected.id)}`" class="info-link">
            打开页面 →
          </router-link>
          <button v-if="selected.pinned" class="info-unpin" @click="unpinNode(selected)">
            解除固定
          </button>
        </div>
      </div>
    </Transition>

    <!-- Filter panel (Obsidian-style) -->
    <div class="filter-panel" :class="{ open: panelOpen }">
      <button class="panel-toggle" @click="panelOpen = !panelOpen">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
          <path d="M1 3h14v1.5L9.5 10v5l-3-1.5V10L1 4.5V3z"/>
        </svg>
        <span>Filters</span>
        <span class="panel-chevron">{{ panelOpen ? '▾' : '▸' }}</span>
      </button>

      <div v-show="panelOpen" class="panel-body">

        <!-- ── Filters ── -->
        <div class="psection">
          <div class="psection-head" @click="sec.filters = !sec.filters">
            <span class="pchev">{{ sec.filters ? '▾' : '▸' }}</span>
            <strong>Filters</strong>
            <button class="icon-action" @click.stop="resetAll" title="重置">↺</button>
          </div>
          <div v-show="sec.filters" class="psection-body">
            <div class="search-field">
              <svg class="search-icon" viewBox="0 0 20 20" fill="currentColor" width="13" height="13">
                <path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clip-rule="evenodd"/>
              </svg>
              <input v-model="search" placeholder="Search files…" class="search-input" />
            </div>
            <div class="toggle-row">
              <span>Orphans</span>
              <div class="os-toggle" :class="{ on: display.showOrphans }" @click="toggleOrphans"></div>
            </div>
          </div>
        </div>

        <!-- ── Display ── -->
        <div class="psection">
          <div class="psection-head" @click="sec.display = !sec.display">
            <span class="pchev">{{ sec.display ? '▾' : '▸' }}</span>
            <strong>Display</strong>
          </div>
          <div v-show="sec.display" class="psection-body">
            <div class="slider-row">
              <label>Text fade threshold</label>
              <input type="range" v-model.number="display.fadeThreshold"
                min="0" max="12" step="0.5" @input="updateLabelVisibility" />
            </div>
            <div class="slider-row">
              <label>Node size</label>
              <input type="range" v-model.number="display.nodeScale"
                min="0.3" max="3" step="0.1" @input="applyNodeScale" />
            </div>
            <div class="slider-row">
              <label>Link thickness</label>
              <input type="range" v-model.number="display.linkThickness"
                min="0.2" max="4" step="0.1" @input="applyLinkStyle" />
            </div>
            <button class="animate-btn" @click="animate">Animate</button>
          </div>
        </div>

        <!-- ── Forces ── -->
        <div class="psection">
          <div class="psection-head" @click="sec.forces = !sec.forces">
            <span class="pchev">{{ sec.forces ? '▾' : '▸' }}</span>
            <strong>Forces</strong>
          </div>
          <div v-show="sec.forces" class="psection-body">
            <div class="slider-row">
              <label>Center force</label>
              <input type="range" v-model.number="forces.centerStrength"
                min="0" max="1" step="0.02" @input="applyForces" />
            </div>
            <div class="slider-row">
              <label>Repel force</label>
              <input type="range" v-model.number="forces.chargeStrength"
                min="-400" max="-5" step="5" @input="applyForces" />
            </div>
            <div class="slider-row">
              <label>Link force</label>
              <input type="range" v-model.number="forces.linkStrength"
                min="0" max="1" step="0.02" @input="applyForces" />
            </div>
            <div class="slider-row">
              <label>Link distance</label>
              <input type="range" v-model.number="forces.linkDistance"
                min="10" max="250" step="5" @input="applyForces" />
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as d3 from 'd3'

const router   = useRouter()
const svgRef   = ref(null)
const search   = ref('')
const selected = ref(null)
const panelOpen = ref(true)

// Panel sections open state
const sec = reactive({ filters: true, display: true, forces: true })

// All node/link data
const allNodes = ref([])
const allLinks = ref([])

const visibleNodeCount = computed(() =>
  allNodes.value.filter(n => display.showOrphans || (n.linkCount || 0) > 0).length
)
const visibleLinkCount = computed(() => allLinks.value.length)

// ── Display settings ──────────────────────────────────────────────────────────
const display = reactive({
  showOrphans:   true,
  fadeThreshold: 4,
  nodeScale:     1,
  linkThickness: 0.8,
})

// ── Force settings ────────────────────────────────────────────────────────────
const forces = reactive({
  centerStrength: 0.28,
  chargeStrength: -45,
  linkStrength:   0.5,
  linkDistance:   55,
})

const DEFAULT_DISPLAY = { showOrphans: true, fadeThreshold: 4, nodeScale: 1, linkThickness: 0.8 }
const DEFAULT_FORCES  = { centerStrength: 0.28, chargeStrength: -45, linkStrength: 0.5, linkDistance: 55 }

function resetAll() {
  Object.assign(display, DEFAULT_DISPLAY)
  Object.assign(forces,  DEFAULT_FORCES)
  applyForces(); applyNodeScale(); applyLinkStyle(); updateLabelVisibility()
  if (!display.showOrphans) toggleOrphans()
}

// ── D3 state ──────────────────────────────────────────────────────────────────
let simulation  = null
let nodeCircles = null
let nodeLabels  = null
let linkLines   = null
let svgW = 800, svgH = 600
let currentScale = 1  // zoom k

const NODE_COLORS = { concept: '#4a9eff', entity: '#4ade80', topic: '#fb923c', unknown: '#94a3b8' }

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(async () => {
  const data = await fetch('/api/graph').then(r => r.json())
  allNodes.value = data.nodes
  allLinks.value = data.links
  render(data.nodes, data.links)
})
onUnmounted(() => simulation?.stop())

// ── Search filter ─────────────────────────────────────────────────────────────
watch(search, updateSearch)
function updateSearch() {
  if (!nodeCircles) return
  const q = search.value.toLowerCase()
  nodeCircles.attr('opacity', d => {
    if (!display.showOrphans && d.isOrphan) return 0
    if (!q) return d.isOrphan ? 0.5 : 1
    return d.label.toLowerCase().includes(q) ? 1 : 0.06
  })
  updateLabelVisibility()
}

// ── Orphan toggle ─────────────────────────────────────────────────────────────
function toggleOrphans() {
  display.showOrphans = !display.showOrphans
  if (!nodeCircles) return
  nodeCircles.attr('opacity', d => {
    if (!display.showOrphans && d.isOrphan) return 0
    return d.isOrphan ? 0.5 : 1
  })
  nodeLabels?.attr('display', d => {
    if (!display.showOrphans && d.isOrphan) return 'none'
    return null
  })
  updateLabelVisibility()
}

// ── Label visibility (text fade threshold × zoom) ─────────────────────────────
function updateLabelVisibility() {
  if (!nodeLabels) return
  const q = search.value.toLowerCase()
  nodeLabels.attr('display', d => {
    if (!display.showOrphans && d.isOrphan) return 'none'
    if (q && !d.label.toLowerCase().includes(q)) return 'none'
    // Show label when (zoom * nodeRadius) > threshold
    const effective = currentScale * nodeR(d)
    return effective >= display.fadeThreshold ? null : 'none'
  })
}

// ── Display appliers ──────────────────────────────────────────────────────────
function nodeR(d) {
  return (3 + Math.sqrt((d.linkCount || 0) + 1) * 2) * display.nodeScale
}

function applyNodeScale() {
  if (!nodeCircles) return
  nodeCircles.attr('r', d => nodeR(d))
  nodeLabels?.attr('dx', d => nodeR(d) + 4)
  updateLabelVisibility()
}

function applyLinkStyle() {
  linkLines?.attr('stroke-width', display.linkThickness)
}

function animate() {
  simulation?.alpha(0.5).restart()
}

// ── Force applier ─────────────────────────────────────────────────────────────
function applyForces() {
  if (!simulation) return
  simulation
    .force('link', d3.forceLink(simulation.force('link').links())
      .id(d => d.id)
      .distance(forces.linkDistance)
      .strength(forces.linkStrength))
    .force('charge', d3.forceManyBody().strength(forces.chargeStrength))
    .force('center', d3.forceCenter(svgW / 2, svgH / 2).strength(forces.centerStrength))
    .alpha(0.4).restart()
}

// ── Pin / unpin ───────────────────────────────────────────────────────────────
function refreshPinStyle() {
  if (!nodeCircles) return
  nodeCircles
    .attr('stroke', d => d.pinned ? 'var(--accent)' : 'none')
    .attr('stroke-width', d => d.pinned ? 1.5 : 0)
}

function unpinNode(d) {
  if (d.isOrphan) return
  d.fx = null; d.fy = null; d.pinned = false
  simulation?.alpha(0.15).restart()
  refreshPinStyle()
  if (selected.value?.id === d.id) selected.value = { ...d, pinned: false }
}

// ── Main render ───────────────────────────────────────────────────────────────
function render(rawNodes, rawLinks) {
  const svg = d3.select(svgRef.value)
  svgW = svgRef.value.clientWidth  || 800
  svgH = svgRef.value.clientHeight || 600

  svg.selectAll('*').remove()

  const g = svg.append('g')
  svg.call(
    d3.zoom().scaleExtent([0.03, 12]).on('zoom', e => {
      g.attr('transform', e.transform)
      currentScale = e.transform.k
      updateLabelVisibility()
    })
  )

  const nodeData = rawNodes.map(n => ({ ...n }))
  const linkData = rawLinks.map(l => ({ ...l }))

  // Mark orphans
  nodeData.forEach(d => { d.isOrphan = (d.linkCount || 0) === 0 })

  // ── Simulation: pure organic physics, no type anchors ──────────────────
  simulation = d3.forceSimulation(nodeData)
    .force('link', d3.forceLink(linkData).id(d => d.id)
      .distance(forces.linkDistance)
      .strength(forces.linkStrength))
    .force('charge', d3.forceManyBody()
      .strength(d => d.isOrphan ? -8 : forces.chargeStrength))
    .force('center', d3.forceCenter(svgW / 2, svgH / 2)
      .strength(forces.centerStrength))
    .force('collision', d3.forceCollide().radius(d => nodeR(d) + 1.5))

  // ── Links ──────────────────────────────────────────────────────────────
  linkLines = g.append('g')
    .selectAll('line').data(linkData).join('line')
    .attr('class', 'graph-link')
    .attr('stroke-width', display.linkThickness)

  // ── Nodes ──────────────────────────────────────────────────────────────
  nodeCircles = g.append('g')
    .selectAll('circle').data(nodeData).join('circle')
    .attr('r', d => nodeR(d))
    .attr('fill', d => NODE_COLORS[d.type] || NODE_COLORS.unknown)
    .attr('opacity', d => d.isOrphan ? 0.5 : 1)
    .attr('stroke', 'none')
    .attr('cursor', 'pointer')
    .on('click', (evt, d) => { evt.stopPropagation(); selected.value = d })
    .on('dblclick', (evt, d) => {
      evt.stopPropagation()
      if (!d.isOrphan) router.push(`/wiki/${encodeURIComponent(d.id)}`)
    })
    .call(d3.drag()
      .on('start', (e, d) => {
        if (!e.active) simulation.alphaTarget(0.3).restart()
        d.fx = d.x; d.fy = d.y
      })
      .on('drag',  (e, d) => { d.fx = e.x; d.fy = e.y })
      .on('end',   (e, d) => {
        if (!e.active) simulation.alphaTarget(0)
        if (!d.isOrphan) { d.pinned = true; refreshPinStyle() }
      })
    )

  // ── Labels ─────────────────────────────────────────────────────────────
  nodeLabels = g.append('g')
    .selectAll('text').data(nodeData).join('text')
    .text(d => d.label)
    .attr('class', 'graph-label')
    .attr('dx', d => nodeR(d) + 4)
    .attr('dy', '0.35em')
    .attr('display', 'none')  // start hidden; updateLabelVisibility reveals them

  // ── Tick ───────────────────────────────────────────────────────────────
  simulation.on('tick', () => {
    linkLines
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
    nodeCircles.attr('cx', d => d.x).attr('cy', d => d.y)
    nodeLabels.attr('x', d => d.x).attr('y', d => d.y)
  })

  // First-pass label update after alpha settles a bit
  setTimeout(updateLabelVisibility, 1200)
}
</script>

<style scoped>
.graph-wrap { position: relative; width: 100%; height: 100%; overflow: hidden; background: var(--bg); }
.graph-svg  { width: 100%; height: 100%; display: block; }

/* Top bar */
.topbar {
  position: absolute; top: 14px; left: 14px;
  display: flex; align-items: center; gap: 14px; z-index: 10;
  pointer-events: none;
}
.legend { display: flex; align-items: center; gap: 8px; }
.leg-dot   { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.leg-label { font-size: 11px; color: var(--muted); }
.node-count { font-size: 11px; color: var(--muted); }

/* Node info card */
.info-card {
  position: absolute; top: 14px; right: 16px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; padding: 14px 16px 12px; min-width: 170px;
  display: flex; flex-direction: column; gap: 7px; z-index: 20;
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
}
.info-close {
  position: absolute; top: 8px; right: 10px;
  background: none; border: none; cursor: pointer;
  color: var(--muted); font-size: 12px; padding: 2px 4px;
}
.info-close:hover { color: var(--text); }
.info-title { font-weight: 600; font-size: 13px; padding-right: 16px; }
.info-stat  { font-size: 11px; color: var(--muted); }
.info-actions { display: flex; flex-direction: column; gap: 5px; margin-top: 2px; }
.info-link {
  font-size: 12px; color: var(--accent); text-decoration: none;
  transition: opacity 0.15s;
}
.info-link:hover { opacity: 0.75; }
.info-unpin {
  font-size: 11px; padding: 3px 8px; border-radius: 5px;
  border: 1px solid var(--border); background: transparent;
  cursor: pointer; color: var(--muted); text-align: left;
  transition: color 0.15s, border-color 0.15s;
}
.info-unpin:hover { color: var(--accent); border-color: var(--accent); }

/* Filter panel */
.filter-panel {
  position: absolute; bottom: 16px; left: 16px; z-index: 20;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; overflow: hidden; width: 224px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
}
.panel-toggle {
  display: flex; align-items: center; gap: 7px;
  width: 100%; padding: 9px 12px; background: none; border: none;
  cursor: pointer; font-size: 12px; font-weight: 600; color: var(--text);
  text-align: left; transition: background 0.15s;
}
.panel-toggle:hover { background: var(--surface2); }
.panel-toggle svg { color: var(--muted); flex-shrink: 0; }
.panel-chevron { margin-left: auto; color: var(--muted); font-size: 10px; }

.panel-body { border-top: 1px solid var(--border); }

.psection { border-bottom: 1px solid var(--border); }
.psection:last-child { border-bottom: none; }

.psection-head {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 12px; cursor: pointer; user-select: none;
  transition: background 0.15s; font-size: 12px;
}
.psection-head:hover { background: var(--surface2); }
.pchev { font-size: 9px; color: var(--muted); width: 10px; }
.psection-head strong { font-size: 12px; font-weight: 600; flex: 1; }
.icon-action {
  background: none; border: none; cursor: pointer; color: var(--muted);
  font-size: 13px; padding: 1px 4px; border-radius: 3px;
  transition: color 0.15s; margin-left: auto;
}
.icon-action:hover { color: var(--text); }

.psection-body {
  padding: 6px 12px 10px; display: flex; flex-direction: column; gap: 9px;
}

/* Search field */
.search-field {
  display: flex; align-items: center; gap: 7px;
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 6px; padding: 5px 9px;
}
.search-icon { color: var(--muted); flex-shrink: 0; }
.search-input {
  flex: 1; border: none; background: transparent; outline: none;
  font-size: 12px; color: var(--text);
}
.search-input::placeholder { color: var(--muted); }

/* Obsidian-style toggle */
.toggle-row {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 12px; color: var(--text);
}
.os-toggle {
  width: 34px; height: 18px; border-radius: 9px; background: var(--border);
  position: relative; cursor: pointer; transition: background 0.2s; flex-shrink: 0;
}
.os-toggle.on { background: var(--accent); }
.os-toggle::after {
  content: ''; position: absolute; top: 2px; left: 2px;
  width: 14px; height: 14px; border-radius: 50%; background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2); transition: transform 0.2s;
}
.os-toggle.on::after { transform: translateX(16px); }

/* Sliders (Obsidian pill style) */
.slider-row { display: flex; flex-direction: column; gap: 5px; }
.slider-row label { font-size: 11px; color: var(--muted); }
.slider-row input[type=range] {
  -webkit-appearance: none; width: 100%; height: 4px;
  background: var(--border); border-radius: 2px; outline: none; cursor: pointer;
}
.slider-row input[type=range]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 20px; height: 20px; border-radius: 10px;
  background: var(--surface); border: 1px solid var(--border);
  box-shadow: 0 1px 4px rgba(0,0,0,0.15); cursor: pointer;
}

/* Animate button */
.animate-btn {
  width: 100%; padding: 8px; border-radius: 7px; border: none;
  background: var(--accent); color: #fff; font-size: 12px;
  font-weight: 600; cursor: pointer; transition: opacity 0.15s; margin-top: 2px;
}
.animate-btn:hover { opacity: 0.85; }

/* Transitions */
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* D3 SVG globals */
:global(.graph-link) {
  stroke: var(--graph-link);
  stroke-opacity: 1;
}
:global(.graph-label) {
  fill: var(--text); font-size: 10px;
  pointer-events: none; user-select: none;
}
</style>
