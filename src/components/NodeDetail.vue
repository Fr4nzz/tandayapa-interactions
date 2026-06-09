<script setup>
import { computed, ref, watch } from 'vue'
import { X, ExternalLink, MapPin } from 'lucide-vue-next'
import { useGraphStore, GROUP_COLORS, GROUP_LABELS, TYPE_COLORS, TYPE_LABELS } from '../stores/graph'

const store = useGraphStore()

// Lazy, cached load of the build-time GBIF image map (public/data/species_images.json).
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

const id = computed(() => store.selectedId)
const node = computed(() => store.selectedNode)
const img = computed(() => images.value[id.value] || null)

watch(id, (v) => v && ensureImages(), { immediate: true })

// Group this taxon's interactions by type, with a readable partner phrase.
const grouped = computed(() => {
  const out = {}
  for (const r of store.selectedRecords) {
    const outgoing = r.source === id.value
    const partner = outgoing ? r.target : r.source
    const phrase = outgoing
      ? `${TYPE_LABELS[r.type]} →`
      : `← ${TYPE_LABELS[r.type]}`
    ;(out[r.type] ||= []).push({ partner, phrase, outgoing, ...r })
  }
  return out
})
</script>

<template>
  <transition name="slide">
    <aside
      v-if="id"
      class="detail w-[340px] shrink-0 border-l border-slate-200 bg-white/95 backdrop-blur overflow-y-auto"
    >
      <div class="relative">
        <div class="h-44 w-full bg-slate-100 overflow-hidden flex items-center justify-center">
          <img
            v-if="img"
            :src="img.image_url"
            :alt="id"
            class="h-full w-full object-cover"
            loading="lazy"
          />
          <div v-else class="text-slate-300 text-sm px-6 text-center">
            No GBIF image found for this taxon
          </div>
        </div>
        <button
          class="absolute top-2 right-2 grid place-items-center w-8 h-8 rounded-full bg-black/40 text-white hover:bg-black/60"
          @click="store.select(null)"
        >
          <X :size="16" />
        </button>
        <div
          class="absolute top-2 left-2 px-2 py-0.5 rounded-full text-[11px] font-medium text-white shadow"
          :style="{ background: GROUP_COLORS[node?.group] }"
        >
          {{ GROUP_LABELS[node?.group] || node?.group }}
        </div>
      </div>

      <div class="p-4">
        <h2 class="text-xl font-semibold italic text-slate-900 leading-tight" style="font-family: Newsreader, Georgia, serif">
          {{ id }}
        </h2>
        <p class="text-xs text-slate-500 mt-0.5">
          {{ store.selectedRecords.length }} interaction(s) · degree {{ node?.degree }}
        </p>
        <p v-if="img" class="text-[10px] text-slate-400 mt-1 leading-snug">
          {{ img.attribution || 'Image via GBIF' }}
          <a v-if="img.source_url" :href="img.source_url" target="_blank" rel="noopener" class="underline inline-flex items-center gap-0.5">
            source <ExternalLink :size="9" />
          </a>
        </p>

        <div v-for="(items, type) in grouped" :key="type" class="mt-4">
          <div class="flex items-center gap-2 mb-1.5">
            <span class="w-3 h-1.5 rounded" :style="{ background: TYPE_COLORS[type] }"></span>
            <span class="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {{ TYPE_LABELS[type] }}
            </span>
          </div>
          <ul class="space-y-1.5">
            <li
              v-for="(it, i) in items"
              :key="i"
              class="group rounded-lg px-2.5 py-1.5 hover:bg-slate-50 cursor-pointer border border-transparent hover:border-slate-200"
              @click="store.select(it.partner)"
            >
              <div class="text-sm italic text-slate-800" style="font-family: Newsreader, Georgia, serif">
                {{ it.partner }}
              </div>
              <div class="flex items-center gap-1.5 text-[11px] text-slate-400 mt-0.5">
                <MapPin :size="10" /> {{ it.locality }}
                <span class="text-slate-300">·</span> {{ store.scopeLabel(it.scope) }}
              </div>
              <div class="text-[11px] text-slate-400">{{ it.ref }}</div>
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
</style>
