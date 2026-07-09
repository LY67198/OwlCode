"""Hook 相关数据模型定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from owlcode.hooks.conditions import ConditionGroup


@dataclass
class Action:
    """Hook 动作定义，描述当条件满足时执行什么操作。"""

    type: str
    command: str = ""
    message: str = ""
    url: str = ""
    method: str = "POST"
    body: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    prompt: str = ""
    timeout: int = 30


@dataclass
class ActionResult:
    """Hook 动作执行结果。"""

    output: str = ""
    success: bool = True


@dataclass
class Hook:
    """单个 Hook 定义，将事件、条件和动作绑定在一起。"""

    id: str
    event: str
    action: Action
    condition: ConditionGroup | None = None
    reject: bool = False
    once: bool = False
    async_exec: bool = False
    executed: bool = False

    def should_run(self) -> bool:
        """判断 Hook 是否应当运行。

        对于 once=True 且已执行过的 Hook，返回 False。

        Returns:
            应当运行返回 True，否则返回 False。
        """
        if self.once and self.executed:
            return False
        return True

    def mark_executed(self) -> None:
        """标记 Hook 为已执行状态。"""
        self.executed = True


@dataclass
class HookContext:
    """Hook 执行上下文，提供事件相关的运行时信息。

    支持字段取值（get_field）和模板变量展开（expand）两种访问方式。
    """

    event_name: str = ""
    tool_name: str = ""
    tool_args: dict[str, Any] = field(default_factory=dict)
    file_path: str = ""
    message: str = ""
    error: str = ""

    def get_field(self, name: str) -> str:
        """按名称获取上下文字段的值。

        支持字段：tool、event、args.<key>。

        Args:
            name: 字段名。

        Returns:
            字段对应的字符串值，未知字段返回空字符串。
        """
        if name == "tool":
            return self.tool_name
        if name == "event":
            return self.event_name
        if name.startswith("args."):
            key = name[5:]
            value = self.tool_args.get(key, "")
            return str(value) if value else ""
        return ""

    def expand(self, template: str) -> str:
        """展开模板字符串中的变量占位符。

        支持的变量：$EVENT、$TOOL_NAME、$FILE_PATH、$MESSAGE、$ERROR、
        $TOOL_ARGS.<key>。

        Args:
            template: 包含变量的模板字符串。

        Returns:
            变量替换后的字符串。
        """
        result = template
        result = result.replace("$EVENT", self.event_name)
        result = result.replace("$TOOL_NAME", self.tool_name)
        result = result.replace("$FILE_PATH", self.file_path)
        result = result.replace("$MESSAGE", self.message)
        result = result.replace("$ERROR", self.error)
        for key, value in self.tool_args.items():
            result = result.replace(f"$TOOL_ARGS.{key}", str(value))
        return result


class ToolRejectedError(Exception):
    """Hook 拒绝工具调用时抛出的异常。"""

    def __init__(self, tool: str, reason: str, hook_id: str) -> None:
        """初始化工具拒绝异常。

        Args:
            tool: 被拒绝的工具名称。
            reason: 拒绝原因。
            hook_id: 触发拒绝的 Hook ID。
        """
        self.tool = tool
        self.reason = reason
        self.hook_id = hook_id
        super().__init__(f"Tool '{tool}' rejected by hook '{hook_id}': {reason}")
