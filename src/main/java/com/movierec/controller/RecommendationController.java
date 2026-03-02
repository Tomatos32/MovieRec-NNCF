package com.movierec.controller;

import com.movierec.service.RecommendationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/recommendations")
public class RecommendationController {

    private final RecommendationService recommendationService;

    @Autowired
    public RecommendationController(RecommendationService recommendationService) {
        this.recommendationService = recommendationService;
    }

    /**
     * 获取推荐流接口
     * GET /api/recommendations?userId={id}
     */
    @GetMapping
    public Mono<ResponseEntity<Map<String, Object>>> getRecommendations(
            @RequestParam("userId") Long userId,
            @RequestParam(value = "topK", defaultValue = "10") int topK) {
        
        return recommendationService.getRecommendationForUser(userId, topK)
                .map(movies -> ResponseEntity.ok(Map.of(
                        "code", 200,
                        "message", "Success",
                        "data", movies
                )));
    }
}
