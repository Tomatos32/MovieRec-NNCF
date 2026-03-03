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
@Table("movies")
public class Movie {
    @Id
    private Long id;
    private String title;
    private String genres;
    private Integer releaseYear;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
