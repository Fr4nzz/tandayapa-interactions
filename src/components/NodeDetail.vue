<script setup>
import { computed, ref, watch } from 'vue'
import { ArrowLeft, ExternalLink, MapPin, ChevronLeft, ChevronRight } from 'lucide-vue-next'
import {
  useGraphStore, GROUP_COLORS, GROUP_LABELS, TYPE_COLORS, TYPE_DIR_LABELS,
  gbifSpeciesUrl, globiTaxonUrl,
} from '../stores/graph'

const store = useGraphStore()

// Lazy, cached load of the build-time GBIF image map (new shape: { taxon: { images: [...] } }).
let imagesPromise = null
const images = ref({})
function ensureImages() {
  if (!imagesPromise) {
    imagesPromise = fetch(`${import.meta.env.BASE_URL}data/species_images.json`)
      .then((r) => (r.ok ? r.json() : {}))
      .catch(() => ({}))
      .then((j) => (images.value = j || {}))
  }
  return imagesPromise
}
function imagesFor(name) {
  const e = images.value[name]
  if (!e) return []
  if (Array.isArray(e.images)) return e.images
  if (e.image_url) return [e] // tolerate the old single-image shape
  return []
}
function thumbFor(name) {
  const a = imagesFor(name)
  return a.length ? a[0].image_url : null
}

const id = computed(() => store.selectedId)
const node = computed(() => store.selectedNode)
const gallery = computed(() => imagesFor(id.value))
const idx = ref(0)
const current = computed(() => gallery.value[idx.value] || null)

watch(id, (v) => { idx.value = 0; if (v) ensureImages() }, { immediate: true })
function step(d) {
  const n = gallery.value.length
  if (n) idx.value = (idx.value + d + n) % n
}

// Group by (type + direction) with the correct reciprocal phrase.
const groups = computed(() => {
  const map = new Map()
  for (const r of store.selectedRecords) {
    const outgoing = r.source === id.value
    const dir = outgoing ? 'out' : 'in'
    const key = `${r.type}:${dir}`
    const label = (TYPE_DIR_LABELS[r.type] || { out: r.type, in: r.type })[dir]
    if (!map.has(key)) map.set(key, { key, type: r.type, label, items: [] })
    map.get(key).items.push({ partner: outgoing ? r.target : r.source, ...r })
  }
  return [...map.values()]
})
</script>

