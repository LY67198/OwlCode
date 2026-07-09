"""MCP 工具包装器：将 MCP 工具定义包装为内部 Tool 接口。"""

from __future__ import annotations

from typing import Any

from mcp import types as mcp_types
from pydantic import BaseModel, create_model

from owlcode.mcp.client import MCPClient
from owlcode.tools.base import Tool, ToolResult


def _build_params_model(
    tool_name: str, input_schema: dict[str, Any]
) -> type[BaseModel]:
    """根据 JSON schema 动态构建 Pydantic 参数模型。

    Args:
        tool_name: 工具名称，用于命名模型。
        input_schema: MCP 工具的 inputSchema。

    Returns:
        动态生成的 Pydantic BaseModel 子类。
    """
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))

    field_definitions: dict[str, Any] = {}
    for name, prop in properties.items():
        py_type = _json_type_to_python(prop.get("type", "string"))
        if name in required:
            field_definitions[name] = (py_type, ...)
        else:
            field_definitions[name] = (py_type | None, None)

    return create_model(f"{tool_name}Params", **field_definitions)


def _json_type_to_python(json_type: str) -> type:
    """将 JSON schema 类型字符串映射为 Python 类型。

    Args:
        json_type: JSON schema 类型名，如 "string"、"integer"。

    Returns:
        对应的 Python 类型。
    """
    mapping: dict[str, type] = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "object": dict,
        "array": list,
    }
    return mapping.get(json_type, str)


def _extract_text(content: list[Any]) -> str:
    """从 MCP 工具返回的内容列表中提取文本。

    支持 TextContent、ImageContent 和 EmbeddedResource 等类型。

    Args:
        content: MCP 返回的内容对象列表。

    Returns:
        拼接后的文本字符串。
    """
    parts: list[str] = []
    for block in content:
        if isinstance(block, mcp_types.TextContent):
            parts.append(block.text)
        elif isinstance(block, mcp_types.ImageContent):
            parts.append(f"[image: {block.mimeType}]")
        elif isinstance(block, mcp_types.EmbeddedResource):
            resource = block.resource
            if hasattr(resource, "text"):
                parts.append(resource.text)
            else:
                parts.append(f"[binary resource: {resource.uri}]")
    return "\n".join(parts) if parts else "(no output)"


class MCPToolWrapper(Tool):
    """MCP 工具包装器，将 MCP 协议定义的 Tool 适配为 owlcode 的 Tool 接口。"""

    def __init__(
        self,
        server_name: str,
        tool_def: mcp_types.Tool,
        client: MCPClient,
    ) -> None:
        self._server_name = server_name
        self._tool_def = tool_def
        self._client = client
        self.name = f"mcp_{server_name}_{tool_def.name}"
        self.description = tool_def.description or tool_def.name
        self.category = "command"
        self.is_concurrency_safe = False
        self.should_defer = True
        self.params_model = _build_params_model(
            tool_def.name, tool_def.inputSchema
        )

    @property
    def mcp_tool_name(self) -> str:
        """原始 MCP 工具名称（不含服务器名前缀）。"""
        return self._tool_def.name

    def get_schema(self) -> dict[str, Any]:
        """返回工具的 JSON schema 描述。

        Returns:
            包含 name、description 和 input_schema 的字典。
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self._tool_def.inputSchema,
        }

    async def execute(self, params: BaseModel) -> ToolResult:
        """执行 MCP 工具调用。

        如果客户端连接断开会自动尝试重连。

        Args:
            params: 工具调用参数。

        Returns:
            包含执行结果或错误信息的 ToolResult。
        """
        if not self._client.is_alive:
            try:
                await self._client.connect()
            except Exception as e:
                return ToolResult(
                    output=f"MCP server '{self._server_name}' reconnect failed: {e}",
                    is_error=True,
                )

        try:
            result = await self._client.call_tool(
                self._tool_def.name, params.model_dump(exclude_none=True)
            )
        except Exception as e:
            self._client._alive = False
            return ToolResult(
                output=f"MCP tool call failed: {e}",
                is_error=True,
            )

        text = _extract_text(result.content)
        return ToolResult(output=text, is_error=bool(result.isError))
