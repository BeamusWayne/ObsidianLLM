<template>
  <div class="graph-wrap">
    <!-- Toolbar -->
    <div class="toolbar">
      <input v-model="search" placeholder="搜索节点…" class="search" />
      <div class="legend">
        <span class="tag tag-concept">concept</span>
        <span class="tag tag-entity">entity</span>
        <span class="tag tag-topic">topic</span>
      </div>
      <span class="count">{{ nodes.length }} 页 · {{ links.length }} 链接</span>
    </div>

    <svg ref="svgRef" class="graph-svg" @click.self="selected = null"></svg>

    <!-- Node info panel -->
    <div v-if="selected" class="info-panel">
      <div class="info-title">{{ selected.label }}</div>
      <div class="info-badges">
        <span :class="`tag tag-${selected.type}`">{{ selected.type }}</span>
        <span v-if="selected.pinned" class="pin-tag">📌 已固定</span>
      </div>
      <div class="info-stat">{{ selected.linkCount }} 条入链</div>
      <router-link v-if="!selected.isOrphan"
        :to="`/wiki/${encodeURIComponent(selected.id)}`" class="btn-primary btn-sm">
        打开 →
      </router-link>
      <button v-if="selected.pinned" class="btn-unpin" @click="unpinNode(selected)">
        解除固定
      </button>
    </div>

    <!-- Forces control panel -->
    <div class="forces-panel" :class="{ open: showForces }">
      <button class="forces-toggle" @click="showForces = !showForces">
        <span class="forces-icon">⚙</span>
        <span>图形力学</span>
        <span class="chevron">{{ showForces ? '▾' : '▸' }}</span>
      </button>
      <div class="forces-body" v-show="showForces">
        <div class="force-row">
          <label>节点间距</label>
          <input type="range" v-model.number="forces.linkDistance" min="20" max="300" step="10" @input="applyForces" />
          <span class="force-val">{{ forces.linkDistance }}</span>
        </div>
        <div class="force-row">
          <label>斥力强度</label>
          <input type="range" v-model.number="forces.chargeStrength" min="-400" max="-10" step="10" @input="applyForces" />
          <span class="force-val">{{ forces.chargeStrength }}</span>
        </div>
        <div class="force-row">
          <label>连线强度</label>
          <input type="range" v-model.number="forces.linkStrength" min="0.05" max="2" step="0.05" @input="applyForces" />
          <span class="force-val">{{ forces.linkStrength.toFixed(2) }}</span>
        </div>
        <div class="force-row">
          <label>中心引力</label>
          <input type="range" v-model.number="forces.centerStrength" min="0" max="1" step="0.05" @input="applyForces" />
          <span class="force-val">{{ forces.centerStrength.toFixed(2) }}</span>
        </div>
        <div class="force-row">
          <label>分区引力</label>
          <input type="range" v-model.number="forces.clusterStrength" min="0" max="0.4" step="0.01" @input="applyForces" />
          <span class="force-val">{{ forces.clusterStrength.toFixed(2) }}</span>
        </div>
        <div class="force-row">
          <label>Hub 向心</label>
          <input type="range" v-model.number="forces.radialStrength" min="0" max="0.3" step="0.01" @input="applyForces" />
          <span class="force-val">{{ forces.radialStrength.toFixed(2) }}</span>
        </div>
        <div class="force-row">
          <label>节点大小</label>
          <input type="range" v-model.number="forces.nodeScale" min="0.4" max="3" step="0.1" @input="applyNodeScale" />
          <span class="force-val">{{ forces.nodeScale.toFixed(1) }}×</span>
        </div>
        <div class="forces-actions">
          <button class="reset-btn" @click="resetForces">恢复默认</button>
          <button class="reset-btn" @click="unpinAll">全部解除固定</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as d3 from 'd3'

const router   = useRouter()
const svgRef   = ref(null)
const search   = ref('')
const selected = ref(null)
const nodes    = ref([])
const links    = ref([])
const showForces = ref(false)

