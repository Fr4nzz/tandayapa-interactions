import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// Project page lives at https://<user>.github.io/tandayapa-interactions/
// so the production base must be the repo name. Local dev stays at '/'.
export default defineConfig({
  base: process.env.GITHUB_ACTIONS ? '/tandayapa-interactions/' : '/',
  plugins: [vue(), tailwindcss()],
})
