from __future__ import annotations

from typing import Callable

from pydantic import BaseModel

from owlcode.tools.base import Tool, ToolResult


class ExitPlanModeParams(BaseModel):
    pass


class ExitPlanModeTool(Tool):
    """退出计划模式并向用户提交计划以供审批。

    仅在计划模式中且计划已写入计划文件后才能调用。
    """

    name = "ExitPlanMode"
    description = (
        "Exit plan mode and present the plan for user approval. "
        "Call this when your plan is complete and written to the plan file."
    )
    params_model = ExitPlanModeParams
    category = "read"

    def __init__(
        self,
        is_plan_mode: Callable[[], bool] | None = None,
        plan_exists: Callable[[], bool] | None = None,
    ) -> None:
        self._is_plan_mode = is_plan_mode
        self._plan_exists = plan_exists

    async def execute(self, params: ExitPlanModeParams) -> ToolResult:
        """退出计划模式。

        Args:
            params: ExitPlanModeParams（无参数）。

        Returns:
            ToolResult，若不在计划模式或计划文件不存在则 is_error 为 True。
        """
        if self._is_plan_mode is not None and not self._is_plan_mode():
            return ToolResult(
                output="You are not in plan mode. This tool is only for exiting plan mode after writing a plan.",
                is_error=True,
            )
        if self._plan_exists is not None and not self._plan_exists():
            return ToolResult(
                output="No plan file found. Please write your plan to the plan file before calling ExitPlanMode.",
                is_error=True,
            )
        return ToolResult(
            output=(
                "Plan mode will be exited after this turn. "
                "The user will be shown the plan approval dialog. "
                "Do not call any more tools — end your turn now."
            )
        )
