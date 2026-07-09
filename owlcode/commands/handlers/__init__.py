"""命令处理器模块入口，汇总所有内置命令并注册。"""

from __future__ import annotations

from owlcode.commands.handlers.clear import CLEAR_COMMAND
from owlcode.commands.handlers.compact import COMPACT_COMMAND
from owlcode.commands.handlers.help import HELP_COMMAND
from owlcode.commands.handlers.mcp import MCP_COMMAND
from owlcode.commands.handlers.memory import MEMORY_COMMAND
from owlcode.commands.handlers.permission import PERMISSION_COMMAND
from owlcode.commands.handlers.plan import PLAN_COMMAND
from owlcode.commands.handlers.session import SESSION_COMMAND
from owlcode.commands.handlers.skill import SKILL_COMMAND
from owlcode.commands.handlers.rewind import REWIND_COMMAND
from owlcode.commands.handlers.status import STATUS_COMMAND
from owlcode.commands.registry import CommandRegistry


ALL_COMMANDS = [
    HELP_COMMAND,
    COMPACT_COMMAND,
    CLEAR_COMMAND,
    PLAN_COMMAND,
    SESSION_COMMAND,
    MCP_COMMAND,
    MEMORY_COMMAND,
    PERMISSION_COMMAND,
    REWIND_COMMAND,
    STATUS_COMMAND,
    SKILL_COMMAND,
]


def register_all_commands(registry: CommandRegistry) -> None:
    """将所有内置命令注册到指定的命令注册表中。

    Args:
        registry: 目标命令注册表实例。
    """
    for cmd in ALL_COMMANDS:
        registry.register_sync(cmd)
