<template>
  <div class="min-h-screen bg-gray-900 text-gray-100 font-sans p-6 md:p-12 lg:px-24">
    <!-- 头部标题区 -->
    <header class="mb-12 flex flex-col md:flex-row md:justify-between md:items-end border-b border-gray-800 pb-6">
      <div>
        <h1 class="text-4xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-500 to-purple-500 tracking-tight">
          MovieRec NNCF
        </h1>
        <p class="text-gray-400 mt-3 text-lg font-medium">深度神经矩阵分解与实时反馈协同系统 (Vue 3)</p>
      </div>
      
      <!-- 冷启动或个性化状态微交互标识 -->
      <div v-if="!isLoading" class="mt-6 md:mt-0 flex items-center space-x-3 bg-gray-800/80 px-5 py-2.5 rounded-full border border-gray-700 shadow-sm backdrop-blur-sm">
        <template v-if="isColdStart">
          <span class="relative flex h-3.5 w-3.5">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-3.5 w-3.5 bg-yellow-500"></span>
          </span>
          <span class="text-sm font-semibold text-yellow-500 tracking-wide uppercase">Cold Start Mode (Trending)</span>
        </template>
        <template v-else>
          <span class="relative flex h-3.5 w-3.5">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-3.5 w-3.5 bg-emerald-500"></span>
          </span>
          <span class="text-sm font-semibold text-emerald-500 tracking-wide uppercase">Personalized Engine Active</span>
        </template>
      </div>
    </header>

    <!-- 瀑布流/网格主陈列区 -->
    <main class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5 gap-8">
      <!-- 骨架屏加载状态 -->
      <template v-if="isLoading">
        <div v-for="i in 10" :key="i" class="bg-gray-800 rounded-xl overflow-hidden shadow-lg animate-pulse flex flex-col">
          <div class="h-72 bg-gray-700 w-full"></div>
          <div class="p-5 flex flex-col flex-grow justify-between">
            <div>
              <div class="h-6 bg-gray-600 rounded-md w-3/4 mb-3"></div>
              <div class="h-4 bg-gray-600 rounded-md w-1/2 mb-5"></div>
            </div>
            <div class="h-10 bg-gray-600 rounded-lg w-full mt-3"></div>
          </div>
        </div>
      </template>

      <!-- 电影卡片展示 -->
      <template v-else>
        <div 
          v-for="movie in movies" 
          :key="movie.movie_id"
          class="bg-gray-800 rounded-xl overflow-hidden shadow-lg transition-transform duration-300 hover:scale-[1.03] group relative cursor-pointer flex flex-col"
          @click="handleCardClick(movie.movie_id)"
        >
          <div class="h-72 bg-gray-700 w-full relative">
            <img 
              :src="movie.poster_url || 'https://via.placeholder.com/300x450/1f2937/9ca3af?text=No+Poster'" 
              :alt="movie.title" 
              class="object-cover h-full w-full opacity-80 group-hover:opacity-100 transition-opacity duration-300"
            />
            <!-- AI 特征匹配度 -->
            <div v-if="movie.score" class="absolute top-3 right-3 bg-gradient-to-r from-indigo-500 to-purple-600 text-xs font-bold px-3 py-1 rounded-full shadow-lg text-white">
              {{ (movie.score * 100).toFixed(1) }}% Match
            </div>
          </div>
          <div class="p-5 flex flex-col flex-grow justify-between">
            <div>
              <h3 class="text-lg font-bold text-gray-100 line-clamp-1">{{ movie.title }}</h3>
              <p class="text-indigo-400 text-sm mt-1 mb-3 line-clamp-1">{{ movie.genres }}</p>
            </div>
            <button 
              @click.stop="handleDislikeClick(movie.movie_id)"
              class="w-full bg-gray-700/50 hover:bg-rose-500/80 text-gray-300 hover:text-white font-medium py-2 rounded-lg transition-all duration-300 text-sm flex items-center justify-center space-x-2"
            >
              <span>✗ 不感兴趣</span>
            </button>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

// 定义接口
interface Movie {
  movie_id: number;
  title: string;
  genres: string;
  score: number;
  poster_url?: string;
}

interface ApiResponse {
  code: number;
  mode: string;
  data: Movie[];
}

// 状态声明
const movies = ref<Movie[]>([]);
const isLoading = ref<boolean>(true);
const isColdStart = ref<boolean>(false);

const USER_ID = 1012; // 模拟当前用户 ID

// 自定义防抖执行器，也可以使用 VueUse 的 useDebounceFn
const createDebounce = (fn: Function, delay: number) => {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  return (...args: any[]) => {
    if (timeoutId) clearTimeout(timeoutId);
    timeoutId = setTimeout(() => {
      fn(...args);
    }, delay);
  };
};

// 实际发送异步埋点网络请求的核心方法 (无阻塞抛 Kafka 网关)
const sendFeedbackEvent = (movieId: number, actionType: string) => {
  const payload = {
    user_id: USER_ID,
    movie_id: movieId,
    action_type: actionType,
    timestamp: Date.now()
  };
  console.log(`[Kafka Telemetry Vue3]`, payload);
  // fetch('/api/feedback', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
};

// 绑定防抖
const debouncedClick = createDebounce((movieId: number) => sendFeedbackEvent(movieId, 'click'), 300);
const debouncedDislike = createDebounce((movieId: number) => sendFeedbackEvent(movieId, 'ignore'), 500);

// 事件处理程序
const handleCardClick = (movieId: number) => {
  debouncedClick(movieId);
};

const handleDislikeClick = (movieId: number) => {
  debouncedDislike(movieId);
};

// 生命周期钩子
onMounted(() => {
  isLoading.value = true;
  
  // 模拟基于 axios/fetch 去请求 Spring Boot 主业务 GET /api/recommendations
  setTimeout(() => {
    const mockResponse: ApiResponse = {
      code: 200,
      mode: "cold_start", // 验证模式 A 回退逻辑 
      data: [
        { movie_id: 1, title: 'Inception', genres: 'Action|Sci-Fi|Thriller', score: 0.98 },
        { movie_id: 2, title: 'The Dark Knight', genres: 'Action|Crime|Drama', score: 0.95 },
        { movie_id: 3, title: 'Interstellar', genres: 'Adventure|Drama|Sci-Fi', score: 0.92 },
        { movie_id: 4, title: 'Pulp Fiction', genres: 'Crime|Drama', score: 0.88 },
        { movie_id: 5, title: 'The Matrix', genres: 'Action|Sci-Fi', score: 0.85 },
        { movie_id: 6, title: 'Forrest Gump', genres: 'Drama|Romance', score: 0.82 },
        { movie_id: 7, title: 'Gladiator', genres: 'Action|Adventure|Drama', score: 0.79 },
        { movie_id: 8, title: 'Titanic', genres: 'Drama|Romance', score: 0.75 },
      ]
    };
    
    movies.value = mockResponse.data;
    isColdStart.value = mockResponse.mode === "cold_start";
    isLoading.value = false;
  }, 800);
});
</script>
