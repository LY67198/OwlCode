from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from owlcode.tools.base import Tool, ToolResult


class SyntheticOutputParams(BaseModel):
    output: dict[str, Any] | list[Any] | str


class SyntheticOutputTool(Tool):
    """返回结构化 JSON 输出，用于非交互或协调者模式下的最终结果。

    若配置了 json_schema，会对输出进行 schema 校验。
    """

    name = "SyntheticOutput"
    description = (
        "Return structured output in JSON format. "
        "Use this tool to return your final response as structured data "
        "in non-interactive or coordinator mode sessions."
    )
    params_model = SyntheticOutputParams
    category = "read"
    is_concurrency_safe = True
    is_system_tool = True


    def __init__(self, json_schema: dict[str, Any] | None = None) -> None:
        self._json_schema = json_schema


    async def execute(self, params: BaseModel) -> ToolResult:
        """返回格式化输出。

        Args:
            params: 包含 output（输出数据，可为 dict、list 或 str）的
                   SyntheticOutputParams。

        Returns:
            ToolResult，若配置了 schema 且校验失败则 is_error 为 True。
        """
        p: SyntheticOutputParams = params  # type: ignore[assignment]

        if self._json_schema is not None:
            error = self._validate_schema(p.output)
            if error:
                return ToolResult(output=f"Output does not match required schema: {error}", is_error=True)

        if isinstance(p.output, str):
            return ToolResult(output=p.output)

        return ToolResult(output=json.dumps(p.output, ensure_ascii=False, indent=2))


    def _validate_schema(self, data: Any) -> str | None:
        """根据 json_schema 校验输出数据。

        Args:
            data: 待校验的数据。

        Returns:
            校验失败时返回错误描述字符串，通过则返回 None。
        """
        schema = self._json_schema
        if schema is None:
            return None

        if "type" in schema:
            expected_type = schema["type"]
            if expected_type == "object" and not isinstance(data, dict):
                return f"Expected object, got {type(data).__name__}"
            if expected_type == "array" and not isinstance(data, list):
                return f"Expected array, got {type(data).__name__}"
            if expected_type == "string" and not isinstance(data, str):
                return f"Expected string, got {type(data).__name__}"

        if "required" in schema and isinstance(data, dict):
            missing = [k for k in schema["required"] if k not in data]
            if missing:
                return f"Missing required fields: {', '.join(missing)}"

        return None
