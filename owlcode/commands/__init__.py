"""命令系统入口模块。

从子模块中导出命令解析、自动补全、命令注册等核心组件。
"""

from owlcode.commands.parser import complete, parse_command
from owlcode.commands.registry import (
    Command,
    CommandContext,
    CommandHandler,
    CommandRegistry,
    CommandType,
    UIController,
)


__all__ = [
    "Command",
    "CommandContext",
    "CommandHandler",
    "CommandRegistry",
    "CommandType",
    "UIController",
    "complete",
    "parse_command",
]
