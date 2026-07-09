from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from owlcode.conversation import ConversationManager, Message, ToolResultBlock, ToolUseBlock


def _serialize_conversation(conv: ConversationManager) -> list[dict[str, Any]]:
    """将会话管理器序列化为 JSON 友好的字典列表。

    将历史消息中的 tool_uses 和 tool_results 分别转换为字典格式。

    Args:
        conv: 会话管理器实例。

    Returns:
        消息字典列表。
    """
    messages: list[dict[str, Any]] = []
    for msg in conv.history:
        entry: dict[str, Any] = {"role": msg.role, "content": msg.content}
        if msg.tool_uses:
            entry["tool_uses"] = [
                {
                    "tool_use_id": tu.tool_use_id,
                    "tool_name": tu.tool_name,
                    "arguments": tu.arguments,
                }
                for tu in msg.tool_uses
            ]
        if msg.tool_results:
            entry["tool_results"] = [
                {
                    "tool_use_id": tr.tool_use_id,
                    "content": tr.content,
                    "is_error": tr.is_error,
                }
                for tr in msg.tool_results
            ]
        messages.append(entry)
    return messages


def _deserialize_conversation(data: list[dict[str, Any]]) -> ConversationManager:
    """从字典列表反序列化回 ConversationManager。

    重建 Message、ToolUseBlock、ToolResultBlock 对象，
    并标记 env_injected 和 ltm_injected 为 True 以避免重复注入。

    Args:
        data: 序列化的消息字典列表。

    Returns:
        恢复的 ConversationManager 实例。
    """
    conv = ConversationManager()
    for entry in data:
        tool_uses = [
            ToolUseBlock(
                tool_use_id=tu["tool_use_id"],
                tool_name=tu["tool_name"],
                arguments=tu["arguments"],
            )
            for tu in entry.get("tool_uses", [])
        ]
        tool_results = [
            ToolResultBlock(
                tool_use_id=tr["tool_use_id"],
                content=tr["content"],
                is_error=tr.get("is_error", False),
            )
            for tr in entry.get("tool_results", [])
        ]
        msg = Message(
            role=entry["role"],
            content=entry.get("content", ""),
            tool_uses=tool_uses,
            tool_results=tool_results,
        )
        conv.history.append(msg)
    conv.env_injected = True
    conv.ltm_injected = True
    return conv


def save_transcript(
    team_name: str,
    agent_id: str,
    conversation: ConversationManager,
) -> Path:
    """保存 Agent 会话转录到磁盘。

    将完整会话历史序列化为 JSON 文件存储在团队转录目录中。

    Args:
        team_name: 团队名称。
        agent_id: Agent ID。
        conversation: 会话管理器。

    Returns:
        保存文件的 Path 对象。
    """
    from owlcode.teams.models import resolve_team_dir

    transcript_dir = resolve_team_dir(team_name) / "transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    path = transcript_dir / f"{agent_id}.json"
    data = _serialize_conversation(conversation)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_transcript(
    team_name: str,
    agent_id: str,
) -> ConversationManager | None:
    """从磁盘加载 Agent 会话转录。

    Args:
        team_name: 团队名称。
        agent_id: Agent ID。

    Returns:
        恢复的 ConversationManager，文件不存在则返回 None。
    """
    from owlcode.teams.models import resolve_team_dir

    path = resolve_team_dir(team_name) / "transcripts" / f"{agent_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return _deserialize_conversation(data)
