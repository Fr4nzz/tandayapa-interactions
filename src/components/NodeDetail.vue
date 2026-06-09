<script setup>
import { computed } from 'vue'
import { useGraphStore, GROUP_COLORS } from '../stores/graph'

const store = useGraphStore()
const id = computed(() => store.selectedId)
const group = computed(() => store.selectedGroup)
const records = computed(() => store.selectedRecords)

function partner(r) {
  return r.source === id.value ? r.target : r.source
}
function role(r) {
  return r.source === id.value ? `→ ${r.type}` : `${r.type} →`
}
</script>

<template>
  <aside class="w-80 shrink-0 border-l border-gray-200 bg-white overflow-y-auto p-4">
    <div v-if="!id" class="text-gray-400 text-sm mt-8 text-center">
      Click a node to see its interactions.
    </div>
    <div v-else>
      <div class="flex items-center gap-2 mb-1">
        <span class="w-3 h-3 rounded-full" :style="{ background: GROUP_COLORS[group] }"></span>
        <span class="text-xs uppercase tracking-wide text-gray-500">{{ group }}</span>
      </div>
      <h2 class="text-lg font-semibold italic text-gray-900 mb-1">{{ id }}</h2>
      <p class="text-xs text-gray-400 mb-3">
        GBIF image goes here (Phase 3) · {{ records.length }} interaction(s)
      </p>

      <ul class="space-y-2">
        <li v-for="(r, i) in records" :key="i" class="text-sm border-b border-gray-100 pb-2">
          <div class="font-medium italic text-gray-800">{{ partner(r) }}</div>
          <div class="text-xs text-gray-500">{{ role(r) }}</div>
          <div class="text-xs text-gray-400">{{ r.locality }} · {{ r.scope }}</div>
          <div class="text-xs text-gray-400">{{ r.ref }}</div>
        </li>
      </ul>
    </div>
  </aside>
</template>
