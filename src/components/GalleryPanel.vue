<script setup>
import { ref, computed } from 'vue'
import { useGraphStore, GROUP_COLORS, GROUP_LABELS } from '../stores/graph'

const store = useGraphStore()

// Load the prebuilt GBIF image map (new shape { taxon: { images:[...] } }).
const images = ref({})
fetch(`${import.meta.env.BASE_URL}data/species_images.json`)
  .then((r) => (r.ok ? r.json() : {}))
  .catch(() => ({}))
  .then((j) => (images.value = j || {}))

function thumb(name) {
  const e = images.value[name]
  if (!e) return null
  if (Array.isArray(e.images)) return e.images[0]?.image_url || null
  return e.image_url || null
}

const q = ref('')

// Cards: taxa whose group is active, optionally matching the search, that have an image first.
const cards = computed(() => {
  const term = q.value.trim().toLowerCase()
  return store.nodes
    .filter((n) => store.activeGroups.includes(n.group))
    .filter((n) => !term || n.id.toLowerCase().includes(term))
    .map((n) => ({ ...n, img: thumb(n.id) }))
    .sort((a, b) => (b.img ? 1 : 0) - (a.img ? 1 : 0) || b.degree - a.degree)
})
const withImg = computed(() => cards.value.filter((c) => c.img).length)
</script>

<template>
  <div class="w-full h-full flex flex-col bg-[var(--bg)]">
    <div class="px-4 py-2 flex items-center gap-3 border-b border-[var(--border)]">
      <input
        v-model="q"
        type="text"
        placeholder="Search the gallery…"
        class="flex-1 max-w-xs px-3 py-1.5 text-sm rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text)] focus:outline-none"
      />
      <span class="text-xs text-[var(--muted)]">{{ withImg }} taxa with images · {{ cards.length }} shown</span>
    </div>

    <div class="flex-1 overflow-auto p-3">
      <div class="grid gap-3" style="grid-template-columns: repeat(auto-fill, minmax(140px, 1fr))">
        <button
          v-for="c in cards"
          :key="c.id"
          class="group text-left rounded-xl overflow-hidden border border-[var(--border)] bg-[var(--surface)] hover:shadow-lg transition"
          @click="store.select(c.id)"
        >
          <div class="aspect-square bg-[var(--surface-3)] overflow-hidden relative">
            <img v-if="c.img" :src="c.img" :alt="c.id" loading="lazy" class="w-full h-full object-cover group-hover:scale-105 transition" />
            <div v-else class="w-full h-full grid place-items-center text-[var(--faint)] text-xs">no image</div>
            <span class="absolute top-1.5 left-1.5 w-2.5 h-2.5 rounded-full border border-white/70" :style="{ background: GROUP_COLORS[c.group] }" :title="GROUP_LABELS[c.group] || c.group"></span>
          </div>
          <div class="px-2 py-1.5">
            <div class="text-xs italic text-[var(--text)] leading-tight line-clamp-2" style="font-family: Newsreader, Georgia, serif">{{ c.id }}</div>
            <div class="text-[10px] text-[var(--faint)] mt-0.5">{{ c.degree }} interaction(s)</div>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
</style>
