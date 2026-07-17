# Implementation Plan: add-text-to-3d-webapp

**Generated**: 2026-07-17T10:09:13Z
**Source**: openspec/changes/add-text-to-3d-webapp/tasks.md
**Project root**: /root/meshy-text-to-3d
**Stack**: Python 3.10+ / venv / FastAPI + Uvicorn / Jinja2 + 原生 JS / httpx / SQLite

## Summary
- Total tasks: 40
- Parallel groups: 12 个执行波次（wave）
- Estimated complexity: medium
  - 后端 Meshy 客户端 + SSE 透传 + 本地落盘 + SQLite 持久化为核心复杂点
  - 前端原生 JS + EventSource，无构建工具，复杂度低
  - 两步手动 refine、资产 3 天保留期是关键约束

## Dependency Graph

```
Wave 1:  1.1 venv | 1.3 dirs | 1.4 .env.example
Wave 2:  1.2 install deps (needs 1.1+1.3)
Wave 3:  2.1 config | 2.2 schemas (need 1.2)
Wave 4:  3.1 meshy base (needs 2.1) | 4.1 db (needs 1.2)
Wave 5:  3.2 3.3 3.4 3.5 3.6 3.7 3.8 (need 3.1, parallel)
Wave 6:  4.2 storage (needs 3.6 + 4.1)
Wave 7:  4.3 delete cleanup (needs 4.1 + 4.2 + 3.7)
Wave 8:  5.1 main app skeleton (needs 1.2)
Wave 9:  5.2-5.10 routes (need 5.1 + client/db/storage, parallel)
Wave 10: 6.1 index.html | 6.2 css (parallel)
Wave 11: 6.3-6.7 js logic (need 6.1 + routes, parallel)
Wave 12: 7.1-7.6 verification (need full app)
```

## Tasks

### Task 1.1: 创建 Python venv
- **Depends on**: none
- **Files**: `venv/`（项目根下）
- **Steps**:
  1. `cd /root/meshy-text-to-3d && python3 -m venv venv`
  2. 验证 `venv/bin/python` 存在
- **Acceptance criteria**:
  - [ ] venv/bin/python 与 venv/bin/pip 可用
- **Risk**: low
- **Status**: pending

### Task 1.2: 编写 requirements.txt 并安装
- **Depends on**: 1.1, 1.3
- **Files**: `requirements.txt`
- **Steps**:
  1. 写入 fastapi、uvicorn[standard]、jinja2、httpx、python-dotenv
  2. `venv/bin/pip install -r requirements.txt`
- **Acceptance criteria**:
  - [ ] pip install 成功，fastapi/uvicorn/httpx 可 import
- **Risk**: low
- **Status**: pending

### Task 1.3: 创建项目目录结构
- **Depends on**: none
- **Files**: `app/`, `templates/`, `static/css/`, `static/js/`, `storage/`, `.gitignore`
- **Steps**:
  1. mkdir -p app templates static/css static/js storage
  2. 写 .gitignore（忽略 venv/、storage/、tasks.db、.env）
- **Acceptance criteria**:
  - [ ] 目录结构齐全，.gitignore 含 venv/storage/tasks.db/.env
- **Risk**: low
- **Status**: pending

### Task 1.4: 编写 .env.example
- **Depends on**: none
- **Files**: `.env.example`
- **Steps**:
  1. 写 MESHY_API_KEY=msy_xxx 占位符、MESHY_API_BASE=https://api.meshy.ai
- **Acceptance criteria**:
  - [ ] 只含占位符，无真实 key
- **Risk**: low
- **Status**: pending

### Task 2.1: 实现 app/config.py
- **Depends on**: 1.2
- **Files**: `app/config.py`
- **Steps**:
  1. 用 python-dotenv 加载 .env；读 MESHY_API_KEY（缺失 raise SystemExit）、MESHY_API_BASE（默认 https://api.meshy.ai）
  2. 暴露 Settings 单例
- **Acceptance criteria**:
  - [ ] 缺 key 时启动报错；key 不进日志脱敏前 8-12 字符