// ── Type cluster anchors (fraction of SVG dimensions) ─────────────────────────
const TYPE_ANCHORS = {
  concept: { ax: 0.32, ay: 0.30 },
  entity:  { ax: 0.68, ay: 0.30 },
  topic:   { ax: 0.50, ay: 0.72 },
  unknown: { ax: 0.50, ay: 0.50 },
}
const ORPHAN_ANCHOR = { ax: 0.88, ay: 0.84 }

const ZONE_META = [
  { type: 'concept', label: 'Concepts' },
  { type: 'entity',  label: 'Entities'  },
  { type: 'topic',   label: 'Topics'    },
]

// ── Default force values ──────────────────────────────────────────────────────
const DEFAULT_FORCES = {
  linkDistance:    80,
  chargeStrength: -80,
  linkStrength:    0.7,
  centerStrength:  0.12,
  clusterStrength: 0.10,
  radialStrength:  0.05,
  nodeScale:       1,
}
const forces = reactive({ ...DEFAULT_FORCES })
function resetForces() { Object.assign(forces, DEFAULT_FORCES); applyForces(); applyNodeScale() }

let simulation  = null
let nodeCircles = null
let nodeLabels  = null
let linkLines   = null
let svgWidth    = 800
let svgHeight   = 600

const colors = { concept: '#4a9eff', entity: '#4ade80', topic: '#fb923c', unknown: '#888' }

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(async () => {
  const data = await fetch('/api/graph').then(r => r.json())
  nodes.value = data.nodes
  links.value = data.links
  render(data.nodes, data.links)
})

onUnmounted(() => simulation?.stop())

watch(search, val => {
  if (!nodeCircles) return
  const q = val.toLowerCase()
  nodeCircles.attr('opacity', d => {
    if (d.isOrphan) return !q || d.label.toLowerCase().includes(q) ? 0.45 : 0.08
    return !q || d.label.toLowerCase().includes(q) ? 1 : 0.10
  })
  nodeLabels?.attr('opacity', d => !q || d.label.toLowerCase().includes(q) ? 1 : 0.08)
})

// ── Force controls ────────────────────────────────────────────────────────────
function applyForces() {
  if (!simulation) return
  const maxLinks = Math.max(...simulation.nodes().map(d => d.linkCount || 0), 1)
  simulation
    .force('link', d3.forceLink(simulation.force('link').links())
      .id(d => d.id)
      .distance(forces.linkDistance)
      .strength(forces.linkStrength))
    .force('charge', d3.forceManyBody()
      .strength(d => d.isOrphan ? 0 : forces.chargeStrength))
    .force('center', d3.forceCenter(svgWidth / 2, svgHeight / 2)
      .strength(forces.centerStrength))
    .force('cluster-x', d3.forceX(d =>
      svgWidth  * (TYPE_ANCHORS[d.type]?.ax ?? 0.5)
    ).strength(d => d.isOrphan ? 0 : forces.clusterStrength))
    .force('cluster-y', d3.forceY(d =>
      svgHeight * (TYPE_ANCHORS[d.type]?.ay ?? 0.5)
    ).strength(d => d.isOrphan ? 0 : forces.clusterStrength))
    .force('radial', d3.forceRadial(
      d => Math.max(20, 260 * (1 - (d.linkCount || 0) / maxLinks)),
      svgWidth / 2, svgHeight / 2
    ).strength(d => d.isOrphan ? 0 : forces.radialStrength))
    .alpha(0.4).restart()
}

function applyNodeScale() {
  if (!nodeCircles) return
  nodeCircles.attr('r', d => nodeR(d))
  nodeLabels?.attr('dx', d => nodeR(d) + 5)
}

function nodeR(d) {
  return (4 + Math.sqrt((d.linkCount || 0) + 1) * 2.5) * forces.nodeScale
}

// ── Pin / unpin ───────────────────────────────────────────────────────────────
function updateNodeStyles() {
  if (!nodeCircles) return
  nodeCircles
    .attr('stroke', d =>
      d.pinned   ? 'var(--accent)' :
      d.isOrphan ? 'transparent'   : 'var(--graph-stroke)')
    .attr('stroke-width', d => d.pinned ? 2.5 : 1.5)
}

