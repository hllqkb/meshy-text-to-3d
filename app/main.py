import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.db import delete_task as db_delete_task
from app.db import get_task as db_get_task
from app.db import get_task_by_refine_id as db_get_task_by_refine_id
from app.db import init_db, insert_task, list_tasks, update_task
from app.meshy_client import MeshyClient, MeshyError
from app.mimo_client import MimoClient
from app.schemas import CreatePreviewRequest, CreateRefineRequest, ErrorResponse, TaskResponse, PolishRequest, PolishResponse
from app.storage import cleanup_task_storage, download_task_assets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Meshy Text-to-3D", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(MeshyError)
async def meshy_error_handler(request: Request, exc: MeshyError):
    msg_map = {
        400: "请求参数错误",
        401: "API Key 无效",
        402: exc.detail.get("message", "额度不足"),
        404: "任务不存在",
        429: "速率限制，请稍后重试",
        503: "服务暂不可用",
    }
    body = ErrorResponse(
        error=msg_map.get(exc.status_code, "未知错误"),
        detail=str(exc),
        code=exc.status_code,
    )
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.post("/api/tasks/preview")
async def create_preview_task(req: CreatePreviewRequest):
    client = MeshyClient()
    try:
        preview_id = await client.create_preview(req.model_dump(exclude_unset=True))
        insert_task(
            task_id=preview_id,
            preview_task_id=preview_id,
            status="preview_pending",
            prompt=req.prompt,
        )
        return {"id": preview_id, "status": "preview_pending"}
    finally:
        await client.close()


@app.post("/api/polish")
async def polish_prompt(req: PolishRequest):
    """使用 AI 润色提示词。"""
    client = MimoClient()
    try:
        polished = await client.polish_prompt(req.text)
        return PolishResponse(original=req.text, polished=polished)
    finally:
        await client.close()


@app.post("/api/tasks/{task_id}/refine")
async def create_refine_task(task_id: str, req: CreateRefineRequest):
    record = db_get_task(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="任务不存在")
    if record["status"] != "SUCCEEDED":
        raise HTTPException(status_code=400, detail="preview 尚未完成，无法 refine")

    client = MeshyClient()
    try:
        refine_id = await client.create_refine(
            {
                "preview_task_id": task_id,
                **req.model_dump(exclude_unset=True),
            }
        )
        update_task(
            task_id=task_id,
            refine_task_id=refine_id,
            status="refine_pending",
        )
        return {"id": refine_id, "status": "refine_pending"}
    finally:
        await client.close()


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    record = db_get_task(task_id)
    is_refine_task = False
    # 如果 task_id 不是主键，尝试通过 refine_task_id 查找
    if not record:
        record = db_get_task_by_refine_id(task_id)
        if record:
            is_refine_task = True
    if not record:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 合并本地数据与 Meshy 实时状态
    client = MeshyClient()
    try:
        # 如果是精修任务，用 refine_task_id 查询 Meshy API
        meshy_task_id = record.get("refine_task_id") if is_refine_task else task_id
        remote = await client.get_task(meshy_task_id)
        remote_task = remote.get("result", remote)
        status = remote_task.get("status", record["status"])
        progress = remote_task.get("progress", record["progress"])

        # 更新 DB - 始终用数据库主键
        db_id = record.get("id", task_id)
        if status != record["status"] or progress != record["progress"]:
            update_task(db_id, status=status, progress=progress)

        local_files = {}
        if record.get("local_files"):
            try:
                local_files = json.loads(record["local_files"])
            except json.JSONDecodeError:
                pass

        return TaskResponse(
            id=task_id,
            status=status,
            progress=progress,
            prompt=record.get("prompt") or "",
            thumbnail_url=remote_task.get("thumbnail_url") or "",
            model_urls=remote_task.get("model_urls") or {},
            texture_urls=remote_task.get("texture_urls") or None,
            preview_task_id=record.get("preview_task_id") or "",
            refine_task_id=record.get("refine_task_id") or "",
            local_files=local_files,
            created_at=record.get("created_at") or 0,
            is_refined=bool(record.get("refine_task_id")),
        )
    finally:
        await client.close()


