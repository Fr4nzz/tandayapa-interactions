import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './style.css'
import { useThemeStore } from './stores/theme'

const app = createApp(App)
app.use(createPinia())

// Apply persisted theme/mode before mount so there's no flash.
useThemeStore().apply()

app.mount('#app')
