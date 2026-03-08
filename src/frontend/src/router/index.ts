import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/login',
            name: 'login',
            component: () => import('@/views/Login.vue'),
            meta: { requiresGuest: true }
        },
        {
            path: '/',
            name: 'home',
            component: () => import('@/views/Home.vue'),
            meta: { requiresAuth: true }
        }
    ]
})

router.beforeEach((to, _from, next) => {
    const userStore = useUserStore()

    if (to.meta.requiresAuth && !userStore.isAuthenticated) {
        next('/login')
    } else if (to.meta.requiresGuest && userStore.isAuthenticated) {
        next('/')
    } else {
        next()
    }
})

export default router
