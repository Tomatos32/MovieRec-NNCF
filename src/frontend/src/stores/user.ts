import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
    const token = ref(localStorage.getItem('token') || '')
    const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

    const isAuthenticated = computed(() => !!token.value)

    // Mock Login API
    const login = async (credentials: any) => {
        return new Promise((resolve, reject) => {
            setTimeout(() => {
                if (credentials.username === 'admin' && credentials.password !== '123456') {
                    reject(new Error('密码错误'))
                    return
                }

                const mockToken = 'mock-jwt-token-12345'
                const mockUser = { id: 1, username: credentials.username }

                token.value = mockToken
                user.value = mockUser

                localStorage.setItem('token', mockToken)
                localStorage.setItem('user', JSON.stringify(mockUser))

                resolve({ token: mockToken, user: mockUser })
            }, 1000)
        })
    }

    // Mock Register API
    const register = async (userData: any) => {
        return new Promise((resolve, reject) => {
            setTimeout(() => {
                if (userData.username === 'admin') {
                    reject(new Error('用户名已存在'))
                    return
                }
                resolve({ message: 'Success' })
            }, 1000)
        })
    }

    const logout = () => {
        token.value = ''
        user.value = null
        localStorage.removeItem('token')
        localStorage.removeItem('user')
    }

    return {
        token,
        user,
        isAuthenticated,
        login,
        register,
        logout
    }
})
