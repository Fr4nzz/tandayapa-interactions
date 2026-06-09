<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import cytoscape from 'cytoscape'
import fcose from 'cytoscape-fcose'
import { useGraphStore, GROUP_COLORS, TYPE_COLORS } from '../stores/graph'

cytoscape.use(fcose)

const props = defineProps({ layout: { type: String, default: 'fcose' } })
const store = useGraphStore()
const el = ref(null)
let cy = null

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
      color: '#e5e7eb',
      'text-outline-color': '#0b1020',
      'text-outline-width': 2,
      'text-wrap': 'wrap',
      'text-max-width': 110,
      'text-valign': 'bottom',
      'text-margin-y': 3,
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
  { selector: 'node.selected', style: { 'border-width': 4, 'border-color': '#ffffff' } },
  { selector: '.dim', style: { opacity: 0.07, 'text-opacity': 0.04 } },
  { selector: 'edge.highlight', style: { opacity: 0.95, width: 2.6 } },
  { selector: 'node.highlight', style: { 'border-color': '#ffffff', 'border-width': 3 } },
  { selector: '.hidden', style: { display: 'none' } },
]

function layoutOpts(name) {
  if (name === 'fcose')
    return { name: 'fcose', quality: 'proof', animate: true, animationDuration: 600, nodeSeparation: 110, idealEdgeLength: 95, nodeRepulsion: 7000 }
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

function exportPng() {
  if (!cy) return null
  return cy.png({ full: true, scale: 2, bg: '#0b1020' })
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

onBeforeUnmount(() => cy && cy.destroy())
</script>

<template>
  <div ref="el" class="graph-canvas"></div>
</template>

<style scoped>
.graph-canvas {
  width: 100%;
  height: 100%;
  background:
    radial-gradient(1200px 600px at 30% 10%, #15203a 0%, transparent 60%),
    radial-gradient(900px 500px at 80% 90%, #161a33 0%, transparent 55%),
    linear-gradient(160deg, #0b1020 0%, #0a0e1c 100%);
}
</style>
