import { defineStore } from 'pinia'
import data from '../data/sample-interactions.json'

// Visual config: one color per taxon group and per interaction type.
export const GROUP_COLORS = {
  hummingbird: '#e85d75',
  bat: '#6c5ce7',
  plant: '#2e9e5b',
  bird: '#e0892e',
  parasite: '#c0392b',
}

export const TYPE_COLORS = {
  visitsFlowersOf: '#9aa0a6',
  pollinates: '#2e9e5b',
  dispersesSeedsOf: '#e0892e',
  eatsFruitPulpOf: '#caa15a',
  parasiteOf: '#c0392b',
}

export const useGraphStore = defineStore('graph', {
  state: () => ({
    records: data.records,
    activeTypes: [...new Set(data.records.map((r) => r.type))],
    selectedId: null,
  }),

  getters: {
    allTypes: (s) => [...new Set(s.records.map((r) => r.type))],

    // Unique nodes derived from records (a taxon may appear as source or target).
    nodes(s) {
      const map = new Map()
      for (const r of s.records) {
        if (!map.has(r.source)) map.set(r.source, { id: r.source, group: r.sourceGroup })
        if (!map.has(r.target)) map.set(r.target, { id: r.target, group: r.targetGroup })
      }
      return [...map.values()]
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

    selectedRecords(s) {
      if (!s.selectedId) return []
      return s.records.filter((r) => r.source === s.selectedId || r.target === s.selectedId)
    },

    selectedGroup(s) {
      if (!s.selectedId) return null
      const n = this.nodes.find((x) => x.id === s.selectedId)
      return n ? n.group : null
    },
  },

  actions: {
    toggleType(t) {
      const i = this.activeTypes.indexOf(t)
      if (i === -1) this.activeTypes.push(t)
      else this.activeTypes.splice(i, 1)
    },
    select(id) {
      this.selectedId = id
    },
  },
})
