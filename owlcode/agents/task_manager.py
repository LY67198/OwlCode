from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from owlcode.agent import Agent

log = logging.getLogger(__name__)


@dataclass
class ProgressInfo:
    """后台任务进度信息，记录工具调用次数与 Token 消耗。"""
    tool_call_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    last_activity: str = ""


@dataclass
class BackgroundTask:
    """后台任务数据类，封装一次异步 Agent 执行的完整生命周期。"""
    id: str
    name: str
    agent: Agent
    task: str
    status: str = "running"
    result: str = ""
    start_time: float = field(default_factory=time.monotonic)
    end_time: float | None = None
    cancel: Callable[[], None] | None = None
    progress: ProgressInfo = field(default_factory=ProgressInfo)


class TaskManager:
    """后台任务管理器，负责任务的启动、取消与结果轮询。

    通过 asyncio.Task 异步执行 Agent 任务，维护任务状态并提供完成通知队列。
    """

    def __init__(self) -> None:
        """初始化任务管理器。"""
        self._tasks: dict[str, BackgroundTask] = {}
        self._notify_queue: asyncio.Queue[str] = asyncio.Queue()
        self._async_tasks: dict[str, asyncio.Task[None]] = {}


    def launch(
        self,
        agent: Agent,
        task: str,
        name: str = "",
        fork_conversation: Any = None,
    ) -> str:
        """启动一个新的后台任务。

        Args:
            agent: 执行任务的 Agent 实例。
            task: 任务描述/提示词。
            name: 任务显示名称，为空时使用 task_id。
            fork_conversation: 可选的 Fork 会话对象。

        Returns:
            新创建任务的唯一 ID（8 位十六进制字符串）。
        """
        task_id = uuid.uuid4().hex[:8]
        bg = BackgroundTask(
            id=task_id,
            name=name or task_id,
            agent=agent,
            task=task,
        )
        self._tasks[task_id] = bg

        async_task = asyncio.create_task(
            self._run_background(task_id, fork_conversation)
        )
        self._async_tasks[task_id] = async_task

        bg.cancel = async_task.cancel
        return task_id


    async def _run_background(
        self, task_id: str, fork_conversation: Any = None
    ) -> None:
        """后台执行 Agent 任务的核心协程。

        支持 Fork 会话模式和普通模式。任务完成后，如果 Agent 属于某个团队，
        会通过 mailbox 向 lead 汇报空闲状态并持续监听后续指令。

        Args:
            task_id: 任务 ID。
            fork_conversation: 可选的 Fork 会话对象。
        """
        bg = self._tasks.get(task_id)
        if bg is None:
            return

        try:
            if fork_conversation is not None:
                result = await bg.agent.run_to_completion("", fork_conversation)
            else:
                result = await bg.agent.run_to_completion(bg.task)
            bg.result = result
            bg.status = "completed"

            if bg.agent.team_name and bg.agent._team_manager:
                mailbox = bg.agent._team_manager.get_mailbox(bg.agent.team_name)
                if mailbox:
                    from owlcode.teams.mailbox import create_message
                    msg = create_message(
                        from_agent=bg.name,
                        to_agent="lead",
                        content=f"[idle] {bg.name}: completed initial task",
                        summary=f"{bg.name} idle",
                    )
                    mailbox.write("lead", msg)

                    for _ in range(60):
                        await asyncio.sleep(1)
                        msgs = mailbox.consume(bg.agent.agent_id)
                        if not msgs:
                            continue
                        prompt = "\n\n".join(
                            f"[Message from {m.from_agent}] {m.content}" for m in msgs
                        )
                        result = await bg.agent.run_to_completion(prompt)
                        bg.result = result
                        msg = create_message(
                            from_agent=bg.name,
                            to_agent="lead",
                            content=f"[idle] {bg.name}: completed follow-up",
                            summary=f"{bg.name} idle",
                        )
                        mailbox.write("lead", msg)

        except asyncio.CancelledError:
            bg.status = "cancelled"
            bg.result = "Task was cancelled"
        except Exception as e:
            log.error("Background task %s failed: %s", task_id, e)
            bg.status = "failed"
            bg.result = f"Error: {e}"
        finally:
            bg.end_time = time.monotonic()
            bg.progress.input_tokens = bg.agent.total_input_tokens
            bg.progress.output_tokens = bg.agent.total_output_tokens
            self._async_tasks.pop(task_id, None)
            await self._notify_queue.put(task_id)


    def adopt_running(
        self,
        agent: Agent,
        task_description: str,
        partial_result: str = "",
        name: str = "",
    ) -> str:
        """接管一个已在运行的 Agent 作为后台任务。

        适用于会话恢复等场景，Agent 可能已有部分结果。

        Args:
            agent: 已在运行的 Agent 实例。
            task_description: 任务描述。
            partial_result: 已有的部分执行结果。
            name: 任务显示名称。

        Returns:
            新创建的任务 ID。
        """
        task_id = uuid.uuid4().hex[:8]
        bg = BackgroundTask(
            id=task_id,
            name=name or task_id,
            agent=agent,
            task=task_description,
            result=partial_result,
        )
        self._tasks[task_id] = bg

        async_task = asyncio.create_task(self._continue_background(task_id))
        self._async_tasks[task_id] = async_task
        bg.cancel = async_task.cancel
        return task_id


    async def _continue_background(self, task_id: str) -> None:
        """继续执行已接管的后台任务。

        在已有 partial_result 基础上追加 Agent 的 run_to_completion 结果。

        Args:
            task_id: 任务 ID。
        """
        bg = self._tasks.get(task_id)
        if bg is None:
            return

        try:
            result = await bg.agent.run_to_completion(bg.task)
            bg.result = (bg.result + "\n" + result).strip() if bg.result else result
            bg.status = "completed"
        except asyncio.CancelledError:
            bg.status = "cancelled"
        except Exception as e:
            log.error("Background task %s failed: %s", task_id, e)
            bg.status = "failed"
            bg.result = f"Error: {e}"
        finally:
            bg.end_time = time.monotonic()
            bg.progress.input_tokens = bg.agent.total_input_tokens
            bg.progress.output_tokens = bg.agent.total_output_tokens
            self._async_tasks.pop(task_id, None)
            await self._notify_queue.put(task_id)

    def get(self, task_id: str) -> BackgroundTask | None:
        """获取指定 ID 的后台任务。

        Args:
            task_id: 任务 ID。

        Returns:
            对应的 BackgroundTask，不存在则返回 None。
        """
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[BackgroundTask]:
        """列出所有后台任务。

        Returns:
            BackgroundTask 列表。
        """
        return list(self._tasks.values())

    def cancel(self, task_id: str) -> bool:
        """取消指定任务。

        Args:
            task_id: 任务 ID。

        Returns:
            成功取消返回 True，若任务不存在或已结束则返回 False。
        """
        bg = self._tasks.get(task_id)
        if bg is None or bg.status != "running":
            return False
        async_task = self._async_tasks.get(task_id)
        if async_task and not async_task.done():
            async_task.cancel()
            return True
        return False

    def poll_completed(self) -> list[BackgroundTask]:
        """轮询已完成的任务列表（非阻塞）。

        从通知队列中取出所有已完成的 task_id，返回对应的 BackgroundTask。

        Returns:
            已完成的后台任务列表。
        """
        completed: list[BackgroundTask] = []
        while not self._notify_queue.empty():
            try:
                task_id = self._notify_queue.get_nowait()
                bg = self._tasks.get(task_id)
                if bg is not None:
                    completed.append(bg)
            except asyncio.QueueEmpty:
                break
        return completed
