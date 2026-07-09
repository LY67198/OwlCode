"""条件解析与求值模块，用于判断 Hook 的触发条件是否满足。"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlcode.hooks.models import HookContext


@dataclass
class Condition:
    """单个条件，由字段、运算符和值组成，用于匹配 Hook 上下文字段。"""

    field: str
    operator: str
    value: str

    def evaluate(self, ctx: HookContext) -> bool:
        """在给定的 Hook 上下文中求值当前条件。

        Args:
            ctx: Hook 执行上下文，提供字段取值。

        Returns:
            条件匹配成功返回 True，否则返回 False。
        """
        field_value = ctx.get_field(self.field)
        if self.operator == "==":
            return field_value == self.value
        if self.operator == "!=":
            return field_value != self.value
        if self.operator == "=~":
            pattern = self.value
            if pattern.startswith("/") and pattern.endswith("/"):
                pattern = pattern[1:-1]
            try:
                return bool(re.search(pattern, field_value))
            except re.error:
                return False
        if self.operator == "~=":
            return fnmatch.fnmatch(field_value, self.value)
        return False


@dataclass
class ConditionGroup:
    """条件组，包含多个 Condition，支持 AND/OR 逻辑组合求值。"""

    conditions: list[Condition] = field(default_factory=list)
    logic: str = "and"

    def evaluate(self, ctx: HookContext) -> bool:
        """对条件组内所有条件按逻辑运算符求值。

        Args:
            ctx: Hook 执行上下文，供每个条件取字段值。

        Returns:
            条件组整体匹配成功返回 True。空条件组默认返回 True。
        """
        if not self.conditions:
            return True
        if self.logic == "and":
            return all(c.evaluate(ctx) for c in self.conditions)
        return any(c.evaluate(ctx) for c in self.conditions)


class ConditionParseError(Exception):
    """条件表达式解析失败时抛出的异常。"""

    pass


_OPERATORS = ("==", "!=", "=~", "~=")


def _parse_single(expr: str) -> Condition:
    expr = expr.strip()
    for op in _OPERATORS:
        idx = expr.find(op)
        if idx == -1:
            continue
        field_part = expr[:idx].strip()
        value_part = expr[idx + len(op):].strip()
        if value_part.startswith('"') and value_part.endswith('"'):
            value_part = value_part[1:-1]
        return Condition(field=field_part, operator=op, value=value_part)
    raise ConditionParseError(f"No valid operator found in condition: '{expr}'")


def parse_condition(expr: str) -> ConditionGroup | None:
    """解析条件表达式字符串，生成 ConditionGroup。

    支持用 &&、|| 连接多个条件，分别对应 AND/OR 逻辑。
    空字符串返回 None。

    Args:
        expr: 条件表达式字符串，如 "tool == Grep || tool == Glob"。

    Returns:
        解析后的 ConditionGroup，表达式为空时返回 None。

    Raises:
        ConditionParseError: 解析失败时抛出。
    """
    if not expr or not expr.strip():
        return None

    expr = expr.strip()
    has_and = "&&" in expr
    has_or = "||" in expr

    if has_and and has_or:
        raise ConditionParseError(
            "Cannot mix '&&' and '||' in a single condition expression. "
            "Split into separate hooks instead."
        )

    if has_and:
        parts = expr.split("&&")
        logic = "and"
    elif has_or:
        parts = expr.split("||")
        logic = "or"
    else:
        parts = [expr]
        logic = "and"

    conditions = [_parse_single(p) for p in parts]
    return ConditionGroup(conditions=conditions, logic=logic)
