"""Worktree 初始化设置：创建 worktree 后执行的环境配置。"""

from __future__ import annotations

import fnmatch
import logging
import os
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

LOCAL_CONFIG_FILES = [
    "settings.local.json",
    ".env",
]


def perform_post_creation_setup(
    repo_root: str,
    wt_path: str,
    symlink_directories: list[str] | None = None,
) -> None:
    """在 worktree 创建后执行各类初始化配置。

    包括：复制本地配置文件、设置 Git hooks 路径、创建目录符号链接、
    复制 .worktreeinclude 中指定的被忽略文件。

    Args:
        repo_root: 主仓库根目录。
        wt_path: 新 worktree 目录路径。
        symlink_directories: 需要符号链接的目录名列表。
    """
    root = Path(repo_root)
    wt = Path(wt_path)

    _copy_local_configs(root, wt)
    _setup_git_hooks(root, wt)
    _create_symlinks(root, wt, symlink_directories or [])
    _copy_ignored_files(root, wt)


def _copy_local_configs(root: Path, wt: Path) -> None:
    """将本地配置文件从主仓库复制到 worktree。

    Args:
        root: 主仓库根目录。
        wt: worktree 根目录。
    """
    for name in LOCAL_CONFIG_FILES:
        src = root / name
        if src.exists():
            dst = wt / name
            try:
                shutil.copy2(str(src), str(dst))
                log.debug("Copied %s to worktree", name)
            except OSError as e:
                log.warning("Failed to copy %s: %s", name, e)


def _setup_git_hooks(root: Path, wt: Path) -> None:
    """在 worktree 中设置 Git hooks 路径。

    优先使用 .husky 目录，其次使用 .git/hooks。

    Args:
        root: 主仓库根目录。
        wt: worktree 根目录。
    """
    hooks_path: str | None = None

    husky_dir = root / ".husky"
    if husky_dir.is_dir():
        hooks_path = str(husky_dir)
    else:
        git_hooks = root / ".git" / "hooks"
        if git_hooks.is_dir():
            hooks_path = str(git_hooks)

    if hooks_path is None:
        return

    try:
        subprocess.run(
            ["git", "config", "core.hooksPath", hooks_path],
            cwd=str(wt),
            capture_output=True,
            timeout=10,
        )
        log.debug("Set core.hooksPath to %s in worktree", hooks_path)
    except (subprocess.SubprocessError, OSError) as e:
        log.warning("Failed to set hooks path: %s", e)


def _create_symlinks(root: Path, wt: Path, directories: list[str]) -> None:
    """在 worktree 中创建指向主仓库目录的符号链接。

    Args:
        root: 主仓库根目录。
        wt: worktree 根目录。
        directories: 需要链接的目录名列表。
    """
    for dirname in directories:
        src = root / dirname
        dst = wt / dirname
        if not src.exists():
            continue
        if dst.exists() or dst.is_symlink():
            continue
        try:
            os.symlink(str(src), str(dst))
            log.debug("Symlinked %s to worktree", dirname)
        except OSError as e:
            log.warning("Failed to symlink %s: %s", dirname, e)


def _copy_ignored_files(root: Path, wt: Path) -> None:
    """将 .worktreeinclude 中列出的被 git 忽略的文件复制到 worktree。

    Args:
        root: 主仓库根目录。
        wt: worktree 根目录。
    """
    include_file = root / ".worktreeinclude"
    if not include_file.exists():
        return

    try:
        patterns = [
            line.strip()
            for line in include_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    except OSError:
        return

    if not patterns:
        return

    try:
        result = subprocess.run(
            [
                "git", "ls-files",
                "--others", "--ignored", "--exclude-standard", "--directory",
            ],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return
        ignored_files = [f.rstrip("/") for f in result.stdout.splitlines() if f.strip()]
    except (subprocess.SubprocessError, OSError):
        return

    for rel_path in ignored_files:
        if not any(fnmatch.fnmatch(rel_path, pat) for pat in patterns):
            continue
        src = root / rel_path
        dst = wt / rel_path
        if not src.is_file():
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
            log.debug("Copied ignored file %s to worktree", rel_path)
        except OSError as e:
            log.warning("Failed to copy ignored file %s: %s", rel_path, e)
