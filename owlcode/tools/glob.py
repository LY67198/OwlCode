from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from owlcode.tools.base import SKIP_DIRS, Tool, ToolResult


class Params(BaseModel):
    pattern: str = Field(description="Glob pattern to match (e.g. '**/*.py')")
    path: str = Field(default=".", description="Base directory to search from")


class Glob(Tool):
    """使用 glob 模式匹配文件路径，返回匹配文件的相对路径列表。

    自动跳过 .git、node_modules 等常见非代码目录。
    """

    name = "Glob"
    description = "Find files matching a glob pattern, returning relative paths."
    params_model = Params
    category = "read"
    is_concurrency_safe = True


    async def execute(self, params: Params) -> ToolResult:
        """按 glob 模式搜索文件。

        Args:
            params: 包含 pattern（glob 模式）和 path（搜索基目录）的参数。

        Returns:
            ToolResult，output 为匹配文件的相对路径列表（每行一个）。
        """
        base = Path(params.path)
        if not base.exists():
            return ToolResult(output=f"Error: path not found: {params.path}", is_error=True)

        try:
            matches = sorted(
                str(p.relative_to(base))
                for p in base.glob(params.pattern)
                if p.is_file() and not any(part in SKIP_DIRS for part in p.parts)
            )
        except Exception as e:
            return ToolResult(output=f"Error: {e}", is_error=True)

        if not matches:
            return ToolResult(output="No files matched the pattern.")
        return ToolResult(output="\n".join(matches))

