from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MailboxMessage:
    """邮箱消息数据类，表示团队成员之间的通信消息。"""
    id: str
    from_agent: str
    to_agent: str
    content: str
    summary: str = ""
    message_type: str = "text"  # text | shutdown_request | shutdown_response
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


    def to_dict(self) -> dict[str, Any]:
        """将消息序列化为字典。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MailboxMessage:
        """从字典反序列化消息。

        Args:
            data: 消息字典。

        Returns:
            MailboxMessage 实例。
        """
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class Mailbox:
    """基于文件系统的邮箱，用于团队成员间的异步消息传递。

    消息以 JSON 文件形式存储在磁盘上，支持写入、读取、消费（读后即删）
    和广播操作。
    """

    def __init__(self, base_dir: str | Path) -> None:
        """初始化邮箱。

        Args:
            base_dir: 邮箱文件存储的根目录。
        """
        self._base_dir = Path(base_dir)

    def _agent_dir(self, agent_id: str) -> Path:
        return self._base_dir / agent_id


    def write(self, agent_id: str, message: MailboxMessage) -> None:
        """向指定 Agent 写入一条消息。

        Args:
            agent_id: 目标 Agent ID。
            message: 要写入的消息对象。
        """
        d = self._agent_dir(agent_id)
        d.mkdir(parents=True, exist_ok=True)
        filename = f"{message.timestamp:.6f}_{message.id}.json"
        (d / filename).write_text(
            json.dumps(message.to_dict(), ensure_ascii=False),
            encoding="utf-8",
        )

    def read(self, agent_id: str) -> list[MailboxMessage]:
        """读取指定 Agent 的所有消息（不删除）。

        Args:
            agent_id: 目标 Agent ID。

        Returns:
            MailboxMessage 列表，按时间戳排序。
        """
        d = self._agent_dir(agent_id)
        if not d.exists():
            return []
        messages: list[MailboxMessage] = []
        for f in sorted(d.iterdir()):
            if f.suffix != ".json":
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                messages.append(MailboxMessage.from_dict(data))
            except (json.JSONDecodeError, KeyError):
                continue
        return messages

    def consume(self, agent_id: str) -> list[MailboxMessage]:
        """消费（读取并删除）指定 Agent 的所有消息。

        Args:
            agent_id: 目标 Agent ID。

        Returns:
            MailboxMessage 列表，读取后文件被删除。
        """
        d = self._agent_dir(agent_id)
        if not d.exists():
            return []
        messages: list[MailboxMessage] = []
        for f in sorted(d.iterdir()):
            if f.suffix != ".json":
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                messages.append(MailboxMessage.from_dict(data))
                f.unlink()
            except (json.JSONDecodeError, KeyError):
                continue
        return messages

    def broadcast(
        self,
        team_members: list[str],
        message: MailboxMessage,
        exclude: str = "",
    ) -> None:
        """向团队所有成员广播消息。

        Args:
            team_members: 团队成员的 Agent ID 列表。
            message: 要广播的消息。
            exclude: 排除的 Agent ID（可选）。
        """
        for agent_id in team_members:
            if agent_id == exclude:
                continue
            self.write(agent_id, message)


    def cleanup(self, agent_id: str) -> None:
        """清理指定 Agent 的邮箱目录。

        Args:
            agent_id: 目标 Agent ID。
        """
        d = self._agent_dir(agent_id)
        if d.exists():
            for f in d.iterdir():
                f.unlink(missing_ok=True)
            d.rmdir()

    def cleanup_all(self) -> None:
        """清理所有 Agent 的邮箱目录。"""
        if not self._base_dir.exists():
            return
        for d in self._base_dir.iterdir():
            if d.is_dir():
                for f in d.iterdir():
                    f.unlink(missing_ok=True)
                d.rmdir()


def create_message(
    from_agent: str,
    to_agent: str,
    content: str,
    summary: str = "",
    message_type: str = "text",
    metadata: dict[str, Any] | None = None,
) -> MailboxMessage:
    """创建一条新的邮箱消息。

    Args:
        from_agent: 发送者 Agent ID 或名称。
        to_agent: 接收者 Agent ID 或名称。
        content: 消息正文。
        summary: 消息摘要。
        message_type: 消息类型，默认为 "text"。
        metadata: 附加元数据字典。

    Returns:
        新创建的 MailboxMessage 实例。
    """
    return MailboxMessage(
        id=uuid.uuid4().hex[:12],
        from_agent=from_agent,
        to_agent=to_agent,
        content=content,
        summary=summary,
        message_type=message_type,
        timestamp=time.time(),
        metadata=metadata or {},
    )
