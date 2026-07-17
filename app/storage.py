import asyncio
import json
import logging
import shutil
from pathlib import Path

from app.db import update_task
from app.meshy_client import MeshyClient

logger = logging.getLogger(__name__)

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"


def ensure_storage_dir():
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)


async def download_task_assets(
    client: MeshyClient,
    db_id: str,
    model_urls: dict,
    texture_urls: dict | list | None = None,
    storage_id: str | None = None,
) -> dict:
    """下载任务资产到本地 storage/<storage_id>/ 目录。

    db_id: 数据库主键，用于更新 local_files
    storage_id: 存储目录名，默认与 db_id 相同
    返回 {format: local_path} 映射。下载失败的保留原始 URL 作为兜底。
    """
    storage_id = storage_id or db_id
    ensure_storage_dir()
    task_dir = STORAGE_DIR / storage_id
    task_dir.mkdir(parents=True, exist_ok=True)

    local_files: dict[str, str] = {}
    all_urls = {}
    all_urls.update({f"model_{k}": v for k, v in (model_urls.items() if isinstance(model_urls, dict) else {})})
    # texture_urls can be dict or list
    if isinstance(texture_urls, dict):
        all_urls.update({f"texture_{k}": v for k, v in texture_urls.items()})
    elif isinstance(texture_urls, list):
        for item in texture_urls:
            if isinstance(item, dict):
                key = item.get("format", f"texture_{len(all_urls)}")
                all_urls[f"texture_{key}"] = item.get("url", "")

    semaphore = asyncio.Semaphore(3)

    async def _dl(key: str, url: str) -> tuple[str, str | None]:
        async with semaphore:
            ext = Path(url).suffix or ".bin"
            if ext == ".bin" and "glb" in key:
                ext = ".glb"
            elif ext == ".bin" and "fbx" in key:
                ext = ".fbx"
            elif ext == ".bin" and "usdz" in key:
                ext = ".usdz"
            dest = task_dir / f"{key}{ext}"
            ok = await client.download_asset(url, str(dest))
            if ok:
                return key, str(dest)
            return key, None

    results = await asyncio.gather(*[_dl(k, u) for k, u in all_urls.items()])

    for key, path in results:
        if path:
            local_files[key] = path
        else:
            # 下载失败，保留原始 URL 兜底
            original_url = all_urls.get(key, "")
            local_files[key] = original_url
            logger.warning("Asset download failed for %s, keeping URL: %s", key, original_url)

    update_task(db_id, local_files=local_files)
    return local_files


def cleanup_task_storage(task_id: str) -> None:
    """删除任务的本地存储目录。"""
    task_dir = STORAGE_DIR / task_id
    if task_dir.exists():
        shutil.rmtree(task_dir, ignore_errors=True)
        logger.info("Cleaned up storage for task %s", task_id)