function unpinNode(d) {
  if (d.isOrphan) return
  d.fx = null; d.fy = null; d.pinned = false
  simulation?.alpha(0.2).restart()
  updateNodeStyles()
  if (selected.value === d) selected.value = { ...d }
}

function unpinAll() {
  if (!simulation) return
  simulation.nodes().forEach(d => {
    if (d.pinned && !d.isOrphan) { d.fx = null; d.fy = null; d.pinned = false }
  })
  simulation.alpha(0.3).restart()
  updateNodeStyles()
  if (selected.value?.pinned) selected.value = { ...selected.value, pinned: false }
}

// ── Main render ───────────────────────────────────────────────────────────────
function render(rawNodes, rawLinks) {
  const svg = d3.select(svgRef.value)
  svgWidth  = svgRef.value.clientWidth  || 800
  svgHeight = svgRef.value.clientHeight || 600

  svg.selectAll('*').remove()

  const g = svg.append('g')
  svg.call(
    d3.zoom().scaleExtent([0.05, 8]).on('zoom', e => g.attr('transform', e.transform))
  )

  const nodeData = rawNodes.map(n => ({ ...n }))
  const linkData = rawLinks.map(l => ({ ...l }))
  const maxLinks = Math.max(...nodeData.map(d => d.linkCount || 0), 1)

  const orphans   = nodeData.filter(d => (d.linkCount || 0) === 0)
  const connected = nodeData.filter(d => (d.linkCount || 0) > 0)

  // ── A: Pre-seed positions near type anchors ──────────────────────────────
  connected.forEach(d => {
    const anc = TYPE_ANCHORS[d.type] || TYPE_ANCHORS.unknown
    d.x = svgWidth  * anc.ax + (Math.random() - 0.5) * 100
    d.y = svgHeight * anc.ay + (Math.random() - 0.5) * 100
  })

  // ── D: Pin orphans to a tidy grid in the corner ──────────────────────────
  const oCols = Math.max(3, Math.ceil(Math.sqrt(orphans.length * 1.8)))
  orphans.forEach((d, i) => {
    const col = i % oCols
    const row = Math.floor(i / oCols)
    d.x = svgWidth  * ORPHAN_ANCHOR.ax + (col - oCols / 2) * 22
    d.y = svgHeight * ORPHAN_ANCHOR.ay + row * 22
    d.fx = d.x; d.fy = d.y
    d.isOrphan = true
  })

  // ── Zone watermark labels ────────────────────────────────────────────────
  const bgLabels = g.append('g').attr('class', 'zone-labels')
  ZONE_META.forEach(({ type, label }) => {
    const anc = TYPE_ANCHORS[type]
    bgLabels.append('text')
      .attr('class', `zone-label zone-label-${type}`)
      .attr('x', svgWidth  * anc.ax)
      .attr('y', svgHeight * anc.ay - 52)
      .attr('text-anchor', 'middle')
      .text(label)
  })

  // ── Orphan zone indicator ────────────────────────────────────────────────
  if (orphans.length > 0) {
    const zW = oCols * 22 + 36
    const zH = Math.ceil(orphans.length / oCols) * 22 + 36
    g.append('rect')
      .attr('class', 'orphan-zone')
      .attr('x', svgWidth  * ORPHAN_ANCHOR.ax - zW / 2)
      .attr('y', svgHeight * ORPHAN_ANCHOR.ay - 26)
      .attr('width', zW).attr('height', zH)
      .attr('rx', 8)
    g.append('text')
      .attr('class', 'orphan-zone-label')
      .attr('x', svgWidth  * ORPHAN_ANCHOR.ax)
      .attr('y', svgHeight * ORPHAN_ANCHOR.ay - 12)
      .attr('text-anchor', 'middle')
      .text(`未链接 (${orphans.length})`)
  }

  // ── Simulation ───────────────────────────────────────────────────────────
  simulation = d3.forceSimulation(nodeData)
    .force('link', d3.forceLink(linkData).id(d => d.id)
      .distance(forces.linkDistance).strength(forces.linkStrength))
    .force('charge', d3.forceManyBody()
      .strength(d => d.isOrphan ? 0 : forces.chargeStrength))
    .force('center', d3.forceCenter(svgWidth / 2, svgHeight / 2)
      .strength(forces.centerStrength))
    .force('collision', d3.forceCollide()
      .radius(d => nodeR(d) + (d.isOrphan ? 1 : 5)))
    // A: type clustering
    .force('cluster-x', d3.forceX(d =>
      svgWidth  * (TYPE_ANCHORS[d.type]?.ax ?? 0.5)
    ).strength(d => d.isOrphan ? 0 : forces.clusterStrength))
    .force('cluster-y', d3.forceY(d =>
      svgHeight * (TYPE_ANCHORS[d.type]?.ay ?? 0.5)
    ).strength(d => d.isOrphan ? 0 : forces.clusterStrength))
    // B: hub-spoke radial (high linkCount → closer to center)
    .force('radial', d3.forceRadial(
      d => Math.max(20, 260 * (1 - (d.linkCount || 0) / maxLinks)),
      svgWidth / 2, svgHeight / 2
    ).strength(d => d.isOrphan ? 0 : forces.radialStrength))

  // ── Links ────────────────────────────────────────────────────────────────
  linkLines = g.append('g')
    .selectAll('line').data(linkData).join('line')
    .attr('class', 'graph-link')

  // ── Node circles ─────────────────────────────────────────────────────────
  nodeCircles = g.append('g')
    .selectAll('circle').data(nodeData).join('circle')
    .attr('r', d => nodeR(d))
    .attr('fill', d => colors[d.type] || colors.unknown)
    .attr('opacity', d => d.isOrphan ? 0.40 : 1)
    .attr('stroke', 'var(--graph-stroke)')
    .attr('stroke-width', 1.5)
    .attr('cursor', 'pointer')
    .on('click', (evt, d) => { evt.stopPropagation(); selected.value = d })
    .on('dblclick', (evt, d) => {
      evt.stopPropagation()
      if (!d.isOrphan) router.push(`/wiki/${encodeURIComponent(d.id)}`)
    })
    // F: sticky drag — keep fx/fy on drag end
    .call(
      d3.drag()
        .on('start', (e, d) => {
          if (!e.active) simulation.alphaTarget(0.3).restart()
          d.fx = d.x; d.fy = d.y
        })
        .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y })
        .on('end',  (e, d) => {
          if (!e.active) simulation.alphaTarget(0)
          if (!d.isOrphan) {
            d.pinned = true
            updateNodeStyles()
            if (selected.value?.id === d.id) selected.value = d
          }
        })
    )

  // ── Labels ───────────────────────────────────────────────────────────────
  nodeLabels = g.append('g')
    .selectAll('text').data(nodeData).join('text')
    .text(d => d.label)
    .attr('class', d => d.isOrphan ? 'graph-label graph-label-dim' : 'graph-label')
    .attr('dx', d => nodeR(d) + 5)
    .attr('dy', 4)

  // ── Tick ─────────────────────────────────────────────────────────────────
  simulation.on('tick', () => {
    linkLines
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
    nodeCircles.attr('cx', d => d.x).attr('cy', d => d.y)
    nodeLabels.attr('x',  d => d.x).attr('y',  d => d.y)
  })
}
</script>

