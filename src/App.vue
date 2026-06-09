<script setup>
import { ref } from 'vue'
import { Info, SlidersHorizontal, Github, X } from 'lucide-vue-next'
import { useGraphStore, TYPE_COLORS, TYPE_LABELS } from './stores/graph'
import InteractionGraph from './components/InteractionGraph.vue'
import NodeDetail from './components/NodeDetail.vue'
import FilterPanel from './components/FilterPanel.vue'

const store = useGraphStore()
const layout = ref('fcose')
const graphRef = ref(null)
const showAbout = ref(false)
const showFilters = ref(false)

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
  <div class="h-full flex flex-col bg-slate-100">
    <!-- Header -->
    <header class="flex items-center gap-3 px-4 py-2.5 bg-white border-b border-slate-200 z-10">
      <div class="flex items-center gap-2 min-w-0">
        <span class="text-lg">🦋</span>
        <div class="min-w-0">
          <h1 class="text-sm font-semibold text-slate-900 leading-tight truncate">
            Tandayapa Ecological Interactions
          </h1>
          <p class="text-[11px] text-slate-400 leading-tight">NW Ecuador · Chocó Andino</p>
        </div>
      </div>

      <div class="hidden md:flex items-center gap-1.5 ml-4">
        <span class="stat"><b>{{ store.stats.taxa }}</b> taxa</span>
        <span class="stat"><b>{{ store.stats.interactions }}</b> interactions</span>
        <span class="stat"><b>{{ store.stats.types }}</b> types</span>
        <span class="stat"><b>{{ store.stats.sources }}</b> sources</span>
      </div>

      <div class="ml-auto flex items-center gap-1.5">
        <button class="hbtn md:hidden" @click="showFilters = !showFilters" title="Filters">
          <SlidersHorizontal :size="16" />
        </button>
        <a class="hbtn" href="https://github.com/Fr4nzz/tandayapa-interactions" target="_blank" rel="noopener" title="Repo">
          <Github :size="16" />
        </a>
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
        <InteractionGraph ref="graphRef" :layout="layout" />

        <!-- floating legend / hint -->
        <div class="absolute bottom-3 left-3 bg-black/40 backdrop-blur text-white rounded-lg px-3 py-2 text-[11px] leading-relaxed pointer-events-none">
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
        <div class="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl relative">
          <button class="absolute top-4 right-4 text-slate-400 hover:text-slate-600" @click="showAbout = false">
            <X :size="18" />
          </button>
          <h2 class="text-lg font-semibold text-slate-900 mb-2">About this map</h2>
          <div class="text-sm text-slate-600 space-y-2.5 leading-relaxed">
            <p>
              An interactive, GloBI-compatible network of <b>ecological interactions</b> in the
              Tandayapa–Mindo corridor and the wider Chocó Andino of northwestern Ecuador — who
              pollinates, disperses, eats, and parasitizes whom.
            </p>
            <p>
              Edges are hand-extracted from <b>open-access literature</b> (EPHI/Maquipucuna,
              Muchhala 2002/2006/2009, Mahoney 2018, Guevara 2017, Abad 2021, Dellinger 2014).
              This is a curated sample, not yet the full database — the Duchenne/EPHI Dryad anchor
              (~1,690 plant–hummingbird interactions) is pending ingestion.
            </p>
            <p class="text-slate-500">
              <b>Honesty:</b> every interaction keeps its true locality; nearby-reserve records are
              flagged by <i>scope</i>, never relabeled “Tandayapa.” No interactions are invented from
              pollination-syndrome inference.
            </p>
            <p class="text-slate-500">
              Taxa images & occurrence data via <a class="underline" href="https://www.gbif.org" target="_blank" rel="noopener">GBIF</a>,
              under each record’s CC license. Built with Vue, Cytoscape.js & Tailwind.
            </p>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.stat {
  font-size: 12px; color: #64748b;
  padding: 2px 8px; border-radius: 9999px; background: #f1f5f9;
}
.stat b { color: #0f172a; font-weight: 600; }
.hbtn {
  display: grid; place-items: center; width: 32px; height: 32px;
  border-radius: 8px; color: #475569; background: #f8fafc;
  border: 1px solid #e2e8f0; transition: all 0.15s;
}
.hbtn:hover { background: #f1f5f9; color: #0f172a; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
