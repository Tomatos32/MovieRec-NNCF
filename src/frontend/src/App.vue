<template>
  <div class="app-container">
    <!-- ========== 顶部导航栏 ========== -->
    <header class="app-header">
      <div class="header-inner">
        <div class="header-brand">
          <svg class="brand-icon" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18" />
            <line x1="7" y1="2" x2="7" y2="22" />
            <line x1="17" y1="2" x2="17" y2="22" />
            <line x1="2" y1="12" x2="22" y2="12" />
            <line x1="2" y1="7" x2="7" y2="7" />
            <line x1="2" y1="17" x2="7" y2="17" />
            <line x1="17" y1="7" x2="22" y2="7" />
            <line x1="17" y1="17" x2="22" y2="17" />
          </svg>
          <h1 class="brand-title">MovieRec</h1>
          <span class="brand-tag">NeuMF Engine</span>
        </div>

        <div class="header-controls">
          <!-- 冷启动状态提示 -->
          <transition name="fade">
            <span v-if="isColdStart" class="cold-start-badge">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
              冷启动模式
            </span>
          </transition>

          <!-- 用户 ID 输入 -->
          <div class="user-input-group">
            <label for="userId">User ID</label>
            <input
              id="userId"
              v-model.number="userId"
              type="number"
              min="0"
              placeholder="输入用户 ID"
              @keydown.enter="loadRecommendations"
            />
            <button class="btn-load" @click="loadRecommendations" :disabled="isLoading">
              {{ isLoading ? '加载中...' : '获取推荐' }}
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- ========== 主内容区域 ========== -->
    <main class="app-main">
      <!-- 错误提示 -->
      <div v-if="hasError" class="error-banner">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="15" y1="9" x2="9" y2="15" />
          <line x1="9" y1="9" x2="15" y2="15" />
        </svg>
        <span>{{ errorMessage }}</span>
        <button @click="loadRecommendations">重试</button>
      </div>

      <!-- 骨架屏加载态 -->
      <div v-if="isLoading" class="movie-grid">
        <SkeletonCard v-for="i in 12" :key="'sk-' + i" />
      </div>

      <!-- 空状态 -->
      <div v-else-if="movies.length === 0 && !hasError" class="empty-state">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
          <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18" />
          <line x1="7" y1="2" x2="7" y2="22" />
          <line x1="17" y1="2" x2="17" y2="22" />
          <line x1="2" y1="12" x2="22" y2="12" />
        </svg>
        <h2>发现你的下一部好电影</h2>
        <p>输入你的用户 ID，AI 将为你生成个性化推荐</p>
      </div>

      <!-- 电影卡片网格 -->
      <div v-else class="movie-grid">
        <transition-group name="card-enter">
          <MovieCard
            v-for="(movie, index) in movies"
            :key="movie.movieId"
            :movie="movie"
            :style="{ animationDelay: `${index * 50}ms` }"
            @click="onMovieClick"
            @dislike="onMovieDislike"
          />
        </transition-group>
      </div>
    </main>

    <!-- ========== 底部信息栏 ========== -->
    <footer class="app-footer">
      <p>MovieRec-NNCF &middot; 基于 NeuMF 神经矩阵分解的工业级推荐引擎</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import MovieCard from './components/MovieCard.vue'
import SkeletonCard from './components/SkeletonCard.vue'
import { useRecommendations } from './composables/useRecommendations'
import { useDebounce } from './composables/useDebounce'
import type { FeedbackPayload } from './types'

const userId = ref<number>(1)

const {
  movies,
  isLoading,
  hasError,
  errorMessage,
  isColdStart,
  fetchRecommendations,
  sendFeedback,
} = useRecommendations()

const { debounce } = useDebounce()

/** 拉取推荐列表 */
const loadRecommendations = () => {
  if (userId.value >= 0) {
    fetchRecommendations(userId.value)
  }
}

