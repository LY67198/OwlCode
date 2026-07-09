"""权限模式定义：不同模式下对各种工具类别的默认处理策略。"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from owlcode.tools.base import ToolCategory


DecisionEffect = Literal["allow", "deny", "ask"]


class PermissionMode(str, Enum):
    """权限模式枚举，定义不同安全等级下工具调用的默认行为。"""

    DEFAULT = "default"
    ACCEPT_EDITS = "acceptEdits"
    PLAN = "plan"
    BYPASS = "bypassPermissions"
    CUSTOM = "custom"
    DONT_ASK = "dontAsk"


_MODE_MATRIX: dict[PermissionMode, dict[ToolCategory, DecisionEffect]] = {
    PermissionMode.DEFAULT: {"read": "allow", "write": "ask", "command": "ask"},
    PermissionMode.ACCEPT_EDITS: {"read": "allow", "write": "allow", "command": "ask"},
    PermissionMode.PLAN: {"read": "allow", "write": "ask", "command": "ask"},
    PermissionMode.BYPASS: {"read": "allow", "write": "allow", "command": "allow"},
    PermissionMode.CUSTOM: {"read": "ask", "write": "ask", "command": "ask"},
    PermissionMode.DONT_ASK: {"read": "allow", "write": "allow", "command": "allow"},
}


def mode_decide(mode: PermissionMode, category: ToolCategory) -> DecisionEffect:
    """根据权限模式和工具类别返回兜底决策。

    Args:
        mode: 当前权限模式。
        category: 工具类别（read/write/command）。

    Returns:
        决策效果：allow、deny 或 ask。
    """
    return _MODE_MATRIX[mode][category]