<template>
  <transition name="slide">
    <aside
      v-if="id"
      class="detail w-[340px] shrink-0 border-r border-[var(--border)] bg-[var(--surface)] overflow-y-auto
             max-md:absolute max-md:inset-0 max-md:w-full max-md:z-30"
    >
      <!-- Back to menu -->
      <button
        class="w-full flex items-center gap-1.5 px-3 py-2 text-sm text-[var(--muted)] hover:text-[var(--text)] border-b border-[var(--border)]"
        @click="store.select(null)"
      >
        <ArrowLeft :size="15" /> Back to filters
      </button>

      <!-- Image carousel -->
      <div class="relative">
        <div class="h-48 w-full bg-[var(--surface-3)] overflow-hidden flex items-center justify-center">
          <img v-if="current" :src="current.image_url" :alt="id" class="h-full w-full object-cover" loading="lazy" />
          <div v-else class="text-[var(--faint)] text-sm px-6 text-center">No GBIF image found for this taxon</div>
        </div>

        <template v-if="gallery.length > 1">
          <button class="navarrow left-2" @click="step(-1)"><ChevronLeft :size="18" /></button>
          <button class="navarrow right-2" @click="step(1)"><ChevronRight :size="18" /></button>
          <div class="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1">
            <span v-for="(g, i) in gallery" :key="i" class="dot" :class="{ 'dot-on': i === idx }"></span>
          </div>
        </template>

        <div class="absolute top-2 left-2 px-2 py-0.5 rounded-full text-[11px] font-medium text-white shadow" :style="{ background: GROUP_COLORS[node?.group] }">
          {{ GROUP_LABELS[node?.group] || node?.group }}
        </div>
        <div v-if="current?.source === 'iNaturalist'" class="absolute bottom-2 right-2 px-1.5 py-0.5 rounded text-[9px] font-medium bg-emerald-600/90 text-white">
          observation
        </div>
      </div>

      <div class="p-4">
        <h2 class="text-xl font-semibold italic text-[var(--text)] leading-tight" style="font-family: Newsreader, Georgia, serif">{{ id }}</h2>
        <p class="text-xs text-[var(--muted)] mt-0.5">{{ store.selectedRecords.length }} interaction(s) · degree {{ node?.degree }}</p>
        <p v-if="current" class="text-[10px] text-[var(--faint)] mt-1 leading-snug">
          {{ current.attribution || 'Image via GBIF' }}
          <a v-if="current.source_url" :href="current.source_url" target="_blank" rel="noopener" class="underline inline-flex items-center gap-0.5" style="color:var(--accent)">
            source <ExternalLink :size="9" />
          </a>
        </p>

        <div class="flex gap-1.5 mt-2.5">
          <a class="extlink" :href="gbifSpeciesUrl(id)" target="_blank" rel="noopener">GBIF <ExternalLink :size="9" /></a>
          <a class="extlink" :href="globiTaxonUrl(id)" target="_blank" rel="noopener">GloBI <ExternalLink :size="9" /></a>
        </div>

        <div v-for="g in groups" :key="g.key" class="mt-4">
          <div class="flex items-center gap-2 mb-1.5">
            <span class="w-3 h-1.5 rounded" :style="{ background: TYPE_COLORS[g.type] }"></span>
            <span class="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">{{ g.label }}</span>
          </div>
          <ul class="space-y-1.5">
            <li
              v-for="(it, i) in g.items"
              :key="i"
              class="flex items-center gap-2.5 rounded-lg px-2 py-1.5 hover:bg-[var(--surface-3)] cursor-pointer border border-transparent hover:border-[var(--border)]"
              @click="store.select(it.partner)"
            >
              <span class="shrink-0 w-9 h-9 rounded-md overflow-hidden bg-[var(--surface-3)] grid place-items-center">
                <img v-if="thumbFor(it.partner)" :src="thumbFor(it.partner)" :alt="it.partner" class="w-full h-full object-cover" loading="lazy" />
                <span v-else class="text-[8px] text-[var(--faint)]">—</span>
              </span>
              <div class="min-w-0">
                <div class="text-sm italic text-[var(--text)] truncate" style="font-family: Newsreader, Georgia, serif">{{ it.partner }}</div>
                <div class="flex items-center gap-1 text-[11px] text-[var(--faint)]">
                  <MapPin :size="10" /> <span class="truncate">{{ it.locality }} · {{ store.scopeLabel(it.scope) }}</span>
                </div>
                <div class="text-[11px] text-[var(--faint)] truncate italic">{{ it.ref }}</div>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </aside>
  </transition>
</template>

<style scoped>
.slide-enter-active, .slide-leave-active { transition: transform 0.25s ease, opacity 0.25s ease; }
.slide-enter-from, .slide-leave-to { transform: translateX(20px); opacity: 0; }
.extlink {
  display: inline-flex; align-items: center; gap: 3px;
  font-size: 11px; padding: 2px 8px; border-radius: 9999px;
  border: 1px solid var(--border); color: var(--muted); background: var(--surface-2);
}
.extlink:hover { color: var(--text); border-color: var(--faint); }
.navarrow {
  position: absolute; top: 50%; transform: translateY(-50%);
  display: grid; place-items: center; width: 30px; height: 30px;
  border-radius: 9999px; background: rgba(0,0,0,0.4); color: #fff;
}
.navarrow:hover { background: rgba(0,0,0,0.6); }
.dot { width: 6px; height: 6px; border-radius: 9999px; background: rgba(255,255,255,0.5); }
.dot-on { background: #fff; }
</style>
