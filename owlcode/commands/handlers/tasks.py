"""后台任务管理的命令处理器。"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from owlcode.commands.registry import Command, CommandContext, CommandType

if TYPE_CHECKING:
    from owlcode.agents.task_manager import TaskManager


def _format_elapsed(start: float, end: float | None) -> str:
    elapsed = (end or time.monotonic()) - start
    if elapsed >= 60:
        return f"{elapsed / 60:.1f}m"
    return f"{elapsed:.0f}s"


def _format_status(status: str) -> str:
    icons = {"running": "\u23f3", "completed": "\u2713", "failed": "\u2717", "cancelled": "\u2298"}
    return f"{icons.get(status, '?')} {status}"


def create_tasks_handler(task_manager: TaskManager):
    """创建后台任务管理的命令处理函数。

    Args:
        task_manager: 后台任务管理器实例。

    Returns:
        一个 async handler 函数，处理 /tasks 命令。
    """

    async def handler(ctx: CommandContext) -> None:
        args = ctx.args.strip()
        parts = args.split(maxsplit=1) if args else []
        subcmd = parts[0] if parts else ""

        if subcmd == "info":
            if len(parts) < 2:
                ctx.ui.add_system_message("\u7528\u6cd5: /tasks info <task-id>")
                return
            task_id = parts[1].strip()
            bg = task_manager.get(task_id)
            if bg is None:
                ctx.ui.add_system_message(f"\u672a\u627e\u5230\u4efb\u52a1: {task_id}")
                return
            elapsed = _format_elapsed(bg.start_time, bg.end_time)
            lines = [
                f"\u4efb\u52a1\u8be6\u60c5: {task_id}",
                f"  \u540d\u79f0:    {bg.name}",
                f"  \u72b6\u6001:    {_format_status(bg.status)}",
                f"  \u8017\u65f6:    {elapsed}",
                f"  Tokens:  \u2191{bg.progress.input_tokens} \u2193{bg.progress.output_tokens}",
            ]
            if bg.result:
                result_preview = bg.result[:2000]
                if len(bg.result) > 2000:
                    result_preview += "\n... (truncated)"
                lines.append(f"  \u7ed3\u679c:\n{result_preview}")
            ctx.ui.add_system_message("\n".join(lines))
            return

        if subcmd == "cancel":
            if len(parts) < 2:
                ctx.ui.add_system_message("\u7528\u6cd5: /tasks cancel <task-id>")
                return
            task_id = parts[1].strip()
            if task_manager.cancel(task_id):
                ctx.ui.add_system_message(f"\u5df2\u53d6\u6d88\u4efb\u52a1: {task_id}")
            else:
                ctx.ui.add_system_message(
                    f"\u65e0\u6cd5\u53d6\u6d88\u4efb\u52a1: {task_id}\uff08\u53ef\u80fd\u4e0d\u5b58\u5728\u6216\u5df2\u5b8c\u6210\uff09"
                )
            return

        # \u9ed8\u8ba4\uff1a\u5217\u51fa\u6240\u6709\u4efb\u52a1
        tasks = task_manager.list_tasks()
        if not tasks:
            ctx.ui.add_system_message("\u6ca1\u6709\u540e\u53f0\u4efb\u52a1")
            return

        lines = ["\u540e\u53f0\u4efb\u52a1\u5217\u8868:"]
        for bg in tasks:
            elapsed = _format_elapsed(bg.start_time, bg.end_time)
            lines.append(
                f"  [{bg.id}] {bg.name:<20} {_format_status(bg.status):<14} {elapsed}"
            )
        ctx.ui.add_system_message("\n".join(lines))

    return handler


def create_tasks_command(task_manager: TaskManager) -> Command:
    """创建后台任务管理的命令对象。

    Args:
        task_manager: 后台任务管理器实例。

    Returns:
        配置好的 Command 对象。
    """
    return Command(
        name="tasks",
        description="\u7ba1\u7406\u540e\u53f0\u4efb\u52a1\uff08/tasks, /tasks info <id>, /tasks cancel <id>\uff09",
        type=CommandType.LOCAL,
        handler=create_tasks_handler(task_manager),
        aliases=["task"],
        usage="/tasks [info|cancel] [task-id]",
    )
