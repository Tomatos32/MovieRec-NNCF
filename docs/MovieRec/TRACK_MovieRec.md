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

### M2: 数据工程与离线特征管道 (feat/m2-data-engineering)
- [x] 分支创建与环境确认
- [x] **数据清洗与划分 (`data_pipeline/data_processor.py`)**
  - [x] 1-5星隐式反馈二值化转换
  - [x] Leave-One-Out 时间戳划分法
- [x] **PyTorch Dataset (`data_pipeline/data_processor.py`)**
  - [x] UserID / MovieID 连续化索引映射
  - [x] 动态负采样生成器 (1:4 正负比例，均匀抽取)

#### 测试与检查事项 (M2)
- [x] 数据集比例检查：`__len__` 返回的正负样本比例严格为 1:4。
- [x] Future Data Leakage：采用基于时间戳排序的严格 Leave-One-Out 划分。

### M3: 神经矩阵分解深度模型构建 (feat/m3-neumf-model)
- [x] 分支创建与环境确认
- [x] **NeuMF PyTorch 网络 (`model/neumf.py`)**
  - [x] GMF / MLP 双通道独立 Embedding
  - [x] MLP 塔式减半架构与 ReLU 非线性映射
  - [x] GMF 点乘与 MLP 级联的联合全连接 Fusion Layer
  - [x] 仅在 MLP 参数与 Embedding 上使用 Weight Decay 正则化引擎
  - [x] 带梯度追踪的 Single Epoch 训练循环

#### 测试与检查事项 (M3)
- [x] 架构检查：维度映射一致，双 Embedding 均不发生共享。
- [x] 优化与损失函数：BCELoss 输出介于 0-1 的二分类似然。仅对包含 mlp 关键字层加惩罚。

### M4: FastAPI 推理边车微服务 (feat/m4-fastapi-sidecar)
- [x] 分支创建与环境确认
- [x] **推理边车构建 (`inference/main.py`)**
  - [x] 生命周期事件载入：`startup` 缓存加载模型权重与 Eval 模式锁定 
  - [x] REST 接口：`POST /api/predict`
  - [x] Batch 批处理：对请求中的候选电影 ID 构建 Tensor 进行并行非梯度推断
  - [x] 数据排序与响应：输出降序排列的 Top-K 电影得分数组

#### 测试与检查事项 (M4)
- [x] 无梯度计算检查：使用 `torch.no_grad()` 上下文防止 OOM 内存泄漏。
- [x] 网络延迟保障：采用异步 ASGI (FastAPI + Uvicorn) 保障极低延迟响应。

---