@app.get("/api/tasks/{task_id}/stream")
async def stream_task(task_id: str):
    record = db_get_task(task_id)
    # 如果 task_id 不是主键，尝试通过 refine_task_id 查找
    if not record:
        record = db_get_task_by_refine_id(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 使用数据库记录的主键 ID，而不是传入的 task_id
    db_id = record.get("id", task_id)

    async def event_generator():
        client = MeshyClient()
        try:
            async for event in client.stream_task(task_id):
                status = event.get("status", "")
                progress = event.get("progress", 0)

                if status:
                    # 使用数据库主键 ID 更新记录
                    update_task(db_id, status=status, progress=progress)

                # SUCCEEDED 时触发落盘
                if status == "SUCCEEDED":
                    model_urls = event.get("model_urls") or {}
                    texture_urls = event.get("texture_urls") or None
                    if model_urls:
                        # 如果是精修任务，使用精修任务 ID 做目录名，db_id 更新数据库
                        storage_id = record.get("refine_task_id") if record.get("refine_task_id") else db_id
                        logger.info(f"Downloading assets for task {storage_id}, db_id={db_id}, model_urls: {list(model_urls.keys())}")
                        asyncio.create_task(
                            download_task_assets(client, db_id, model_urls, texture_urls, storage_id=storage_id)
                        )

                yield f"data: {json.dumps(event)}\n\n"

                if status in ("SUCCEEDED", "FAILED"):
                    break

            yield "data: [DONE]\n\n"
        finally:
            await client.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/tasks/{task_id}/download")
async def download_asset(task_id: str, format: str):
    record = db_get_task(task_id)
    # 如果 task_id 不是主键，尝试通过 refine_task_id 查找
    if not record:
        record = db_get_task_by_refine_id(task_id)
    if not record or not record.get("local_files"):
        raise HTTPException(status_code=404, detail="文件未找到")

    try:
        local_files = json.loads(record["local_files"])
    except json.JSONDecodeError:
        raise HTTPException(status_code=404, detail="文件记录损坏")

    key = f"model_{format}"
    path = local_files.get(key, "")
    if not path or not path.startswith("/"):
        raise HTTPException(status_code=404, detail="该格式未下载或不可用")

    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="本地文件已删除")

    return FileResponse(
        path=str(file_path),
        filename=f"{task_id}_{format}{file_path.suffix}",
        media_type="application/octet-stream",
    )



@app.get("/api/balance")
async def get_balance():
    """查询账户积分余额。"""
    client = MeshyClient()
    try:
        balance = await client.get_balance()
        return balance
    finally:
        await client.close()

@app.get("/api/tasks")
async def get_tasks():
    records = list_tasks()
    result = []
    for r in records:
        local_files = {}
        if r.get("local_files"):
            try:
                local_files = json.loads(r["local_files"])
            except json.JSONDecodeError:
                pass
        result.append(
            {
                "id": r["id"],
                "status": r["status"],
                "progress": r["progress"],
                "prompt": r.get("prompt", ""),
                "created_at": r.get("created_at", 0),
                "local_files": local_files,
                "is_refined": bool(r.get("refine_task_id")),
            }
        )
    return result


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    record = db_get_task(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="任务不存在")

    client = MeshyClient()
    try:
        # 删除 Meshy 端任务
        preview_id = record.get("preview_task_id", "")
        refine_id = record.get("refine_task_id", "")
        if preview_id:
            await client.delete_task(preview_id)
        if refine_id:
            await client.delete_task(refine_id)
    except MeshyError:
        pass
    finally:
        await client.close()

    # 清理本地存储
    cleanup_task_storage(task_id)

    # 删除 DB 记录
    db_delete_task(task_id)
    return {"deleted": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
