# **基于多源融合与大模型协同的推荐系统：全栈开发流程与Agent提示词库**

本指南严格遵循现代软件工程规范，将系统开发拆解为 7 个高内聚、低耦合的核心模块。每个模块均附带极其详尽的 Agent 开发提示词（Prompt），您可以直接将这些提示词输入给编程大模型（如 Gemini, Claude, ChatGPT 等）以生成达到工业级标准的高质量代码。

## **模块一：基础设施与持久化层建设 (Infrastructure & DB)**

**模块目标：** 搭建系统底层的数据存储基石，设计高度范式化且利于高频读写的 MySQL 数据库表结构，以及支撑亚毫秒级响应的 Redis 缓存结构。

**Agent 开发提示词：**	

**角色与任务：** 你现在是一位资深的 DBA 与后端架构师。请为我的“工业级电影推荐系统”设计 MySQL 数据库（版本 8.0+）的 DDL 脚本，并规划 Redis 的数据结构。

**MySQL 设计需求：**

1. 包含四张核心表：users (用户信息), movies (电影元数据), ratings (显式评分, 1-5星), interactions (隐式行为, Enum: click, view, wishlist)。  
2. 必须包含主键 (Auto Increment / UUID)，以及必要的创建/更新时间戳。  
3. **性能优化：** 针对 movies 表的 genres 和 release\_year 建立复合索引；针对 ratings 表的 (user\_id, movie\_id) 建立联合唯一约束；针对 interactions 表的 timestamp 建立范围分区索引以支持大数据量的高效查询。  
4. 提供带详尽中文注释的 SQL 脚本。

**Redis 缓存结构规划需求：**

请用 Markdown 表格说明如何使用 Redis 存储以下三种数据，需明确标出 Key 格式、数据结构（如 Hash, Sorted Set, String）以及过期策略（TTL）：

1. **热门排行榜 (Cold-Start Fallback)：** 存储基于威尔逊区间算法计算出的热门电影 ID 及分数。  
2. **用户短期会话特征 (Session Profiling)：** 存储用户最近交互的流派标签及其权重。  
3. **语义缓存 (Semantic Cache)：** 存储高频且短时间内重复的完整推荐结果列表。

## **模块二：数据工程与离线特征管道 (Data Engineering Pipeline)**

**模块目标：** 处理 MovieLens 1M 数据集，执行隐式反馈二值化转换，并构建基于动态负采样的训练数据管道。

**Agent 开发提示词：**

**角色与任务：** 你是一位精通 Python 和 Pandas/PyTorch 的大数据算法工程师。请编写一段用于处理 MovieLens 1M 数据集的离线特征工程代码。

**具体需求：**

1. **隐式反馈转换：** 将 ratings.csv 中的1-5星评分全部二值化为 1（正样本），表示存在交互。  
2. **动态负采样生成器（核心突破）：** 编写一个高效的函数，针对训练集中的每一个正样本，从该用户未交互过的电影池中，利用均匀分布随机抽取 4 个负样本（打标为 0）。必须保证**正负样本比例严格为 1:4**。  
3. **特征映射：** 将离散的 UserID 和 MovieID 重新映射为从 0 开始的连续整数，以适配 PyTorch 的 Embedding 层。  
4. **数据集划分：** 按照留一法（Leave-One-Out）或时间戳顺序划分训练集、验证集和测试集，坚决避免未来数据穿越（Data Leakage）。  
5. 输出规范的面向对象代码（如封装为 MovieLensDataset 类），并继承 torch.utils.data.Dataset。

## **模块三：神经矩阵分解深度模型构建 (NeuMF Deep Learning Model)**

**模块目标：** 遵循 NCF 论文架构，使用 PyTorch 搭建融合 GMF 与 MLP 双通道的推荐内核。

**Agent 开发提示词：**

**角色与任务：** 你是一位顶尖的 AI 推荐算法研究员。请使用 PyTorch 框架为我编写一段完整的神经矩阵分解（NeuMF）模型类及训练循环代码。

**架构与工程约束：**

1. **双通道 Embedding（严格要求）：** 必须为 GMF 和 MLP 分别实例化完全独立的用户和电影 Embedding 矩阵。不可共享 Embedding！假设潜在维度（Latent Factors）默认为 64。  
2. **GMF 路径：** 实现元素级乘积（Element-wise product）。  
3. **MLP 路径：** 包含 3-4 层全连接塔式网络，使用 ReLU 激活函数，每层神经元数量减半（例如 128-\>64-\>32-\>16）。  
4. **神经融合层：** 将两条路径的输出 concat，通过单层线性层和 Sigmoid 激活函数，输出 (0,1) 区间的预测概率。  
5. **损失与优化器：** 使用 nn.BCELoss，搭配 Adam 优化器。仅在 MLP 的 Embedding 和权重上应用轻量级的 L2 正则化（Weight Decay \= 1e-4）。  
6. 请提供一段清晰的单次 Epoch 训练逻辑，包含前向传播、计算 Loss、反向传播和梯度清零。代码必须配有详细的中文工程注释，方便我在毕业论文中绘制算法架构图。

## **模块四：FastAPI 推理边车微服务 (Python Sidecar Inference)**

**模块目标：** （核心创新点）将训练好的 PyTorch 模型封装为极低延迟的独立推理节点，天然适配多并发。

**Agent 开发提示词：**

**角色与任务：** 你是一位精通 MLOps 和后端架构的高级工程师。请使用 FastAPI 构建一个模型推理服务（Sidecar 节点），用于为推荐系统提供实时的打分排序。

