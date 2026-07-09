from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from owlcode.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from owlcode.cache import FileCache
    from owlcode.tools.file_state_cache import FileStateCache


class Params(BaseModel):
    file_path: str = Field(description="Path to the file to write")
    content: str = Field(description="Content to write to the file")


class WriteFile(Tool):
    """将内容写入文件，必要时自动创建父目录。

    若文件已存在则覆盖。覆盖已存在文件前必须先用 ReadFile 读取，否则
    FileStateCache 会阻止操作。
    """

    name = "WriteFile"
    description = (
        "Write content to a file, creating parent directories if needed. Overwrites existing files.\n"
        "You MUST read existing files with ReadFile before overwriting them. This tool will fail otherwise."
    )
    params_model = Params
    category = "write"


    def __init__(self, file_cache: FileCache | None = None, file_history: Any = None, file_state_cache: FileStateCache | None = None) -> None:
        self._cache = file_cache
        self.file_history = file_history
        self._state_cache = file_state_cache


    async def execute(self, params: Params) -> ToolResult:
        """将内容写入文件。

        Args:
            params: 包含 file_path（目标文件路径）和 content（写入内容）的参数。

        Returns:
            ToolResult，写入成功返回确认信息，失败返回错误描述。
        """
        if self.file_history is not None:
            self.file_history.track_edit(params.file_path)

        path = Path(params.file_path)

        if self._state_cache and path.exists():
            resolved = str(path.resolve())
            ok, err_msg = self._state_cache.check(resolved)
            if not ok:
                return ToolResult(output=err_msg, is_error=True)

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(params.content, encoding="utf-8")
            if self._cache:
                self._cache.invalidate(str(path.resolve()))
            if self._state_cache:
                self._state_cache.update(str(path.resolve()))
        except Exception as e:
            return ToolResult(output=f"Error writing file: {e}", is_error=True)
        return ToolResult(output=f"Successfully wrote to {params.file_path}")
