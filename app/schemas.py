from typing import Any

from pydantic import BaseModel, Field, field_validator


class CreatePreviewRequest(BaseModel):
    """创建 preview 任务的请求参数。"""

    prompt: str = Field(..., max_length=600, description="文本提示，最多 600 字符")
    mode: str = Field(default="preview", description="固定为 preview")
    model_type: str = Field(default="standard", description="模型类型: standard / lowpoly")
    ai_model: str = Field(default="meshy-6", description="AI 模型版本")
    target_formats: list[str] = Field(
        default=["glb", "fbx", "usdz"],
        description="目标输出格式",
    )
    art_style: str = Field(default="realistic", description="艺术风格")
    negative_prompt: str = Field(default="", description="负向提示")
    topology: str = Field(default="triangle", description="拓扑结构")
    target_polycount: int = Field(default=30000, description="目标多边形数")
    should_remesh: bool = Field(default=True, description="是否重新网格化")
    enable_pbr: bool = Field(default=False, description="是否启用 PBR")

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("prompt cannot be empty")
        if len(v) > 600:
            raise ValueError("prompt cannot exceed 600 characters")
        return v


class CreateRefineRequest(BaseModel):
    """创建 refine 任务的请求参数。"""

    preview_task_id: str = Field(default="", description="关联的 preview 任务 ID（可选，URL 已提供）")
    mode: str = Field(default="refine", description="固定为 refine")
    enable_pbr: bool = Field(default=False, description="是否启用 PBR")
    hd_texture: bool = Field(default=False, description="是否生成高清贴图")
    texture_prompt: str = Field(default="", description="贴图专用提示")
    texture_richness: str = Field(default="high", description="贴图丰富度")


class PolishRequest(BaseModel):
    """AI 润色请求参数。"""

    text: str = Field(..., max_length=600, description="原始提示词")

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text cannot be empty")
        return v


class PolishResponse(BaseModel):
    """AI 润色响应。"""

    original: str
    polished: str


class TaskResponse(BaseModel):
    """任务响应模型。"""

    id: str
    status: str
    progress: int = 0
    prompt: str = ""
    thumbnail_url: str = ""
    model_urls: dict[str, str] = Field(default_factory=dict)
    texture_urls: list[dict[str, str]] | dict[str, str] | None = Field(default=None)
    preview_task_id: str = ""
    refine_task_id: str = ""
    local_files: dict[str, str] = Field(default_factory=dict)
    created_at: int = 0
    error_message: str = ""
    is_refined: bool = False


class ErrorResponse(BaseModel):
    """错误响应模型。"""

    error: str
    detail: str = ""
    code: int = 500
