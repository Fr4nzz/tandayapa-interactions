<script setup>
import { ref, onMounted, defineAsyncComponent } from 'vue'
import { Info, SlidersHorizontal, Github, X, Sun, Moon, Palette, Share2, Map as MapIcon, Table as TableIcon } from 'lucide-vue-next'
import { useGraphStore, TYPE_COLORS, TYPE_LABELS } from './stores/graph'
import { useThemeStore, THEMES } from './stores/theme'
import InteractionGraph from './components/InteractionGraph.vue'
import NodeDetail from './components/NodeDetail.vue'
import FilterPanel from './components/FilterPanel.vue'
import TablePanel from './components/TablePanel.vue'
// Lazy: the maplibre chunk (~1 MB) loads only when the map view is first opened.
const MapPanel = defineAsyncComponent(() => import('./components/MapPanel.vue'))

const store = useGraphStore()
const theme = useThemeStore()
const layout = ref('fcose')
const view = ref('network')
const graphRef = ref(null)
const showAbout = ref(false)
const showFilters = ref(false)
const showPalette = ref(false)
const gbif = ref(null)

onMounted(() => {
  fetch(`${import.meta.env.BASE_URL}data/gbif_attribution.json`)
    .then((r) => (r.ok ? r.json() : null))
    .then((j) => (gbif.value = j))
    .catch(() => {})
})

function onExport() {
  const url = graphRef.value?.exportPng()
  if (!url) return
  const a = document.createElement('a')
  a.href = url
  a.download = 'tandayapa-interactions.png'
  a.click()
}
</script>

