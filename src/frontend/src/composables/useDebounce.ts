import { ref, onUnmounted } from 'vue'

/**
 * 防抖 composable —— 防止高频连击压垮后端 Kafka 队列
 * @param fn 需要防抖的函数
 * @param delayMs 延迟毫秒数，默认 600ms
 */
export const useDebounce = () => {
    let timer: ReturnType<typeof setTimeout> | null = null
    const isPending = ref(false)

    const debounce = <T extends (...args: any[]) => void>(fn: T, delayMs = 600) => {
        return (...args: Parameters<T>) => {
            isPending.value = true
            if (timer) clearTimeout(timer)
            timer = setTimeout(() => {
                fn(...args)
                isPending.value = false
                timer = null
            }, delayMs)
        }
    }

    onUnmounted(() => {
        if (timer) clearTimeout(timer)
    })

    return { debounce, isPending }
}
