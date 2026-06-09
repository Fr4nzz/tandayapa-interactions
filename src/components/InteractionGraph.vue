<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import cytoscape from 'cytoscape'
import fcose from 'cytoscape-fcose'
import { useGraphStore, GROUP_COLORS, TYPE_COLORS } from '../stores/graph'

cytoscape.use(fcose)

const store = useGraphStore()
const el = ref(null)
let cy = null

function buildElements() {
  const nodes = store.nodes.map((n) => ({
    data: { id: n.id, group: n.group, label: n.id },
  }))
  const edges = store.edges.map((e) => ({
    data: { id: e.id, source: e.source, target: e.target, type: e.type },
  }))
  return [...nodes, ...edges]
}

const stylesheet = [
  {
    selector: 'node',
    style: {
      'background-color': (n) => GROUP_COLORS[n.data('group')] || '#888',
      label: 'data(label)',
      'font-size': 9,
      'font-style': 'italic',
      color: '#1f2937',
      'text-wrap': 'wrap',
      'text-max-width': 90,
      'text-valign': 'bottom',
      'text-margin-y': 2,
      width: 18,
      height: 18,
      'border-width': 1,
      'border-color': '#fff',
    },
  },
  {
    selector: 'edge',
    style: {
      width: 1.6,
      'line-color': (e) => TYPE_COLORS[e.data('type')] || '#bbb',
      'curve-style': 'bezier',
      'target-arrow-shape': (e) =>
        e.data('type') === 'parasiteOf' || e.data('type') === 'dispersesSeedsOf' ? 'triangle' : 'none',
      'target-arrow-color': (e) => TYPE_COLORS[e.data('type')] || '#bbb',
      opacity: 0.7,
    },
  },
  { selector: '.faded', style: { opacity: 0.08, 'text-opacity': 0.05 } },
  { selector: 'node.selected', style: { 'border-width': 3, 'border-color': '#111' } },
  { selector: '.hidden', style: { display: 'none' } },
]

function applyFilter() {
  if (!cy) return
  const active = new Set(store.activeTypes)
  cy.batch(() => {
    cy.edges().forEach((e) => {
      e.toggleClass('hidden', !active.has(e.data('type')))
    })
    cy.nodes().forEach((n) => {
      const visibleEdges = n.connectedEdges().filter((e) => !e.hasClass('hidden'))
      n.toggleClass('hidden', visibleEdges.length === 0)
    })
  })
}

onMounted(() => {
  cy = cytoscape({
    container: el.value,
    elements: buildElements(),
    style: stylesheet,
    layout: { name: 'fcose', quality: 'default', animate: false, nodeSeparation: 90 },
    wheelSensitivity: 0.25,
  })

  cy.on('tap', 'node', (evt) => {
    cy.nodes().removeClass('selected')
    evt.target.addClass('selected')
    store.select(evt.target.id())
  })

  cy.on('tap', (evt) => {
    if (evt.target === cy) {
      cy.nodes().removeClass('selected')
      store.select(null)
    }
  })

  // Obsidian-style: hover a node -> highlight its neighborhood, fade the rest.
  cy.on('mouseover', 'node', (evt) => {
    const n = evt.target
    const keep = n.closedNeighborhood()
    cy.elements().not(keep).addClass('faded')
  })
  cy.on('mouseout', 'node', () => cy.elements().removeClass('faded'))

  applyFilter()
})

watch(() => [...store.activeTypes], applyFilter)

onBeforeUnmount(() => cy && cy.destroy())
</script>

<template>
  <div ref="el" class="w-full h-full"></div>
</template>
