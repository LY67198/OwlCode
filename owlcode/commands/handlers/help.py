"""显示帮助信息的命令处理器。"""

from __future__ import annotations

from owlcode.commands.registry import Command, CommandContext, CommandType


def _format_aliases(cmd: Command) -> str:
    if not cmd.aliases:
        return cmd.name
    return cmd.name + ", " + ", ".join(f"/{a}" for a in cmd.aliases)


async def handle_help(ctx: CommandContext) -> None:
    """显示命令帮助信息。

    不带参数时列出所有可用命令；带命令名时显示该命令的详细帮助。

    Args:
        ctx: 命令执行上下文。
    """
    registry = ctx.config["registry"]

    if ctx.args:
        cmd = registry.find(ctx.args.lower())
        if cmd is None:
            ctx.ui.add_system_message(f"\u672a\u77e5\u547d\u4ee4\uff1a{ctx.args}\uff0c\u8f93\u5165 /help \u67e5\u770b\u53ef\u7528\u547d\u4ee4")
            return
        lines = [f"/{cmd.name}"]
        if cmd.aliases:
            lines[0] += f"  (\u522b\u540d: {', '.join('/' + a for a in cmd.aliases)})"
        lines.append(f"  {cmd.description}")
        if cmd.usage:
            lines.append(f"  \u7528\u6cd5: {cmd.usage}")
        if cmd.arg_prompt:
            lines.append(f"  \u53c2\u6570: {cmd.arg_prompt}")
        ctx.ui.add_system_message("\n".join(lines))
        return

    commands = registry.list_commands()
    lines = ["\u53ef\u7528\u547d\u4ee4\uff1a"]
    for cmd in commands:
        aliases_str = f"/{_format_aliases(cmd)}"
        lines.append(f"  {aliases_str:<24} {cmd.description}")
    lines.append("")
    lines.append("\u8f93\u5165 /help <\u547d\u4ee4\u540d> \u67e5\u770b\u8be6\u7ec6\u7528\u6cd5\u3002")
    ctx.ui.add_system_message("\n".join(lines))


HELP_COMMAND = Command(
    name="help",
    aliases=["h", "?"],
    description="\u663e\u793a\u5e2e\u52a9\u4fe1\u606f",
    usage="/help [\u547d\u4ee4\u540d]",
    type=CommandType.LOCAL,
    handler=handle_help,
)
