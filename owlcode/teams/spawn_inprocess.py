from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from owlcode.teams.progress import TeammateProgress, random_verb

if TYPE_CHECKING:
    from owlcode.agent import Agent
    from owlcode.conversation import ConversationManager
    from owlcode.teams.models import TeammateInfo

log = logging.getLogger(__name__)


class InProcessTeammateHandle:
    """进程内团队成员的执行句柄，封装 Agent、异步任务与进度追踪。

    提供 done/result 属性用于检查执行状态和获取结果。
    """

    def __init__(
        self,
        agent: Agent,
        task: asyncio.Task[str],
        name: str,
        progress: TeammateProgress | None = None,
    ) -> None:
        """初始化执行句柄。

        Args:
            agent: 执行任务的 Agent 实例。
            task: 异步任务对象。
            name: 成员名称。
            progress: 可选的进度追踪器。
        """
        self.agent = agent
        self.task = task
        self.name = name
        self.progress = progress


    @property
    def done(self) -> bool:
        """检查异步任务是否已完成。

        Returns:
            True 表示任务已结束（成功、取消或异常）。
        """
        return self.task.done()

    @property
    def result(self) -> str | None:
        """获取异步任务结果（仅在任务完成后可用）。

        Returns:
            任务结果字符串，若取消或异常则返回 None。
        """
        if self.task.done():
            try:
                return self.task.result()
            except (asyncio.CancelledError, Exception):
                return None
        return None


    def cancel(self) -> None:
        """取消正在运行的异步任务。"""
        if not self.task.done():
            self.task.cancel()


def spawn_inprocess_teammate(
    agent: Agent,
    prompt: str,
    name: str,
    conversation: ConversationManager | None = None,
    member: TeammateInfo | None = None,
    team_name: str = "",
) -> InProcessTeammateHandle:
    """在进程内启动一个团队成员并返回执行句柄。

    创建进度追踪器，注册事件回调以记录工具调用和 Token 消耗，
    然后以 asyncio.Task 形式异步执行 Agent 的 run_to_completion。

    Args:
        agent: 执行任务的 Agent 实例。
        prompt: 任务提示词。
        name: 成员名称。
        conversation: 可选会话（Fork 场景）。
        member: 可选的成员信息对象，进度数据会附加到其上。
        team_name: 团队名称。

    Returns:
        InProcessTeammateHandle 执行句柄。
    """

    # Create progress tracker and attach to member if provided
    progress = TeammateProgress(
        name=name,
        team_name=team_name,
        spinner_verb=random_verb(),
    )
    if member is not None:
        member.progress = progress

    def _on_event(event: dict[str, Any]) -> None:
        """Event callback wired into agent.run_to_completion."""
        event_type = event.get("type")
        if event_type == "tool_use":
            tool_name = event.get("toolName", "")
            args = event.get("args", {})
            progress.record_tool_use(tool_name, args)
        elif event_type == "usage":
            usage = event.get("usage", {})
            progress.record_tokens(
                usage.get("inputTokens", 0),
                usage.get("outputTokens", 0),
            )
        elif event_type == "stream_text":
            text = event.get("text")
            if text:
                with progress._lock:
                    progress.last_message = text

    async def _run() -> str:
        try:
            if conversation is not None:
                result = await agent.run_to_completion(
                    "", conversation, event_callback=_on_event,
                )
            else:
                result = await agent.run_to_completion(
                    prompt, event_callback=_on_event,
                )
            progress.status = "completed"
            return result
        except asyncio.CancelledError:
            progress.status = "stopped"
            raise
        except Exception:
            progress.status = "failed"
            raise

    task = asyncio.create_task(_run(), name=f"teammate-{name}")
    log.info("Spawned in-process teammate %s (verb=%s)", name, progress.spinner_verb)
    return InProcessTeammateHandle(agent=agent, task=task, name=name, progress=progress)
