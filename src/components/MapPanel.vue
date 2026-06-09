<script setup>
import { onMounted, onBeforeUnmount, ref, watch, computed } from 'vue'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useGraphStore, GROUP_COLORS, TYPE_COLORS } from '../stores/graph'
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

// Approximate coordinates [lng, lat] for the corridor's named reserves/sites, so an
// interaction's recorded locality can be shown as a marker (where it was observed).
const RESERVES = {
  Tandayapa: [-78.68, -0.005], Bellavista: [-78.685, 0.016], Maquipucuna: [-78.63, 0.123],
  Mashpi: [-78.87, 0.165], 'Las Gralarias': [-78.73, -0.007], Sachatamia: [-78.74, -0.012],
  Mindo: [-78.78, -0.05], Guajalito: [-78.81, -0.23], Milpe: [-78.87, 0.03],
  Puyucunapi: [-78.68, 0.06], Verdecocha: [-78.58, -0.10], Yanacocha: [-78.58, -0.13],
  Otonga: [-79.0, -0.42], Pahuma: [-78.63, 0.02], 'Santa Lucia': [-78.62, 0.10],
  Alaspungo: [-78.6, -0.13], 'Un Poco del Choco': [-78.85, 0.18], Pichincha: [-78.6, -0.05],
}

const groupOf = computed(() => {
  const m = {}
  for (const n of store.nodes) m[n.id] = n.group
  return m
})

// Occurrence points. With a taxon selected: the focal taxon (bright) + its partners (faded)
// so geographic overlap = where the interaction can happen. Otherwise: all taxa (overview).
function buildOccGeoJSON() {
  const feats = []
  const focal = store.selectedId
  let names
  if (focal) {
    const partners = new Set()
    for (const r of store.selectedRecords) partners.add(r.source === focal ? r.target : r.source)
    names = [focal, ...partners]
  } else {
    names = Object.keys(occ).filter((k) => !k.startsWith('_'))
  }
  for (const name of names) {
    const entry = occ[name]
    if (!entry || !entry.points) continue
    const group = groupOf.value[name] || 'plant'
    const role = !focal ? 'all' : name === focal ? 'focal' : 'partner'
    for (const p of entry.points) {
      if (p.lat == null || p.lng == null) continue
      feats.push({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [p.lng, p.lat] },
        properties: { name, group, role, color: GROUP_COLORS[group] || '#888', year: p.year || '', basis: p.basis || '' },
      })
    }
  }
  return { type: 'FeatureCollection', features: feats }
}

// Recorded interaction localities for the selected taxon, matched to known reserves.
function buildLocGeoJSON() {
  const feats = []
  if (!store.selectedId) return { type: 'FeatureCollection', features: feats }
  const seen = new Set()
  for (const r of store.selectedRecords) {
    const loc = r.locality || ''
    for (const [name, coord] of Object.entries(RESERVES)) {
      if (loc.toLowerCase().includes(name.toLowerCase())) {
        const partner = r.source === store.selectedId ? r.target : r.source
        const key = `${name}|${partner}|${r.type}`
        if (seen.has(key)) continue
        seen.add(key)
        feats.push({
          type: 'Feature', geometry: { type: 'Point', coordinates: coord },
          properties: { reserve: name, partner, type: r.type, color: TYPE_COLORS[r.type] || '#fff', ref: r.ref || '' },
        })
        break
      }
    }
  }
  return { type: 'FeatureCollection', features: feats }
}

const SRC = 'occ-src'
const LOC = 'loc-src'
let curCluster = null
let bound = false

function ensureLayers(wantCluster) {
  for (const id of ['clusters', 'cluster-count', 'pts']) if (map.getLayer(id)) map.removeLayer(id)
  if (map.getSource(SRC)) map.removeSource(SRC)
  map.addSource(SRC, { type: 'geojson', data: buildOccGeoJSON(), cluster: wantCluster, clusterMaxZoom: 12, clusterRadius: 45 })
  if (wantCluster) {
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
      layout: { 'text-field': ['get', 'point_count_abbreviated'], 'text-size': 11 }, paint: { 'text-color': '#fff' },
    })
  }
  map.addLayer({
    id: 'pts', type: 'circle', source: SRC, filter: ['!', ['has', 'point_count']],
    paint: {
      'circle-color': ['get', 'color'],
      'circle-radius': ['case', ['==', ['get', 'role'], 'focal'], 6, ['==', ['get', 'role'], 'partner'], 4, 5],
      'circle-opacity': ['case', ['==', ['get', 'role'], 'partner'], 0.45, 0.9],
      'circle-stroke-width': ['case', ['==', ['get', 'role'], 'focal'], 1.5, 0.6],
      'circle-stroke-color': 'rgba(255,255,255,0.85)',
    },
  })
  curCluster = wantCluster
}