/** 构造反馈负载的工厂函数 */
const buildPayload = (movieId: number, actionType: FeedbackPayload['actionType']): FeedbackPayload => ({
  userId: userId.value,
  movieId,
  actionType,
  timestamp: Date.now(),
})

/**
 * 防抖化的反馈上报 —— 600ms 防抖窗口
 * 防止恶意高频连击压垮后端 Kafka 队列
 */
const debouncedFeedback = debounce((payload: FeedbackPayload) => {
  sendFeedback(payload)
}, 600)

/** 用户点击电影详情 */
const onMovieClick = (movieId: number) => {
  debouncedFeedback(buildPayload(movieId, 'click'))
}

/** 用户点击不喜欢 */
const onMovieDislike = (movieId: number) => {
  debouncedFeedback(buildPayload(movieId, 'dislike'))
}
</script>

<style scoped>
/* ========== 布局 ========== */
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* ========== 顶部导航栏 ========== */
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(10, 10, 15, 0.82);
  backdrop-filter: blur(16px) saturate(180%);
  border-bottom: 1px solid var(--color-border);
}

.header-inner {
  max-width: 1440px;
  margin: 0 auto;
  padding: 14px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-icon {
  color: var(--color-accent);
}

.brand-title {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.brand-tag {
  font-size: 11px;
  font-weight: 500;
  color: var(--color-accent-light);
  background: var(--color-accent-glow);
  padding: 2px 10px;
  border-radius: 20px;
  letter-spacing: 0.03em;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

/* 冷启动角标 */
.cold-start-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 500;
  color: var(--color-warning);
  background: rgba(251, 191, 36, 0.1);
  padding: 4px 12px;
  border-radius: 20px;
  border: 1px solid rgba(251, 191, 36, 0.25);
}

/* 用户输入组 */
.user-input-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-input-group label {
  font-size: 13px;
  color: var(--color-text-secondary);
  font-weight: 500;
}

.user-input-group input {
  width: 120px;
  padding: 7px 12px;
  font-size: 13px;
  color: var(--color-text-primary);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  outline: none;
  transition: border-color var(--transition-fast);
}

.user-input-group input:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-accent-glow);
}

.btn-load {
  padding: 7px 18px;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  background: var(--color-accent);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.btn-load:hover:not(:disabled) {
  background: var(--color-accent-light);
  box-shadow: 0 0 16px var(--color-accent-glow);
}

.btn-load:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ========== 主内容 ========== */
.app-main {
  flex: 1;
  max-width: 1440px;
  width: 100%;
  margin: 0 auto;
  padding: 32px;
}

/* 卡片网格 */
.movie-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 24px;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 120px 32px;
  color: var(--color-text-muted);
}

.empty-state svg {
  margin-bottom: 20px;
  opacity: 0.3;
}

.empty-state h2 {
  font-size: 22px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.empty-state p {
  font-size: 14px;
}

/* 错误横幅 */
.error-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  margin-bottom: 24px;
  background: rgba(248, 113, 113, 0.08);
  border: 1px solid rgba(248, 113, 113, 0.2);
  border-radius: var(--radius-sm);
  color: var(--color-danger);
  font-size: 14px;
}

.error-banner button {
  margin-left: auto;
  padding: 4px 14px;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-danger);
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.error-banner button:hover {
  background: rgba(248, 113, 113, 0.15);
}

/* ========== 底部 ========== */
.app-footer {
  padding: 24px 32px;
  text-align: center;
  font-size: 12px;
  color: var(--color-text-muted);
  border-top: 1px solid var(--color-border);
}

/* ========== 动画 ========== */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-normal);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.card-enter-enter-active {
  animation: cardIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes cardIn {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* ========== 响应式 ========== */
@media (max-width: 768px) {
  .header-inner {
    padding: 12px 16px;
  }

  .app-main {
    padding: 20px 16px;
  }

  .movie-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 16px;
  }

  .user-input-group input {
    width: 90px;
  }
}

@media (max-width: 480px) {
  .movie-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .brand-tag {
    display: none;
  }
}
</style>
