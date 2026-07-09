"""MCP 服务器状态查询的命令处理器。"""

from __future__ import annotations

from owlcode.commands.registry import Command, CommandContext, CommandType


async def handle_mcp(ctx: CommandContext) -> None:
    """显示 MCP 服务器连接状态及各服务器提供的工具列表。

    Args:
        ctx: 命令执行上下文。
    """
    app = ctx.ui
    info = getattr(app, "_mcp_server_info", "")
    if not info:
        ctx.ui.add_system_message("No MCP servers connected")
        return

    lines = ["MCP \u72b6\u6001", "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"]
    lines.append(info)

    mcp_mgr = getattr(app, "mcp_manager", None)
    if mcp_mgr and hasattr(mcp_mgr, "_clients"):
        for name, client in mcp_mgr._clients.items():
            tool_names = [
                t.name for t in ctx.agent.registry.list_tools()
                if t.name.startswith(f"mcp__{name}__")
            ]
            lines.append(f"\n  {name}: {len(tool_names)} tools")
            for tn in tool_names[:10]:
                short = tn.replace(f"mcp__{name}__", "")
                lines.append(f"    - {short}")
            if len(tool_names) > 10:
                lines.append(f"    \u2026 and {len(tool_names) - 10} more")

    ctx.ui.add_system_message("\n".join(lines))


MCP_COMMAND = Command(
    name="mcp",
    aliases=[],
    description="\u663e\u793a MCP \u670d\u52a1\u5668\u72b6\u6001",
    usage="/mcp",
    type=CommandType.LOCAL,
    handler=handle_mcp,
)
