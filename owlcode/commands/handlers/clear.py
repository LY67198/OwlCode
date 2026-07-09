"""清除对话历史的命令处理器。"""

from __future__ import annotations

from owlcode.commands.registry import Command, CommandContext, CommandType
from owlcode.conversation import ConversationManager


async def handle_clear(ctx: CommandContext) -> None:
    """清除当前对话历史、创建新会话并重置 Agent 状态。

    Args:
        ctx: 命令执行上下文，包含会话、Agent 和 UI 等引用。
    """
    if ctx.session:
        ctx.session.close()

    if ctx.session_manager:
        new_session = ctx.session_manager.create()
        ctx.config["set_session"](new_session)


    ctx.config["set_conversation"](ConversationManager())

    if ctx.agent:
        ctx.agent._loop_count = 0
        ctx.agent.clear_active_skills()

    ctx.config["clear_chat"]()
    ctx.ui.refresh_status()
    ctx.ui.add_system_message("\u5bf9\u8bdd\u5df2\u6e05\u9664\uff0c\u65b0\u4f1a\u8bdd\u5df2\u521b\u5efa")


CLEAR_COMMAND = Command(
    name="clear",
    description="\u6e05\u9664\u5bf9\u8bdd\u5386\u53f2",
    usage="/clear",
    type=CommandType.LOCAL_UI,
    handler=handle_clear,
)
