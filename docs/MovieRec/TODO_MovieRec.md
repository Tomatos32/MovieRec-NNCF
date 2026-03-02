# TODO 待办交付清单 (MovieRec-NNCF)

根据 6A 工程规范中的 Assess 阶段要求，核心系统基础设施（M1-M7）的源码架构已由 Agent 全自动搭建完毕，接下来需要人工介入进行环境配置、测试启动收尾工作：

## 1. 完善核心密钥与配置环境 (.env)
系统开发时遵守隐私与解耦原则，关键连接串与密码信息不在代码库中硬编码暴露，请在各项目根目录下新建 `.env` 或在 `application.yml` 中注入以下缺失配置：
- [ ] MySQL 8.0 链接字符串 (jdbc:mysql://... & username/password)
- [ ] Redis 缓存网关配置 (host, port, auth)
- [ ] Kafka 代理集群配置 (bootstrap.servers=localhost:9092)
- [ ] PyTorch Sidecar Python 运行环境中的 `NUM_USERS` 与 `NUM_MOVIES`。

## 2. 外部工程与组件依赖的初始化
请按照如下优先顺序安装基础设施以备本地联调：
- [ ] 确保 MySQL 启动，执行 `sql/schema.sql` 结构导入。
- [ ] 确保 Redis 服务器本地或远端就绪。
- [ ] 确保 Zookeeper 与 Kafka 服务正常运行。
- [ ] (后端) 进入 `src/main` 包配置 Maven/Gradle 环境，启动 Spring Boot。
- [ ] (模型端) 安装 `pip install torch fastapi uvicorn pandas`。通过 `python inference/main.py` 开启推理端点（占用 8000 端口）。
- [ ] (前端) 针对 `src/frontend/src/pages/HomePage.vue` 添加 Vue 3 全局框架入口文件 (`main.ts` / `App.vue`)，配置 Tailwind CSS 3.x 扫描路径，打包启动。

## 3. 测试与验证策略
上线联调时，请着重回归测试这两条核心路径：
- [ ] 向 `http://localhost:8080/api/recommendations?userId=1` (冷启动 Mode A) 模拟发起调用，检验是否正常通过 Redis `rec:popular:topk` 降级，骨架屏能否顺利隐去。
- [ ] 发给 `http://localhost:8080/api/recommendations?userId=5` (个性化 Mode B) 模拟进行高耗时推断，关注断路器报错与 `FastAPI Sidecar` 并发调用时的 `OOM` 和 `GPU Memory` 数据。
- [ ] 尝试在主页前端触发 "不感兴趣" 或 "点击详情"，观测 Kafka 控制台能否打印收到 Topic `user-interaction-events`。

*(Agent 已按要求严格实施 Vue 3 模板，替换了原有的 React 组件，全量代码基于 `main`/`dev`/`feat-*` 存储在了 Git 中。请 `checkout main` 合并 `dev` 发版。)*
