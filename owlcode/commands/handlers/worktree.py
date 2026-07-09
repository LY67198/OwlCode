"""Git Worktree 管理的命令处理器。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlcode.commands.registry import Command, CommandContext, CommandType

if TYPE_CHECKING:
    from owlcode.worktree.manager import WorktreeManager


def create_worktree_command(manager: WorktreeManager) -> Command:
    """创建 Git Worktree 管理的命令对象。

    支持创建、列出、进入、退出和查看 worktree 状态。

    Args:
        manager: Worktree 管理器实例。

    Returns:
        配置好的 Command 对象。
    """

    async def handle_worktree(ctx: CommandContext) -> None:
        args = ctx.args.strip()
        if not args:
            ctx.ui.add_system_message(
                "\u7528\u6cd5:\n"
                "  /worktree create <name> [base-branch]\n"
                "  /worktree list\n"
                "  /worktree enter <name>\n"
                "  /worktree exit [--remove] [--discard]\n"
                "  /worktree status"
            )
            return

        parts = args.split()
        sub = parts[0]
        rest = parts[1:]

        if sub == "create":
            await _handle_create(ctx, manager, rest)
        elif sub == "list":
            _handle_list(ctx, manager)
        elif sub == "enter":
            await _handle_enter(ctx, manager, rest)
        elif sub == "exit":
            await _handle_exit(ctx, manager, rest)
        elif sub == "status":
            _handle_status(ctx, manager)
        else:
            ctx.ui.add_system_message(f"\u672a\u77e5\u5b50\u547d\u4ee4: {sub}")

    return Command(
        name="worktree",
        aliases=["wt"],
        description="\u7ba1\u7406 Git Worktree",
        usage="/worktree <create|list|enter|exit|status>",
        type=CommandType.LOCAL,
        handler=handle_worktree,
    )


async def _handle_create(
    ctx: CommandContext,
    manager: WorktreeManager,
    args: list[str],
) -> None:
    """创建新的 worktree 并自动进入。

    Args:
        ctx: 命令执行上下文。
        manager: Worktree 管理器实例。
        args: 命令参数列表，第一个为名称，第二个为基准分支（可选）。
    """
    if not args:
        ctx.ui.add_system_message("\u7528\u6cd5: /worktree create <name> [base-branch]")
        return

    name = args[0]
    base_branch = args[1] if len(args) > 1 else "HEAD"

    try:
        wt = await manager.create(name, base_branch)
    except Exception as e:
        ctx.ui.add_system_message(f"\u521b\u5efa worktree \u5931\u8d25: {e}")
        return

    try:
        session = await manager.enter(name)
        if ctx.agent:
            ctx.agent.work_dir = wt.path
    except Exception as e:
        ctx.ui.add_system_message(
            f"Worktree \u5df2\u521b\u5efa\u4f46\u8fdb\u5165\u5931\u8d25: {e}\n\u8def\u5f84: {wt.path}"
        )
        return

    ctx.ui.add_system_message(
        f"\u5df2\u521b\u5efa\u5e76\u8fdb\u5165 worktree: {name}\n"
        f"\u8def\u5f84: {wt.path}\n"
        f"\u5206\u652f: {wt.branch}\n"
        f"\u57fa\u4e8e: {base_branch}"
    )


def _handle_list(ctx: CommandContext, manager: WorktreeManager) -> None:
    worktrees = manager.list_worktrees()
    if not worktrees:
        ctx.ui.add_system_message("\u5f53\u524d\u6ca1\u6709\u6d3b\u8dc3\u7684 worktree")
        return

    current = manager.current_session
    lines = ["\u6d3b\u8dc3\u7684 Worktrees:", "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"]
    for wt in worktrees:
        marker = " \u2190 \u5f53\u524d" if current and current.worktree_name == wt.name else ""
        lines.append(
            f"  {wt.name}{marker}\n"
            f"    \u8def\u5f84: {wt.path}\n"
            f"    \u5206\u652f: {wt.branch}\n"
            f"    \u521b\u5efa: {wt.created.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    ctx.ui.add_system_message("\n".join(lines))


async def _handle_enter(
    ctx: CommandContext,
    manager: WorktreeManager,
    args: list[str],
) -> None:
    """进入指定的 worktree。

    Args:
        ctx: 命令执行上下文。
        manager: Worktree 管理器实例。
        args: 命令参数列表，第一个为 worktree 名称。
    """
    if not args:
        ctx.ui.add_system_message("\u7528\u6cd5: /worktree enter <name>")
        return

    name = args[0]
    try:
        session = await manager.enter(name)
        if ctx.agent:
            ctx.agent.work_dir = session.worktree_path
        ctx.ui.add_system_message(f"\u5df2\u8fdb\u5165 worktree: {name}\n\u8def\u5f84: {session.worktree_path}")
    except Exception as e:
        ctx.ui.add_system_message(f"\u8fdb\u5165 worktree \u5931\u8d25: {e}")


async def _handle_exit(
    ctx: CommandContext,
    manager: WorktreeManager,
    args: list[str],
) -> None:
    """退出当前 worktree，可选删除或丢弃变更。

    Args:
        ctx: 命令执行上下文。
        manager: Worktree 管理器实例。
        args: 命令参数列表，可包含 --remove 和 --discard。
    """
    session = manager.get_current_session()
    if session is None:
        ctx.ui.add_system_message("\u5f53\u524d\u4e0d\u5728\u4efb\u4f55 worktree \u4e2d")
        return

    remove = "--remove" in args
    discard = "--discard" in args
    action = "remove" if remove else "keep"

    try:
        await manager.exit(session.worktree_name, action=action, discard_changes=discard)
        if ctx.agent:
            ctx.agent.work_dir = session.original_cwd
        msg = f"\u5df2\u9000\u51fa worktree: {session.worktree_name}"
        if remove:
            msg += "\uff08\u5df2\u5220\u9664\uff09"
        ctx.ui.add_system_message(msg)
    except Exception as e:
        ctx.ui.add_system_message(f"\u9000\u51fa worktree \u5931\u8d25: {e}")


def _handle_status(ctx: CommandContext, manager: WorktreeManager) -> None:
    session = manager.get_current_session()
    if session is None:
        ctx.ui.add_system_message("\u5f53\u524d\u4e0d\u5728\u4efb\u4f55 worktree \u4e2d")
        return

    lines = [
        "Worktree \u4f1a\u8bdd\u72b6\u6001:",
        "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
        f"  \u540d\u79f0: {session.worktree_name}",
        f"  \u8def\u5f84: {session.worktree_path}",
        f"  \u539f\u59cb\u76ee\u5f55: {session.original_cwd}",
        f"  \u539f\u59cb\u5206\u652f: {session.original_branch}",
    ]
    ctx.ui.add_system_message("\n".join(lines))