- **Risk**: low
- **Status**: pending

### Task 2.2: 实现 app/schemas.py
- **Depends on**: 1.2
- **Files**: `app/schemas.py`
- **Steps**:
  1. Pydantic 定义 CreatePreviewRequest（prompt 必填 ≤600、model_type、ai_model、target_formats 等）、CreateRefineRequest（enable_pbr、hd_texture、texture_prompt 等）、TaskResponse、ErrorResponse
- **Acceptance criteria**:
  - [ ] prompt 空/超长校验生效；模型字段覆盖 design 决策
- **Risk**: low
- **Status**: pending

### Task 3.1: MeshyClient 基类
- **Depends on**: 2.1
- **Files**: `app/meshy_client.py`
- **Steps**:
  1. httpx.AsyncClient 初始化，headers 含 Authorization Bearer，base_url=MESHY_API_BASE，timeout 配置，trust_env=False
  2. 提供 _request 封装与生命周期 close
- **Acceptance criteria**:
  - [ ] client 携带 Bearer 头；trust_env=False 生效
- **Risk**: low
- **Status**: pending

### Task 3.2: create_preview
- **Depends on**: 3.1, 2.2
- **Files**: `app/meshy_client.py`
- **Steps**:
  1. POST /openapi/v2/text-to-3d，body mode=preview + prompt + 可选参数
  2. 调用前校验 prompt 非空且 ≤600，返回 result 中的 task id
- **Acceptance criteria**:
  - [ ] 空/超长 prompt 抛参数错误不发请求；成功返回 task id
- **Risk**: low
- **Status**: pending

### Task 3.3: create_refine
- **Depends on**: 3.1, 2.2
- **Files**: `app/meshy_client.py`
- **Steps**:
  1. POST mode=refine + preview_task_id + 可选参数（enable_pbr 等），返回 task id
- **Acceptance criteria**:
  - [ ] 成功返回 refine task id；preview 未成功时透传 400
- **Risk**: low
- **Status**: pending

### Task 3.4: get_task
- **Depends on**: 3.1
- **Files**: `app/meshy_client.py`
- **Steps**:
  1. GET /openapi/v2/text-to-3d/:id，返回完整任务对象
- **Acceptance criteria**:
  - [ ] 返回含 status/progress/model_urls/texture_urls 的对象；404 透传
- **Risk**: low
- **Status**: pending

### Task 3.5: stream_task (SSE)
- **Depends on**: 3.1
- **Files**: `app/meshy_client.py`
- **Steps**:
  1. GET /:id/stream，httpx 流式迭代，解析 SSE event/data，向上产出异步事件
  2. 处理 error 事件与连接结束
- **Acceptance criteria**:
  - [ ] 依次产出 PENDING/IN_PROGRESS/SUCCEEDED 事件；不存在时产出 error 事件
- **Risk**: medium（SSE 流式解析边界处理）
- **Status**: pending

### Task 3.6: download_asset
- **Depends on**: 3.1
- **Files**: `app/meshy_client.py`
- **Steps**:
  1. 流式 GET 预签名 URL（chunk_size=8192, timeout=300），写入 dest_path
- **Acceptance criteria**:
  - [ ] 大文件流式落盘不 OOM；超时可控
- **Risk**: low
- **Status**: pending

### Task 3.7: delete_task
- **Depends on**: 3.1
- **Files**: `app/meshy_client.py`
- **Steps**:
  1. DELETE /openapi/v2/text-to-3d/:id，成功返回标识
- **Acceptance criteria**:
  - [ ] 成功返回；不可逆操作有明确语义
- **Risk**: low
- **Status**: pending

### Task 3.8: 错误码处理与 key 脱敏
- **Depends on**: 3.1
- **Files**: `app/meshy_client.py`
- **Steps**:
  1. 区分 400/401/402/404/429 抛带语义异常；402 可调 /openapi/v1/balance 查余额
  2. 429 自动重试（5s 间隔、最多 3 次）；日志 key 脱敏前 8-12 字符
- **Acceptance criteria**:
  - [ ] 402 返回"额度不足"+余额；429 重试 3 次后返回"速率限制"；日志无完整 key
