<script setup>
import { onMounted, onBeforeUnmount, ref, watch, computed } from 'vue'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useGraphStore, GROUP_COLORS } from '../stores/graph'
import { useThemeStore } from '../stores/theme'

const store = useGraphStore()
const theme = useThemeStore()
const el = ref(null)
let map = null
let occ = {}
const loaded = ref(false)

const BASEMAPS = {
  dark: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
  light: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
}

const groupOf = computed(() => {
  const m = {}
  for (const n of store.nodes) m[n.id] = n.group
  return m
})

// Build a GeoJSON FeatureCollection: selected taxon's points, or all taxa if none selected.
function buildGeoJSON() {
  const feats = []
  const names = store.selectedId && occ[store.selectedId] ? [store.selectedId] : Object.keys(occ)
  for (const name of names) {
    const entry = occ[name]
    if (!entry || !entry.points) continue
    const group = groupOf.value[name] || 'plant'
    for (const p of entry.points) {
      if (p.lat == null || p.lng == null) continue
      feats.push({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [p.lng, p.lat] },
        properties: { name, group, color: GROUP_COLORS[group] || '#888', year: p.year || '', basis: p.basis || '' },
      })
    }
  }
  return { type: 'FeatureCollection', features: feats }
}

const SRC = 'occ-src'
function addData(fit = true) {
  if (!map || !map.isStyleLoaded()) return
  const geo = buildGeoJSON()
  if (map.getSource(SRC)) {
    map.getSource(SRC).setData(geo)
  } else {
    map.addSource(SRC, { type: 'geojson', data: geo, cluster: true, clusterMaxZoom: 12, clusterRadius: 45 })
    map.addLayer({
      id: 'clusters', type: 'circle', source: SRC, filter: ['has', 'point_count'],
      paint: {
        'circle-color': ['step', ['get', 'point_count'], '#10b981', 20, '#06b6d4', 100, '#f59e0b', 500, '#ef4444'],
        'circle-radius': ['step', ['get', 'point_count'], 12, 20, 16, 100, 22, 500, 30],
        'circle-opacity': 0.85, 'circle-stroke-width': 1.5, 'circle-stroke-color': 'rgba(255,255,255,0.7)',
      },
    })
    map.addLayer({
      id: 'cluster-count', type: 'symbol', source: SRC, filter: ['has', 'point_count'],
      layout: { 'text-field': ['get', 'point_count_abbreviated'], 'text-size': 11 },
      paint: { 'text-color': '#fff' },
    })
    map.addLayer({
      id: 'pts', type: 'circle', source: SRC, filter: ['!', ['has', 'point_count']],
      paint: {
        'circle-color': ['get', 'color'], 'circle-radius': 5,
        'circle-stroke-width': 1, 'circle-stroke-color': 'rgba(255,255,255,0.8)', 'circle-opacity': 0.9,
      },
    })
    map.on('click', 'clusters', (e) => {
      const f = map.queryRenderedFeatures(e.point, { layers: ['clusters'] })
      map.getSource(SRC).getClusterExpansionZoom(f[0].properties.cluster_id).then((z) => {
        map.easeTo({ center: f[0].geometry.coordinates, zoom: z })
      })
    })
    map.on('click', 'pts', (e) => {
      const p = e.features[0].properties
      new maplibregl.Popup({ closeButton: false })
        .setLngLat(e.features[0].geometry.coordinates)
        .setHTML(`<div style="font-family:Newsreader,serif;font-style:italic;font-weight:600">${p.name}</div>
          <div style="font-size:11px;color:#64748b">${p.basis || ''} ${p.year ? '· ' + p.year : ''}</div>`)
        .addTo(map)
    })
    map.on('mouseenter', 'pts', () => (map.getCanvas().style.cursor = 'pointer'))
    map.on('mouseleave', 'pts', () => (map.getCanvas().style.cursor = ''))
    map.on('mouseenter', 'clusters', () => (map.getCanvas().style.cursor = 'pointer'))
    map.on('mouseleave', 'clusters', () => (map.getCanvas().style.cursor = ''))
  }
  if (fit && geo.features.length) {
    const b = new maplibregl.LngLatBounds()
    geo.features.forEach((f) => b.extend(f.geometry.coordinates))
    map.fitBounds(b, { padding: 50, maxZoom: 10, duration: 500 })
  }
}

onMounted(async () => {
  occ = await fetch(`${import.meta.env.BASE_URL}data/occurrences.json`).then((r) => (r.ok ? r.json() : {})).catch(() => ({}))
  loaded.value = true
  map = new maplibregl.Map({
    container: el.value,
    style: BASEMAPS[theme.mode] || BASEMAPS.dark,
    center: [-78.7, -0.1],
    zoom: 6,
    attributionControl: { compact: true },
  })
  map.addControl(new maplibregl.NavigationControl(), 'top-right')
  map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-right')
  map.on('load', () => addData(true))
})

// Re-style on theme mode change, re-adding the data layer once the new style is ready.
watch(() => theme.mode, (m) => {
  if (!map) return
  map.setStyle(BASEMAPS[m] || BASEMAPS.dark)
  map.once('styledata', () => setTimeout(() => addData(false), 60))
})

// Update points when selection changes.
watch(() => store.selectedId, () => addData(true))

onBeforeUnmount(() => map && map.remove())
</script>

<template>
  <div class="relative w-full h-full">
    <div ref="el" class="w-full h-full"></div>
    <div class="absolute top-3 left-3 bg-black/40 backdrop-blur text-white rounded-lg px-3 py-2 text-[11px] pointer-events-none">
      <div class="font-medium">{{ store.selectedId ? store.selectedId : 'All taxa' }} · GBIF occurrences</div>
      <div class="opacity-80">{{ store.selectedId ? 'click a taxon in the network to change' : 'select a taxon to focus' }}</div>
    </div>
  </div>
</template>
