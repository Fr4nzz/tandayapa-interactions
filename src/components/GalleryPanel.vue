<script setup>
import { ref, computed } from 'vue'
import { ArrowRight } from 'lucide-vue-next'
import { useGraphStore, GROUP_COLORS, TYPE_COLORS, TYPE_LABELS } from '../stores/graph'

const store = useGraphStore()

// Build-time GBIF image map (new shape { taxon: { images:[...] } }).
const images = ref({})
fetch(`${import.meta.env.BASE_URL}data/species_images.json`)
  .then((r) => (r.ok ? r.json() : {})).catch(() => ({})).then((j) => (images.value = j || {}))
function thumb(name) {
  const e = images.value[name]
  if (!e) return null
  return Array.isArray(e.images) ? e.images[0]?.image_url || null : e.image_url || null
}

const q = ref('')
const CAP = 300

// One card per INTERACTION (visible + matching search + the selected taxon if any).
const all = computed(() => {
  const term = q.value.trim().toLowerCase()
  return store.records.filter((r) => {
    if (!store.isEdgeVisible(r)) return false
    if (store.selectedId && r.source !== store.selectedId && r.target !== store.selectedId) return false
    if (term && !(`${r.source} ${r.target}`.toLowerCase().includes(term))) return false
    return true
  })
})
const cards = computed(() => all.value.slice(0, CAP))
</script>

<template>
  <div class="w-full h-full flex flex-col bg-[var(--bg)]">
    <div class="px-4 py-2 flex items-center gap-3 border-b border-[var(--border)] flex-wrap">
      <input v-model="q" type="text" placeholder="Search a pair…" class="flex-1 max-w-xs px-3 py-1.5 text-sm rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text)] focus:outline-none" />
      <span class="text-xs text-[var(--muted)]">
        {{ all.length }} interaction(s)<template v-if="all.length > CAP"> · showing first {{ CAP }} (filter to narrow)</template>
        <template v-if="store.selectedId"> · for <span class="italic">{{ store.selectedId }}</span> · <button class="underline" @click="store.select(null)">clear</button></template>
      </span>
    </div>

    <div class="flex-1 overflow-auto p-3">
      <div class="grid gap-3" style="grid-template-columns: repeat(auto-fill, minmax(230px, 1fr))">
        <div v-for="(r, i) in cards" :key="i" class="rounded-xl overflow-hidden border border-[var(--border)] bg-[var(--surface)] hover:shadow-lg transition">
          <!-- the pair: source image — verb — target image -->
          <div class="relative flex items-stretch">
            <button class="relative w-1/2 aspect-square bg-[var(--surface-3)] overflow-hidden group" @click="store.select(r.source)">
              <img v-if="thumb(r.source)" :src="thumb(r.source)" :alt="r.source" loading="lazy" class="w-full h-full object-cover group-hover:scale-105 transition" />
              <div v-else class="w-full h-full grid place-items-center text-[9px] text-[var(--faint)] px-1 text-center">{{ r.source }}</div>
              <span class="absolute top-1 left-1 w-2 h-2 rounded-full border border-white/70" :style="{ background: GROUP_COLORS[r.sourceGroup] }"></span>
            </button>
            <button class="relative w-1/2 aspect-square bg-[var(--surface-3)] overflow-hidden group" @click="store.select(r.target)">
              <img v-if="thumb(r.target)" :src="thumb(r.target)" :alt="r.target" loading="lazy" class="w-full h-full object-cover group-hover:scale-105 transition" />
              <div v-else class="w-full h-full grid place-items-center text-[9px] text-[var(--faint)] px-1 text-center">{{ r.target }}</div>
              <span class="absolute top-1 right-1 w-2 h-2 rounded-full border border-white/70" :style="{ background: GROUP_COLORS[r.targetGroup] }"></span>
            </button>
            <!-- verb chip centered over the seam -->
            <div class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none">
              <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-medium text-white shadow" :style="{ background: TYPE_COLORS[r.type] || '#64748b' }">
                <ArrowRight :size="9" />
              </span>
            </div>
          </div>
          <div class="px-2.5 py-2">
            <div class="text-xs italic text-[var(--text)] truncate" style="font-family: Newsreader, Georgia, serif">{{ r.source }}</div>
            <div class="text-[10px] font-medium" :style="{ color: TYPE_COLORS[r.type] }">{{ TYPE_LABELS[r.type] || r.type }}</div>
            <div class="text-xs italic text-[var(--text)] truncate" style="font-family: Newsreader, Georgia, serif">{{ r.target }}</div>
            <div class="text-[10px] text-[var(--faint)] mt-0.5 truncate">{{ r.locality }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
