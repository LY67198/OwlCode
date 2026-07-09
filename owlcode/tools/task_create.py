from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from owlcode.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from owlcode.teams.manager import TeamManager


class TaskCreateParams(BaseModel):
    title: str
    description: str = ""
    assignee: str = ""
    blocks: list[str] | None = None
    blocked_by: list[str] | None = None


class TaskCreateTool(Tool):
    """在团队任务面板中创建共享任务。

    支持通过 blocks/blocked_by 字段设置任务之间的依赖关系。
    """

    name = "TaskCreate"
    description = (
        "Create a shared task in the team's task board. "
        "Supports dependency tracking with blocks/blocked_by fields."
    )
    params_model = TaskCreateParams
    category = "command"
    is_concurrency_safe = True


    def __init__(self, team_manager: TeamManager, team_name: str, agent_name: str = "") -> None:
        self._team_manager = team_manager
        self._team_name = team_name
        self._agent_name = agent_name


    async def execute(self, params: BaseModel) -> ToolResult:
        """创建新任务。

        Args:
            params: 包含 title（标题）、description（描述）、assignee（负责人）、
                   blocks（阻塞的任务）和 blocked_by（被阻塞于）的 TaskCreateParams。

        Returns:
            ToolResult，创建成功返回任务 ID、标题、状态和负责人信息。
        """
        p: TaskCreateParams = params  # type: ignore[assignment]

        store = self._team_manager.get_task_store(self._team_name)
        if store is None:
            return ToolResult(output=f"Task store not found for team '{self._team_name}'", is_error=True)

        task = store.create(
            title=p.title,
            description=p.description,
            assignee=p.assignee,
            blocks=p.blocks,
            blocked_by=p.blocked_by,
            created_by=self._agent_name,
        )

        return ToolResult(
            output=(
                f"Task created:\n"
                f"  ID: {task.id}\n"
                f"  Title: {task.title}\n"
                f"  Status: {task.status}\n"
                f"  Assignee: {task.assignee or '(unassigned)'}"
            )
        )
