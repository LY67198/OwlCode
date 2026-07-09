"""Worktree 数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Worktree:
    """Git Worktree 的元数据。"""
    name: str
    path: str
    branch: str
    based_on: str
    head_commit: str
    created: datetime = field(default_factory=datetime.now)


@dataclass
class WorktreeSession:
    """Worktree 会话状态，记录进入前后的环境信息。"""
    original_cwd: str
    worktree_path: str
    worktree_name: str
    original_branch: str
    original_head_commit: str
    session_id: str = ""
    hook_based: bool = False
