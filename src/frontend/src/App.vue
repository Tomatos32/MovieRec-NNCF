<template>
  <router-view />
</template>

<script setup lang="ts">
// 全局样式与基础配置均在 main.ts 与 index.html 中完成
// 路由自动进入 Home 或 Login
</script>

<style>
/* 全局样式预留 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
