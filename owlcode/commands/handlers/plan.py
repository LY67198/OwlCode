"""Plan 模式切换的命令处理器。"""

from __future__ import annotations

from owlcode.commands.registry import Command, CommandContext, CommandType


async def handle_plan(ctx: CommandContext) -> None:
    """切换到 Plan 模式（只读），可选附带任务描述发送给模型。

    Args:
        ctx: 命令执行上下文。
    """
    ctx.ui.set_plan_mode(True)
    ctx.ui.add_system_message("\u5df2\u5207\u6362\u5230 Plan \u6a21\u5f0f \u2014 \u53ea\u8bfb\uff0c\u7981\u6b62\u5199\u5165\u548c\u547d\u4ee4\u6267\u884c")
    if ctx.args:
        ctx.ui.send_user_message(ctx.args)


PLAN_COMMAND = Command(
    name="plan",
    aliases=["p"],
    description="\u5207\u6362\u5230 Plan \u6a21\u5f0f",
    usage="/plan [\u4efb\u52a1\u63cf\u8ff0]",
    type=CommandType.LOCAL_UI,
    handler=handle_plan,
)
