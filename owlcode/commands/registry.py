"""命令注册表与核心数据结构。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Protocol


class CommandType(str, Enum):
    """命令类型枚举。

    LOCAL: 不涉及 UI 的本地命令。
    LOCAL_UI: 需要操作 UI 的本地命令。
    PROMPT: 将用户输入转发给 AI 模型的命令。
    """

    LOCAL = "local"
    LOCAL_UI = "local_ui"
    PROMPT = "prompt"


class UIController(Protocol):
    """UI 控制器协议，定义命令执行过程中可调用的 UI 操作方法。"""

    def add_system_message(self, text: str) -> None: ...


    def send_user_message(self, text: str) -> None: ...
    def set_plan_mode(self, enabled: bool) -> None: ...
    def get_token_count(self) -> tuple[int, int]: ...
    def refresh_status(self) -> None: ...


@dataclass
class CommandContext:
    """命令执行上下文，包含执行命令所需的所有对象引用。"""

    args: str
    agent: Any
    conversation: Any
    session: Any
    session_manager: Any
    memory_manager: Any
    ui: UIController
    config: Any


CommandHandler = Callable[[CommandContext], Awaitable[None]]


@dataclass
class Command:
    """命令定义数据结构，包含名称、描述、类型、处理器等属性。"""

    name: str
    description: str
    type: CommandType
    handler: CommandHandler
    aliases: list[str] = field(default_factory=list)
    usage: str = ""
    arg_prompt: str = ""
    hidden: bool = False


class CommandRegistry:
    """命令注册表，管理所有已注册的命令及其别名映射。"""


    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}
        self._alias_map: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def register(self, command: Command) -> None:
        """异步注册一个命令，处理命令名和别名的冲突检测。

        Args:
            command: 要注册的命令对象。

        Raises:
            ValueError: 命令名或别名与已有命令冲突。
        """
        async with self._lock:
            if command.name in self._commands or command.name in self._alias_map:
                raise ValueError(
                    f"Command name '{command.name}' conflicts with an existing command or alias"
                )
            for alias in command.aliases:
                if alias in self._alias_map or alias in self._commands:
                    raise ValueError(
                        f"Alias '{alias}' conflicts with an existing command or alias"
                    )
            self._commands[command.name] = command
            for alias in command.aliases:
                self._alias_map[alias] = command.name

    def register_sync(self, command: Command) -> None:
        """同步注册一个命令，处理命令名和别名的冲突检测。

        Args:
            command: 要注册的命令对象。

        Raises:
            ValueError: 命令名或别名与已有命令冲突。
        """
        if command.name in self._commands or command.name in self._alias_map:
            raise ValueError(
                f"Command name '{command.name}' conflicts with an existing command or alias"
            )
        for alias in command.aliases:
            if alias in self._alias_map or alias in self._commands:
                raise ValueError(
                    f"Alias '{alias}' conflicts with an existing command or alias"
                )
        self._commands[command.name] = command
        for alias in command.aliases:
            self._alias_map[alias] = command.name


    def find(self, name: str) -> Command | None:
        """根据命令名或别名查找命令。

        Args:
            name: 命令名或别名。

        Returns:
            找到的 Command 对象，未找到时返回 None。
        """
        if name in self._commands:
            return self._commands[name]
        canon = self._alias_map.get(name)
        if canon:
            return self._commands.get(canon)
        return None


    def list_commands(self) -> list[Command]:
        """返回所有非隐藏命令的列表。

        Returns:
            不含 hidden=True 的命令列表。
        """
        return [cmd for cmd in self._commands.values() if not cmd.hidden]
