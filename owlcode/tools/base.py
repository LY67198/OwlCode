from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel

SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".tox", ".mypy_cache"}

MAX_OUTPUT_CHARS = 10000

ToolCategory = Literal["read", "write", "command"]


@dataclass
class ToolResult:
    """工具执行结果，包含输出文本和是否出错的标记。"""
    output: str
    is_error: bool = False


class Tool(ABC):
    """所有工具的抽象基类。

    定义了工具的名称、描述、参数模型、类别等基本属性，
    以及 get_schema 和 execute 两个核心接口。
    """

    name: str
    description: str
    params_model: type[BaseModel]
    category: ToolCategory = "read"
    is_concurrency_safe: bool = False
    is_system_tool: bool = False
    should_defer: bool = False

    @property
    def is_read_only(self) -> bool:
        """是否为只读工具（category 为 "read"）。"""
        return self.category == "read"


    def get_schema(self) -> dict[str, Any]:
        """获取工具的 JSON Schema，供 LLM 使用。

        Returns:
            包含 name、description 和 input_schema 的字典。
        """
        schema = self.params_model.model_json_schema()
        schema.pop("title", None)
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": schema,
        }

    @abstractmethod
    async def execute(self, params: BaseModel) -> ToolResult: ...


# --- 流式事件 ---


@dataclass
class TextDelta:
    """LLM 输出的文本增量。"""
    text: str


@dataclass
class ToolCallStart:
    """工具调用开始的信号。"""
    tool_name: str
    tool_id: str


@dataclass
class ToolCallDelta:
    """工具调用参数的增量文本。"""
    text: str


@dataclass
class ToolCallComplete:
    """工具调用完成，含完整的工具名称和参数。"""
    tool_id: str
    tool_name: str
    arguments: dict[str, Any]


@dataclass
class ThinkingDelta:
    """LLM 思考过程的增量文本。"""
    text: str


@dataclass
class ThinkingComplete:
    """思考过程完成，含完整的思考内容和签名。"""
    thinking: str
    signature: str


@dataclass
class StreamEnd:
    """流式响应结束信号。

    包含停止原因和 token 用量统计。input_tokens 已排除 prompt cache 部分。
    cache_read 为缓存命中量，cache_creation 为缓存写入量。
    OpenAI 系列只暴露 cache_read，cache_creation 始终为 0。
    """
    stop_reason: str
    input_tokens: int = 0
    output_tokens: int = 0
    # API 返回的 prompt cache 用量。Anthropic 把缓存前缀 token 分为
    # "read"（cache 命中，按 10% 计费）和 "creation"（cache 写入）。
    # input_tokens 已排除这两部分，因此实际 prompt 大小 =
    # input + cache_read + cache_creation。OpenAI 系列只暴露
    # cache_read（通过 *_tokens_details.cached_tokens），没有 creation
    # 计数，所以 cache_creation 在那边始终为 0。
    cache_read: int = 0
    cache_creation: int = 0


StreamEvent = TextDelta | ThinkingDelta | ThinkingComplete | ToolCallStart | ToolCallDelta | ToolCallComplete | StreamEnd
