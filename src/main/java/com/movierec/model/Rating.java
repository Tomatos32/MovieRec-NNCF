package com.movierec.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.relational.core.mapping.Table;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Table("ratings")
public class Rating {
    @Id
    private Long id;
    private Long userId;
    private Long movieId;
    private Double rating;
    private Long timestamp;
    private LocalDateTime createdAt;
}
