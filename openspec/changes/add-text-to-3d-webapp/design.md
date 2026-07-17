## Context

全新独立项目，无历史代码。目标是用 Python Web 应用封装 Meshy text-to-3d API 的异步两步工作流（preview 生成几何网格 → refine 贴图），让用户在浏览器完成"输入 prompt → 看进度 → 下载模型"全流程。Meshy API 异步、任务耗时数十秒到数分钟，需实时进度反馈。约束：Python venv、API key 走环境变量、不写测试脚本与使用指南文档。

## Goals / Non-Goals

**Goals:**
- 封装 Meshy API 两步工作流，前端一键触发 preview→refine 全流程
- 实时展示任务进度（轮询 + SSE 两种方式）
- 展示缩略图并提供各格式模型与贴图下载
- API key 不出现在代码与前端，仅服务端从环境变量读取

**Non-Goals:**
- 不做用户认证与多租户
- 不做任务持久化存储（重启丢失，任务记录仅在 Meshy 侧）
- 不做 3D 模型在线预览渲染（仅缩略图 + 下载）
- 不做批量任务调度
- 不写测试脚本与使用指南文档

## Decisions

**1. 后端框架选 FastAPI + Uvicorn**
理由：原生支持 async，便于用 httpx 异步调用 Meshy API 与转发 SSE；自带 API 文档；轻量。备选 Flask（同步、SSE 转发需额外处理），因异步与 SSE 需求选 FastAPI。

**2. Meshy API 调用用 httpx.AsyncClient**
理由：异步、支持流式响应（SSE 转发）、连接池复用。备选 requests（同步，会阻塞事件循环）、aiohttp（功能等价但 httpx API 更友好、与 FastAPI 生态契合）。

**3. 进度获取：默认 SSE 转发，轮询作兜底**
理由：Meshy 提供 `GET /:id/stream`（SSE），后端用 httpx 流式接收并透传给前端 EventSource，实时性最好、轮询压力小。同时提供 `GET /api/tasks/:id` 轮询接口兜底（浏览器不支持 EventSource 或断连时）。备选纯轮询（实现简单但延迟高、请求多），选 SSE 优先。

**4. 前端用 Jinja2 + 原生 HTML/CSS/JS，不引入构建工具与框架**
理由：页面单一、交互简单，原生 JS + EventSource 足够，避免引入 React/Vue 与构建链增加复杂度。备选 React/Vue（过重）。

**5. 任务完成时立即下载模型到本地存储，下载走本地而非 Meshy URL**
理由：Meshy API 生成的资产**最多保留 3 天后自动删除**（官方 Asset Retention 文档），且下载 URL 是带 `?Expires=` 的预签名 URL、**无刷新机制**，过期后只能重跑任务。因此任务 SUCCEEDED 时后端立即把所需格式模型与贴图流式下载到本地磁盘（`storage/<task_id>/`），之后 `GET /api/tasks/:id/download?format=glb` 从本地文件提供，3 天后仍可下载。参考 meshy-3d-agent 官方 skills 的 `download()` 流式实现（chunk_size=8192, timeout=300）。备选纯代理 Meshy URL（3 天后必失效，不可接受）。

**6. API key 仅服务端从 `MESHY_API_KEY` 环境变量读取**
理由：安全。启动时校验存在性，缺失则拒绝启动。前端永不接触 key。日志中 key 脱敏（仅显示前 8-12 字符），参考 meshy-3d-agent 官方做法。httpx 客户端设 `trust_env=False` 绕过系统代理干扰（参考官方）。

**7. preview→refine 手动衔接，不自动触发**
理由：Meshy 两步工作流的本意是先 preview 评估几何形状，用户确认满意后再 refine 贴图，避免 shape 不对时浪费 refine credits。**官方 game-asset-pipeline FAQ 明确"always run preview first, then selectively refine accepted results"，meshy-3d-agent 官方 skills 也是 preview 后询问用户是否 refine**。所有参考项目无一是自动衔接。因此前端提供"生成预览"与"贴图"两个独立按钮，preview SUCCEEDED 后才启用 refine 按钮，由用户决定是否贴图。备选自动衔接（逆官方推荐、shape 错也烧 credits，不采用）。

**8. 任务持久化用 SQLite，记录两步任务与本地文件路径**
理由：refine 需引用 preview_task_id、本地存储需记录文件落盘位置、刷新页面需恢复任务状态——这些都需要持久化（推翻原 Non-Goal"不做任务持久化"）。仅本地自用场景体量小，选 SQLite（单文件、零运维、Python 标准库 sqlite3 即可），不引入外部数据库。参考 print-it-poc 的 generationJobs schema（previewTaskId、refineTaskId、status: preview_pending→refine_pending→succeeded、progress、本地文件路径）。备选 JSON 文件（并发写不安全）、Convex 等外部 DB（过重）。

**9. 仅监听 127.0.0.1，不做鉴权**
理由：仅本地自用，绑 127.0.0.1 即可避免外部访问烧 credits，无需登录系统（维持 Non-Goal"不做用户认证"）。uvicorn 启动指定 `--host 127.0.0.1`。备选加共享密码（本地自用无必要）。

**10. 项目结构**
```
/root/meshy-text-to-3d/
  app/
    main.py            # FastAPI 入口、路由
    meshy_client.py    # Meshy API 客户端
    storage.py         # 模型/贴图本地下载与读取
    db.py              # SQLite 任务持久化
    schemas.py         # Pydantic 请求/响应模型
    config.py          # 配置与环境变量加载
  templates/index.html
  static/ (css, js)
  storage/            # 下载的模型与贴图（按 task_id 分目录）
  tasks.db            # SQLite 任务记录
  requirements.txt
  .env.example
  openspec/
```

## Risks / Trade-offs

- [Meshy 任务耗时不定，SSE 长连接可能超时] → 后端设置合理超时与心跳，前端 EventSource 自动重连，并提供轮询兜底接口
- [Meshy 资产 3 天后自动删除 + 下载 URL 带 Expires 且无刷新机制] → 任务 SUCCEEDED 时立即下载到本地 storage/，之后从本地提供下载，不依赖 Meshy URL；本地文件长期保留由用户自行清理
- [preview 99% 停滞 30-120s 是正常 finalization] → 参考官方 skills，轮询/SSE 在 99% 时不视为超时，继续等待，避免误判
- [API key 泄露风险] → 仅环境变量、不进日志（脱敏前 8-12 字符）、不返回前端；.env.example 只放占位符
- [Meshy API 限流 429] → 按官方文档自动重试（间隔 5s、最多 3 次），超过则向前端返回明确"速率限制"错误（注：官方 skills 模板代码此处为直接退出，与文档不一致，我们按文档做重试）
- [credits 不足 402] → 客户端识别 402，可调 `/openapi/v1/balance` 查余额并在前端展示明确错误
- [本地存储磁盘占用增长] → 提供删除任务接口（同时删 SQLite 记录与本地文件）；不自动清理
- [SQLite 并发写] → 仅本地单用户，用 sqlite3 默认串行写即可；如需可加 WAL 模式