<style scoped>
.graph-wrap { position: relative; width: 100%; height: 100%; overflow: hidden; }
.graph-svg  { width: 100%; height: 100%; display: block; }

/* Toolbar */
.toolbar {
  position: absolute; top: 14px; left: 14px;
  display: flex; align-items: center; gap: 10px; z-index: 10;
}
.search { width: 180px; background: var(--surface); box-shadow: 0 1px 6px rgba(0,0,0,0.12); }
.count  { color: var(--muted); font-size: 12px; }
.legend { display: flex; gap: 6px; }

/* Info panel */
.info-panel {
  position: absolute; right: 16px; top: 14px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; padding: 14px 16px; min-width: 180px;
  display: flex; flex-direction: column; gap: 8px; z-index: 10;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}
.info-title  { font-weight: 600; font-size: 14px; }
.info-badges { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.info-stat   { color: var(--muted); font-size: 12px; }
.btn-sm      { padding: 5px 12px; font-size: 12px; border-radius: 6px; text-align: center; }
.pin-tag {
  font-size: 10px; padding: 1px 6px; border-radius: 4px; font-weight: 600;
  background: color-mix(in srgb, var(--accent) 14%, transparent);
  color: var(--accent);
}
.btn-unpin {
  font-size: 11px; padding: 4px 10px; border-radius: 6px; cursor: pointer;
  border: 1px solid var(--border); background: transparent; color: var(--muted);
  transition: color 0.15s, border-color 0.15s;
}
.btn-unpin:hover { color: var(--accent); border-color: var(--accent); }

/* Forces panel */
.forces-panel {
  position: absolute; bottom: 16px; left: 16px; z-index: 10;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; overflow: hidden; min-width: 230px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}
.forces-toggle {
  display: flex; align-items: center; gap: 7px;
  width: 100%; padding: 9px 13px; background: none; border: none;
  cursor: pointer; font-size: 12px; font-weight: 600;
  color: var(--text); text-align: left; transition: background 0.15s;
}
.forces-toggle:hover { background: var(--surface2); }
.forces-icon { font-size: 13px; }
.chevron { margin-left: auto; color: var(--muted); }

.forces-body {
  padding: 8px 13px 12px; border-top: 1px solid var(--border);
  display: flex; flex-direction: column; gap: 8px;
}
.force-row {
  display: grid; grid-template-columns: 68px 1fr 40px;
  align-items: center; gap: 8px;
}
.force-row label { font-size: 11px; color: var(--muted); white-space: nowrap; }
.force-row input[type=range] {
  -webkit-appearance: none; height: 3px;
  background: var(--border); border-radius: 2px; cursor: pointer; outline: none;
}
.force-row input[type=range]::-webkit-slider-thumb {
  -webkit-appearance: none; width: 12px; height: 12px; border-radius: 50%;
  background: var(--accent); cursor: pointer;
  box-shadow: 0 1px 4px rgba(0,0,0,0.2);
}
.force-val { font-size: 10px; color: var(--accent); text-align: right; }

.forces-actions { display: flex; gap: 6px; margin-top: 2px; flex-wrap: wrap; }
.reset-btn {
  font-size: 11px; color: var(--muted);
  background: none; border: 1px solid var(--border); border-radius: 5px;
  padding: 3px 8px; cursor: pointer; transition: color 0.15s, border-color 0.15s;
}
.reset-btn:hover { color: var(--accent); border-color: var(--accent); }

/* D3 global elements */
:global(.graph-link) {
  stroke: var(--border); stroke-opacity: 0.65; stroke-width: 1px;
}
:global(.graph-label) {
  fill: var(--muted); font-size: 10px;
  pointer-events: none; user-select: none;
}
:global(.graph-label-dim) {
  fill: var(--muted); font-size: 9px; opacity: 0.55;
  pointer-events: none; user-select: none;
}

/* Zone watermark labels */
:global(.zone-label) {
  font-size: 15px; font-weight: 700; letter-spacing: 1px;
  text-transform: uppercase; pointer-events: none; user-select: none;
  opacity: 0.07;
}
:global(.zone-label-concept) { fill: #4a9eff; }
:global(.zone-label-entity)  { fill: #4ade80; }
:global(.zone-label-topic)   { fill: #fb923c; }

/* Orphan zone */
:global(.orphan-zone) {
  fill: var(--surface2); stroke: var(--border);
  stroke-width: 1px; stroke-dasharray: 4 3; opacity: 0.6;
}
:global(.orphan-zone-label) {
  font-size: 9px; font-weight: 600; letter-spacing: 0.5px;
  fill: var(--muted); opacity: 0.6; pointer-events: none; user-select: none;
  text-transform: uppercase;
}
</style>
