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
      <span :class="`tag tag-${selected.type}`">{{ selected.type }}</span>
      <div class="info-stat">{{ selected.linkCount }} 条入链</div>
      <router-link :to="`/wiki/${encodeURIComponent(selected.id)}`" class="btn-primary btn-sm">
        打开 →
      </router-link>
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
          <input type="range" v-model.number="forces.linkDistance" min="20" max="400" step="10" @input="applyForces" />
          <span class="force-val">{{ forces.linkDistance }}</span>
        </div>
        <div class="force-row">
          <label>斥力强度</label>
          <input type="range" v-model.number="forces.chargeStrength" min="-600" max="-10" step="10" @input="applyForces" />
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
          <label>节点大小</label>
          <input type="range" v-model.number="forces.nodeScale" min="0.4" max="3" step="0.1" @input="applyNodeScale" />
          <span class="force-val">{{ forces.nodeScale.toFixed(1) }}×</span>
        </div>
        <button class="reset-btn" @click="resetForces">恢复默认</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as d3 from 'd3'

const router = useRouter()
const svgRef  = ref(null)
const search  = ref('')
const selected = ref(null)
const nodes    = ref([])
const links    = ref([])
const showForces = ref(false)

const DEFAULT_FORCES = { linkDistance: 90, chargeStrength: -180, linkStrength: 0.5, centerStrength: 0.1, nodeScale: 1 }
const forces = reactive({ ...DEFAULT_FORCES })
function resetForces() { Object.assign(forces, DEFAULT_FORCES); applyForces(); applyNodeScale() }

let simulation   = null
let nodeCircles  = null
let nodeLabels   = null
let linkLines    = null
let svgWidth     = 800
let svgHeight    = 600

const colors = { concept: '#4a9eff', entity: '#4ade80', topic: '#fb923c', unknown: '#777' }

onMounted(async () => {
  const data = await fetch('/api/graph').then(r => r.json())
  nodes.value = data.nodes
  links.value = data.links
  render(data.nodes, data.links)
})

onUnmounted(() => simulation?.stop())

watch(search, val => {
  if (!nodeCircles) return
  nodeCircles.attr('opacity', d => !val || d.label.toLowerCase().includes(val.toLowerCase()) ? 1 : 0.12)
  nodeLabels?.attr('opacity', d => !val || d.label.toLowerCase().includes(val.toLowerCase()) ? 1 : 0.1)
})

function applyForces() {
  if (!simulation) return
  simulation
    .force('link', d3.forceLink(simulation.force('link').links())
      .id(d => d.id)
      .distance(forces.linkDistance)
      .strength(forces.linkStrength))
    .force('charge', d3.forceManyBody().strength(forces.chargeStrength))
    .force('center', d3.forceCenter(svgWidth / 2, svgHeight / 2).strength(forces.centerStrength))
    .alpha(0.4).restart()
}

function applyNodeScale() {
  if (!nodeCircles) return
  nodeCircles.attr('r', d => nodeR(d))
  nodeLabels?.attr('dx', d => nodeR(d) + 5)
}

function render(rawNodes, rawLinks) {
  const svg = d3.select(svgRef.value)
  svgWidth  = svgRef.value.clientWidth
  svgHeight = svgRef.value.clientHeight

  svg.selectAll('*').remove()

  const g = svg.append('g')
  svg.call(
    d3.zoom().scaleExtent([0.05, 8]).on('zoom', e => g.attr('transform', e.transform))
  )

  const nodeData = rawNodes.map(n => ({ ...n }))
  const linkData = rawLinks.map(l => ({ ...l }))

  simulation = d3.forceSimulation(nodeData)
    .force('link', d3.forceLink(linkData).id(d => d.id)
      .distance(forces.linkDistance).strength(forces.linkStrength))
    .force('charge', d3.forceManyBody().strength(forces.chargeStrength))
    .force('center', d3.forceCenter(svgWidth / 2, svgHeight / 2).strength(forces.centerStrength))
    .force('collision', d3.forceCollide().radius(d => nodeR(d) + 6))

  linkLines = g.append('g')
    .selectAll('line')
    .data(linkData)
    .join('line')
    .attr('class', 'graph-link')

  nodeCircles = g.append('g')
    .selectAll('circle')
    .data(nodeData)
    .join('circle')
    .attr('r', d => nodeR(d))
    .attr('fill', d => colors[d.type] || colors.unknown)
    .attr('stroke', 'var(--graph-stroke)')
    .attr('stroke-width', 1.5)
    .attr('cursor', 'pointer')
    .on('click', (evt, d) => { evt.stopPropagation(); selected.value = d })
    .on('dblclick', (_, d) => router.push(`/wiki/${encodeURIComponent(d.id)}`))
    .call(
      d3.drag()
        .on('start', (e, d) => { if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
        .on('drag',  (e, d) => { d.fx = e.x; d.fy = e.y })
        .on('end',   (e, d) => { if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null })
    )

  nodeLabels = g.append('g')
    .selectAll('text')
    .data(nodeData)
    .join('text')
    .text(d => d.label)
    .attr('class', 'graph-label')
    .attr('dx', d => nodeR(d) + 5)
    .attr('dy', 4)

  simulation.on('tick', () => {
    linkLines
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
    nodeCircles.attr('cx', d => d.x).attr('cy', d => d.y)
    nodeLabels.attr('x', d => d.x).attr('y', d => d.y)
  })
}

function nodeR(d) {
  return (5 + Math.sqrt((d.linkCount || 0) + 1) * 2.5) * forces.nodeScale
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
.info-title { font-weight: 600; font-size: 14px; }
.info-stat  { color: var(--muted); font-size: 12px; }
.btn-sm { padding: 5px 12px; font-size: 12px; border-radius: 6px; text-align: center; }

/* Forces panel */
.forces-panel {
  position: absolute; bottom: 16px; left: 16px; z-index: 10;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; overflow: hidden; min-width: 220px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}
.forces-toggle {
  display: flex; align-items: center; gap: 7px;
  width: 100%; padding: 9px 13px; background: none; border: none;
  cursor: pointer; font-size: 12px; font-weight: 600;
  color: var(--text); text-align: left;
  transition: background 0.15s;
}
.forces-toggle:hover { background: var(--surface2); }
.forces-icon { font-size: 13px; }
.chevron { margin-left: auto; color: var(--muted); }

.forces-body {
  padding: 8px 13px 12px;
  border-top: 1px solid var(--border);
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

.reset-btn {
  margin-top: 2px; font-size: 11px; color: var(--muted);
  background: none; border: 1px solid var(--border); border-radius: 5px;
  padding: 3px 8px; cursor: pointer; transition: color 0.15s, border-color 0.15s;
  align-self: flex-start;
}
.reset-btn:hover { color: var(--accent); border-color: var(--accent); }

:global(.graph-link)  { stroke: var(--border); stroke-opacity: 0.7; stroke-width: 1px; }
:global(.graph-label) {
  fill: var(--muted); font-size: 10px;
  pointer-events: none; user-select: none;
}
</style>
