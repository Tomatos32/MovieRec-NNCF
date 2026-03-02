package com.movierec.service.kafka;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

@Service
public class FeedbackPipeline {

    private static final Logger log = LoggerFactory.getLogger(FeedbackPipeline.class);
    private static final String TOPIC_NAME = "user-interaction-events";

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ReactiveStringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;

    @Autowired
    public FeedbackPipeline(KafkaTemplate<String, String> kafkaTemplate, 
                            ReactiveStringRedisTemplate redisTemplate,
                            ObjectMapper objectMapper) {
        this.kafkaTemplate = kafkaTemplate;
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
    }

    /**
     * 1. Kafka 生产者: 将接收到的事件序列化为 JSON 异步发送
     */
    public void sendFeedbackEvent(Long userId, Long movieId, String actionType, Long timestamp) {
        Map<String, Object> event = new HashMap<>();
        event.put("user_id", userId);
        event.put("movie_id", movieId);
        event.put("action_type", actionType);
        event.put("timestamp", timestamp);

        try {
            String payload = objectMapper.writeValueAsString(event);
            // 异步解耦向 Kafka 抛出事件
            kafkaTemplate.send(TOPIC_NAME, String.valueOf(userId), payload)
                    .whenComplete((result, ex) -> {
                        if (ex != null) {
                            log.error("Failed to send Kafka feedback event for User ID: " + userId, ex);
                        }
                    });
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize feedback event", e);
        }
    }

    /**
     * 2. 实时消费者 (在线流处理) - Group: realtime-profiler
     * 目的: 当监听到特定事件(如 click/rate)，实时更新 Redis 中用户的特征会话画像
     */
    @KafkaListener(topics = TOPIC_NAME, groupId = "realtime-profiler")
    public void consumeForRealtimeProfile(String message) {
        try {
            Map<String, Object> event = objectMapper.readValue(message, Map.class);
            String action = (String) event.get("action_type");
            
            // 简单演示: 如果是正面极强的交互或直接打分，记录特征轨迹
            if ("click".equals(action) || "rate".equals(action) || "wishlist".equals(action)) {
                Long userId = ((Number) event.get("user_id")).longValue();
                Long movieId = ((Number) event.get("movie_id")).longValue();
                
                // TODO: 根据 movieId 反查出相应的 Genres 标签，增加权重
                String demoGenre = "Action"; 
                
                String redisKey = "user:session:" + userId + ":genres";
                // 增加该流派的偏好权重分 1.0，并续期
                redisTemplate.opsForHash().increment(redisKey, demoGenre, 1.0).subscribe();
            }
        } catch (Exception e) {
            log.error("Realtime Consumer Error", e);
        }
    }

    /**
     * 3. 离线消费者 (持久化落盘) - Group: datalake-archiver
     * 目的: 全量事件消费并沉淀至本地文件或 MySQL 作为数仓数据，供深夜 PyTorch 离线批处理作业重训
     */
    @KafkaListener(topics = TOPIC_NAME, groupId = "datalake-archiver")
    public void consumeForDataLake(String message) {
        try {
            // 解析并准备入库语句，或在此处累积 Batch 然后执行 MySQL 批量插入
            // 模拟落盘
            log.info("[DataLake Archiver] Persisting to Storage: {}", message);
            // -> insert into interactions (user_id, movie_id, action_type, timestamp) values (...)
        } catch (Exception e) {
            log.error("DataLake Consumer Error", e);
        }
    }
}