function ensureLocLayer() {
  if (!map.getSource(LOC)) {
    map.addSource(LOC, { type: 'geojson', data: buildLocGeoJSON() })
    map.addLayer({
      id: 'loc', type: 'circle', source: LOC,
      paint: { 'circle-color': ['get', 'color'], 'circle-radius': 9, 'circle-opacity': 0.9, 'circle-stroke-width': 2.5, 'circle-stroke-color': '#fff' },
    })
  } else {
    map.getSource(LOC).setData(buildLocGeoJSON())
  }
}

function bindEvents() {
  if (bound) return
  bound = true
  map.on('click', 'clusters', (e) => {
    const f = map.queryRenderedFeatures(e.point, { layers: ['clusters'] })
    map.getSource(SRC).getClusterExpansionZoom(f[0].properties.cluster_id).then((z) => map.easeTo({ center: f[0].geometry.coordinates, zoom: z }))
  })
  map.on('click', 'pts', (e) => {
    const p = e.features[0].properties
    new maplibregl.Popup({ closeButton: false }).setLngLat(e.features[0].geometry.coordinates)
      .setHTML(`<div style="font-family:Newsreader,serif;font-style:italic;font-weight:600">${p.name}</div><div style="font-size:11px;color:#64748b">${p.basis || ''} ${p.year ? '· ' + p.year : ''}</div>`).addTo(map)
  })
  map.on('click', 'loc', (e) => {
    const p = e.features[0].properties
    new maplibregl.Popup({ closeButton: false }).setLngLat(e.features[0].geometry.coordinates)
      .setHTML(`<div style="font-weight:600">${p.reserve}</div><div style="font-size:11px"><i>${store.selectedId}</i> × <i>${p.partner}</i></div><div style="font-size:10px;color:#64748b">${p.ref}</div>`).addTo(map)
  })
  for (const lyr of ['pts', 'clusters', 'loc']) {
    map.on('mouseenter', lyr, () => (map.getCanvas().style.cursor = 'pointer'))
    map.on('mouseleave', lyr, () => (map.getCanvas().style.cursor = ''))
  }
}

function render(fit = true) {
  if (!map || !map.isStyleLoaded() || !loaded.value) return
  const wantCluster = !store.selectedId
  if (map.getSource(SRC) && curCluster === wantCluster) map.getSource(SRC).setData(buildOccGeoJSON())
  else ensureLayers(wantCluster)
  ensureLocLayer()
  bindEvents()
  if (fit) {
    const geo = buildOccGeoJSON()
    if (geo.features.length) {
      const b = new maplibregl.LngLatBounds()
      geo.features.forEach((f) => b.extend(f.geometry.coordinates))
      map.fitBounds(b, { padding: 60, maxZoom: store.selectedId ? 9 : 7, duration: 500 })
    }
  }
}

onMounted(() => {
  map = new maplibregl.Map({
    container: el.value, style: BASEMAPS[theme.mode] || BASEMAPS.dark,
    center: [-78.7, -0.1], zoom: 7, attributionControl: { compact: true },
  })
  map.addControl(new maplibregl.NavigationControl(), 'top-right')
  map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-right')
  let styleReady = false
  const tryAdd = () => { if (styleReady && loaded.value) render(true) }
  map.on('load', () => { styleReady = true; tryAdd() })
  fetch(`${import.meta.env.BASE_URL}data/occurrences.json`)
    .then((r) => (r.ok ? r.json() : {})).catch(() => ({})).then((j) => { occ = j || {}; loaded.value = true; tryAdd() })
})

watch(() => theme.mode, (m) => {
  if (!map) return
  curCluster = null
  map.setStyle(BASEMAPS[m] || BASEMAPS.dark)
  map.once('styledata', () => setTimeout(() => render(false), 80))
})
watch(() => store.selectedId, () => render(true))

onBeforeUnmount(() => map && map.remove())
</script>

<template>
  <div class="relative w-full h-full">
    <div ref="el" class="w-full h-full"></div>
    <div class="absolute top-3 left-3 bg-black/45 backdrop-blur text-white rounded-lg px-3 py-2 text-[11px] pointer-events-none max-w-[240px]">
      <div class="font-medium">{{ store.selectedId || 'All taxa' }} · GBIF occurrences</div>
      <div class="opacity-80">
        <span v-if="!loaded">loading occurrences…</span>
        <span v-else-if="store.selectedId">focal (bright) + partners (faded) · ◯ = recorded localities</span>
        <span v-else>select a taxon to see its interaction overlap</span>
      </div>
    </div>
  </div>
</template>
