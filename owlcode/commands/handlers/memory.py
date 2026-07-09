"""记忆管理的命令处理器。"""

from __future__ import annotations

from owlcode.commands.registry import Command, CommandContext, CommandType


async def handle_memory(ctx: CommandContext) -> None:
    """管理自动记忆：查看、列出、清空或编辑记忆文件。

    支持子命令：
      - (无) / list: 显示所有记忆
      - clear: 清空所有记忆
      - edit: 显示记忆文件路径

    Args:
        ctx: 命令执行上下文。
    """
    mm = ctx.memory_manager
    if mm is None:
        ctx.ui.add_system_message("\u8bb0\u5fc6\u7ba1\u7406\u5668\u672a\u521d\u59cb\u5316")
        return


    parts = ctx.args.split(None, 1)
    sub = parts[0] if parts else ""

    if sub == "":
        display = mm.get_display_text()
        ctx.ui.add_system_message(display)

    elif sub == "list":
        display = mm.get_display_text()
        ctx.ui.add_system_message(display)

    elif sub == "clear":
        mm.clear()
        ctx.ui.add_system_message("\u6240\u6709\u81ea\u52a8\u8bb0\u5fc6\u5df2\u6e05\u7a7a\u3002")

    elif sub == "edit":
        ctx.ui.add_system_message(
            f"\u7f16\u8f91\u8bb0\u5fc6\u6587\u4ef6\uff1a\n"
            f"  \u7528\u6237\u7ea7: {mm.user_path}\n"
            f"  \u9879\u76ee\u7ea7: {mm.project_path}"
        )

    else:
        ctx.ui.add_system_message(
            "\u7528\u6cd5: /memory [list | clear | edit]"
        )


MEMORY_COMMAND = Command(
    name="memory",
    description="\u8bb0\u5fc6\u7ba1\u7406",
    usage="/memory [list | clear | edit]",
    type=CommandType.LOCAL,
    handler=handle_memory,
)
