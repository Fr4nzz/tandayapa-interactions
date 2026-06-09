<script setup>
import { useGraphStore, GROUP_COLORS, TYPE_COLORS } from './stores/graph'
import InteractionGraph from './components/InteractionGraph.vue'
import NodeDetail from './components/NodeDetail.vue'

const store = useGraphStore()
</script>

<template>
  <div class="h-full flex flex-col">
    <header class="px-5 py-3 border-b border-gray-200 bg-white">
      <h1 class="text-base font-semibold text-gray-900">
        Tandayapa Ecological Interactions
        <span class="text-gray-400 font-normal">· NW Ecuador / Chocó Andino</span>
      </h1>
      <p class="text-xs text-gray-400">Phase 0 — sample data from open-access sources</p>
    </header>

    <div class="flex-1 flex min-h-0">
      <!-- Filter sidebar -->
      <aside class="w-56 shrink-0 border-r border-gray-200 bg-gray-50 p-4 overflow-y-auto">
        <h3 class="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">
          Interaction types
        </h3>
        <label
          v-for="t in store.allTypes"
          :key="t"
          class="flex items-center gap-2 text-sm py-1 cursor-pointer"
        >
          <input
            type="checkbox"
            :checked="store.activeTypes.includes(t)"
            @change="store.toggleType(t)"
          />
          <span class="w-3 h-1 rounded" :style="{ background: TYPE_COLORS[t] }"></span>
          <span class="text-gray-700">{{ t }}</span>
        </label>

        <h3 class="text-xs font-semibold uppercase tracking-wide text-gray-500 mt-5 mb-2">
          Taxon groups
        </h3>
        <div
          v-for="(c, g) in GROUP_COLORS"
          :key="g"
          class="flex items-center gap-2 text-sm py-0.5"
        >
          <span class="w-3 h-3 rounded-full" :style="{ background: c }"></span>
          <span class="text-gray-600 capitalize">{{ g }}</span>
        </div>
      </aside>

      <!-- Graph -->
      <main class="flex-1 min-w-0 bg-white">
        <InteractionGraph />
      </main>

      <!-- Detail -->
      <NodeDetail />
    </div>
  </div>
</template>