**核心逻辑与约束：**

1. **模型生命周期：** 在应用启动时（@app.on\_event("startup")），加载预训练好的 PyTorch NeuMF 模型权重（.pth 文件）至内存/显存中，设置模型为 eval() 模式，避免每次请求重复加载。  
2. **API 接口：** 提供一个 POST /api/predict 接口。接收 JSON 格式数据：{"user\_id": 123, "candidate\_movie\_ids": \[10, 25, ..., 999\]}。  
3. **批量推理：** 将传入的单一 user\_id 与多个 movie\_id 构建为 PyTorch Tensor 批次（Batch），执行一次前向传播，输出每个电影的点击概率。  
4. **响应格式：** 返回按概率降序排列的 Top-K 电影 ID 及其分数。  
5. **性能保障：** 必须使用 torch.no\_grad() 上下文管理器防止内存泄漏。代码应极其精简、高效，因为该容器将与主业务 Java 容器部署在同一个 Pod（Localhost: 127.0.0.1）内。

## **模块五：Spring Boot 核心业务与双模式动态路由 (Main Service & Dual-Mode Routing)**

**模块目标：** （核心创新点）处理 C 端请求，实现“威尔逊热门榜”与“个性化深度推荐”的智能降级与无缝切换，彻底解决 LLM/深度学习冷启动的高延迟瓶颈。

**Agent 开发提示词：**

**角色与任务：** 你是一位拥有大厂经验的 Java 后端架构师。请基于 Spring Boot 3.x 设计处理用户推荐请求的 RESTful Controller 和 Service 层代码。

**双模式动态调度核心业务逻辑：**

1. **请求入口：** GET /api/recommendations?userId={id}。  
2. **用户状态判定：** 首先判断用户历史交互记录是否达到阈值（如 \>= 5次）。  
3. **模式 A：冷启动降级（热门推荐）：** 如果是冷启动用户，直接从 Redis 缓存中拉取“热门排行榜”。（注：该榜单由离线任务基于**威尔逊区间算法结合时间指数衰减**生成，直接通过 RedisTemplate 读取）。  
4. **模式 B：深度个性化推荐（Sidecar RPC 调用）：** 如果是成熟用户，首先查询 Redis 是否有“语义缓存”。如果没有命中，则使用 Spring WebClient 以**异步非阻塞**的方式向本地边车（http://127.0.0.1:8000/api/predict）发送 HTTP POST 请求进行批量候选集排序。  
5. **高可用设计：** 边车调用必须配置网络超时阻断（如 150ms），并集成熔断器（如 Resilience4j）。一旦发生超时或边车宕机，执行 Fallback 逻辑，降级返回模式 A 的热门推荐列表。  
6. 代码需符合领域驱动设计（DDD）的基本分层，并包含严密的统一异常处理机制。

## **模块六：基于 Kafka 的异步闭环反馈机制 (Kafka Feedback Loop)**

**模块目标：** （核心创新点）打破数据孤岛，捕获前端的隐式/显式反馈，实现实时特征更新与离线模型重训的闭环。

**Agent 开发提示词：**

**角色与任务：** 你是一位分布式流处理专家。请基于 Spring Boot 和 Spring Kafka，实现推荐系统的异步反馈数据采集管道。

**架构需求：**

1. **前端埋点接收接口：** 编写一个高并发的 API POST /api/feedback，接收用户的点击、评分、忽略等动作（包含 user\_id, movie\_id, action\_type, timestamp）。  
2. **Kafka 生产者：** 将接收到的事件不落库，直接序列化为 JSON 并以异步方式发送至 Kafka Topic user-interaction-events。  
3. **实时消费者（在线流处理）：** 编写一个 Kafka Listener，消费该 Topic。当监听到 click 或 rate 事件时，立即更新 Redis 中该用户的近期交互行为轨迹（用于后续召回特征的实时漂移）。  
4. **离线消费者（持久化落盘）：** 编写另一个 Kafka Listener 归属于不同的 Consumer Group，负责将全量日志批量沉淀至本地文件或 MySQL（模拟 Data Lake 落盘），供夜间的 PyTorch 离线批处理作业拉取并重新训练（增量训练）模型。

## **模块七：现代化前端展示与交互 (Frontend UI/UX)**

**模块目标：** 构建一个高颜值、响应迅速的前端界面，展示推荐结果，并执行防抖反馈。

**Agent 开发提示词：**

**角色与任务：** 你是一位资深的前端开发工程师。请使用 React (或 Vue3) \+ Tailwind CSS 编写电影推荐系统的主页面代码。

**视觉与交互要求：**

1. **瀑布流 / 卡片式布局：** 采用现代化的深色模式（Dark Mode），电影以卡片形式展示（包含海报占位图、标题、流派、AI推荐匹配度 %）。  
2. **状态管理：** 页面加载时显示优雅的骨架屏（Skeleton Loading），如果后端返回降级数据（热门推荐），可以在界面角落给予微小的“冷启动”状态提示。  
3. **交互埋点捕获：** 当用户点击某部电影详情、或者点击“不喜欢”按钮时，触发 API 调用向后端的 /api/feedback 发送事件。  
4. **防抖与节流：** 对反馈按钮必须做防抖处理（Debounce），防止恶意的并发连击压垮后端 Kafka 队列。  
5. 请提供完整的单一组件文件代码（包含 JSX 结构、Tailwind 类名和逻辑钩子）。