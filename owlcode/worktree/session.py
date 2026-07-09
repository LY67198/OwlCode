"""Worktree 会话持久化：将会话状态序列化到 JSON 文件。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from owlcode.worktree.models import WorktreeSession

log = logging.getLogger(__name__)

SESSION_FILENAME = "worktree_session.json"


def _session_path(owlcode_dir: Path) -> Path:
    """获取会话文件的完整路径。

    Args:
        owlcode_dir: .owlcode 目录路径。

    Returns:
        会话 JSON 文件的 Path 对象。
    """
    return owlcode_dir / SESSION_FILENAME


def save_worktree_session(
    owlcode_dir: Path,
    session: WorktreeSession | None,
) -> None:
    """将 Worktree 会话保存到持久化文件。

    传入 None 时写入空的 JSON 对象以清除会话。

    Args:
        owlcode_dir: .owlcode 目录路径。
        session: 要保存的 WorktreeSession，或 None 以清除。
    """
    path = _session_path(owlcode_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    if session is None:
        path.write_text("{}", encoding="utf-8")
        return
    data = {
        "original_cwd": session.original_cwd,
        "worktree_path": session.worktree_path,
        "worktree_name": session.worktree_name,
        "original_branch": session.original_branch,
        "original_head_commit": session.original_head_commit,
        "session_id": session.session_id,
        "hook_based": session.hook_based,
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_worktree_session(owlcode_dir: Path) -> WorktreeSession | None:
    """从持久化文件加载 Worktree 会话。

    Args:
        owlcode_dir: .owlcode 目录路径。

    Returns:
        加载的 WorktreeSession，文件不存在或解析失败时返回 None。
    """
    path = _session_path(owlcode_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not data or "worktree_path" not in data:
            return None
        return WorktreeSession(
            original_cwd=data["original_cwd"],
            worktree_path=data["worktree_path"],
            worktree_name=data["worktree_name"],
            original_branch=data["original_branch"],
            original_head_commit=data["original_head_commit"],
            session_id=data.get("session_id", ""),
            hook_based=data.get("hook_based", False),
        )
    except (json.JSONDecodeError, KeyError) as e:
        log.warning("Failed to load worktree session: %s", e)
        return None
