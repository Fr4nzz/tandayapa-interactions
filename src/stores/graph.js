import { defineStore } from 'pinia'
import data from '../data/interactions.json'

// One vivid color per taxon group (tuned for a dark graph canvas).
export const GROUP_COLORS = {
  hummingbird: '#ff5d8f',
  bat: '#8b7cf6',
  bird: '#f59e0b',
  plant: '#34d399',
  parasite: '#ef4444',
  insect: '#facc15',
  mammal: '#fb923c',
}

export const GROUP_LABELS = {
  hummingbird: 'Hummingbirds',
  bat: 'Bats',
  bird: 'Other birds',
  plant: 'Plants',
  parasite: 'Parasites',
  insect: 'Insects',
  mammal: 'Mammals',
}

// One color per interaction type.
export const TYPE_COLORS = {
  visitsFlowersOf: '#94a3b8',
  pollinates: '#34d399',
  dispersesSeedsOf: '#f59e0b',
  eatsFruitPulpOf: '#fbbf24',
  nectarRobs: '#fb7185',
  parasiteOf: '#f87171',
}

export const TYPE_LABELS = {
  visitsFlowersOf: 'visits flowers of',
  pollinates: 'pollinates',
  dispersesSeedsOf: 'disperses seeds of',
  eatsFruitPulpOf: 'eats fruit pulp of',
  nectarRobs: 'nectar-robs',
  parasiteOf: 'parasite of',
}

const SCOPE_LABELS = {
  'Tandayapa core': 'Tandayapa core',
  'nearby reserve': 'Nearby reserve',
  'regional NW Ecuador': 'Regional NW Ecuador',
}

function uniq(arr) {
  return [...new Set(arr)]
}

export const useGraphStore = defineStore('graph', {
  state: () => ({
    records: data.records,
    meta: data._meta,
    activeTypes: uniq(data.records.map((r) => r.type)),
    activeGroups: uniq(data.records.flatMap((r) => [r.sourceGroup, r.targetGroup])),
    activeScopes: uniq(data.records.map((r) => r.scope)),
    search: '',
    selectedId: null,
    hoveredId: null,
  }),

  getters: {
    allTypes: (s) => uniq(s.records.map((r) => r.type)),
    allGroups: (s) => uniq(s.records.flatMap((r) => [r.sourceGroup, r.targetGroup])),
    allScopes: (s) => uniq(s.records.map((r) => r.scope)),
    scopeLabel: () => (sc) => SCOPE_LABELS[sc] || sc,

    typeCounts(s) {
      const c = {}
      for (const r of s.records) c[r.type] = (c[r.type] || 0) + 1
      return c
    },

    groupCounts() {
      const c = {}
      for (const n of this.nodes) c[n.group] = (c[n.group] || 0) + 1
      return c
    },

    // Unique taxa with their group and interaction degree.
    nodes(s) {
      const map = new Map()
      const deg = {}
      for (const r of s.records) {
        if (!map.has(r.source)) map.set(r.source, { id: r.source, group: r.sourceGroup })
        if (!map.has(r.target)) map.set(r.target, { id: r.target, group: r.targetGroup })
        deg[r.source] = (deg[r.source] || 0) + 1
        deg[r.target] = (deg[r.target] || 0) + 1
      }
      return [...map.values()].map((n) => ({ ...n, degree: deg[n.id] || 0 }))
    },

    edges(s) {
      return s.records.map((r, i) => ({
        id: `e${i}`,
        source: r.source,
        target: r.target,
        type: r.type,
        locality: r.locality,
        scope: r.scope,
        ref: r.ref,
      }))
    },

    stats() {
      return {
        taxa: this.nodes.length,
        interactions: this.records.length,
        sources: uniq(this.records.map((r) => r.ref)).length,
        types: this.allTypes.length,
      }
    },

    selectedNode(s) {
      if (!s.selectedId) return null
      return this.nodes.find((n) => n.id === s.selectedId) || null
    },

    selectedRecords(s) {
      if (!s.selectedId) return []
      return s.records.filter((r) => r.source === s.selectedId || r.target === s.selectedId)
    },

    searchMatches(s) {
      const q = s.search.trim().toLowerCase()
      if (!q) return []
      return this.nodes
        .filter((n) => n.id.toLowerCase().includes(q))
        .sort((a, b) => b.degree - a.degree)
        .slice(0, 8)
    },
  },

  actions: {
    toggle(list, value) {
      const arr = this[list]
      const i = arr.indexOf(value)
      if (i === -1) arr.push(value)
      else arr.splice(i, 1)
    },
    toggleType(t) { this.toggle('activeTypes', t) },
    toggleGroup(g) { this.toggle('activeGroups', g) },
    toggleScope(sc) { this.toggle('activeScopes', sc) },
    select(id) { this.selectedId = id },
    setSearch(v) { this.search = v },

    isEdgeVisible(rec) {
      return (
        this.activeTypes.includes(rec.type) &&
        this.activeGroups.includes(rec.sourceGroup) &&
        this.activeGroups.includes(rec.targetGroup) &&
        this.activeScopes.includes(rec.scope)
      )
    },
  },
})