- **Risk**: medium（429 重试与官方文档/代码不一致需按文档实现）
- **Status**: pending

### Task 4.1: app/db.py SQLite 持久化
- **Depends on**: 1.2
- **Files**: `app/db.py`
- **Steps**:
  1. sqlite3 建表 tasks（id PK, preview_task_id, refine_task_id, status, progress, prompt, local_files TEXT/JSON, created_at INTEGER 毫秒）
  2. 提供 insert_task / update_task / get_task / list_tasks
- **Acceptance criteria**:
  - [ ] CRUD 可用；status 取 preview_pending/refine_pending/succeeded/failed
- **Risk**: low
- **Status**: pending

### Task 4.2: app/storage.py 资产落盘
- **Depends on**: 3.6, 4.1
- **Files**: `app/storage.py`
- **Steps**:
  1. 任务 SUCCEEDED 时遍历 model_urls 与 texture_urls，download_asset 到 storage/<task_id>/
  2. 返回本地路径映射并 update_task 写入 local_files
  3. 落盘失败保留 Meshy 原始 URL 兜底并记录错误
- **Acceptance criteria**:
  - [ ] 成功后各格式文件落盘；local_files 记录路径；失败有兜底
- **Risk**: medium（部分格式落盘失败的处理）
- **Status**: pending

### Task 4.3: 删除时清理本地与 DB
- **Depends on**: 4.1, 4.2, 3.7
- **Files**: `app/db.py`, `app/storage.py`
- **Steps**:
  1. 删除任务时调 delete_task（Meshy）+ 清理 storage/<task_id>/ + 删 SQLite 记录
- **Acceptance criteria**:
  - [ ] 三处同步清理；目录不存在时不报错
- **Risk**: low
- **Status**: pending

### Task 5.1: FastAPI 应用骨架
- **Depends on**: 1.2
- **Files**: `app/main.py`
- **Steps**:
  1. 创建 FastAPI app，挂载 Jinja2Templates、StaticFiles，启动时校验 MESHY_API_KEY
  2. uvicorn 入口指定 host=127.0.0.1
- **Acceptance criteria**:
  - [ ] app 可启动；缺 key 拒绝启动；仅 127.0.0.1
- **Risk**: low
- **Status**: pending

### Task 5.2: GET / 主页
- **Depends on**: 5.1, 6.1
- **Files**: `app/main.py`
- **Steps**:
  1. 返回 templates/index.html
- **Acceptance criteria**:
  - [ ] 访问 / 返回页面
- **Risk**: low
- **Status**: pending

### Task 5.3: POST /api/tasks/preview
- **Depends on**: 5.1, 3.2, 4.1, 2.2
- **Files**: `app/main.py`
- **Steps**:
  1. 接收 CreatePreviewRequest，调 create_preview，insert_task（preview_pending），返回 task id
- **Acceptance criteria**:
  - [ ] 成功返回 preview task id 并写 DB；空 prompt 返 4xx
- **Risk**: low
- **Status**: pending

### Task 5.4: POST /api/tasks/:id/refine
- **Depends on**: 5.1, 3.3, 4.1, 2.2
- **Files**: `app/main.py`
- **Steps**:
  1. 用户手动触发，校验 preview 已 SUCCEEDED，调 create_refine，update_task（refine_pending + refine_task_id），返回 refine task id
- **Acceptance criteria**:
  - [ ] preview 未 SUCCEEDED 拒绝；成功返回 refine task id
- **Risk**: low
- **Status**: pending

### Task 5.5: GET /api/tasks/:id 轮询
- **Depends on**: 5.1, 4.1, 3.4
- **Files**: `app/main.py`
- **Steps**:
  1. 从 SQLite 取记录，可选拉取 Meshy 实时状态合并，返回 TaskResponse
- **Acceptance criteria**:
  - [ ] 返回当前状态与进度；刷新可恢复
- **Risk**: low
- **Status**: pending

