import { defineStore } from 'pinia'

// Accent presets (mirrors the ithomiini_maps theme system: one accent per preset,
// light/dark variants handled by CSS variables keyed on data-mode + data-theme).
export const THEMES = {
  emerald: { name: 'Emerald', accent: '#10b981' },
  ocean: { name: 'Ocean', accent: '#06b6d4' },
  forest: { name: 'Forest', accent: '#84cc16' },
  sunset: { name: 'Sunset', accent: '#f97316' },
  lavender: { name: 'Lavender', accent: '#a78bfa' },
}

const DEFAULT_THEME = 'emerald'
const DEFAULT_MODE = 'dark'

function stored(key, fallback) {
  try { return localStorage.getItem(key) || fallback } catch { return fallback }
}

export const useThemeStore = defineStore('theme', {
  state: () => ({
    mode: stored('tdy-mode', DEFAULT_MODE),
    theme: stored('tdy-theme', DEFAULT_THEME),
  }),
  getters: {
    isDark: (s) => s.mode === 'dark',
    accent: (s) => (THEMES[s.theme] || THEMES[DEFAULT_THEME]).accent,
  },
  actions: {
    apply() {
      const root = document.documentElement
      root.setAttribute('data-mode', this.mode)
      root.setAttribute('data-theme', this.theme)
      root.classList.remove('dark', 'light')
      root.classList.add(this.mode)
      try {
        localStorage.setItem('tdy-mode', this.mode)
        localStorage.setItem('tdy-theme', this.theme)
      } catch { /* storage unavailable */ }
    },
    toggleMode() {
      this.mode = this.mode === 'dark' ? 'light' : 'dark'
      this.apply()
    },
    setTheme(t) {
      if (THEMES[t]) { this.theme = t; this.apply() }
    },
  },
})
