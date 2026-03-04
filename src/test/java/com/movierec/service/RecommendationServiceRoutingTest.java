package com.movierec.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.movierec.model.Movie;
import com.movierec.repository.MovieRepository;
import com.movierec.repository.RatingRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Range;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.data.redis.core.ReactiveValueOperations;
import org.springframework.data.redis.core.ReactiveZSetOperations;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

import java.util.List;
import java.util.Map;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
public class RecommendationServiceRoutingTest {

    private RecommendationService recommendationService;

    @Mock
    private ReactiveStringRedisTemplate redisTemplate;
    @Mock
    private ReactiveZSetOperations<String, String> zSetOperations;
    @Mock
    private ReactiveValueOperations<String, String> valueOperations;
    @Mock
    private WebClient.Builder webClientBuilder;
    @Mock
    private WebClient webClient;
    @Mock
    private WebClient.RequestBodyUriSpec requestBodyUriSpec;
    @Mock
    private WebClient.RequestBodySpec requestBodySpec;
    @Mock
    @SuppressWarnings("rawtypes")
    private WebClient.RequestHeadersSpec requestHeadersSpec;
    @Mock
    private WebClient.ResponseSpec responseSpec;
    @Mock
    private ObjectMapper objectMapper;
    @Mock
    private RatingRepository ratingRepository;
    @Mock
    private MovieRepository movieRepository;

    @BeforeEach
    void setUp() {
        Mockito.lenient().when(webClientBuilder.baseUrl(anyString())).thenReturn(webClientBuilder);
        Mockito.lenient().when(webClientBuilder.build()).thenReturn(webClient);
        
        Mockito.lenient().when(redisTemplate.opsForZSet()).thenReturn(zSetOperations);
        Mockito.lenient().when(redisTemplate.opsForValue()).thenReturn(valueOperations);

        recommendationService = new RecommendationService(
                redisTemplate, webClientBuilder, objectMapper, ratingRepository, movieRepository, "http://localhost:8000"
        );
    }

    @Test
    void testColdStartUserRouting() {
        Long userId = 1L;
        // Mock rating count < 5 (Cold start)
        when(ratingRepository.countByUserId(userId)).thenReturn(Mono.just(2L));
        
        // Mock popular fallback from Redis
        when(zSetOperations.reverseRange(eq("rec:popular:topk"), any(Range.class)))
                .thenReturn(Flux.just("101", "102"));
                
        Movie m1 = new Movie(); m1.setId(101L); m1.setTitle("Pop Movie 1");
        Movie m2 = new Movie(); m2.setId(102L); m2.setTitle("Pop Movie 2");
        when(movieRepository.findAllByIdIn(anyList())).thenReturn(Flux.just(m1, m2));

        Mono<RecommendationService.RecommendationResult> resultMono = recommendationService.getRecommendationForUser(userId, 2);

        StepVerifier.create(resultMono)
                .expectNextMatches(result -> 
                        "cold-start".equals(result.mode()) && 
                        result.data().size() == 2 &&
                        result.data().get(0).get("movieId").equals(101L))
                .verifyComplete();
    }

    @Test
    void testMatureUserRoutingWithRpc() {
        Long userId = 2L;
        // Mock rating count >= 5 (Mature user)
        when(ratingRepository.countByUserId(userId)).thenReturn(Mono.just(10L));
        
        // Mock semantic cache missing
        when(valueOperations.get("cache:semantic:" + userId)).thenReturn(Mono.empty());
        
        // Mock WebClient for Sidecar RPC
        when(webClient.post()).thenReturn(requestBodyUriSpec);
        when(requestBodyUriSpec.uri(anyString())).thenReturn(requestBodySpec);
        when(requestBodySpec.bodyValue(any())).thenReturn(requestHeadersSpec);
        when(requestHeadersSpec.retrieve()).thenReturn(responseSpec);
        
        Map<String, Object> sidecarResponse = Map.of("data", List.of(
                Map.of("movie_id", 301),
                Map.of("movie_id", 302)
        ));
        when(responseSpec.bodyToMono(Map.class)).thenReturn(Mono.just(sidecarResponse));

        Movie m1 = new Movie(); m1.setId(301L); m1.setTitle("Personalized 1");
        when(movieRepository.findAllByIdIn(anyList())).thenReturn(Flux.just(m1));

        Mono<RecommendationService.RecommendationResult> resultMono = recommendationService.getRecommendationForUser(userId, 2);

        StepVerifier.create(resultMono)
                .expectNextMatches(result -> 
                        "personalized".equals(result.mode()) &&
                        result.data().size() == 1 &&
                        result.data().get(0).get("movieId").equals(301L))
                .verifyComplete();
    }
}
