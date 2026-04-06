import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

import HomeView from './views/HomeView.vue'
import KnowledgeView from './views/KnowledgeView.vue'
import WikiView from './views/WikiView.vue'
import ImportView from './views/ImportView.vue'
import ReviewView from './views/ReviewView.vue'
import IdeasView from './views/IdeasView.vue'
import GrowthView from './views/GrowthView.vue'
import CollectionsView from './views/CollectionsView.vue'
import GraphView from './views/GraphView.vue'
import SettingsView from './views/SettingsView.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/',                      component: HomeView },
    { path: '/knowledge',             component: KnowledgeView },
    { path: '/wiki/:path(.*)',        component: WikiView },
    { path: '/import',                component: ImportView },
    { path: '/review',                component: ReviewView },
    { path: '/ideas',                 component: IdeasView },
    { path: '/growth',                component: GrowthView },
    { path: '/collections/:id',       component: CollectionsView },
    { path: '/graph',                 component: GraphView },
    { path: '/settings',              component: SettingsView },
  ],
})

createApp(App).use(router).mount('#app')
