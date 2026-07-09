"""Worktree 名称校验与扁平化。"""

from __future__ import annotations

import re

MAX_SLUG_LENGTH = 64
_SEGMENT_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


def validate_slug(name: str) -> str | None:
    """校验 worktree 名称的合法性。

    名称由 / 分隔的段组成，每段只能包含字母、数字、点、横线和下划线。
    不允许包含 ".." 或 "." 作为独立段。

    Args:
        name: 待校验的 worktree 名称。

    Returns:
        合法时返回 None，否则返回错误描述字符串。
    """
    if not name:
        return "name cannot be empty"
    if len(name) > MAX_SLUG_LENGTH:
        return f"name too long (max {MAX_SLUG_LENGTH} characters)"

    segments = name.split("/")
    for seg in segments:
        if not seg:
            return "name contains empty segment"
        if seg in (".", ".."):
            return "name must not contain '.' or '..' as a segment"
        if not _SEGMENT_RE.match(seg):
            return f"invalid segment: {seg!r} (allowed: letters, digits, '.', '-', '_')"

    return None


def flatten_slug(name: str) -> str:
    """将带 / 的名称扁平化为文件系统安全的字符串。

    用 + 替换 /。

    Args:
        name: 原始名称。

    Returns:
        扁平化后的名称。
    """
    return name.replace("/", "+")
