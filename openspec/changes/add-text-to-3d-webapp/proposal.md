## Why

需要一个独立的 Web 应用，让用户通过浏览器输入文本 prompt 调用 Meshy text-to-3d API 生成 3D 模型，实时查看生成进度与缩略图，并在完成后下载模型文件。Meshy API 采用异步两步工作流（preview 生成几何网格 → refine 贴图），直接用 curl 调用门槛高、无法可视化进度，Web 应用可降低使用门槛并提供完整的任务管理与下载体验。

## What Changes

- 新建独立 Python 项目 `/root/meshy-text-to-3d`，与 HugeGraph 项目无关
- 新增 Meshy text-to-3d API 客户端，封装两步工作流（preview/refine）、任务查询、SSE 流式进度、模型与贴图下载、任务删除
- 新增 FastAPI 后端，提供提交 preview、手动触发 refine、查询任务状态、SSE 进度转发、本地下载等 HTTP 接口
- 新增 Web 前端页面（Jinja2 模板 + 原生 HTML/CSS/JS），支持输入 prompt、选择生成参数、实时进度展示、缩略图预览、手动 refine、模型下载、历史任务列表
- preview→refine **手动衔接**：preview 成功后由用户点"贴图"按钮触发 refine（遵循 Meshy 官方推荐，避免形状不对浪费 credits）
- 模型与贴图**落本地存储**：任务成功时立即下载到 storage/，之后从本地提供下载（Meshy 资产 3 天后自动删除且 URL 无刷新机制）
- 任务**持久化用 SQLite**：记录两步 task_id、状态、本地文件路径，支持刷新恢复与历史任务
- 仅监听 **127.0.0.1**，本地自用，不做鉴权
- API key 通过环境变量 `MESHY_API_KEY` 注入，禁止硬编码，日志脱敏
- 不创建测试脚本与使用指南文档

## Capabilities

### New Capabilities
- `meshy-api-client`: 封装 Meshy text-to-3d API 的 Python 客户端，覆盖 preview/refine 任务创建、任务查询、SSE 流式进度、模型与贴图下载、任务删除
- `web-interface`: Web 应用前端界面与 FastAPI 后端服务，支持提交 prompt、实时进度展示、缩略图预览、模型下载

### Modified Capabilities
<!-- 全新项目，无现有 spec，无修改项 -->

## Impact

- 新增代码: 项目根 `/root/meshy-text-to-3d`，含 FastAPI 应用、Meshy 客户端模块、Jinja2 模板、静态资源
- 外部依赖: fastapi, uvicorn, jinja2, httpx (调用 Meshy API), python-dotenv (可选，加载 .env 环境变量)
- 外部 API: Meshy text-to-3d API，调用会消耗账户 credits
- 配置: 环境变量 `MESHY_API_KEY` 必填；可选 `MESHY_API_BASE`（默认 https://api.meshy.ai）
- 无破坏性变更（全新项目）
