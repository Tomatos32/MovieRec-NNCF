package com.movierec.repository;

import com.movierec.model.Rating;
import org.springframework.data.r2dbc.repository.R2dbcRepository;
import reactor.core.publisher.Mono;

public interface RatingRepository extends R2dbcRepository<Rating, Long> {
    Mono<Long> countByUserId(Long userId);
}
