from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from owlcode.teams.progress import TeammateProgress


class BackendType(str, Enum):
    """团队后端类型枚举。"""
    TMUX = "tmux"
    ITERM2 = "iterm2"
    IN_PROCESS = "in-process"


@dataclass
class TeammateInfo:
    """团队成员信息数据类。"""
    name: str
    agent_id: str
    agent_type: str
    model: str
    worktree_path: str
    backend_type: str  # BackendType value
    is_active: bool | None = None
    progress: Optional[TeammateProgress] = None

    def to_dict(self) -> dict:
        """将成员信息序列化为字典（不含运行时 progress）。"""
        # Exclude progress (runtime-only, contains threading.Lock)
        return {
            "name": self.name,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "model": self.model,
            "worktree_path": self.worktree_path,
            "backend_type": self.backend_type,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TeammateInfo:
        """从字典反序列化成员信息。

        Args:
            data: 成员信息字典。

        Returns:
            TeammateInfo 实例。
        """
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def _sanitize_name(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", name.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "team"


@dataclass
class AgentTeam:
    """Agent 团队数据类，管理成员列表及配置的持久化。"""
    name: str
    lead_agent_id: str
    members: list[TeammateInfo] = field(default_factory=list)
    config_path: str = ""
    description: str = ""

    def get_member(self, name: str) -> TeammateInfo | None:
        """按名称或 Agent ID 查找成员。

        Args:
            name: 成员名称或 Agent ID。

        Returns:
            TeammateInfo 或 None。
        """
        for m in self.members:
            if m.name == name or m.agent_id == name:
                return m
        return None


    def add_member(self, member: TeammateInfo) -> None:
        """添加团队成员。

        Args:
            member: 成员信息。
        """
        self.members.append(member)

    def remove_member(self, name: str) -> bool:
        """移除团队成员。

        Args:
            name: 成员名称或 Agent ID。

        Returns:
            成功移除返回 True，未找到返回 False。
        """
        for i, m in enumerate(self.members):
            if m.name == name or m.agent_id == name:
                self.members.pop(i)
                return True
        return False


    def set_member_active(self, name: str, is_active: bool | None) -> bool:
        """设置成员的活跃状态。

        Args:
            name: 成员名称或 Agent ID。
            is_active: 活跃状态，True/False/None。

        Returns:
            设置成功返回 True，未找到返回 False。
        """
        member = self.get_member(name)
        if member is None:
            return False
        member.is_active = is_active
        return True

    def all_idle(self) -> bool:
        """检查是否所有成员均处于空闲状态。

        Returns:
            全部空闲返回 True。
        """
        return all(m.is_active is False for m in self.members)


    def active_members(self) -> list[TeammateInfo]:
        """获取所有活跃成员。

        Returns:
            TeammateInfo 列表。
        """
        return [m for m in self.members if m.is_active is not False]

    def to_dict(self) -> dict:
        """将团队信息序列化为字典。"""
        return {
            "name": self.name,
            "lead_agent_id": self.lead_agent_id,
            "members": [m.to_dict() for m in self.members],
            "config_path": self.config_path,
            "description": self.description,
        }


    @classmethod
    def from_dict(cls, data: dict) -> AgentTeam:
        """从字典反序列化团队信息。

        Args:
            data: 团队信息字典。

        Returns:
            AgentTeam 实例。
        """
        members = [TeammateInfo.from_dict(m) for m in data.get("members", [])]
        return cls(
            name=data["name"],
            lead_agent_id=data["lead_agent_id"],
            members=members,
            config_path=data.get("config_path", ""),
            description=data.get("description", ""),
        )

    def save(self) -> None:
        """将团队配置保存到磁盘。"""
        path = Path(self.config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, config_path: str) -> AgentTeam:
        """从磁盘加载团队配置。

        Args:
            config_path: 配置文件路径。

        Returns:
            加载的 AgentTeam 实例。
        """
        data = json.loads(Path(config_path).read_text(encoding="utf-8"))
        team = cls.from_dict(data)
        team.config_path = config_path
        return team


def resolve_team_dir(team_name: str) -> Path:
    """解析团队存储目录路径。

    Args:
        team_name: 团队名称。

    Returns:
        团队目录的 Path 对象。
    """
    slug = _sanitize_name(team_name)
    return Path.home() / ".owlcode" / "teams" / slug


def unique_team_name(team_name: str) -> str:
    """生成唯一的团队名称（若重复则追加数字后缀）。

    Args:
        team_name: 原始团队名称。

    Returns:
        唯一且已清理的团队名称。
    """
    slug = _sanitize_name(team_name)
    base_dir = Path.home() / ".owlcode" / "teams"
    if not (base_dir / slug).exists():
        return slug
    counter = 2
    while (base_dir / f"{slug}-{counter}").exists():
        counter += 1
    return f"{slug}-{counter}"
