<template>
  <div class="movie-card" @click="handleClick">
    <!-- 海报区域 -->
    <div class="card-poster">
      <img
        :src="movie.posterUrl || fallbackPoster"
        :alt="movie.title"
        loading="lazy"
        @error="onImgError"
      />
      <!-- AI 推荐匹配度角标 -->
      <span class="match-badge">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
        </svg>
        {{ matchPercent }}%
      </span>
    </div>

    <!-- 信息区域 -->
    <div class="card-body">
      <h3 class="card-title">{{ movie.title }}</h3>
      <p class="card-genres">{{ formattedGenres }}</p>

      <!-- 操作按钮区 -->
      <div class="card-actions">
        <button
          class="btn-dislike"
          title="不感兴趣"
          @click.stop="handleDislike"
          :disabled="isDislikeDisabled"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17" />
          </svg>
          不喜欢
        </button>
        <button class="btn-detail" @click.stop="handleClick">
          查看详情 →
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Movie } from '../types'

const props = defineProps<{
  movie: Movie
}>()

const emit = defineEmits<{
  (e: 'click', movieId: number): void
  (e: 'dislike', movieId: number): void
}>()

const isDislikeDisabled = ref(false)

const fallbackPoster = 'https://placehold.co/300x450/1a1a28/5e5e78?text=No+Poster'

const matchPercent = computed(() => Math.round(props.movie.score * 100))

const formattedGenres = computed(() =>
  props.movie.genres
    .split('|')
    .slice(0, 3)
    .join(' · ')
)

const handleClick = () => {
  emit('click', props.movie.movieId)
}

const handleDislike = () => {
  isDislikeDisabled.value = true
  emit('dislike', props.movie.movieId)
  // 3 秒后重新启用按钮
  setTimeout(() => {
    isDislikeDisabled.value = false
  }, 3000)
}

const onImgError = (e: Event) => {
  const target = e.target as HTMLImageElement
  target.src = fallbackPoster
}
</script>

<style scoped>
.movie-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
  transition: transform var(--transition-normal), box-shadow var(--transition-normal);
  cursor: pointer;
}

.movie-card:hover {
  transform: translateY(-6px);
  box-shadow: var(--shadow-card-hover);
  border-color: rgba(124, 92, 252, 0.2);
}

/* 海报 */
.card-poster {
  position: relative;
  width: 100%;
  aspect-ratio: 2 / 3;
  overflow: hidden;
  background: var(--color-bg-skeleton);
}

.card-poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform var(--transition-normal);
}

.movie-card:hover .card-poster img {
  transform: scale(1.05);
}

/* 匹配度角标 */
.match-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  background: rgba(124, 92, 252, 0.85);
  backdrop-filter: blur(8px);
  border-radius: 20px;
  letter-spacing: 0.02em;
}

/* 信息区 */
.card-body {
  padding: 14px 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-genres {
  font-size: 12px;
  color: var(--color-text-secondary);
  letter-spacing: 0.03em;
}

/* 操作按钮 */
.card-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
  gap: 8px;
}

.btn-dislike {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  font-size: 12px;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.btn-dislike:hover:not(:disabled) {
  color: var(--color-danger);
  border-color: var(--color-danger);
  background: rgba(248, 113, 113, 0.08);
}

.btn-dislike:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-detail {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-accent-light);
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.btn-detail:hover {
  background: var(--color-accent-glow);
}
</style>
