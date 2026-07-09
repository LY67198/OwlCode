"""Worktree 集成工具：生成 worktree 名称和通知模板。"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlcode.worktree.manager import WorktreeManager

WORKTREE_NOTICE_TEMPLATE = """\
[WORKTREE CONTEXT]
You have inherited the parent agent's conversation context.
You are currently working in an isolated Git Worktree: {wt_path}
The parent agent's working directory is: {parent_cwd}

IMPORTANT:
- File paths mentioned in the parent conversation refer to the PARENT directory.
- You must translate them to your local worktree path before reading or editing.
- Always re-read files before editing — your copy may differ from the parent's version.
[/WORKTREE CONTEXT]
"""


def generate_worktree_name() -> str:
    """生成一个随机的 worktree 名称。

    Returns:
        格式为 "agent-{8位随机hex}" 的名称字符串。
    """
    return f"agent-{secrets.token_hex(4)}"


def build_worktree_notice(parent_cwd: str, wt_path: str) -> str:
    """生成 worktree 上下文通知消息，告知子 agent 其当前路径和注意事项。

    Args:
        parent_cwd: 父 agent 的工作目录。
        wt_path: worktree 的路径。

    Returns:
        格式化的通知文本。
    """
    return WORKTREE_NOTICE_TEMPLATE.format(
        parent_cwd=parent_cwd,
        wt_path=wt_path,
    )
