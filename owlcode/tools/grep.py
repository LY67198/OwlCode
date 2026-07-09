from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field

from owlcode.tools.base import SKIP_DIRS, Tool, ToolResult


class Params(BaseModel):
    pattern: str = Field(description="Regex pattern to search for")
    path: str = Field(default=".", description="Base directory to search from")
    include: str = Field(default="", description="Glob filter for filenames (e.g. '*.py')")


class Grep(Tool):
    """使用正则表达式搜索文件内容，返回 file:line:content 格式的匹配结果。

    支持文件名过滤，自动跳过 .git、node_modules 等非代码目录。
    """

    name = "Grep"
    description = "Search file contents using a regex pattern, returning file:line:content matches."
    params_model = Params
    category = "read"
    is_concurrency_safe = True


    async def execute(self, params: Params) -> ToolResult:
        """按正则表达式搜索文件内容。

        Args:
            params: 包含 pattern（正则表达式）、path（搜索基目录）
                   和 include（文件名 glob 过滤）的参数。

        Returns:
            ToolResult，output 为匹配行列表（格式：文件:行号:内容）。
        """
        base = Path(params.path)
        if not base.exists():
            return ToolResult(output=f"Error: path not found: {params.path}", is_error=True)

        try:
            regex = re.compile(params.pattern)
        except re.error as e:
            return ToolResult(output=f"Error: invalid regex: {e}", is_error=True)

        glob_pattern = params.include if params.include else "**/*"
        if not glob_pattern.startswith("**/"):
            glob_pattern = "**/" + glob_pattern

        results: list[str] = []
        for file_path in sorted(base.glob(glob_pattern)):
            if not file_path.is_file():
                continue
            if any(part in SKIP_DIRS for part in file_path.parts):
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, UnicodeDecodeError):
                continue
            for line_num, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    rel = file_path.relative_to(base)
                    results.append(f"{rel}:{line_num}:{line}")

        if not results:
            return ToolResult(output="No matches found.")
        return ToolResult(output="\n".join(results))

