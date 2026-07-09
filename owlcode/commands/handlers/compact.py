"""压缩上下文的命令处理器。"""

from __future__ import annotations

from owlcode.commands.registry import Command, CommandContext, CommandType


async def handle_compact(ctx: CommandContext) -> None:
    """触发上下文压缩以降低 token 使用量。

    当输入 token 数低于 5000 时跳过压缩；否则调用 Agent 的手动压缩
    并将压缩边界持久化到会话记录中。

    Args:
        ctx: 命令执行上下文。
    """
    if ctx.agent is None:
        ctx.ui.add_system_message("Agent \u672a\u521d\u59cb\u5316")
        return


    input_tokens, _ = ctx.ui.get_token_count()
    if input_tokens < 5000:
        ctx.ui.add_system_message(f"\u5f53\u524d token \u6570 {input_tokens:,}\uff0c\u65e0\u9700\u538b\u7f29")
        return

    from owlcode.agent import CompactNotification, ErrorEvent


    result = await ctx.agent.manual_compact(ctx.conversation)
    if isinstance(result, CompactNotification):
        # \u6301\u4e45\u5316 compact_boundary\uff0c\u4f7f\u540e\u7eed resume \u53ef\u91cd\u5efa\u538b\u7f29\u540e\u7684\u72b6\u6001\u3002
        # manual_compact \u5df2\u91cd\u5199\u4e86 ctx.conversation\uff1b\u4e0b\u4e00\u6b21 _send_message
        # \u4f1a\u91cd\u65b0\u6355\u83b7 history_cursor\uff0c\u6240\u4ee5\u8fd9\u91cc\u65e0\u9700\u624b\u52a8\u91cd\u7f6e\u3002
        if ctx.session is not None and result.boundary is not None:
            from owlcode.memory.session import make_compact_boundary

            ctx.session.append_record(
                make_compact_boundary(result.boundary.summary, result.boundary.keep)
            )
        ctx.ui.add_system_message(result.message)
    elif isinstance(result, ErrorEvent):
        ctx.ui.add_system_message(f"\u538b\u7f29\u5931\u8d25: {result.message}")


COMPACT_COMMAND = Command(
    name="compact",
    aliases=["c"],
    description="\u538b\u7f29\u4e0a\u4e0b\u6587",
    usage="/compact [\u4fdd\u7559\u91cd\u70b9]",
    type=CommandType.LOCAL,
    handler=handle_compact,
)
