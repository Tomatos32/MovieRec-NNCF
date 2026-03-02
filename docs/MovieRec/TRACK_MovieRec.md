# TRACK - 进度与测试跟踪文档 (MovieRec-NNCF)

## 任务执行状态
本文件用于记录各个模块的功能实现状态、测试进度与异常记录。

### M1: 基础设施与持久化层建设 (feat/m1-infra-mysql-redis)
- [x] 分支创建与环境确认
- [x] **MySQL DDL 设计 (`sql/schema.sql`)**
  - [x] `users` 表及主键
  - [x] `movies` 表及 `genres` & `release_year` 复合索引
  - [x] `ratings` 表及 `(user_id, movie_id)` 联合唯一约束
  - [x] `interactions` 表及 `timestamp` 范围分区
- [x] **Redis 缓存结构规划 (`docs/MovieRec/Redis_Design.md`)**
  - [x] 热门排行榜 (ZSET)
  - [x] 用户短期会话特征 (HASH)
  - [x] 语义缓存 (STRING)

#### 测试与检查事项 (M1)
- [x] SQL 语法检查：兼容 MySQL 8.0+。
- [x] 分区约束检查：在 MySQL 中，分区键必须是主键/联合主键的一部分。`interactions` 使用 `(id, timestamp)` 作为主键。
- [x] 表引擎检查：均使用 InnoDB，以支持强事务控制与外键级别一致性（应用层控制）。

---