### Task 5.6: GET /api/tasks/:id/stream SSE
- **Depends on**: 5.1, 3.5, 4.2, 4.1
- **Files**: `app/main.py`
- **Steps**:
  1. StreamingResponse 透传 stream_task 事件；SUCCEEDED 时触发 storage 落盘并 update_task
- **Acceptance criteria**:
  - [ ] 前端 EventSource 收到进度；SUCCEEDED 后模型落盘
- **Risk**: high（SSE 透传 + 落盘时机的协程编排）
- **Status**: pending

### Task 5.7: GET /api/tasks/:id/download
- **Depends on**: 5.1, 4.1, 4.2
- **Files**: `app/main.py`
- **Steps**:
  1. 从 local_files 取本地路径，FileResponse 流式返回，设 Content-Disposition
- **Acceptance criteria**:
  - [ ] 已落盘格式可下载；未落盘返 404
- **Risk**: low
- **Status**: pending

### Task 5.8: GET /api/tasks 历史列表
- **Depends on**: 5.1, 4.1
- **Files**: `app/main.py`
- **Steps**:
  1. list_tasks 返回历史任务摘要
- **Acceptance criteria**:
  - [ ] 重启后仍可列出历史任务
- **Risk**: low
- **Status**: pending

### Task 5.9: DELETE /api/tasks/:id
- **Depends on**: 5.1, 3.7, 4.3
- **Files**: `app/main.py`
- **Steps**:
  1. 调 4.3 的清理（Meshy + 本地 + DB）
- **Acceptance criteria**:
  - [ ] 三处同步删除
- **Risk**: low
- **Status**: pending

### Task 5.10: 全局异常处理
- **Depends on**: 5.1, 3.8
- **Files**: `app/main.py`
- **Steps**:
  1. 捕获 Meshy 语义异常转为前端可读中文 ErrorResponse（402 额度不足、429 速率限制等）
- **Acceptance criteria**:
  - [ ] 各错误码返回对应中文提示
- **Risk**: low
- **Status**: pending

### Task 6.1: templates/index.html
- **Depends on**: 5.2
- **Files**: `templates/index.html`
- **Steps**:
  1. 布局：prompt 输入框、参数控件（model_type、ai_model、target_formats、enable_pbr 等）、"生成预览"按钮、"贴图"按钮（初始 disabled）、进度区、缩略图区、下载区、历史任务列表
  2. 引用 static/css、static/js
- **Acceptance criteria**:
  - [ ] 含全部控件；贴图按钮初始禁用
- **Risk**: low
- **Status**: pending

### Task 6.2: static/css 样式
- **Depends on**: none
- **Files**: `static/css/style.css`
- **Steps**:
  1. 基础布局与控件样式
- **Acceptance criteria**:
  - [ ] 页面可用、无错位
- **Risk**: low
- **Status**: pending

### Task 6.3: static/js 提交与进度
- **Depends on**: 6.1, 5.3, 5.6
- **Files**: `static/js/app.js`
- **Steps**:
  1. 提交 preview 逻辑、EventSource 订阅 /stream、轮询兜底、渲染进度条与状态
- **Acceptance criteria**:
  - [ ] 进度条随 SSE 更新；EventSource 断连自动转轮询
- **Risk**: medium
- **Status**: pending

### Task 6.4: refine 触发逻辑
- **Depends on**: 6.1, 5.4
- **Files**: `static/js/app.js`
- **Steps**:
  1. preview SUCCEEDED 后启用"贴图"按钮，点击调 POST /api/tasks/:id/refine 并订阅其进度
- **Acceptance criteria**:
  - [ ] 仅 preview SUCCEEDED 可点；点击后进入 refine 进度
- **Risk**: low
- **Status**: pending

### Task 6.5: 缩略图展示
- **Depends on**: 6.1, 5.5
- **Files**: `static/js/app.js`
- **Steps**:
  1. 任务含 thumbnail_url 时加载展示
- **Acceptance criteria**:
  - [ ] 缩略图正确显示
- **Risk**: low
- **Status**: pending

### Task 6.6: 下载区逻辑
- **Depends on**: 6.1, 5.7
- **Files**: `static/js/app.js`
- **Steps**:
  1. 据已落盘格式渲染下载按钮，点击触发 /api/tasks/:id/download?format=
