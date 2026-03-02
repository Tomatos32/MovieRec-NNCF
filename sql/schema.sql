-- MySQL DDL 脚本
-- 目标数据库版本: MySQL 8.0+

CREATE DATABASE IF NOT EXISTS movierec_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE movierec_db;

-- 1. users: 用户信息表
CREATE TABLE `users` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '用户主键',
    `username` VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    `password_hash` VARCHAR(255) COMMENT '密码摘要(若需登录验证)',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户信息表';

-- 2. movies: 电影元数据表
CREATE TABLE `movies` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '电影主键',
    `title` VARCHAR(255) NOT NULL COMMENT '电影名称',
    `genres` VARCHAR(255) NOT NULL COMMENT '流派信息(以分隔符分割或JSON)',
    `release_year` INT NOT NULL COMMENT '发行年份',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_movies_genres_year` (`genres`, `release_year`) COMMENT '针对流派和发行年份的复合索引，加速品类聚类和打标分析'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='电影元数据表';

-- 3. ratings: 显式评分表
CREATE TABLE `ratings` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '评分主键',
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `movie_id` BIGINT NOT NULL COMMENT '电影ID',
    `rating` DECIMAL(2,1) NOT NULL COMMENT '显式评分(1.0到5.0星)',
    `timestamp` BIGINT NOT NULL COMMENT '原始时间戳(秒级或毫秒级)',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '库内记录创建时间',
    UNIQUE KEY `uk_user_movie` (`user_id`, `movie_id`) COMMENT '用户针对某部电影的评分联合唯一约束，避免重复刷分'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='显式评分表';

-- 4. interactions: 隐式行为表 
-- 解析: MySQL 8.0 对 TIMESTAMP 分区有部分局限，推荐使用 DATETIME 进行基于 RANGE 或 RANGE COLUMNS 的分区。
-- 规则要求: 针对 interactions 表的 timestamp 建立范围分区索引以支持大数据量的高效查询。并且分区键必须包含在聚合主键中。
CREATE TABLE `interactions` (
    `id` BIGINT AUTO_INCREMENT COMMENT '行为自增ID',
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `movie_id` BIGINT NOT NULL COMMENT '电影ID',
    `action_type` ENUM('click', 'view', 'wishlist') NOT NULL COMMENT '行为类型(点击/长时浏览/加入心愿单)',
    `timestamp` DATETIME NOT NULL COMMENT '行为发生时间',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录生成时间',
    PRIMARY KEY (`id`, `timestamp`),
    INDEX `idx_user_action` (`user_id`, `action_type`) COMMENT '查询某用户特定行为的索引加速'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='隐式行为表'
PARTITION BY RANGE (YEAR(`timestamp`)) (
    PARTITION p_old VALUES LESS THAN (2020),
    PARTITION p_2020 VALUES LESS THAN (2021),
    PARTITION p_2021 VALUES LESS THAN (2022),
    PARTITION p_2022 VALUES LESS THAN (2023),
    PARTITION p_2023 VALUES LESS THAN (2024),
    PARTITION p_2024 VALUES LESS THAN (2025),
    PARTITION p_2025 VALUES LESS THAN (2026),
    PARTITION p_2026 VALUES LESS THAN (2027),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);
-- 备注: 范围分区(Range Partitioning)能够帮助系统在查询某段时间数据，或淘汰远古数据时直接 prune 整个分区文件，极大提升查询及运维性能。
