"""teams 模块：团队协作基础设施，包含 mailbox、模型、进度追踪、注册表等。"""

from owlcode.teams.mailbox import Mailbox, MailboxMessage, create_message
from owlcode.teams.models import (
    AgentTeam,
    BackendType,
    TeammateInfo,
    resolve_team_dir,
    unique_team_name,
)
from owlcode.teams.progress import TeammateProgress, ToolActivity
from owlcode.teams.registry import AgentNameRegistry
from owlcode.teams.shared_task import SharedTask, SharedTaskStore


__all__ = [
    "AgentTeam",
    "AgentNameRegistry",
    "BackendType",
    "Mailbox",
    "MailboxMessage",
    "SharedTask",
    "SharedTaskStore",
    "TeammateInfo",
    "TeammateProgress",
    "ToolActivity",
    "create_message",
    "resolve_team_dir",
    "unique_team_name",
]
