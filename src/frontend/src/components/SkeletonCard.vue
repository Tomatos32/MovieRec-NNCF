<template>
  <div class="skeleton-card">
    <div class="skeleton-poster shimmer"></div>
    <div class="skeleton-body">
      <div class="skeleton-line skeleton-title shimmer"></div>
      <div class="skeleton-line skeleton-genre shimmer"></div>
      <div class="skeleton-line skeleton-score shimmer"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 骨架屏卡片 —— 纯展示组件，无需任何逻辑
</script>

<style scoped>
.skeleton-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--color-border);
}

.skeleton-poster {
  width: 100%;
  aspect-ratio: 2 / 3;
  background: var(--color-bg-skeleton);
}

.skeleton-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skeleton-line {
  height: 14px;
  border-radius: 4px;
  background: var(--color-bg-skeleton);
}

.skeleton-title {
  width: 75%;
  height: 18px;
}

.skeleton-genre {
  width: 55%;
}

.skeleton-score {
  width: 35%;
}

/* 微光动画 */
.shimmer {
  position: relative;
  overflow: hidden;
}

.shimmer::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.04) 50%,
    transparent 100%
  );
  animation: shimmer 1.8s infinite;
}

@keyframes shimmer {
  0% { left: -100%; }
  100% { left: 100%; }
}
</style>
