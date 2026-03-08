import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import 'element-plus/dist/index.css' // Import element plus styles
import './style.css'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
