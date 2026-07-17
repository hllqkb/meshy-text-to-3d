## 1. 项目初始化

- [ ] 1.1 在 /root/meshy-text-to-3d 创建 Python venv 虚拟环境
- [ ] 1.2 编写 requirements.txt（fastapi、uvicorn、jinja2、httpx、python-dotenv）并安装
- [ ] 1.3 创建项目目录结构（app/、templates/、static/、storage/）
- [ ] 1.4 编写 .env.example（仅含 MESHY_API_KEY、MESHY_API_BASE 占位符）

## 2. 配置与模型

- [ ] 2.1 实现 app/config.py：从环境变量读取 MESHY_API_KEY（必填，缺失抛错）与 MESHY_API_BASE（默认 https://api.meshy.ai）
- [ ] 2.2 实现 app/schemas.py：用 Pydantic 定义 CreatePreviewRequest、CreateRefineRequest、TaskResponse、ErrorResponse 等模型

## 3. Meshy API 客户端

- [ ] 3.1 实现 app/meshy_client.py 的 MeshyClient 基类：httpx.AsyncClient 初始化、Authorization Bearer 头、base_url 与超时配置、trust_env=False
- [ ] 3.2 实现 create_preview(prompt, **params)：POST mode=preview，校验 prompt 非空且 ≤600 字符，返回 task id
- [ ] 3.3 实现 create_refine(preview_task_id, **params)：POST mode=refine，返回 task id
- [ ] 3.4 实现 get_task(task_id)：GET /:id 返回完整任务对象
- [ ] 3.5 实现 stream_task(task_id)：GET /:id/stream，异步迭代 SSE 事件并向上透传
- [ ] 3.6 实现 download_asset(url, dest_path)：流式下载（chunk_size=8192, timeout=300）写入本地文件
- [ ] 3.7 实现 delete_task(task_id)：DELETE /:id
- [ ] 3.8 实现错误码处理：区分 400/401/402/404/429；402 可调 /openapi/v1/balance 查余额；429 按官方文档自动重试（5s 间隔、最多 3 次）；日志中 API key 脱敏（前 8-12 字符）

## 4. 本地存储与持久化

- [ ] 4.1 实现 app/db.py：SQLite 建表 tasks（id, preview_task_id, refine_task_id, status, progress, prompt, local_files JSON, created_at），提供 insert/update/get/list 操作
- [ ] 4.2 实现 app/storage.py：任务 SUCCEEDED 时把 model_urls 与 texture_urls 各文件下载到 storage/<task_id>/，返回本地路径映射
- [ ] 4.3 实现删除任务时同时清理 storage/<task_id>/ 目录与 SQLite 记录

## 5. FastAPI 后端路由

- [ ] 5.1 实现 app/main.py 的 FastAPI 应用与 Jinja2 模板挂载、静态资源挂载
- [ ] 5.2 实现 GET /：返回 templates/index.html
- [ ] 5.3 实现 POST /api/tasks/preview：接收 prompt 与参数，创建 preview 任务、写 SQLite、返回 preview task id
- [ ] 5.4 实现 POST /api/tasks/:id/refine：用户手动触发，创建 refine 任务、写 SQLite、返回 refine task id
- [ ] 5.5 实现 GET /api/tasks/:id：从 SQLite 返回任务状态（轮询兜底，刷新可恢复）
- [ ] 5.6 实现 GET /api/tasks/:id/stream：SSE 透传 Meshy 进度事件，SUCCEEDED 时触发落盘
- [ ] 5.7 实现 GET /api/tasks/:id/download?format=：从本地 storage/ 流式返回文件，设置 Content-Disposition
- [ ] 5.8 实现 GET /api/tasks：列出历史任务
- [ ] 5.9 实现 DELETE /api/tasks/:id：删除任务（Meshy + 本地文件 + SQLite）
- [ ] 5.10 实现全局异常处理：将 Meshy 错误码转为前端可读的中文错误响应

## 6. 前端界面

- [ ] 6.1 编写 templates/index.html：prompt 输入框、参数控件（model_type、ai_model、target_formats、enable_pbr 等）、"生成预览"按钮、"贴图"按钮（初始禁用）、进度区、缩略图区、下载区、历史任务列表
- [ ] 6.2 编写 static/css：基础布局与样式
- [ ] 6.3 编写 static/js：提交 preview 逻辑、EventSource 订阅进度、轮询兜底、渲染进度条与状态
- [ ] 6.4 编写 refine 触发逻辑：preview SUCCEEDED 后启用"贴图"按钮，点击调 POST /api/tasks/:id/refine
- [ ] 6.5 编写缩略图展示逻辑：任务含 thumbnail_url 时加载展示
- [ ] 6.6 编写下载区逻辑：根据已落盘格式渲染下载按钮，点击触发 /api/tasks/:id/download
- [ ] 6.7 编写刷新恢复逻辑：页面加载时从 URL 或 localStorage 取 task_id，调 GET /api/tasks/:id 恢复状态

## 7. 验证

- [ ] 7.1 设置 MESHY_API_KEY 环境变量后启动 uvicorn --host 127.0.0.1，确认仅本地监听
- [ ] 7.2 浏览器访问 /，提交一个 prompt 生成 preview，确认形状后手动点"贴图"触发 refine，全流程跑通
- [ ] 7.3 确认进度实时更新、缩略图展示、模型下载成功
- [ ] 7.4 确认任务 SUCCEEDED 后模型落盘到 storage/，3 天模拟（断网/改 URL）后仍可从本地下载
- [ ] 7.5 确认刷新页面后能恢复任务状态与下载入口
- [ ] 7.6 确认缺 MESHY_API_KEY 时启动被拒绝