- **Acceptance criteria**:
  - [ ] 仅已落盘格式显示按钮；点击下载成功
- **Risk**: low
- **Status**: pending

### Task 6.7: 刷新恢复逻辑
- **Depends on**: 6.1, 5.5
- **Files**: `static/js/app.js`
- **Steps**:
  1. 页面加载从 URL query 或 localStorage 取 task_id，调 GET /api/tasks/:id 恢复状态与下载入口
- **Acceptance criteria**:
  - [ ] 刷新后恢复进度与下载按钮
- **Risk**: low
- **Status**: pending

### Task 7.1: 启动与监听验证
- **Depends on**: 5.1, 2.1
- **Files**: -
- **Steps**:
  1. 设 MESHY_API_KEY 启动 uvicorn --host 127.0.0.1，确认仅本地监听
- **Acceptance criteria**:
  - [ ] 仅 127.0.0.1 可访问；外部不可达
- **Risk**: low
- **Status**: pending

### Task 7.2: 全流程验证
- **Depends on**: 全部实现
- **Files**: -
- **Steps**:
  1. 浏览器提交 prompt 生成 preview，确认形状后手动点"贴图"触发 refine，跑通
- **Acceptance criteria**:
  - [ ] preview→手动 refine 全流程成功
- **Risk**: medium（消耗真实 credits，可用官方测试 key msy_dummy_api_key_for_test_mode_12345678 降本）
- **Status**: pending

### Task 7.3: 进度与下载验证
- **Depends on**: 6.3, 6.5, 6.6
- **Files**: -
- **Steps**:
  1. 确认进度实时更新、缩略图展示、模型下载成功
- **Acceptance criteria**:
  - [ ] 三项均正常
- **Risk**: low
- **Status**: pending

### Task 7.4: 本地落盘与 3 天兜底验证
- **Depends on**: 4.2, 5.7
- **Files**: -
- **Steps**:
  1. 确认 SUCCEEDED 后模型落盘 storage/；模拟 URL 失效（断网/改 URL）后仍可从本地下载
- **Acceptance criteria**:
  - [ ] 落盘成功；Meshy URL 失效后本地下载仍可用
- **Risk**: low
- **Status**: pending

### Task 7.5: 刷新恢复验证
- **Depends on**: 6.7, 4.1
- **Files**: -
- **Steps**:
  1. 任务进行中刷新页面，确认恢复状态与下载入口
- **Acceptance criteria**:
  - [ ] 刷新后状态与下载入口恢复
- **Risk**: low
- **Status**: pending

### Task 7.6: 缺 key 启动验证
- **Depends on**: 2.1, 5.1
- **Files**: -
- **Steps**:
  1. 不设 MESHY_API_KEY 启动，确认拒绝启动
- **Acceptance criteria**:
  - [ ] 启动失败并输出明确错误
- **Risk**: low
- **Status**: pending

## Execution Order

1. **Wave 1**: 1.1, 1.3, 1.4（并行：venv、目录、env 示例）
2. **Wave 2**: 1.2（装依赖，需 1.1+1.3）
3. **Wave 3**: 2.1, 2.2（并行：config、schemas）
4. **Wave 4**: 3.1, 4.1（并行：meshy 基类、db）
5. **Wave 5**: 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8（并行：meshy 各方法）
6. **Wave 6**: 4.2（storage 落盘，需 3.6+4.1）
7. **Wave 7**: 4.3（删除清理，需 4.1+4.2+3.7）
8. **Wave 8**: 5.1（main 骨架）
9. **Wave 9**: 5.2–5.10（并行：各路由，需 5.1+client/db/storage）
10. **Wave 10**: 6.1, 6.2（并行：HTML、CSS）
11. **Wave 11**: 6.3–6.7（并行：JS 逻辑，需 6.1+路由）
12. **Wave 12**: 7.1–7.6（验证，需完整应用）

## Risks / Concerns

