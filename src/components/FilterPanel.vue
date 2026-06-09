<script setup>
import { ref } from 'vue'
import { Search, Crosshair, Download, Layers } from 'lucide-vue-next'
import {
  useGraphStore, GROUP_COLORS, GROUP_LABELS, TYPE_COLORS, TYPE_LABELS,
} from '../stores/graph'

defineProps({ layout: String })
const emit = defineEmits(['update:layout', 'fit', 'export'])
const store = useGraphStore()
const showResults = ref(false)

const LAYOUTS = [
  { id: 'fcose', label: 'Force' },
  { id: 'concentric', label: 'Concentric' },
  { id: 'circle', label: 'Circle' },
  { id: 'breadthfirst', label: 'Tree' },
]

function pick(id) {
  store.select(id)
  store.setSearch('')
  showResults.value = false
}
function onBlur() {
  window.setTimeout(() => (showResults.value = false), 150)
}
</script>

<template>
  <aside class="w-64 shrink-0 border-r border-[var(--border)] bg-[var(--surface-2)] flex flex-col overflow-y-auto">
    <div class="p-3.5 space-y-4">
      <!-- Search -->
      <div class="relative">
        <Search :size="14" class="absolute left-2.5 top-2.5 text-[var(--faint)]" />
        <input
          :value="store.search"
          @input="store.setSearch($event.target.value); showResults = true"
          @focus="showResults = true"
          @blur="onBlur"
          type="text"
          placeholder="Search a taxon…"
          class="w-full pl-8 pr-2 py-1.5 text-sm rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:ring-2"
          style="--tw-ring-color: var(--accent)"
        />
        <ul
          v-if="showResults && store.searchMatches.length"
          class="absolute z-20 mt-1 w-full bg-[var(--surface)] rounded-lg shadow-lg border border-[var(--border)] overflow-hidden"
        >
          <li
            v-for="m in store.searchMatches"
            :key="m.id"
            @mousedown.prevent="pick(m.id)"
            class="px-3 py-1.5 text-sm italic hover:bg-[var(--surface-3)] cursor-pointer flex items-center gap-2 text-[var(--text)]"
            style="font-family: Newsreader, Georgia, serif"
          >
            <span class="w-2 h-2 rounded-full" :style="{ background: GROUP_COLORS[m.group] }"></span>
            {{ m.id }}
          </li>
        </ul>
      </div>

      <!-- Layout + controls -->
      <div>
        <h3 class="panel-h"><Layers :size="12" /> Layout</h3>
        <div class="grid grid-cols-2 gap-1.5">
          <button
            v-for="l in LAYOUTS"
            :key="l.id"
            @click="emit('update:layout', l.id)"
            class="text-xs py-1 rounded-md border transition"
            :style="layout === l.id
              ? { background: 'var(--accent)', color: '#fff', borderColor: 'var(--accent)' }
              : {}"
            :class="layout === l.id ? '' : 'bg-[var(--surface)] text-[var(--muted)] border-[var(--border)] hover:border-[var(--faint)]'"
          >
            {{ l.label }}
          </button>
        </div>
        <div class="flex gap-1.5 mt-2">
          <button class="ctrl" @click="emit('fit')"><Crosshair :size="13" /> Fit</button>
          <button class="ctrl" @click="emit('export')"><Download :size="13" /> PNG</button>
        </div>
      </div>

      <!-- Interaction types -->
      <div>
        <h3 class="panel-h">Interaction types</h3>
        <label v-for="t in store.allTypes" :key="t" class="row">
          <input type="checkbox" :checked="store.activeTypes.includes(t)" @change="store.toggleType(t)" :style="{ accentColor: 'var(--accent)' }" />
          <span class="w-3 h-1.5 rounded" :style="{ background: TYPE_COLORS[t] }"></span>
          <span class="flex-1 text-[var(--text)]">{{ TYPE_LABELS[t] }}</span>
          <span class="text-[10px] text-[var(--faint)] tabular-nums">{{ store.typeCounts[t] }}</span>
        </label>
      </div>

      <!-- Taxon groups -->
      <div>
        <h3 class="panel-h">Taxon groups</h3>
        <label v-for="g in store.allGroups" :key="g" class="row">
          <input type="checkbox" :checked="store.activeGroups.includes(g)" @change="store.toggleGroup(g)" :style="{ accentColor: 'var(--accent)' }" />
          <span class="w-3 h-3 rounded-full" :style="{ background: GROUP_COLORS[g] }"></span>
          <span class="flex-1 text-[var(--text)]">{{ GROUP_LABELS[g] || g }}</span>
          <span class="text-[10px] text-[var(--faint)] tabular-nums">{{ store.groupCounts[g] }}</span>
        </label>
      </div>

      <!-- Locality scope -->
      <div>
        <h3 class="panel-h">Locality scope</h3>
        <label v-for="sc in store.allScopes" :key="sc" class="row">
          <input type="checkbox" :checked="store.activeScopes.includes(sc)" @change="store.toggleScope(sc)" :style="{ accentColor: 'var(--accent)' }" />
          <span class="flex-1 text-[var(--text)]">{{ store.scopeLabel(sc) }}</span>
        </label>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.panel-h {
  display: flex; align-items: center; gap: 4px;
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.05em; color: var(--faint); margin-bottom: 6px;
}
.row {
  display: flex; align-items: center; gap: 8px;
  font-size: 14px; padding: 2px 0; cursor: pointer; user-select: none;
}
.ctrl {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 4px;
  font-size: 12px; padding: 4px 0; border-radius: 6px;
  border: 1px solid var(--border); background: var(--surface); color: var(--muted);
  transition: border-color 0.15s;
}
.ctrl:hover { border-color: var(--faint); }
</style>
