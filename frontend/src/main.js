import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

import GraphView from './views/GraphView.vue'
import WikiView from './views/WikiView.vue'
import ClipperView from './views/ClipperView.vue'
import SettingsView from './views/SettingsView.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', component: GraphView },
    { path: '/wiki/:path(.*)', component: WikiView },
    { path: '/clip', component: ClipperView },
    { path: '/settings', component: SettingsView },
  ],
})

createApp(App).use(router).mount('#app')