- **spec 与 tasks 端点不一致**：web-interface spec 的"提交生成任务"需求文本仍写 `POST /api/tasks` 触发两步，但 tasks.md 已拆为 `POST /api/tasks/preview` + `POST /api/tasks/:id/refine`（手动 refine）。实现以 tasks.md 为准（拆分端点 + 手动 refine），建议后续同步修订该 spec 需求文本。
- **SSE 透传 + 落盘时机（Task 5.6，high）**：SUCCEEDED 事件到达时触发落盘的协程编排需谨慎，避免阻塞 SSE 流或落盘失败导致前端拿不到文件。建议落盘在后台 task 执行，SSE 先推送 SUCCEEDED。
- **429 重试（Task 3.8）**：官方 skills 模板代码与文档不一致（模板直接退出，文档说重试 5s×3）。按文档实现自动重试。
- **真实 credits 消耗（Task 7.2）**：端到端验证会消耗 credits，可用官方测试 key `msy_dummy_api_key_for_test_mode_12345678` 降本。
- **部分格式落盘失败（Task 4.2）**：某格式下载失败不应阻塞其他格式；保留 Meshy 原始 URL 作短期兜底。
- **SQLite 并发**：仅本地单用户，默认串行写即可；如遇问题加 WAL 模式。

## Code Review Report

**Date**: 2026-07-17T19:23:00Z
**Reviewer**: Claude Code

### Summary
- Files reviewed: 13
- Issues found: 5 (4 Must Fix + 1 API 变更)
- Must-fix: 4 (全部已修复)
- Nice-to-have: 3

### Must Fix (全部已修复)

1. **[app/main.py:47] 异常处理器返回 Pydantic 模型而非 Response，导致二次 500**
   - Impact: MeshyError 触发后 Starlette 尝试调用 ErrorResponse 对象，产生 `TypeError: 'ErrorResponse' object is not callable`
   - Fix: 导入 `JSONResponse`，处理器改为 `return JSONResponse(status_code=exc.status_code, content=body.model_dump())`

2. **[app/schemas.py:19] topology 默认值 "triangle-mesh" 不符合 API 规范**
   - Impact: Meshy API 返回 400 `Topology must be one of [quad triangle]`
   - Fix: 默认值改为 `"triangle"`

3. **[templates/index.html:35] ai-model 下拉框选项值错误**
   - Impact: 默认发送 `"lowpoly"` 给 API，触发 400 `AIModel must be one of [meshy-4 meshy-5 meshy-6 latest]`
   - Fix: 替换为 `meshy-4`/`meshy-5`/`meshy-6`/`latest` 选项

4. **[templates/index.html:52-53] topology option value 不符合 API 规范**
   - Impact: 前端发送 `"triangle-mesh"`/`"quad-mesh"`，API 不识别
   - Fix: value 改为 `"triangle"`/`"quad"`

### API 变更（运行时发现，已修复）

5. **[app/schemas.py:12] meshy-4 已被 API 弃用**
   - Impact: API 返回 `"meshy-4 is deprecated, please use meshy-6 instead"`
   - Fix: `ai_model` 默认值改为 `"meshy-6"`，HTML 默认选中 `meshy-6`

### Nice to Have (非阻塞)

1. **[app/storage.py:35] model_urls 为 None 时可能抛 AttributeError**
   - 建议: 前置兜底 `model_urls = model_urls or {}`

2. **[app/main.py:203] 局部 import `pathlib.Path`**
   - 建议: 移到文件顶部统一导入

3. **[app/meshy_client.py:51] URL 拼接冗余**
   - 建议: `httpx.AsyncClient` 已设置 `base_url`，直接传 `path` 即可

### 验证结果

- 启动验证通过：`GET /` 200、`GET /api/tasks` 正常返回
- Preview 提交成功：Meshy API 返回 202 Accepted，本地返回 task_id
- 轮询正常：进度从 23% -> 28% -> 39% 递增
- 错误处理正常：无效参数返回 400 + JSON 错误体，不再触发 500
- 删除任务正常：Meshy 端 200 OK，本地 DB 清理成功

### Status: APPROVED (after fixes)
