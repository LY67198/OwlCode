from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from owlcode.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from owlcode.agent import Agent
    from owlcode.teams.manager import TeamManager


class TeamDeleteParams(BaseModel):
    team_name: str


class TeamDeleteTool(Tool):
    """删除 Agent 团队。

    终止所有 pane 进程、移除 worktree、清理邮箱和团队目录。
    要求所有成员处于空闲状态。
    """

    name = "TeamDelete"
    description = (
        "Delete an Agent Team. Terminates all pane processes, removes worktrees, "
        "cleans up mailbox and team directory. Requires all members to be idle."
    )
    params_model = TeamDeleteParams
    category = "command"
    is_concurrency_safe = False


    def __init__(self, team_manager: TeamManager, parent_agent: Agent | None = None) -> None:
        self._team_manager = team_manager
        self._parent_agent = parent_agent


    async def execute(self, params: BaseModel) -> ToolResult:
        """删除指定团队。

        Args:
            params: 包含 team_name 的 TeamDeleteParams。

        Returns:
            ToolResult，删除成功返回确认信息，若处于协调者模式则同时恢复完整工具集。
        """
        p: TeamDeleteParams = params  # type: ignore[assignment]

        from owlcode.teams.manager import TeamError

        try:
            self._team_manager.delete_team(p.team_name)
        except TeamError as e:
            return ToolResult(output=str(e), is_error=True)
        except Exception as e:
            return ToolResult(output=f"Failed to delete team: {e}", is_error=True)

        coordinator_note = ""
        if self._parent_agent and self._parent_agent.coordinator_mode:
            full_registry = getattr(self._parent_agent, '_full_registry', None)
            if full_registry is not None:
                self._parent_agent.registry = full_registry
                self._parent_agent._full_registry = None
            self._parent_agent.coordinator_mode = False
            coordinator_note = "\nCoordinator Mode deactivated: full tools restored."

        return ToolResult(output=f"Team '{p.team_name}' deleted successfully.{coordinator_note}")
