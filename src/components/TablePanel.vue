<script setup>
import { ref, reactive, computed } from 'vue'
import { ArrowUpDown, ExternalLink } from 'lucide-vue-next'
import { useGraphStore, TYPE_COLORS, TYPE_LABELS } from '../stores/graph'

const store = useGraphStore()

const COLS = [
  { key: 'source', label: 'Source' },
  { key: 'type', label: 'Interaction' },
  { key: 'target', label: 'Target' },
  { key: 'locality', label: 'Locality' },
  { key: 'scope', label: 'Scope' },
  { key: 'evidence', label: 'Evidence' },
  { key: 'ref', label: 'Reference' },
]

const sortKey = ref('source')
const sortDir = ref(1)
const filters = reactive(Object.fromEntries(COLS.map((c) => [c.key, ''])))

function sortBy(k) {
  if (sortKey.value === k) sortDir.value *= -1
  else { sortKey.value = k; sortDir.value = 1 }
}

// Cell text used for both filtering and display (type shows its label, scope its label).
function cell(r, key) {
  if (key === 'type') return TYPE_LABELS[r.type] || r.type
  if (key === 'scope') return store.scopeLabel(r.scope)
  return r[key] ?? ''
}

// A clickable link to the source: the DOI/URL if present, else a Scholar search of the citation.
function refLink(r) {
  if (r.ref_doi_or_url) {
    const u = r.ref_doi_or_url
    return /^https?:\/\//.test(u) ? u : `https://doi.org/${u.replace(/^doi:/i, '')}`
  }
  return `https://scholar.google.com/scholar?q=${encodeURIComponent(r.ref || '')}`
}

const rows = computed(() => {
  const active = Object.entries(filters).filter(([, v]) => v.trim())
  const out = store.records.filter((r) => {
    if (!store.isEdgeVisible(r)) return false
    return active.every(([k, v]) => cell(r, k).toString().toLowerCase().includes(v.trim().toLowerCase()))
  })
  const k = sortKey.value
  return out.sort((a, b) => {
    const av = cell(a, k).toString().toLowerCase()
    const bv = cell(b, k).toString().toLowerCase()
    return av < bv ? -sortDir.value : av > bv ? sortDir.value : 0
  })
})
</script>

<template>
  <div class="w-full h-full flex flex-col bg-[var(--bg)]">
    <div class="px-4 py-2 text-xs text-[var(--muted)] border-b border-[var(--border)] flex items-center justify-between">
      <span>{{ rows.length }} interactions · filter each column · click a reference to open the source</span>
      <button v-if="Object.values(filters).some((v) => v)" class="underline" @click="Object.keys(filters).forEach((k) => (filters[k] = ''))">clear filters</button>
    </div>
    <div class="flex-1 overflow-auto">
      <table class="w-full border-collapse text-sm">
        <thead class="sticky top-0 z-10 bg-[var(--surface)]">
          <tr>
            <th
              v-for="c in COLS" :key="c.key"
              class="text-left font-semibold text-[var(--muted)] px-3 pt-2 border-b border-[var(--border)] cursor-pointer whitespace-nowrap select-none"
              @click="sortBy(c.key)"
            >
              <span class="inline-flex items-center gap-1">
                {{ c.label }}
                <ArrowUpDown :size="11" :class="sortKey === c.key ? 'opacity-100' : 'opacity-30'" />
              </span>
            </th>
          </tr>
          <tr>
            <th v-for="c in COLS" :key="c.key" class="px-2 pb-2 bg-[var(--surface)] border-b border-[var(--border)]">
              <input
                v-model="filters[c.key]"
                type="text"
                :placeholder="`filter…`"
                class="w-full min-w-[80px] px-2 py-1 text-xs font-normal rounded border border-[var(--border)] bg-[var(--surface-2)] text-[var(--text)] focus:outline-none"
                @click.stop
              />
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(r, i) in rows" :key="i" class="hover:bg-[var(--surface-2)] border-b border-[var(--border)]">
            <td class="px-3 py-1.5 italic text-[var(--text)] whitespace-nowrap cursor-pointer" style="font-family: Newsreader, Georgia, serif" @click="store.select(r.source)">{{ r.source }}</td>
            <td class="px-3 py-1.5 whitespace-nowrap">
              <span class="inline-flex items-center gap-1.5">
                <span class="w-2.5 h-1 rounded" :style="{ background: TYPE_COLORS[r.type] }"></span>
                <span class="text-[var(--muted)]">{{ TYPE_LABELS[r.type] || r.type }}</span>
              </span>
            </td>
            <td class="px-3 py-1.5 italic text-[var(--text)] whitespace-nowrap cursor-pointer" style="font-family: Newsreader, Georgia, serif" @click="store.select(r.target)">{{ r.target }}</td>
            <td class="px-3 py-1.5 text-[var(--muted)] whitespace-nowrap">{{ r.locality }}</td>
            <td class="px-3 py-1.5 text-[var(--faint)] whitespace-nowrap">{{ store.scopeLabel(r.scope) }}</td>
            <td class="px-3 py-1.5 text-[var(--faint)]">{{ r.evidence }}</td>
            <td class="px-3 py-1.5 text-[var(--muted)] italic">
              <a :href="refLink(r)" target="_blank" rel="noopener" class="inline-flex items-center gap-1 hover:underline" style="color: var(--accent)">
                {{ r.ref }} <ExternalLink :size="10" class="opacity-70" />
              </a>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
