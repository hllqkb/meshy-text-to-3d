## ADDED Requirements

### Requirement: 提供主页界面
系统 SHALL 在根路径 `/` 返回 Web 页面，包含 prompt 输入框、生成参数控件、提交按钮、任务进度区、缩略图区与下载区。

#### Scenario: 访问主页
- **WHEN** 用户浏览器访问根路径 /
- **THEN** 系统返回包含输入表单与进度展示区的 HTML 页面

### Requirement: 提交生成任务
系统 SHALL 提供 `POST /api/tasks` 接口接收 prompt 与可选参数，触发 preview→refine 两步工作流，返回任务 id 供前端跟踪。

#### Scenario: 提交合法 prompt
- **WHEN** 前端 POST /api/tasks，body 含非空 prompt（≤600 字符）
- **THEN** 系统创建 preview 任务并返回 preview task id 与状态

#### Scenario: 提交空 prompt
- **WHEN** 前端 POST /api/tasks 但 prompt 为空或超长
- **THEN** 系统返回 4xx 参数错误，不调用 Meshy

### Requirement: 手动触发 refine 步骤
系统 SHALL 在 preview 任务 SUCCEEDED 后由用户手动触发 refine，不自动创建 refine 任务。前端提供独立的"贴图"按钮，仅 preview SUCCEEDED 后启用；用户点击后系统才创建 refine 任务（按用户选择是否启用 PBR、HD 纹理等）。此设计遵循 Meshy 官方推荐流程：先 preview 评估几何形状，用户确认满意后再 refine 贴图，避免形状不对时浪费 refine credits。

#### Scenario: 用户手动触发 refine
- **WHEN** preview 任务状态为 SUCCEEDED 且用户点击"贴图"按钮
- **THEN** 系统 SHALL 创建 refine 任务（带 preview_task_id）并返回 refine task id

#### Scenario: preview 未成功时 refine 按钮不可用
- **WHEN** preview 任务状态非 SUCCEEDED
- **THEN** 前端 SHALL 禁用"贴图"按钮，不允许触发 refine

#### Scenario: preview 失败
- **WHEN** preview 任务状态变为 FAILED
- **THEN** 系统 SHALL 停止流程并将错误信息返回前端展示，不提供 refine 入口

### Requirement: 实时进度展示
系统 SHALL 提供 `GET /api/tasks/:id/stream`（SSE）与 `GET /api/tasks/:id`（轮询）两种方式向前端推送任务 progress 与 status，前端实时渲染进度条与状态。

#### Scenario: SSE 实时推送
- **WHEN** 前端通过 EventSource 订阅 /api/tasks/:id/stream
- **THEN** 系统 SHALL 透传 Meshy 的进度事件，前端进度条随 progress 更新

#### Scenario: 轮询兜底
- **WHEN** 前端改用轮询 GET /api/tasks/:id
- **THEN** 系统 SHALL 返回当前任务对象，前端据此更新进度

### Requirement: 缩略图预览
系统 SHALL 在任务产生 thumbnail_url 后于页面展示缩略图；若启用 alpha_thumbnail，同时展示透明背景版本。

#### Scenario: 展示缩略图
- **WHEN** 任务对象包含 thumbnail_url
- **THEN** 前端 SHALL 加载并展示该缩略图

### Requirement: 资产本地化存储
系统 SHALL 在 preview 或 refine 任务 SUCCEEDED 时立即将生成的模型与贴图文件流式下载到本地 `storage/<task_id>/` 目录，并记录本地文件路径到任务记录。此举因 Meshy 资产最多保留 3 天且下载 URL 无刷新机制，确保 3 天后仍可下载。

#### Scenario: 任务成功后落盘
- **WHEN** 任务状态变为 SUCCEEDED 且 model_urls/texture_urls 非空
- **THEN** 系统 SHALL 立即把各格式模型与贴图下载到 storage/<task_id>/，并记录本地路径

#### Scenario: 落盘失败
- **WHEN** 下载落盘过程中发生网络或磁盘错误
- **THEN** 系统 SHALL 记录错误并保留 Meshy 原始 URL 作为短期兜底，向前端提示该任务需尽快重试下载

### Requirement: 模型与贴图下载
系统 SHALL 提供 `GET /api/tasks/:id/download?format=<fmt>` 下载接口，**从本地存储**返回模型或贴图文件（非代理 Meshy URL），前端提供各已生成格式的下载入口。

#### Scenario: 下载已落盘格式
- **WHEN** 前端请求 /api/tasks/:id/download?format=glb 且该格式已落盘到本地
- **THEN** 系统 SHALL 从本地文件流式返回内容并设置正确 Content-Disposition

#### Scenario: 下载未落盘格式
- **WHEN** 前端请求一个未落盘的格式
- **THEN** 系统 SHALL 返回 404 或明确的"该格式未生成/未落盘"错误

### Requirement: 任务持久化
系统 SHALL 用 SQLite 持久化任务记录，至少包含 preview_task_id、refine_task_id、status（preview_pending/refine_pending/succeeded/failed）、progress、prompt、本地文件路径、创建时间。刷新页面或重启服务后 SHALL 能据 task_id 恢复任务状态与下载入口。

#### Scenario: 刷新页面恢复任务
- **WHEN** 用户在任务进行中刷新页面
- **THEN** 系统 SHALL 据 task_id 从 SQLite 读取并恢复任务状态、进度与下载入口

#### Scenario: 重启后查看历史任务
- **WHEN** 服务重启后用户访问
- **THEN** 系统 SHALL 能列出已持久化的历史任务及其本地下载入口

### Requirement: 错误信息展示
系统 SHALL 将 Meshy 的 400/401/402/404/429 等错误转换为用户可读的中文提示在前端展示。

#### Scenario: 额度不足提示
- **WHEN** Meshy 返回 402
- **THEN** 前端 SHALL 显示"额度不足"类提示

#### Scenario: 限流提示
- **WHEN** Meshy 返回 429
- **THEN** 前端 SHALL 显示"请求过于频繁，请稍后再试"类提示

### Requirement: 配置与启动
系统 SHALL 通过环境变量配置（MESHY_API_KEY 必填、MESHY_API_BASE 可选默认 https://api.meshy.ai），缺失 key 时拒绝启动。系统 SHALL 仅监听 127.0.0.1（本地自用），不对外暴露，无需鉴权。

#### Scenario: 正常启动
- **WHEN** 设置了 MESHY_API_KEY 后启动 uvicorn（--host 127.0.0.1）
- **THEN** 系统 SHALL 仅在 127.0.0.1 监听端口并提供服务

#### Scenario: 缺 key 启动
- **WHEN** 未设置 MESHY_API_KEY 启动
- **THEN** 系统 SHALL 立即退出并输出缺少 API key 的错误
