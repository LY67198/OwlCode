"""Hook 引擎：匹配事件与条件，调度执行 Hook 动作。"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from owlcode.hooks.executors import execute_action
from owlcode.hooks.models import ActionResult, Hook, HookContext, ToolRejectedError

log = logging.getLogger(__name__)


@dataclass
class HookNotification:
    """Hook 执行通知，记录单个 Hook 的执行结果。"""

    hook_id: str
    event: str
    output: str
    success: bool


class HookEngine:
    """Hook 执行引擎，负责匹配并运行符合条件的事件 Hook。

    管理注册的 Hook 列表，根据事件类型和条件筛选匹配的 Hook，
    按同步或异步方式执行，并收集 prompt 消息和通知。
    """

    def __init__(self, hooks: list[Hook] | None = None) -> None:
        """初始化 Hook 引擎。

        Args:
            hooks: 初始注册的 Hook 列表，可选。
        """
        self.hooks: list[Hook] = hooks or []
        self._prompt_messages: list[str] = []
        self._notifications: list[HookNotification] = []

    def find_matching_hooks(self, event: str, ctx: HookContext) -> list[Hook]:
        """查找与指定事件和上下文匹配的 Hook 列表。

        Args:
            event: 事件名称。
            ctx: Hook 执行上下文。

        Returns:
            匹配的 Hook 列表。
        """
        matched: list[Hook] = []
        for hook in self.hooks:
            if hook.event != event:
                continue
            if not hook.should_run():
                continue
            if hook.condition is not None and not hook.condition.evaluate(ctx):
                continue
            matched.append(hook)
        return matched

    async def run_hooks(self, event: str, ctx: HookContext) -> None:
        """运行所有匹配指定事件的 Hook。

        对于标记为 async 的 Hook，使用 asyncio.ensure_future 异步执行，
        不阻塞当前流程；其余 Hook 按顺序同步 await。

        Args:
            event: 事件名称。
            ctx: Hook 执行上下文。
        """
        matched = self.find_matching_hooks(event, ctx)
        for hook in matched:
            hook.mark_executed()
            if hook.async_exec:
                asyncio.ensure_future(self._run_single(hook, ctx))
            else:
                await self._run_single(hook, ctx)

    async def _run_single(self, hook: Hook, ctx: HookContext) -> None:
        """执行单个 Hook 并收集结果到通知列表和 prompt 消息中。

        Args:
            hook: 要执行的 Hook。
            ctx: Hook 执行上下文。
        """
        try:
            result = await execute_action(hook.action, ctx)
            if hook.action.type == "prompt" and result.success:
                self._prompt_messages.append(result.output)
            self._notifications.append(
                HookNotification(
                    hook_id=hook.id,
                    event=hook.event,
                    output=result.output,
                    success=result.success,
                )
            )
            if not result.success:
                log.warning(
                    "Hook '%s' action failed: %s", hook.id, result.output
                )
        except Exception as e:
            log.warning("Hook '%s' execution error: %s", hook.id, e)
            self._notifications.append(
                HookNotification(
                    hook_id=hook.id,
                    event=hook.event,
                    output=str(e),
                    success=False,
                )
            )

    async def run_pre_tool_hooks(
        self, ctx: HookContext
    ) -> ToolRejectedError | None:
        """运行 pre_tool_use 事件的匹配 Hook，支持工具调用拒绝。

        与 run_hooks 不同，此方法为同步顺序执行，且支持 Hook 的 reject 模式：
        当匹配的 Hook 标记为 reject 时，返回 ToolRejectedError 以阻止工具调用。

        Args:
            ctx: Hook 执行上下文，需包含 tool_name 等工具相关信息。

        Returns:
            如果 Hook 拒绝了该工具调用，返回 ToolRejectedError；否则返回 None。
        """
        matched = self.find_matching_hooks("pre_tool_use", ctx)
        for hook in matched:
            hook.mark_executed()
            try:
                result = await execute_action(hook.action, ctx)
                self._notifications.append(
                    HookNotification(
                        hook_id=hook.id,
                        event="pre_tool_use",
                        output=result.output,
                        success=result.success,
                    )
                )
                if hook.reject:
                    return ToolRejectedError(
                        tool=ctx.tool_name,
                        reason=result.output,
                        hook_id=hook.id,
                    )
            except Exception as e:
                log.warning("Hook '%s' execution error: %s", hook.id, e)
        return None

    def get_prompt_messages(self) -> list[str]:
        """获取并清空已收集的 prompt 消息列表。

        Returns:
            prompt 类型的 Hook 执行结果消息列表。
        """
        messages = list(self._prompt_messages)
        self._prompt_messages.clear()
        return messages

    def drain_notifications(self) -> list[HookNotification]:
        """排空并返回所有已收集的 Hook 通知。

        Returns:
            自上次排空以来积累的 Hook 通知列表。
        """
        notifications = list(self._notifications)
        self._notifications.clear()
        return notifications
