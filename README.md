# MovieRec-NNCF

## 项目概述
MovieRec-NNCF 是一个基于神经矩阵分解（NeuMF）构建的双模工业级关联推荐引擎。本项目采用核心业务调度与深度学习推理相解耦的端到端微服务架构。在实现个性化推荐的同时，建立基于实时交互时间截的高可用冷启动降级策略及数据漂移监控机制。

## 核心架构与工程设计

### 1. 业务网关与动态调度层 (Spring Boot)
- **非阻塞 I/O**：使用基于 WebFlux/Reactor (Mono, ReactiveRedisTemplate) 的异步调用链路控制系统总资源。
- **双模路由及熔断隔离 (Resilience4j)**：根据交互阈值判定冷启动状态，或向 FastAPI 侧下发推理请求。基于严格的超时中断（150ms 级别）实现网络隔离熔断，在模型挂起时自动降级提供安全兜底数据。
- **混合缓存策略**：借由短效语义 Cache 和全平台 ZSET 热门榜单构成流量穿透屏障。

### 2. 模型推理边车 (PyTorch + FastAPI)
- **神经计算与维度投射**：NeuMF 网络集成 GMF（广义矩阵分解）与 MLP（多层感知机）双通道嵌入隔离。利用塔式级联与权值衰减抑制过拟合。
- **运行时环境保证**：模型服务在 `startup` 载入权重锁定为 Eval 模式；所有的请求合并至 `torch.no_grad()` 上下文流中执行快速批处理推演，最大程度消除显存侧泄漏风险。

### 3. 数据总线与离线计算环境 (Kafka + Python Pipeline)
- **多端闭环反馈**：依托 Kafka 构建跨服务的事件流；包含用于捕捉临时兴趣迁移的在线侧消费集群 (`realtime-profiler`) 与维护长期一致性的落地存储 (`datalake-archiver`)。
- **数据工程体系**：借助 Pandas/Dataset 构建涵盖：1:4 比例动态负采样、去极化隐式评分（1-5星二值隐性转换）与遵守未来不发生数据泄露（Future Data Leakage）的严格 Leave-One-Out 验证流划分。
- **持久层结构设计**：
  -  MySQL 8.0+ InnoDB 提供交互记录的范围分区主键定义与复合聚簇索引能力。
  -  Redis 提供用于短期会话特征 (User Profile HASH) 维持的内存聚合。

### 4. 前端视窗交互 (Vue 3 + Tailwind CSS)
- **防高频攻击防护**：摒弃传统实现构建专用防抖（Debounce）及指令层拦截包装栈，规避恶意埋点的高频连击风险引发的总线震荡。
- **视觉及动效工程**：使用 Composition + TS 特性重制网格卡片排列逻辑。依据 HTTP Response 类型触发界面无感知的“降级冷启动”微交互，配合骨架屏（Skeleton Loading）过渡网络延迟边界。

## 目录结构
```text
MovieRec-NNCF/
├── data_pipeline/         # 负采样、清洗与离线流切分器
├── docs/                  # 包含架构 SPEC 与追踪 TRACK 的相关规范文档
├── inference/             # 基于 FastAPI + PyTorch 提供预测推演微服务
├── model/                 # neuMF 神经网络层、激活及损失监控代码定义
├── sql/                   # DDL 表结构与时间分区建立 SQL 实体脚本
└── src/
    ├── main/java/         # 核心路由管控中心、事件消费者及反馈探针业务代码
    └── frontend/          # Vite + Vue 3 的前端资产
```

## 部署与启动指引

1. **环境准备**
   - JDK 17 及 Maven 构建链
   - Python 3.8+ (CUDA 环境)，通过 `pip install -r inference/requirements.txt` 加载推理引擎所需依赖。
   - Node.js 18.x

2. **数据库与流组件服务拉起**
   - 请按本地环境确保实例开放（MySQL, Redis, Kafka Broker），并载入 `sql/schema.sql` 结构映射。

3. **微服务集群启动**
   - 推理计算挂载端：`cd inference && uvicorn main:app --port 8000`
   - 主业务路由应用：启动 Spring Boot 应用入口 `MovieRecApplication`。
   - 交互呈现层：`cd src/frontend && npm install && npm run dev`

更多任务及交付点梳理参见 [TODO_MovieRec](./docs/MovieRec/TODO_MovieRec.md)。
