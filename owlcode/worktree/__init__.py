"""Git Worktree 管理模块：创建、进入、退出和清理隔离的开发工作空间。"""

from owlcode.worktree.changes import (
    Changes,
    CleanupResult,
    count_worktree_changes,
    has_worktree_changes,
)
from owlcode.worktree.cleanup import cleanup_stale_worktrees, start_stale_cleanup_task
from owlcode.worktree.manager import WorktreeError, WorktreeManager
from owlcode.worktree.models import Worktree, WorktreeSession
from owlcode.worktree.session import load_worktree_session, save_worktree_session
from owlcode.worktree.slug import flatten_slug, validate_slug

__all__ = [
    "Changes",
    "CleanupResult",
    "Worktree",
    "WorktreeError",
    "WorktreeManager",
    "WorktreeSession",
    "cleanup_stale_worktrees",
    "count_worktree_changes",
    "flatten_slug",
    "has_worktree_changes",
    "load_worktree_session",
    "save_worktree_session",
    "start_stale_cleanup_task",
    "validate_slug",
]
