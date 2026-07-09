"""Hooks 模块：提供生命周期钩子机制，支持在事件触发时执行自定义动作。"""

from owlcode.hooks.conditions import (
    Condition,
    ConditionGroup,
    ConditionParseError,
    parse_condition,
)
from owlcode.hooks.engine import HookEngine
from owlcode.hooks.events import LifecycleEvent
from owlcode.hooks.loader import HookConfigError, load_hooks
from owlcode.hooks.models import (
    Action,
    ActionResult,
    Hook,
    HookContext,
    ToolRejectedError,
)


__all__ = [
    "Action",
    "ActionResult",
    "Condition",
    "ConditionGroup",
    "ConditionParseError",
    "Hook",
    "HookConfigError",
    "HookContext",
    "HookEngine",
    "LifecycleEvent",
    "ToolRejectedError",
    "load_hooks",
    "parse_condition",
]
