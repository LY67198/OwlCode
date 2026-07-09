from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from owlcode.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from owlcode.teams.manager import TeamManager

log = logging.getLogger(__name__)


class SendMessageParams(BaseModel):
    to: str
    message: str
    summary: str = ""
    message_type: str = "text"
    metadata: dict[str, Any] | None = None


VALID_MESSAGE_TYPES = {"text", "shutdown_request", "shutdown_response"}


class SendMessageTool(Tool):
    """向队友发送消息的工具。

    支持按名称或 agent ID 发送，支持广播（to='*'）和结构化消息类型。
    """

    name = "SendMessage"
    description = (
        "Send a message to a teammate by name or agent ID. "
        "Use to='*' to broadcast to all teammates. "
        "For text messages, include a short summary (5-10 words). "
        "Supports structured types: shutdown_request, shutdown_response."
    )
    params_model = SendMessageParams
    category = "command"
    is_concurrency_safe = True


    def __init__(
        self,
        team_manager: TeamManager,
        team_name: str,
        from_agent_id: str,
        from_agent_name: str = "",
    ) -> None:
        self._team_manager = team_manager
        self._team_name = team_name
        self._from_agent_id = from_agent_id
        self._from_agent_name = from_agent_name


    async def execute(self, params: BaseModel) -> ToolResult:
        """发送消息给指定队友或广播给全体。

        Args:
            params: 包含 to（接收者）、message（消息内容）、summary（摘要）、
                   message_type（消息类型）的 SendMessageParams。

        Returns:
            ToolResult，发送成功返回确认信息，无效类型或解析失败返回错误。
        """
        p: SendMessageParams = params  # type: ignore[assignment]

        if p.message_type not in VALID_MESSAGE_TYPES:
            return ToolResult(
                output=f"Invalid message_type '{p.message_type}'. Must be one of: {', '.join(sorted(VALID_MESSAGE_TYPES))}",
                is_error=True,
            )

        if p.message_type == "text" and not p.summary:
            return ToolResult(
                output="Text messages require a 'summary' field (5-10 words).",
                is_error=True,
            )

        from owlcode.teams.mailbox import create_message
        from owlcode.teams.registry import AgentNameRegistry

        team = self._team_manager.get_team(self._team_name)
        if team is None:
            return ToolResult(output=f"Team '{self._team_name}' not found", is_error=True)

        mailbox = self._team_manager.get_mailbox(self._team_name)
        if mailbox is None:
            return ToolResult(output=f"Mailbox not found for team '{self._team_name}'", is_error=True)

        msg = create_message(
            from_agent=self._from_agent_name or self._from_agent_id,
            to_agent=p.to,
            content=p.message,
            summary=p.summary,
            message_type=p.message_type,
            metadata=p.metadata,
        )

        registry = AgentNameRegistry.instance()

        if p.to == "*":
            member_ids = [
                m.agent_id for m in team.members
                if m.agent_id != self._from_agent_id
            ]
            if team.lead_agent_id != self._from_agent_id:
                member_ids.append(team.lead_agent_id)
            mailbox.broadcast(member_ids, msg, exclude=self._from_agent_id)
            self._wake_pane_members(team, member_ids)
            return ToolResult(output=f"Message broadcast to {len(member_ids)} teammates.")

        target_id = registry.resolve(p.to)
        if target_id is None:
            return ToolResult(
                output=f"Cannot resolve recipient '{p.to}'. Check the name or agent ID.",
                is_error=True,
            )

        mailbox.write(target_id, msg)
        self._wake_pane(target_id)

        return ToolResult(output=f"Message sent to '{p.to}'.")


    def _wake_pane(self, agent_id: str) -> None:
        """唤醒指定 agent 的 tmux pane（若存在）。"""
        pane_id = self._team_manager.get_pane_id(agent_id)
        if pane_id is None:
            return
        try:
            from owlcode.teams.spawn_tmux import send_keys_to_pane
            send_keys_to_pane(pane_id, "")
        except Exception:
            pass

    def _wake_pane_members(self, team: Any, agent_ids: list[str]) -> None:
        """批量唤醒多个 agent 的 tmux pane。"""
        for aid in agent_ids:
            self._wake_pane(aid)
