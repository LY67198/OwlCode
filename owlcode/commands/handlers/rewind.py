"""回退到历史检查点的命令处理器。"""

from __future__ import annotations

import time

from owlcode.commands.registry import Command, CommandType


async def _handle_rewind(ctx) -> None:
    """回退到文件历史快照中的某个检查点。

    不指定参数时列出所有可用检查点；指定参数时根据编号和选项执行回退：
        选项 1: 同时恢复代码和对话
        选项 2: 仅恢复对话
        选项 3: 仅恢复代码

    Args:
        ctx: 命令执行上下文。
    """
    fh = getattr(ctx.agent, "file_history", None)
    if fh is None or not fh.has_snapshots():
        ctx.ui.add_system_message("No checkpoints to rewind to.")
        return

    snapshots = fh.get_snapshots()

    lines = ["\u27f2 Rewind \u2014 select a checkpoint:\n"]
    for i, snap in enumerate(snapshots):
        ago = int(time.time() - snap.timestamp)
        label = snap.user_text[:50] + "\u2026" if len(snap.user_text) > 50 else snap.user_text
        lines.append(f"  [{i + 1}] {label} ({ago}s ago, {len(snap.backups)} file(s))")
    lines.append("\nOptions after selecting:")
    lines.append("  1) Restore code and conversation")
    lines.append("  2) Restore conversation only")
    lines.append("  3) Restore code only")
    lines.append(f"\nUsage: /rewind <checkpoint> [option]  (e.g. /rewind {len(snapshots)} 1)")
    ctx.ui.add_system_message("\n".join(lines))

    args = ctx.args.strip()
    if not args:
        return

    parts = args.split()
    try:
        idx = int(parts[0]) - 1
    except (ValueError, IndexError):
        ctx.ui.add_system_message("Invalid checkpoint number.")
        return

    if idx < 0 or idx >= len(snapshots):
        ctx.ui.add_system_message(f"Checkpoint {idx + 1} not found. Valid: 1-{len(snapshots)}")
        return

    option = 1
    if len(parts) > 1:
        try:
            option = int(parts[1])
        except ValueError:
            pass

    snap = snapshots[idx]

    if option == 1:
        changed = fh.rewind(idx)
        ctx.conversation.replace_history(ctx.conversation.history[: snap.message_index])
        ctx.ui.add_system_message(
            f"\u27f2 Rewound to checkpoint {idx + 1}. Restored {len(changed)} file(s) and conversation."
        )
    elif option == 2:
        ctx.conversation.replace_history(ctx.conversation.history[: snap.message_index])
        ctx.ui.add_system_message(
            f"\u27f2 Rewound conversation to checkpoint {idx + 1}. Files unchanged."
        )
    elif option == 3:
        changed = fh.rewind(idx)
        ctx.ui.add_system_message(
            f"\u27f2 Restored {len(changed)} file(s) to checkpoint {idx + 1}. Conversation unchanged."
        )
    else:
        ctx.ui.add_system_message("Invalid option. Use 1 (both), 2 (conversation), or 3 (code).")


REWIND_COMMAND = Command(
    name="rewind",
    description="Rewind to a previous checkpoint",
    type=CommandType.LOCAL,
    handler=_handle_rewind,
    usage="/rewind [checkpoint_number] [option]",
)
