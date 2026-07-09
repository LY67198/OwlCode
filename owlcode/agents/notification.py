from __future__ import annotations

from typing import TYPE_CHECKING

from owlcode.conversation import ConversationManager

if TYPE_CHECKING:
    from owlcode.agents.task_manager import BackgroundTask

MAX_NOTIFICATION_RESULT_LENGTH = 5000


def format_task_notification(task: BackgroundTask) -> str:
    """将后台任务的状态格式化为 XML 格式的通知字符串。

    Args:
        task: 已完成的后台任务对象。

    Returns:
        <task-notification> 格式的通知文本，包含任务 ID、Agent、状态、
        耗时、Token 用量及结果摘要。
    """
    result = task.result
    if len(result) > MAX_NOTIFICATION_RESULT_LENGTH:
        result = result[:MAX_NOTIFICATION_RESULT_LENGTH] + "\n... (truncated)"

    elapsed = ""
    if task.end_time is not None:
        secs = task.end_time - task.start_time
        if secs >= 60:
            elapsed = f"{secs / 60:.1f}m"
        else:
            elapsed = f"{secs:.1f}s"


    tokens = ""
    if task.progress.input_tokens or task.progress.output_tokens:
        tokens = (
            f"\nTokens: input={task.progress.input_tokens}, "
            f"output={task.progress.output_tokens}"
        )

    return (
        f"<task-notification>\n"
        f"Task ID: {task.id}\n"
        f"Agent: {task.name}\n"
        f"Status: {task.status}\n"
        f"Elapsed: {elapsed}\n"
        f"{tokens}\n"
        f"Result:\n{result}\n"
        f"</task-notification>"
    )


def inject_task_notifications(
    conversation: ConversationManager,
    completed_tasks: list[BackgroundTask],
) -> None:
    """将已完成的后台任务通知注入到会话中作为用户消息。

    Args:
        conversation: 目标会话管理器。
        completed_tasks: 已完成的后台任务列表。
    """
    for task in completed_tasks:
        notification = format_task_notification(task)
        conversation.add_user_message(notification)
