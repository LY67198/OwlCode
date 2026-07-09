from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, Field

from owlcode.tools.base import Tool, ToolResult


class QuestionItem(BaseModel):
    """单个问题定义，支持多种问题类型。"""

    type: str = Field(description="Question type: text, radio, select, checkbox")
    name: str = Field(description="Question identifier")
    message: str = Field(description="Question text to display")
    options: list[str] = Field(
        default_factory=list,
        description="Options for radio/select/checkbox types",
    )


class AskUserParams(BaseModel):
    questions: list[QuestionItem] = Field(
        description="List of questions to ask the user"
    )


class AskUserEvent:
    """向用户提问的事件载体，包含问题列表和等待答案的 Future。"""


    def __init__(
        self,
        questions: list[dict[str, Any]],
        future: asyncio.Future[dict[str, str]],
    ) -> None:
        self.questions = questions
        self.future = future


class AskUserTool(Tool):
    """向用户提问以获取代码或上下文无法确定的信息。

    支持 text、radio、select、checkbox 四种问题类型。最多等待 5 分钟。
    """

    name = "AskUserQuestion"
    description = (
        "Ask the user one or more questions when you need information "
        "that cannot be determined from code or context alone. Supports "
        "text input, radio (single select), select, and checkbox (multi select) "
        "question types."
    )
    params_model = AskUserParams
    category: str = "read"
    is_system_tool = True
    should_defer = True


    def __init__(self) -> None:
        self._pending_event: AskUserEvent | None = None

    async def execute(self, params: AskUserParams) -> ToolResult:
        """向用户展示问题并等待回答。

        Args:
            params: 包含 questions（问题列表）的 AskUserParams。

        Returns:
            ToolResult，output 为各问题的回答汇总，超时则 is_error 为 True。
        """
        questions_data = [q.model_dump() for q in params.questions]

        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, str]] = loop.create_future()

        self._pending_event = AskUserEvent(questions=questions_data, future=future)

        try:
            answers = await asyncio.wait_for(future, timeout=300)
        except asyncio.TimeoutError:
            return ToolResult(
                output="User did not respond within 5 minutes", is_error=True
            )
        finally:
            self._pending_event = None

        lines = []
        for q in params.questions:
            answer = answers.get(q.name, "(no answer)")
            lines.append(f"{q.name}: {answer}")

        return ToolResult(output="\n".join(lines))
