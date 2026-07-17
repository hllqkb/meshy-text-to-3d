import asyncio
import json
import logging
from typing import AsyncIterator

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class MeshyError(Exception):
    """Meshy API 错误基类。"""

    def __init__(self, message: str, status_code: int = 500, detail: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail or {}


class MeshyClient:
    """Meshy API 异步客户端。"""

    def __init__(self):
        self.base_url = settings.MESHY_API_BASE.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {settings.MESHY_API_KEY}",
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=httpx.Timeout(connect=10, read=60, write=30, pool=5),
            trust_env=False,
        )
        logger.info("MeshyClient initialized with key=%s", settings.masked_key)

    async def close(self):
        await self.client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict = None,
        params: dict = None,
        stream: bool = False,
        retries: int = 3,
    ) -> httpx.Response:
        url = f"{self.base_url}{path}"
        last_error = None

        for attempt in range(retries):
            try:
                response = await self.client.request(
                    method=method,
                    url=url,
                    json=json_data,
                    params=params,
                )

                if response.status_code == 429:
                    if attempt < retries - 1:
                        wait = 5 * (attempt + 1)
                        logger.warning("Rate limited, retrying in %ds (attempt %d/%d)", wait, attempt + 1, retries)
                        await asyncio.sleep(wait)
                        continue
                    raise MeshyError("速率限制，请稍后重试", status_code=429)

                if response.status_code == 401:
                    raise MeshyError("API Key 无效", status_code=401)

                if response.status_code == 402:
                    balance = await self._check_balance()
                    raise MeshyError(f"额度不足，当前余额: {balance}", status_code=402)

                if response.status_code == 404:
                    raise MeshyError("任务不存在", status_code=404)

                if response.status_code == 400:
                    detail = response.json() if response.text else {}
                    raise MeshyError(f"请求参数错误: {detail}", status_code=400, detail=detail)

                response.raise_for_status()
                return response

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code not in (429,):
                    raise MeshyError(f"HTTP {e.response.status_code}: {e.response.text}", status_code=e.response.status_code)
            except httpx.RequestError as e:
                last_error = e
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise MeshyError(f"请求失败: {e}", status_code=503)

        raise MeshyError("请求多次失败后放弃", status_code=503)

    async def _check_balance(self) -> str:
        try:
            resp = await self.client.get("/openapi/v1/balance")
            if resp.status_code == 200:
                data = resp.json()
                return str(data.get("balance", "unknown"))
        except Exception:
            pass
        return "unknown"

    async def get_balance(self) -> dict:
        """查询账户积分余额。"""
        try:
            resp = await self.client.get("/openapi/v1/balance")
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {"balance": "unknown"}

    def _extract_task_id(self, resp: httpx.Response) -> str:
        """从响应中提取 task id，支持 JSON 或纯文本。"""
        text = resp.text.strip()
        if not text:
            return ""
        try:
            data = resp.json()
            if isinstance(data, dict):
                result = data.get("result")
                if isinstance(result, str):
                    return result
                if isinstance(result, dict):
                    return result.get("id", text)
                return text
            if isinstance(data, str):
                return data
            return text
        except Exception:
            return text

    async def create_preview(self, request: dict) -> str:
        """创建 preview 任务，返回 task id。
        
        参考 meshy-3d-agent 最佳实践：
        - ai_model 始终从配置读取，确保使用有效值
        - auto_size=true 自动估算真实尺寸
        """
        payload = {
            "mode": "preview",
            "ai_model": settings.MESHY_MODEL,
            "auto_size": True,
            **request,
        }
        # 确保 mode 不被前端覆盖
        payload["mode"] = "preview"
        resp = await self._request("POST", "/openapi/v2/text-to-3d", json_data=payload)
        return self._extract_task_id(resp)

    async def create_refine(self, request: dict) -> str:
        """创建 refine 任务，返回 task id。
        
        参考 meshy-3d-agent:
        - ai_model 保持与 preview 同一模型族
        - 移除 mode 强制覆盖，由前端保证
        """
        payload = {
            "mode": "refine",
            "ai_model": settings.MESHY_MODEL,
            **request,
        }
        resp = await self._request("POST", "/openapi/v2/text-to-3d", json_data=payload)
        return self._extract_task_id(resp)

    async def get_task(self, task_id: str) -> dict:
        """获取任务详情。"""
        resp = await self._request("GET", f"/openapi/v2/text-to-3d/{task_id}")
        return resp.json()

    async def stream_task(self, task_id: str) -> AsyncIterator[dict]:
        """SSE 流式获取任务进度。"""
        url = f"{self.base_url}/openapi/v2/text-to-3d/{task_id}/stream"
        try:
            async with self.client.stream("GET", url) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            yield data
                        except json.JSONDecodeError:
                            logger.warning("Failed to parse SSE data: %s", data_str)
                    elif line.startswith("event:"):
                        event_type = line[6:].strip()
                        if event_type == "error":
                            yield {"status": "error", "error_message": "SSE stream error"}
        except httpx.HTTPStatusError as e:
            yield {"status": "error", "error_message": f"HTTP {e.response.status_code}"}
        except httpx.RequestError as e:
            yield {"status": "error", "error_message": f"Connection error: {e}"}

    async def download_asset(self, url: str, dest_path: str, chunk_size: int = 8192) -> bool:
        """流式下载资产到本地。"""
        try:
            async with httpx.AsyncClient(timeout=300) as dl_client:
                async with dl_client.stream("GET", url, follow_redirects=True) as response:
                    response.raise_for_status()
                    with open(dest_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                            f.write(chunk)
            return True
        except Exception as e:
            logger.error("Download failed: %s -> %s: %s", url, dest_path, e)
            return False

    async def delete_task(self, task_id: str) -> bool:
        """删除 Meshy 任务。"""
        try:
            resp = await self._request("DELETE", f"/openapi/v2/text-to-3d/{task_id}")
            return resp.status_code in (200, 202, 204)
        except MeshyError:
            return False
