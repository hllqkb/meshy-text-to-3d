import json
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """你是一个专业的 3D 模型文本提示词优化助手。你的任务是将用户的原始描述优化为高质量的英文提示词，使其更适合 AI 3D 模型生成。

优化规则：
1. 保留用户的核心创意和意图
2. 补充合理的细节（材质、纹理、姿态、环境光等）
3. 使用专业的英文术语
4. 输出必须是纯英文，不要添加任何解释、前缀或注释
5. 总长度控制在 200 词以内
6. 如果输入是中文，翻译成英文并润色；如果输入是英文，直接润色优化
7. 格式为一段连贯的描述，不要分点"""


class MimoClient:
    """MiMo API 异步客户端。"""

    def __init__(self):
        self.base_url = settings.MIMO_API_BASE.rstrip("/")
        self.api_key = settings.MIMO_API_KEY
        self.model = settings.MIMO_MODEL
        self.timeout = httpx.Timeout(60.0, connect=10.0)
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            trust_env=False,
        )

    async def close(self):
        await self.client.aclose()

    async def polish_prompt(self, text: str) -> str:
        """使用 MiMo 模型润色提示词，返回优化后的英文描述。"""
        if not self.api_key:
            logger.warning("MIMO_API_KEY not set, skipping polish")
            return text

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "temperature": 0.7,
            "max_tokens": 500,
        }

        try:
            resp = await self.client.post(
                "/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()

            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                if content:
                    content = content.strip().strip("'\"").strip('"')
                    logger.info("Polished prompt: %s", content[:100])
                    return content

            return text
        except httpx.HTTPStatusError as e:
            logger.error("MiMo API HTTP error: %s %s", e.response.status_code, e.response.text)
            return text
        except httpx.RequestError as e:
            logger.error("MiMo API request error: %s", e)
            return text
        except Exception as e:
            logger.error("MiMo API unexpected error: %s", e)
            return text
