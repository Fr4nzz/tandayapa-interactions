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
  // delay so a click on a result registers before the list closes
  window.setTimeout(() => (showResults.value = false), 150)
}
</script>

<template>
  <aside class="w-64 shrink-0 border-r border-slate-200 bg-slate-50/80 backdrop-blur flex flex-col overflow-y-auto">
    <div class="p-3.5 space-y-4">
      <!-- Search -->
      <div class="relative">
        <Search :size="14" class="absolute left-2.5 top-2.5 text-slate-400" />
        <input
          :value="store.search"
          @input="store.setSearch($event.target.value); showResults = true"
          @focus="showResults = true"
          @blur="onBlur"
          type="text"
          placeholder="Search a taxon…"
          class="w-full pl-8 pr-2 py-1.5 text-sm rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-300"
        />
        <ul
          v-if="showResults && store.searchMatches.length"
          class="absolute z-20 mt-1 w-full bg-white rounded-lg shadow-lg border border-slate-200 overflow-hidden"
        >
          <li
            v-for="m in store.searchMatches"
            :key="m.id"
            @mousedown.prevent="pick(m.id)"
            class="px-3 py-1.5 text-sm italic hover:bg-emerald-50 cursor-pointer flex items-center gap-2"
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
            :class="layout === l.id
              ? 'bg-slate-800 text-white border-slate-800'
              : 'bg-white text-slate-600 border-slate-200 hover:border-slate-400'"
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
        <label
          v-for="t in store.allTypes"
          :key="t"
          class="flex items-center gap-2 text-sm py-0.5 cursor-pointer select-none"
        >
          <input type="checkbox" :checked="store.activeTypes.includes(t)" @change="store.toggleType(t)" class="accent-emerald-500" />
          <span class="w-3 h-1.5 rounded" :style="{ background: TYPE_COLORS[t] }"></span>
          <span class="text-slate-700 flex-1">{{ TYPE_LABELS[t] }}</span>
          <span class="text-[10px] text-slate-400 tabular-nums">{{ store.typeCounts[t] }}</span>
        </label>
      </div>

      <!-- Taxon groups -->
      <div>
        <h3 class="panel-h">Taxon groups</h3>
        <label
          v-for="g in store.allGroups"
          :key="g"
          class="flex items-center gap-2 text-sm py-0.5 cursor-pointer select-none"
        >
          <input type="checkbox" :checked="store.activeGroups.includes(g)" @change="store.toggleGroup(g)" class="accent-emerald-500" />
          <span class="w-3 h-3 rounded-full" :style="{ background: GROUP_COLORS[g] }"></span>
          <span class="text-slate-700 flex-1">{{ GROUP_LABELS[g] || g }}</span>
          <span class="text-[10px] text-slate-400 tabular-nums">{{ store.groupCounts[g] }}</span>
        </label>
      </div>

      <!-- Locality scope -->
      <div>
        <h3 class="panel-h">Locality scope</h3>
        <label
          v-for="sc in store.allScopes"
          :key="sc"
          class="flex items-center gap-2 text-sm py-0.5 cursor-pointer select-none"
        >
          <input type="checkbox" :checked="store.activeScopes.includes(sc)" @change="store.toggleScope(sc)" class="accent-emerald-500" />
          <span class="text-slate-700 flex-1">{{ store.scopeLabel(sc) }}</span>
        </label>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.panel-h {
  display: flex; align-items: center; gap: 4px;
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.05em; color: #94a3b8; margin-bottom: 6px;
}
.ctrl {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 4px;
  font-size: 12px; padding: 4px 0; border-radius: 6px;
  border: 1px solid #e2e8f0; background: #fff; color: #475569;
  transition: border-color 0.15s;
}
.ctrl:hover { border-color: #94a3b8; }
</style>
