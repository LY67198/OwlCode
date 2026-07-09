from __future__ import annotations

import secrets
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

from owlcode.tools.base import Tool, ToolResult
from owlcode.worktree.slug import validate_slug

if TYPE_CHECKING:
    from owlcode.worktree.manager import WorktreeManager


class EnterWorktreeParams(BaseModel):
    name: Optional[str] = Field(
        default=None,
        description=(
            'Optional name for the worktree. Each "/"-separated segment may '
            "contain only letters, digits, dots, underscores, and dashes; "
            "max 64 chars total. A random name is generated if not provided."
        ),
    )


class EnterWorktreeTool(Tool):
    """创建独立的 git worktree 并将当前会话切换到其中。

    用于隔离文件操作，避免影响主工作区。
    """

    name = "EnterWorktree"
    description = (
        "Creates an isolated worktree (via git) and switches the session into it"
    )
    params_model = EnterWorktreeParams
    category = "command"
    should_defer = True


    def __init__(self, worktree_manager: WorktreeManager) -> None:
        self._manager = worktree_manager


    async def execute(self, params: EnterWorktreeParams) -> ToolResult:
        """创建并进入一个隔离的 git worktree。

        Args:
            params: 包含 name（可选的 worktree 名称）的 EnterWorktreeParams。

        Returns:
            ToolResult，创建成功后返回 worktree 路径信息，
            若已在 worktree 会话中则 is_error 为 True。
        """
        if self._manager.get_current_session() is not None:
            return ToolResult(
                output="Already in a worktree session", is_error=True
            )

        slug = params.name or f"wt-{secrets.token_hex(4)}"

        err = validate_slug(slug)
        if err:
            return ToolResult(output=f"Invalid worktree name: {err}", is_error=True)

        try:
            wt = await self._manager.create(slug)
            session = await self._manager.enter(slug)
        except Exception as e:
            return ToolResult(
                output=f"Error creating worktree: {e}", is_error=True
            )

        branch_info = f" on branch {wt.branch}" if wt.branch else ""
        return ToolResult(
            output=(
                f"Created worktree at {session.worktree_path}{branch_info}. "
                "The session is now working in the worktree. "
                "Use ExitWorktree to leave mid-session, or exit the session to be prompted."
            )
        )
