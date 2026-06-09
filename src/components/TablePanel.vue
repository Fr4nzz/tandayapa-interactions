<script setup>
import { ref, computed } from 'vue'
import { ArrowUpDown } from 'lucide-vue-next'
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
function sortBy(k) {
  if (sortKey.value === k) sortDir.value *= -1
  else { sortKey.value = k; sortDir.value = 1 }
}

const rows = computed(() => {
  const visible = store.records.filter((r) => store.isEdgeVisible(r))
  const k = sortKey.value
  return [...visible].sort((a, b) => {
    const av = (a[k] ?? '').toString().toLowerCase()
    const bv = (b[k] ?? '').toString().toLowerCase()
    return av < bv ? -sortDir.value : av > bv ? sortDir.value : 0
  })
})
</script>

<template>
  <div class="w-full h-full flex flex-col bg-[var(--bg)]">
    <div class="px-4 py-2 text-xs text-[var(--muted)] border-b border-[var(--border)]">
      {{ rows.length }} interactions (filtered) · click a header to sort · click a row to focus the taxon
    </div>
    <div class="flex-1 overflow-auto">
      <table class="w-full border-collapse text-sm">
        <thead class="sticky top-0 bg-[var(--surface)] z-10">
          <tr>
            <th
              v-for="c in COLS" :key="c.key"
              class="text-left font-semibold text-[var(--muted)] px-3 py-2 border-b border-[var(--border)] cursor-pointer whitespace-nowrap select-none"
              @click="sortBy(c.key)"
            >
              <span class="inline-flex items-center gap-1">
                {{ c.label }}
                <ArrowUpDown :size="11" :class="sortKey === c.key ? 'opacity-100' : 'opacity-30'" />
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(r, i) in rows" :key="i"
            class="hover:bg-[var(--surface-2)] cursor-pointer border-b border-[var(--border)]"
            @click="store.select(r.source)"
          >
            <td class="px-3 py-1.5 italic text-[var(--text)] whitespace-nowrap" style="font-family: Newsreader, Georgia, serif">{{ r.source }}</td>
            <td class="px-3 py-1.5 whitespace-nowrap">
              <span class="inline-flex items-center gap-1.5">
                <span class="w-2.5 h-1 rounded" :style="{ background: TYPE_COLORS[r.type] }"></span>
                <span class="text-[var(--muted)]">{{ TYPE_LABELS[r.type] || r.type }}</span>
              </span>
            </td>
            <td class="px-3 py-1.5 italic text-[var(--text)] whitespace-nowrap" style="font-family: Newsreader, Georgia, serif">{{ r.target }}</td>
            <td class="px-3 py-1.5 text-[var(--muted)] whitespace-nowrap">{{ r.locality }}</td>
            <td class="px-3 py-1.5 text-[var(--faint)] whitespace-nowrap">{{ store.scopeLabel(r.scope) }}</td>
            <td class="px-3 py-1.5 text-[var(--faint)]">{{ r.evidence }}</td>
            <td class="px-3 py-1.5 text-[var(--muted)] italic">{{ r.ref }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
