package com.movierec.service;

import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import io.github.resilience4j.timelimiter.annotation.TimeLimiter;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class RecommendationService {

    private final ReactiveStringRedisTemplate redisTemplate;
    private final WebClient webClient;
    private final ObjectMapper objectMapper;

    // TODO: 从数据库或缓存中判断用户是否产生过足够的交互行为
    private static final int COLD_START_THRESHOLD = 5;

    @Value("${sidecar.url:http://127.0.0.1:8000}")
    private String sidecarUrl;

    @Autowired
    public RecommendationService(ReactiveStringRedisTemplate redisTemplate, WebClient.Builder webClientBuilder, ObjectMapper objectMapper) {
        this.redisTemplate = redisTemplate;
        this.webClient = webClientBuilder.baseUrl(sidecarUrl).build();
        this.objectMapper = objectMapper;
    }

    /**
     * 核心双模路由判定
     */
    public Mono<List<Long>> getRecommendationForUser(Long userId, int topK) {
        return getUserInteractionCount(userId)
                .flatMap(interactionCount -> {
                    if (interactionCount < COLD_START_THRESHOLD) {
                        // 模式 A: 冷启动降级，直接返回热门推荐
                        return getPopularFallback(topK);
                    } else {
                        // 模式 B: 深度个性化推荐
                        return getPersonalizedRecommendation(userId, topK);
                    }
                });
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
    @CircuitBreaker(name = "inferenceSidecar", fallbackMethod = "sidecarFallback")
    @TimeLimiter(name = "inferenceSidecar") // 对应配置文件的 150ms
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
        // 可引入日志记录 Throwable 细节
        return getPopularFallback(topK);
    }

    /**
     * 模式 A: 从 Redis 读取基于威尔逊区间计算出的排行榜冷启动数据
     */
    private Mono<List<Long>> getPopularFallback(int topK) {
        String key = "rec:popular:topk";
        return redisTemplate.opsForZSet().reverseRange(key, 0, topK - 1)
                .map(Long::valueOf)
                .collectList();
    }

    /**
     * 模拟获取用户历史交互次数 (实际可从数据库或 Redis 中提取)
     */
    private Mono<Integer> getUserInteractionCount(Long userId) {
        // TODO: 查询 Interactions 表或者直接查询 Redis Bitmap / Set 缓存统计结果
        // 模拟返回：假设尾号为0的用户是新用户
        return Mono.just(userId % 10 == 0 ? 0 : 10);
    }
}
