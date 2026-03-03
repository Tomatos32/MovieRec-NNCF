package com.movierec.service;

import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import io.github.resilience4j.timelimiter.annotation.TimeLimiter;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;
import org.springframework.data.domain.Range;
import com.movierec.repository.RatingRepository;
import com.movierec.repository.MovieRepository;
import com.movierec.model.Movie;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.time.Duration;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class RecommendationService {

    private final ReactiveStringRedisTemplate redisTemplate;
    private final WebClient webClient;
    private final ObjectMapper objectMapper;
    private final RatingRepository ratingRepository;
    private final MovieRepository movieRepository;

    private static final int COLD_START_THRESHOLD = 5;

    /**
     * 推荐结果 DTO，包含电影列表和推荐模式
     */
    public record RecommendationResult(List<Map<String, Object>> data, String mode) {}

    @Autowired
    public RecommendationService(ReactiveStringRedisTemplate redisTemplate,
                                 WebClient.Builder webClientBuilder,
                                 ObjectMapper objectMapper,
                                 RatingRepository ratingRepository,
                                 MovieRepository movieRepository,
                                 @Value("${sidecar.url:http://127.0.0.1:8000}") String sidecarUrl) {
        this.redisTemplate = redisTemplate;
        this.webClient = webClientBuilder.baseUrl(sidecarUrl).build();
        this.objectMapper = objectMapper;
        this.ratingRepository = ratingRepository;
        this.movieRepository = movieRepository;
    }

    /**
     * 核心双模路由判定，返回包含完整电影信息和推荐模式的结果
     */
    public Mono<RecommendationResult> getRecommendationForUser(Long userId, int topK) {
        return getUserInteractionCount(userId)
                .flatMap(interactionCount -> {
                    if (interactionCount < COLD_START_THRESHOLD) {
                        // 模式 A: 冷启动降级，直接返回热门推荐
                        return getPopularFallback(topK)
                                .flatMap(movieIds -> enrichMovieIds(movieIds, "cold-start", topK));
                    } else {
                        // 模式 B: 深度个性化推荐
                        return getPersonalizedRecommendation(userId, topK)
                                .flatMap(movieIds -> enrichMovieIds(movieIds, "personalized", topK));
                    }
                });
    }

    /**
     * 将 movieId 列表查数据库补全为完整的 Movie 信息
     * 如果 movieId 列表为空，降级从数据库直接拉一批电影兜底
     */
    private Mono<RecommendationResult> enrichMovieIds(List<Long> movieIds, String mode, int topK) {
        if (movieIds == null || movieIds.isEmpty()) {
            // Redis 无数据时，直接从数据库拉取兜底
            return movieRepository.findTopMovies(topK)
                    .collectList()
                    .map(movies -> toResult(movies, mode));
        }
        return movieRepository.findAllByIdIn(movieIds)
                .collectList()
                .map(movies -> toResult(movies, mode));
    }

    /**
     * Movie 实体列表 → 前端 DTO 列表
     */
    private RecommendationResult toResult(List<Movie> movies, String mode) {
        List<Map<String, Object>> data = movies.stream()
                .map(movie -> Map.<String, Object>of(
                        "movieId", movie.getId(),
                        "title", movie.getTitle() != null ? movie.getTitle() : "未知电影",
                        "genres", movie.getGenres() != null ? movie.getGenres() : "未分类",
                        "score", 0.0,
                        "posterUrl", ""
                ))
                .collect(Collectors.toList());
        return new RecommendationResult(data, mode);
    }

    /**
     * 模式 B: 从语义缓存拉取，若未中则请求 FastAPI Sidecar 进行推断
     */
    private Mono<List<Long>> getPersonalizedRecommendation(Long userId, int topK) {
        String cacheKey = "cache:semantic:" + userId;
        return redisTemplate.opsForValue().get(cacheKey)
                .flatMap(cachedJson -> {
                    try {
                        List<Long> cachedMovies = objectMapper.readValue(cachedJson,
                            objectMapper.getTypeFactory().constructCollectionType(List.class, Long.class));
                        return Mono.just(cachedMovies);
                    } catch (Exception e) {
                        return Mono.empty(); // fallback to sidecar if parsing fails
                    }
                })
                .switchIfEmpty(Mono.defer(() -> invokeSidecarInference(userId, topK)));
    }

    /**
     * 异步调用 FastAPI 边车微服务
     * 结合 Resilience4j 做断路器与极其严格的网络超时(150ms)保护
     */
    @CircuitBreaker(name = "fastApiInference", fallbackMethod = "sidecarFallback")
    @TimeLimiter(name = "fastApiInference")
    private Mono<List<Long>> invokeSidecarInference(Long userId, int topK) {
        // 构建请求报文，由推荐引擎先召回一批 candidate_movie_ids 供给模型推断 (这里用 Dummy Data 代替)
        List<Long> candidateIds = List.of(101L, 105L, 203L, 999L, 404L, 502L, 888L);
        Map<String, Object> requestBody = Map.of(
                "user_id", userId,
                "candidate_movie_ids", candidateIds,
                "top_k", topK
        );

        return webClient.post()
                .uri("/api/predict")
                .bodyValue(requestBody)
                .retrieve()
                .bodyToMono(Map.class)
                .map(response -> {
                    List<Map<String, Object>> data = (List<Map<String, Object>>) response.get("data");
                    return data.stream()
                            .map(item -> Long.valueOf(item.get("movie_id").toString()))
                            .collect(Collectors.toList());
                });
    }

    /**
     * 熔断与超时回退 (Fallback): 当 Sidecar 挂掉或延迟过高，回退至威尔逊热门榜
     */
    public Mono<List<Long>> sidecarFallback(Long userId, int topK, Throwable t) {
        return getPopularFallback(topK);
    }

    /**
     * 模式 A: 从 Redis 读取基于威尔逊区间计算出的排行榜冷启动数据
     */
    private Mono<List<Long>> getPopularFallback(int topK) {
        String key = "rec:popular:topk";
        return redisTemplate.opsForZSet().reverseRange(key, Range.closed(0L, (long) topK - 1))
                .map(Long::valueOf)
                .collectList();
    }

    /**
     * 获取用户历史交互次数 (从数据库中读取)
     */
    private Mono<Integer> getUserInteractionCount(Long userId) {
        return ratingRepository.countByUserId(userId).defaultIfEmpty(0L).map(Long::intValue);
    }
}
