"""Worktree 变更检测：检查工作空间中的未提交修改和新提交。"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass

log = logging.getLogger(__name__)

GIT_ENV = {"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": ""}


def _run_git(args: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    """在指定目录下运行 git 命令。

    Args:
        args: git 子命令参数列表。
        cwd: 工作目录。

    Returns:
        subprocess 完成结果。
    """
    import os
    env = {**os.environ, **GIT_ENV}
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


@dataclass
class Changes:
    """Worktree 变更统计。"""
    uncommitted: int = 0
    new_commits: int = 0


def count_worktree_changes(wt_path: str, head_commit: str) -> Changes:
    """统计 worktree 中相对于原始 HEAD 的变更数量。

    包括未提交的文件变更数和新增的提交数。

    Args:
        wt_path: worktree 目录路径。
        head_commit: 原始 HEAD 提交 SHA。

    Returns:
        Changes 对象，包含未提交数和新增提交数。
    """
    changes = Changes()
    try:
        status = _run_git(["status", "--porcelain"], cwd=wt_path)
        if status.returncode == 0:
            changes.uncommitted = len(
                [line for line in status.stdout.splitlines() if line.strip()]
            )
    except (subprocess.SubprocessError, OSError):
        changes.uncommitted = 1

    try:
        rev_list = _run_git(
            ["rev-list", "--count", f"{head_commit}..HEAD"], cwd=wt_path
        )
        if rev_list.returncode == 0:
            changes.new_commits = int(rev_list.stdout.strip())
    except (subprocess.SubprocessError, OSError, ValueError):
        changes.new_commits = 1

    return changes


def has_worktree_changes(wt_path: str, head_commit: str) -> bool:
    """检查 worktree 中是否存在任何变更。

    Args:
        wt_path: worktree 目录路径。
        head_commit: 原始 HEAD 提交 SHA。

    Returns:
        存在未提交修改或新增提交时返回 True。
    """
    c = count_worktree_changes(wt_path, head_commit)
    return c.uncommitted > 0 or c.new_commits > 0


@dataclass
class CleanupResult:
    """Worktree 清理结果。"""
    kept: bool
    path: str = ""
    branch: str = ""


def has_unpushed_commits(wt_path: str) -> bool:
    """检查 worktree 中是否存在未推送到远程的提交。

    Args:
        wt_path: worktree 目录路径。

    Returns:
        存在未推送提交时返回 True。
    """
    try:
        result = _run_git(
            ["rev-list", "--max-count=1", "HEAD", "--not", "--remotes"],
            cwd=wt_path,
        )
        return bool(result.stdout.strip()) if result.returncode == 0 else True
    except (subprocess.SubprocessError, OSError):
        return True
