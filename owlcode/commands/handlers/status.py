"""系统状态显示的命令处理器。"""

from __future__ import annotations

import os

from owlcode.commands.registry import Command, CommandContext, CommandType


VERSION = "v0.9.0"


async def handle_status(ctx: CommandContext) -> None:
    """显示当前系统状态：模式、会话、Token 用量、工具和记忆等信息。

    Args:
        ctx: 命令执行上下文。
    """
    lines = ["OwlCode \u72b6\u6001", "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"]

    mode = ctx.agent.permission_mode.value if ctx.agent else "unknown"
    lines.append(f"\u6a21\u5f0f: {mode}")

    if ctx.session:
        m = ctx.session.meta
        lines.append(f"\u4f1a\u8bdd: {m.id}\uff08{m.message_count} \u6761\u6d88\u606f\uff09")
    else:
        lines.append("\u4f1a\u8bdd: \u65e0")

    input_tokens, output_tokens = ctx.ui.get_token_count()
    context_window = ctx.agent.context_window if ctx.agent else 200_000
    pct = int(input_tokens / context_window * 100) if context_window else 0
    lines.append(f"Token: {input_tokens:,} / {context_window:,}\uff08{pct}%\uff09")

    if ctx.agent:
        enabled = [t for t in ctx.agent.registry.list_tools()
                   if ctx.agent.registry.is_enabled(t.name)]
        lines.append(f"\u5de5\u5177: {len(enabled)} \u4e2a\u5df2\u542f\u7528")


    if ctx.memory_manager:
        content = ctx.memory_manager.load()
        mem_lines = [l for l in content.split("\n") if l.strip().startswith("- ")]
        lines.append(f"\u8bb0\u5fc6: {len(mem_lines)} \u6761")

    work_dir = ctx.agent.work_dir if ctx.agent else os.getcwd()
    lines.append(f"\u5de5\u4f5c\u76ee\u5f55: {work_dir}")
    lines.append(f"\u7248\u672c: {VERSION}")

    ctx.ui.add_system_message("\n".join(lines))


STATUS_COMMAND = Command(
    name="status",
    aliases=["s"],
    description="\u663e\u793a\u72b6\u6001\u4fe1\u606f",
    usage="/status",
    type=CommandType.LOCAL,
    handler=handle_status,
)
