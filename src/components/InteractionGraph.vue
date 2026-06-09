<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import cytoscape from 'cytoscape'
import fcose from 'cytoscape-fcose'
import { useGraphStore, GROUP_COLORS, TYPE_COLORS } from '../stores/graph'
import { useThemeStore } from '../stores/theme'

cytoscape.use(fcose)

const props = defineProps({ layout: { type: String, default: 'fcose' } })
const store = useGraphStore()
const theme = useThemeStore()
const el = ref(null)
let cy = null

// With the EPHI anchor merged the graph is large; only label nodes on hover/selection
// to avoid an unreadable hairball.
const big = store.nodes.length > 120

function cssVar(name, fallback) {
  if (typeof window === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

function buildElements() {
  const nodes = store.nodes.map((n) => ({
    data: { id: n.id, group: n.group, label: n.id, degree: n.degree },
  }))
  const edges = store.edges.map((e) => ({
    data: { id: e.id, source: e.source, target: e.target, type: e.type },
  }))
  return [...nodes, ...edges]
}

const dashed = ['nectarRobs']
const arrowed = ['parasiteOf', 'dispersesSeedsOf']

const stylesheet = [
  {
    selector: 'node',
    style: {
      'background-color': (n) => GROUP_COLORS[n.data('group')] || '#9aa0a6',
      label: 'data(label)',
      'font-size': 9,
      'font-style': 'italic',
      'font-family': 'Newsreader, Georgia, serif',
      color: cssVar('--node-label', '#e5e7eb'),
      'text-outline-color': cssVar('--node-label-outline', '#0b1020'),
      'text-outline-width': 2,
      'text-wrap': 'wrap',
      'text-max-width': 110,
      'text-valign': 'bottom',
      'text-margin-y': 3,
      'text-opacity': big ? 0 : 1,
      width: (n) => 14 + Math.min(n.data('degree') * 2.4, 30),
      height: (n) => 14 + Math.min(n.data('degree') * 2.4, 30),
      'border-width': 1.5,
      'border-color': 'rgba(255,255,255,0.55)',
      'transition-property': 'opacity, border-width, width, height',
      'transition-duration': '150ms',
    },
  },
  {
    selector: 'edge',
    style: {
      width: 1.5,
      'line-color': (e) => TYPE_COLORS[e.data('type')] || '#64748b',
      'line-style': (e) => (dashed.includes(e.data('type')) ? 'dashed' : 'solid'),
      'curve-style': 'bezier',
      'target-arrow-shape': (e) => (arrowed.includes(e.data('type')) ? 'triangle' : 'none'),
      'target-arrow-color': (e) => TYPE_COLORS[e.data('type')] || '#64748b',
      'arrow-scale': 0.8,
      opacity: 0.55,
    },
  },
  { selector: 'node.selected', style: { 'border-width': 4, 'border-color': '#ffffff', 'text-opacity': 1 } },
  { selector: '.dim', style: { opacity: 0.07, 'text-opacity': 0.04 } },
  { selector: 'edge.highlight', style: { opacity: 0.95, width: 2.6 } },
  { selector: 'node.highlight', style: { 'border-color': '#ffffff', 'border-width': 3, 'text-opacity': 1 } },
  { selector: '.hidden', style: { display: 'none' } },
]

function layoutOpts(name) {
  if (name === 'fcose')
    return {
      name: 'fcose',
      quality: big ? 'default' : 'proof',
      animate: !big,
      animationDuration: 600,
      nodeSeparation: big ? 75 : 110,
      idealEdgeLength: big ? 70 : 95,
      nodeRepulsion: big ? 9000 : 7000,
      numIter: big ? 1500 : 2500,
    }
  if (name === 'concentric')
    return { name: 'concentric', animate: true, concentric: (n) => n.degree(), levelWidth: () => 2, minNodeSpacing: 26 }
  if (name === 'circle') return { name: 'circle', animate: true, spacingFactor: 1.1 }
  if (name === 'breadthfirst') return { name: 'breadthfirst', animate: true, spacingFactor: 1.0, circle: false }
  return { name: 'grid', animate: true }
}

function applyFilter() {
  if (!cy) return
  cy.batch(() => {
    store.edges.forEach((e, i) => {
      const rec = store.records[i]
      const vis = store.isEdgeVisible(rec)
      cy.getElementById(`e${i}`).toggleClass('hidden', !vis)
    })
    cy.nodes().forEach((n) => {
      const visEdges = n.connectedEdges().filter((e) => !e.hasClass('hidden'))
      n.toggleClass('hidden', visEdges.length === 0)
    })
  })
}

function highlightNeighborhood(node) {
  const keep = node.closedNeighborhood()
  cy.elements().not(keep).addClass('dim')
  keep.edges().addClass('highlight')
  keep.nodes().addClass('highlight')
}
function clearHighlight() {
  cy.elements().removeClass('dim highlight')
}

function focusNode(id) {
  if (!cy) return
  cy.nodes().removeClass('selected')
  if (!id) return
  const n = cy.getElementById(id)
  if (n.empty()) return
  n.addClass('selected')
  cy.animate({ center: { eles: n }, zoom: Math.max(cy.zoom(), 1.3) }, { duration: 400 })
}

function reTheme() {
  if (!cy) return
  cy.style()
    .selector('node')
    .style({
      color: cssVar('--node-label', '#e5e7eb'),
      'text-outline-color': cssVar('--node-label-outline', '#0b1020'),
    })
    .update()
}

function exportPng() {
  if (!cy) return null
  return cy.png({ full: true, scale: 2, bg: cssVar('--graph-bg-3', '#0b1020') })
}
function runLayout(name) {
  if (cy) cy.layout(layoutOpts(name)).run()
}
function fit() {
  if (cy) cy.animate({ fit: { padding: 40 } }, { duration: 400 })
}
defineExpose({ exportPng, runLayout, fit })

onMounted(() => {
  cy = cytoscape({
    container: el.value,
    elements: buildElements(),
    style: stylesheet,
    layout: layoutOpts(props.layout),
    wheelSensitivity: 0.25,
    minZoom: 0.2,
    maxZoom: 4,
    // Nodes are not draggable, so a touch/drag that starts on a node pans the
    // canvas instead of grabbing the node — essential for mobile sliding.
    autoungrabify: true,
    boxSelectionEnabled: false,
  })

  cy.on('tap', 'node', (evt) => {
    store.select(evt.target.id())
    focusNode(evt.target.id())
  })
  cy.on('tap', (evt) => {
    if (evt.target === cy) store.select(null)
  })
  cy.on('mouseover', 'node', (evt) => highlightNeighborhood(evt.target))
  cy.on('mouseout', 'node', clearHighlight)

  applyFilter()
})

watch(() => [store.activeTypes.length, store.activeGroups.length, store.activeScopes.length], applyFilter)
watch(() => store.selectedId, (id) => focusNode(id))
watch(() => props.layout, (l) => runLayout(l))
watch(() => theme.mode, () => reTheme())

onBeforeUnmount(() => cy && cy.destroy())
</script>

<template>
  <div ref="el" class="graph-canvas"></div>
</template>

<style scoped>
.graph-canvas {
  width: 100%;
  height: 100%;
  transition: background 0.3s ease;
  background:
    radial-gradient(1200px 600px at 30% 10%, var(--graph-bg-1) 0%, transparent 60%),
    radial-gradient(900px 500px at 80% 90%, var(--graph-bg-2) 0%, transparent 55%),
    linear-gradient(160deg, var(--graph-bg-3) 0%, var(--bg) 100%);
}
</style>
