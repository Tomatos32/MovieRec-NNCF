package com.movierec;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.data.r2dbc.repository.config.EnableR2dbcRepositories;

@SpringBootApplication
@EnableR2dbcRepositories(basePackages = "com.movierec.repository")
public class MovieRecApplication {
    public static void main(String[] args) {
        SpringApplication.run(MovieRecApplication.class, args);
    }
}
