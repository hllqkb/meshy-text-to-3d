## ADDED Requirements

### Requirement: 创建 Preview 任务
系统 SHALL 通过 `POST /openapi/v2/text-to-3d`（mode=preview）创建预览任务，传入 prompt 与可选生成参数（model_type、ai_model、should_remesh、target_polycount、pose_mode、target_formats 等），并返回新建任务的 id。

#### Scenario: 仅传 prompt 创建 preview 成功
- **WHEN** 调用创建 preview 任务，prompt 为 "a monster mask"，其余参数缺省
- **THEN** 系统向 Meshy 发送 mode=preview 的请求并返回 result 中的 task id

#### Scenario: prompt 缺失
- **WHEN** 调用创建 preview 任务但未提供 prompt
- **THEN** 系统 SHALL 在调用 Meshy 前校验并返回参数错误，不发起请求

#### Scenario: prompt 超过 600 字符
- **WHEN** prompt 长度超过 600 字符
- **THEN** 系统 SHALL 在调用前校验并返回参数错误

### Requirement: 创建 Refine 任务
系统 SHALL 通过 `POST /openapi/v2/text-to-3d`（mode=refine）创建贴图任务，传入已成功 preview 任务的 id 与可选参数（enable_pbr、hd_texture、texture_prompt、texture_image_url、target_formats 等），返回新建 refine 任务 id。

#### Scenario: 用成功 preview 的 id 创建 refine
- **WHEN** 调用创建 refine 任务，preview_task_id 指向一个 SUCCEEDED 的 preview 任务
- **THEN** 系统向 Meshy 发送 mode=refine 请求并返回 result 中的 task id

#### Scenario: preview 任务未成功
- **WHEN** preview_task_id 对应的 preview 任务状态非 SUCCEEDED
- **THEN** 系统 SHALL 将 Meshy 返回的 400 错误透传给调用方并附上下文信息

### Requirement: 查询单个任务
系统 SHALL 通过 `GET /openapi/v2/text-to-3d/:id` 查询任务对象，返回包含 status、progress、model_urls、texture_urls、thumbnail_url 等字段的完整对象。

#### Scenario: 查询存在的任务
- **WHEN** 查询一个存在的 task id
- **THEN** 系统返回该任务的完整对象，包含当前 status 与 progress

#### Scenario: 查询不存在的任务
- **WHEN** 查询一个不存在的 task id
- **THEN** 系统 SHALL 将 Meshy 的 404 错误透传给调用方

### Requirement: SSE 流式获取进度
系统 SHALL 通过 `GET /openapi/v2/text-to-3d/:id/stream` 以 Server-Sent Events 形式接收任务实时更新，并支持将事件流透传给上层调用方。

#### Scenario: 流式接收进度事件
- **WHEN** 订阅一个进行中任务的 SSE 流
- **THEN** 系统 SHALL 依次产出 PENDING、IN_PROGRESS、SUCCEEDED 等状态对应的 message 事件

#### Scenario: 任务不存在时订阅
- **WHEN** 订阅一个不存在的 task id 的 SSE 流
- **THEN** 系统 SHALL 产出一个 error 事件并结束流

### Requirement: 下载模型与贴图
系统 SHALL 提供按格式下载模型文件与贴图文件的能力，从查询到的任务对象中读取对应预签名 URL 并流式获取内容（chunk_size=8192，timeout=300），支持写入本地文件。因 Meshy 资产 3 天后删除且 URL 无刷新机制，下载 SHALL 在任务 SUCCEEDED 后尽快执行并落盘。

#### Scenario: 下载指定格式模型到本地
- **WHEN** 请求下载某任务的 glb 格式模型且该格式已生成
- **THEN** 系统 SHALL 从 model_urls.glb 流式获取内容并写入本地 storage/<task_id>/ 目录

#### Scenario: 请求未生成的格式
- **WHEN** 请求下载某任务未生成的格式（如 3mf 未在 target_formats 中指定）
- **THEN** 系统 SHALL 返回明确的"该格式未生成"错误

### Requirement: 删除任务
系统 SHALL 通过 `DELETE /openapi/v2/text-to-3d/:id` 删除任务及其关联数据，该操作不可逆。

#### Scenario: 删除存在的任务
- **WHEN** 删除一个存在的 task id
- **THEN** 系统 SHALL 调用 Meshy 删除接口并在成功时返回成功标识

### Requirement: API key 安全管理
系统 SHALL 仅从环境变量 `MESHY_API_KEY` 读取 API key，置于 Authorization Bearer 头调用 Meshy，禁止将 key 写入日志或返回给前端。

#### Scenario: 启动时 key 缺失
- **WHEN** 应用启动且环境变量 MESHY_API_KEY 未设置
- **THEN** 系统 SHALL 拒绝启动并输出明确错误

#### Scenario: key 不进日志
- **WHEN** 调用 Meshy 发生错误需记录日志
- **THEN** 日志中 SHALL 出现脱敏后的 key（仅保留末几位）而非完整 key

### Requirement: 错误码透传
系统 SHALL 识别 Meshy 返回的 400/401/402/404/429 错误，并向调用方提供区分类型的错误信息。

#### Scenario: credits 不足
- **WHEN** Meshy 返回 402
- **THEN** 系统 SHALL 返回"额度不足"语义的错误而非通用错误

#### Scenario: 触发限流
- **WHEN** Meshy 返回 429
- **THEN** 系统 SHALL 按官方文档自动重试（间隔 5s、最多 3 次），仍失败则返回"速率限制"语义的错误