<template>
  <div class="h-full flex flex-col bg-[var(--bg)] text-[var(--text)]">
    <!-- Header -->
    <header class="flex items-center gap-3 px-4 py-2.5 bg-[var(--surface)] border-b border-[var(--border)] z-10">
      <div class="flex items-center gap-2 min-w-0">
        <span class="text-lg">🦋</span>
        <div class="min-w-0">
          <h1 class="text-sm font-semibold leading-tight truncate">Tandayapa Ecological Interactions</h1>
          <p class="text-[11px] text-[var(--faint)] leading-tight">NW Ecuador · Chocó Andino</p>
        </div>
      </div>

      <div class="hidden md:flex items-center gap-1.5 ml-4">
        <span class="stat"><b>{{ store.stats.taxa }}</b> taxa</span>
        <span class="stat"><b>{{ store.stats.interactions }}</b> interactions</span>
        <span class="stat"><b>{{ store.stats.types }}</b> types</span>
        <span class="stat"><b>{{ store.stats.sources }}</b> sources</span>
      </div>

      <!-- view toggle -->
      <div class="ml-auto flex items-center rounded-lg border border-[var(--border)] overflow-hidden mr-1">
        <button
          class="seg" :class="view === 'network' ? 'seg-on' : ''"
          :style="view === 'network' ? { background: 'var(--accent)', color: '#fff' } : {}"
          @click="view = 'network'"
        ><Share2 :size="13" /> <span class="hidden sm:inline">Network</span></button>
        <button
          class="seg" :class="view === 'map' ? 'seg-on' : ''"
          :style="view === 'map' ? { background: 'var(--accent)', color: '#fff' } : {}"
          @click="view = 'map'"
        ><MapIcon :size="13" /> <span class="hidden sm:inline">Map</span></button>
        <button
          class="seg" :class="view === 'table' ? 'seg-on' : ''"
          :style="view === 'table' ? { background: 'var(--accent)', color: '#fff' } : {}"
          @click="view = 'table'"
        ><TableIcon :size="13" /> <span class="hidden sm:inline">Table</span></button>
      </div>

      <div class="flex items-center gap-1.5">
        <!-- accent palette -->
        <div class="relative hidden sm:block">
          <button class="hbtn" @click="showPalette = !showPalette" title="Accent"><Palette :size="16" /></button>
          <div
            v-if="showPalette"
            class="absolute right-0 mt-1 p-2 rounded-xl bg-[var(--surface)] border border-[var(--border)] shadow-xl flex gap-1.5 z-30"
          >
            <button
              v-for="(t, key) in THEMES"
              :key="key"
              class="w-6 h-6 rounded-full border-2 transition"
              :style="{ background: t.accent, borderColor: theme.theme === key ? 'var(--text)' : 'transparent' }"
              :title="t.name"
              @click="theme.setTheme(key); showPalette = false"
            ></button>
          </div>
        </div>
        <button class="hbtn" @click="theme.toggleMode()" :title="theme.isDark ? 'Light mode' : 'Dark mode'">
          <Sun v-if="theme.isDark" :size="16" />
          <Moon v-else :size="16" />
        </button>
        <button class="hbtn md:hidden" @click="showFilters = !showFilters" title="Filters"><SlidersHorizontal :size="16" /></button>
        <a class="hbtn hidden sm:grid" href="https://github.com/Fr4nzz/tandayapa-interactions" target="_blank" rel="noopener" title="Repo"><Github :size="16" /></a>
        <button class="hbtn" @click="showAbout = true" title="About"><Info :size="16" /></button>
      </div>
    </header>

    <!-- Body -->
    <div class="flex-1 flex min-h-0 relative">
      <FilterPanel
        :layout="layout"
        @update:layout="layout = $event"
        @fit="graphRef?.fit()"
        @export="onExport"
        class="max-md:absolute max-md:inset-y-0 max-md:left-0 max-md:z-20 max-md:shadow-xl"
        :class="{ 'max-md:hidden': !showFilters }"
      />

      <main class="flex-1 min-w-0 relative">
        <InteractionGraph v-show="view === 'network'" ref="graphRef" :layout="layout" />
        <MapPanel v-if="view === 'map'" />
        <TablePanel v-if="view === 'table'" />

        <div v-if="view === 'network'" class="absolute bottom-3 left-3 bg-black/40 backdrop-blur text-white rounded-lg px-3 py-2 text-[11px] leading-relaxed pointer-events-none">
          <div class="font-medium mb-1 opacity-90">Hover to highlight · click for details</div>
          <div class="flex flex-wrap gap-x-3 gap-y-0.5 max-w-[260px]">
            <span v-for="t in store.allTypes" :key="t" class="inline-flex items-center gap-1">
              <span class="w-2.5 h-1 rounded" :style="{ background: TYPE_COLORS[t] }"></span>
              {{ TYPE_LABELS[t] }}
            </span>
          </div>
        </div>
      </main>

      <NodeDetail />
    </div>

    <!-- About modal -->
    <transition name="fade">
      <div v-if="showAbout" class="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4" @click.self="showAbout = false">
        <div class="bg-[var(--surface)] text-[var(--text)] rounded-2xl max-w-lg w-full p-6 shadow-2xl relative border border-[var(--border)]">
          <button class="absolute top-4 right-4 text-[var(--faint)] hover:text-[var(--text)]" @click="showAbout = false"><X :size="18" /></button>
          <h2 class="text-lg font-semibold mb-2">About this map</h2>
          <div class="text-sm text-[var(--muted)] space-y-2.5 leading-relaxed">
            <p>
              An interactive, GloBI-compatible network of <b class="text-[var(--text)]">ecological interactions</b> in the
              Tandayapa–Mindo corridor and the wider Chocó Andino of northwestern Ecuador — who pollinates,
              disperses, eats, and parasitizes whom.
            </p>
            <p>
              Edges are hand-extracted from <b class="text-[var(--text)]">open-access literature</b> (EPHI/Maquipucuna,
              Muchhala 2002/2006/2009, Mahoney 2018, Guevara 2017, Abad 2021, Dellinger 2014) plus the
              <b class="text-[var(--text)]">Duchenne/EPHI</b> camera-trap anchor (Dryad, ~1,686 plant–hummingbird
              interactions across 11 Pichincha reserves).
            </p>
            <p>
              <b class="text-[var(--text)]">Honesty:</b> every interaction keeps its true locality; nearby-reserve records
              are flagged by <i>scope</i>, never relabeled “Tandayapa.” No interactions are invented from syndrome inference.
            </p>
            <p>
              Taxa images & occurrences via <a class="underline" style="color:var(--accent)" href="https://www.gbif.org" target="_blank" rel="noopener">GBIF</a>,
              under each record’s CC license. Built with Vue, Cytoscape.js & Tailwind.
            </p>
            <p v-if="gbif?.doi" class="text-[11px] text-[var(--faint)] border-t border-[var(--border)] pt-2">
              Occurrence & media: GBIF Occurrence Download
              <a class="underline" style="color:var(--accent)" :href="`https://doi.org/${gbif.doi}`" target="_blank" rel="noopener">https://doi.org/{{ gbif.doi }}</a>
              (one citable export; observations prioritised over museum specimens).
            </p>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.stat {
  font-size: 12px; color: var(--muted);
  padding: 2px 8px; border-radius: 9999px; background: var(--surface-3);
}
.stat b { color: var(--text); font-weight: 600; }
.hbtn {
  display: grid; place-items: center; width: 32px; height: 32px;
  border-radius: 8px; color: var(--muted); background: var(--surface-2);
  border: 1px solid var(--border); transition: all 0.15s;
}
.hbtn:hover { background: var(--surface-3); color: var(--text); }
.seg {
  display: flex; align-items: center; gap: 4px;
  font-size: 12px; padding: 5px 10px; color: var(--muted); background: var(--surface-2);
}
.seg:hover { color: var(--text); }
.seg-on { color: #fff; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
