"""会话持久化模块：管理会话记录的创建、追加、恢复和清理。"""

from __future__ import annotations

import json
import random
import string
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import IO, Any

from owlcode.conversation import ConversationManager, Message, ToolResultBlock, ToolUseBlock

SESSIONS_DIR = ".owlcode/sessions"
DEFAULT_MAX_AGE_DAYS = 30
TITLE_MAX_LENGTH = 50

SESSION_SUMMARY_PROMPT = (
    "你是一个对话摘要助手。请根据下面的对话内容，用一句话总结这个会话的主要内容。"
    "只输出摘要文本，不要加任何前缀或标点符号外的修饰。不要调用任何工具。"
)


# ---------------------------------------------------------------------------
# RecordType & SessionRecord
# ---------------------------------------------------------------------------


class RecordType(str, Enum):
    """会话记录类型枚举。"""

    SYSTEM_PROMPT = "system_prompt"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL_RESULT = "tool_result"
    COMPRESSION = "compression"
    # Layer-2 compact 标记。auto_compact 压缩对话记录时写入。
    # 内容为结构化载荷（参见 make_compact_boundary / parse_compact_boundary），
    # 包含摘要文本和原样保留的 keep 尾部（以序列化 record 形式内联），
    # 使 resume 可以仅凭此标记重建压缩后的状态，无需重放标记之前的原始前缀。
    COMPACT_BOUNDARY = "compact_boundary"


@dataclass
class SessionRecord:
    """单条会话记录，包含类型、内容、时间戳和可选的工具使用 ID。"""

    type: RecordType
    content: Any
    timestamp: datetime
    tool_use_id: str | None = None
    is_error: bool = False

    def to_jsonl(self) -> str:
        """将记录序列化为 JSONL 行。

        Returns:
            单行 JSON 字符串（不含换行符，由调用方追加 \\n）。
        """
        data: dict[str, Any] = {
            "type": self.type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.tool_use_id is not None:
            data["tool_use_id"] = self.tool_use_id
        if self.type == RecordType.TOOL_RESULT:
            data["is_error"] = self.is_error
        return json.dumps(data, ensure_ascii=False)

    @classmethod
    def from_jsonl(cls, line: str) -> SessionRecord | None:
        """从 JSONL 行反序列化为 SessionRecord。

        Args:
            line: JSONL 单行字符串。

        Returns:
            SessionRecord 实例；解析失败返回 None。
        """
        try:
            data = json.loads(line)
            return cls(
                type=RecordType(data["type"]),
                content=data["content"],
                timestamp=datetime.fromisoformat(data["timestamp"]),
                tool_use_id=data.get("tool_use_id"),
                is_error=data.get("is_error", False),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    @classmethod
    def from_message(cls, message: Message) -> list[SessionRecord]:
        """将一条 Message 转换为 SessionRecord 列表。

        助手消息中的 tool_uses 会被打包为 content-blocks 结构，
        tool_results 每项独立为一条 TOOL_RESULT 记录。

        Args:
            message: 要转换的 Message。

        Returns:
            对应的 SessionRecord 列表。
        """
        now = datetime.now(timezone.utc)
        records: list[SessionRecord] = []

        if message.tool_results:
            for tr in message.tool_results:
                records.append(
                    cls(
                        type=RecordType.TOOL_RESULT,
                        content=tr.content,
                        timestamp=now,
                        tool_use_id=tr.tool_use_id,
                        is_error=tr.is_error,
                    )
                )
        elif message.role == "assistant":
            if message.tool_uses:
                content_blocks: list[dict[str, Any]] = []
                if message.content:
                    content_blocks.append({"type": "text", "text": message.content})
                for tu in message.tool_uses:
                    content_blocks.append(
                        {
                            "type": "tool_use",
                            "id": tu.tool_use_id,
                            "name": tu.tool_name,
                            "input": tu.arguments,
                        }
                    )
                records.append(
                    cls(type=RecordType.ASSISTANT, content=content_blocks, timestamp=now)
                )
            else:
                records.append(
                    cls(type=RecordType.ASSISTANT, content=message.content, timestamp=now)
                )
        else:
            records.append(
                cls(type=RecordType.USER, content=message.content, timestamp=now)
            )

        return records


# ---------------------------------------------------------------------------
# Compact boundary 载荷（摘要 + 内联的 keep 尾部）
# ---------------------------------------------------------------------------


def _message_to_record_dicts(message: Message) -> list[dict[str, Any]]:
    """将单条 Message 序列化为与磁盘存储格式一致的 record-dict 列表。

    复用 SessionRecord.from_message，使内联的 keep 尾部与正常追加消息的持久化
    结果逐字节一致（assistant 的 tool_uses 变为 content-blocks 列表，每个
    tool_result 独立成一条 record）。这保证了 tool_use↔tool_result 配对的
    无损往返——不像纯 role+content 文本导出那样会丢失 tool call 的关联关系。
    """
    dicts: list[dict[str, Any]] = []
    for rec in SessionRecord.from_message(message):
        data: dict[str, Any] = {"type": rec.type.value, "content": rec.content}
        if rec.tool_use_id is not None:
            data["tool_use_id"] = rec.tool_use_id
        if rec.type == RecordType.TOOL_RESULT:
            data["is_error"] = rec.is_error
        dicts.append(data)
    return dicts


def make_compact_boundary(summary: str, keep: list[Message]) -> SessionRecord:
    """构建一条 COMPACT_BOUNDARY record，内联摘要和原样保留的 keep 尾部。

    `keep` 是 auto_compact 原样保留的近期尾部消息。将其存储在 boundary record
    内部（而不是依赖它在文件中的物理位置），意味着 resume 可以仅凭 boundary
    重建压缩后的状态——boundary 之前的原始前缀保留在磁盘上但不会被重放。
    """
    keep_dicts: list[dict[str, Any]] = []
    for msg in keep:
        keep_dicts.extend(_message_to_record_dicts(msg))
    payload = {"summary": summary, "keep": keep_dicts}
    return SessionRecord(
        type=RecordType.COMPACT_BOUNDARY,
        content=payload,
        timestamp=datetime.now(timezone.utc),
    )


def parse_compact_boundary(record: SessionRecord) -> tuple[str, list[Message]]:
    """make_compact_boundary 的逆操作：返回 (summary, keep_messages)。

    对遗留或格式异常的 payload 降级返回 ("", [])，确保单条损坏的 boundary
    不会导致 resume 崩溃。
    """
    content = record.content
    if not isinstance(content, dict):
        return "", []
    summary = content.get("summary", "")
    keep_raw = content.get("keep", [])
    keep_records: list[SessionRecord] = []
    for item in keep_raw if isinstance(keep_raw, list) else []:
        if not isinstance(item, dict) or "type" not in item:
            continue
        try:
            keep_records.append(
                SessionRecord(
                    type=RecordType(item["type"]),
                    content=item.get("content"),
                    timestamp=record.timestamp,
                    tool_use_id=item.get("tool_use_id"),
                    is_error=item.get("is_error", False),
                )
            )
        except ValueError:
            continue
    return summary, records_to_messages(keep_records)


# ---------------------------------------------------------------------------
# Record ↔ Message 转换
# ---------------------------------------------------------------------------


def records_to_messages(records: list[SessionRecord]) -> list[Message]:
    """将 SessionRecord 列表转换为 Message 列表。

    将相邻的 TOOL_RESULT 记录聚合为一条 user 消息（带 tool_results），
    assistant 消息的 content-blocks 被展开为纯文本和 tool_uses。
    COMPRESSION 和 COMPACT_BOUNDARY 记录会展开为摘要 user 消息。

    Args:
        records: 要转换的记录列表。

    Returns:
        重建的 Message 列表。
    """
    messages: list[Message] = []
    pending_tool_results: list[ToolResultBlock] = []

    for record in records:
        if record.type == RecordType.TOOL_RESULT:
            pending_tool_results.append(
                ToolResultBlock(
                    tool_use_id=record.tool_use_id or "",
                    content=(
                        record.content
                        if isinstance(record.content, str)
                        else json.dumps(record.content)
                    ),
                    is_error=record.is_error,
                )
            )
            continue

        if pending_tool_results:
            messages.append(
                Message(role="user", content="", tool_results=pending_tool_results)
            )
            pending_tool_results = []

        if record.type == RecordType.SYSTEM_PROMPT:
            continue

        if record.type == RecordType.COMPRESSION:
            messages.append(
                Message(
                    role="user",
                    content="本次会话延续自之前的对话，因上下文空间不足进行了压缩。以下是早期对话的摘要：\n\n" + (record.content or ""),
                )
            )
            continue

        if record.type == RecordType.COMPACT_BOUNDARY:
            # 内联展开：摘要作为 user 消息，后接原样保留的 keep 尾部。
            # resume() 通常已预裁剪到最后一个 boundary，所以这里只会处理
            # 权威的那一条；但在此展开可以保证 records_to_messages 对任何
            # 直接调用者都保持自洽。
            summary, keep_messages = parse_compact_boundary(record)
            messages.append(Message(role="user", content="本次会话延续自之前的对话，因上下文空间不足进行了压缩。以下是早期对话的摘要：\n\n" + summary))
            messages.extend(keep_messages)
            continue

        if record.type == RecordType.USER:
            messages.append(Message(role="user", content=record.content or ""))
        elif record.type == RecordType.ASSISTANT:
            if isinstance(record.content, list):
                text = ""
                tool_uses: list[ToolUseBlock] = []
                for block in record.content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text":
                        text += block.get("text", "")
                    elif block.get("type") == "tool_use":
                        tool_uses.append(
                            ToolUseBlock(
                                tool_use_id=block.get("id", ""),
                                tool_name=block.get("name", ""),
                                arguments=block.get("input", {}),
                            )
                        )
                messages.append(
                    Message(role="assistant", content=text, tool_uses=tool_uses)
                )
            else:
                messages.append(
                    Message(role="assistant", content=record.content or "")
                )

    if pending_tool_results:
        messages.append(
            Message(role="user", content="", tool_results=pending_tool_results)
        )

    return messages


# ---------------------------------------------------------------------------
# 消息链校验
# ---------------------------------------------------------------------------


def validate_message_chain(records: list[SessionRecord]) -> int:
    """校验消息链的完整性，返回最后一条完整消息的索引（不含悬空 tool_uses）。

    tool_use 和 tool_result 必须成对出现，未匹配的尾部记录会被截断。

    Args:
        records: 会话记录列表。

    Returns:
        最后一条有效记录的索引（截断位置）。
    """
    last_valid = 0
    pending_tool_uses: set[str] = set()

    for i, record in enumerate(records):
        if record.type == RecordType.ASSISTANT and isinstance(record.content, list):
            for block in record.content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_id = block.get("id", "")
                    if tool_id:
                        pending_tool_uses.add(tool_id)

        if record.type == RecordType.TOOL_RESULT and record.tool_use_id:
            pending_tool_uses.discard(record.tool_use_id)

        if not pending_tool_uses:
            last_valid = i + 1

    return last_valid


# ---------------------------------------------------------------------------
# SessionMeta
# ---------------------------------------------------------------------------


@dataclass
class SessionMeta:
    """会话元信息，包含摘要、统计和生命周期时间戳。"""

    id: str
    title: str = ""
    summary: str = ""
    message_count: int = 0
    total_tokens: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def save(self, path: Path) -> None:
        """将会话元信息保存为 JSON 文件。

        Args:
            path: 保存路径。
        """
        data = {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "message_count": self.message_count,
            "total_tokens": self.total_tokens,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
        }
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @classmethod
    def load(cls, path: Path) -> SessionMeta | None:
        """从 JSON 文件加载会话元信息。

        Args:
            path: 元信息文件路径。

        Returns:
            加载的 SessionMeta，解析失败返回 None。
        """
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                id=data["id"],
                title=data.get("title", ""),
                summary=data.get("summary", ""),
                message_count=data.get("message_count", 0),
                total_tokens=data.get("total_tokens", 0),
                created_at=datetime.fromisoformat(data["created_at"]),
                last_active=datetime.fromisoformat(data["last_active"]),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return None


# ---------------------------------------------------------------------------
# Session（活跃会话句柄）
# ---------------------------------------------------------------------------


class Session:
    """活跃会话句柄，封装文件写入和元信息更新。

    持有 JSONL 文件句柄，提供消息追加和元信息更新能力。
    """

    def __init__(
        self,
        session_id: str,
        file: IO[str],
        meta: SessionMeta,
        sessions_dir: Path,
    ) -> None:
        """初始化会话句柄。

        Args:
            session_id: 会话 ID。
            file: 已打开的 JSONL 文件句柄（追加模式）。
            meta: 会话元信息。
            sessions_dir: 会话目录。
        """
        self.session_id = session_id
        self._file = file
        self.meta = meta
        self._sessions_dir = sessions_dir

    def append(self, message: Message) -> None:
        """追加一条 Message 到会话文件并更新元信息。

        自动提取首条用户消息的前 TITLE_MAX_LENGTH 个字符作为标题。

        Args:
            message: 要追加的 Message。
        """
        records = SessionRecord.from_message(message)
        for record in records:
            self._file.write(record.to_jsonl() + "\n")
        self._file.flush()

        self.meta.message_count += 1
        self.meta.last_active = datetime.now(timezone.utc)

        if not self.meta.title and message.role == "user" and message.content:
            self.meta.title = message.content[:TITLE_MAX_LENGTH]

        self.meta.save(self._sessions_dir / f"{self.session_id}.meta")

    def append_record(self, record: SessionRecord) -> None:
        """追加一条原始 SessionRecord（例如 compact_boundary 标记）。

        与 append() 不同，此方法不会更新 message_count/title——boundary 是
        结构性标记而非对话轮次。last_active 仍会更新，以保证 session 按最近
        使用排序。
        """
        self._file.write(record.to_jsonl() + "\n")
        self._file.flush()
        self.meta.last_active = datetime.now(timezone.utc)
        self.meta.save(self._sessions_dir / f"{self.session_id}.meta")

    def close(self) -> None:
        """关闭会话文件句柄。"""
        if self._file and not self._file.closed:
            self._file.flush()
            self._file.close()


# ---------------------------------------------------------------------------
# ResumeResult
# ---------------------------------------------------------------------------


@dataclass
class ResumeResult:
    """会话恢复结果，包含 Session 句柄、重建的消息列表和最后活跃时间。"""

    session: Session
    messages: list[Message]
    last_active: datetime


# ---------------------------------------------------------------------------
# Session 摘要生成
# ---------------------------------------------------------------------------


async def generate_session_summary(
    client: Any, conversation: ConversationManager, protocol: str
) -> str:
    """生成会话的一句话摘要，用于列表展示。

    取最近 10 条消息，调用 LLM 生成简短摘要。

    Args:
        client: LLM 客户端。
        conversation: 当前对话管理器。
        protocol: 消息序列化协议。

    Returns:
        生成的摘要文本。失败时返回空字符串。
    """
    from owlcode.tools.base import StreamEnd, TextDelta

    recent = conversation.history[-10:]
    if not recent:
        return ""

    summary_conv = ConversationManager()
    summary_conv.history = [Message(role="user", content=SESSION_SUMMARY_PROMPT)]
    for msg in recent:
        summary_conv.history.append(msg)
    summary_conv.history.append(
        Message(role="user", content="请用一句话总结上面的对话内容。不要调用工具。")
    )

    collected = ""
    try:
        async for event in client.stream(
            summary_conv, system=SESSION_SUMMARY_PROMPT
        ):
            if isinstance(event, TextDelta):
                collected += event.text
            elif isinstance(event, StreamEnd):
                pass
    except Exception:
        return ""

    return collected.strip()


# ---------------------------------------------------------------------------
# SessionManager
# ---------------------------------------------------------------------------


def _generate_session_id() -> str:
    now = datetime.now()
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"session_{now.strftime('%Y%m%d_%H%M%S')}_{suffix}"


class SessionManager:
    """会话管理器，负责创建、列出、恢复、删除和清理会话。

    会话以 JSONL 格式存储在 work_dir 下的 .owlcode/sessions/ 目录中，
    每条会话包含 .jsonl 数据文件和 .meta 元信息文件。
    """

    def __init__(self, work_dir: str) -> None:
        """初始化会话管理器。

        Args:
            work_dir: 工作目录，会话文件存储在其 .owlcode/sessions/ 子目录下。
        """
        self._sessions_dir = Path(work_dir) / SESSIONS_DIR
        self._sessions_dir.mkdir(parents=True, exist_ok=True)

    def create(self) -> Session:
        """创建新会话。

        Returns:
            新创建的 Session 对象，含打开的文件句柄。
        """
        session_id = _generate_session_id()
        jsonl_path = self._sessions_dir / f"{session_id}.jsonl"
        meta = SessionMeta(id=session_id)
        meta.save(self._sessions_dir / f"{session_id}.meta")

        file = open(jsonl_path, "a", encoding="utf-8")  # noqa: SIM115
        return Session(
            session_id=session_id,
            file=file,
            meta=meta,
            sessions_dir=self._sessions_dir,
        )

    def list(self) -> list[SessionMeta]:
        """列出所有会话的元信息，按最后活跃时间倒序排列。

        Returns:
            SessionMeta 列表。
        """
        metas: list[SessionMeta] = []
        for meta_path in self._sessions_dir.glob("*.meta"):
            meta = SessionMeta.load(meta_path)
            if meta is not None:
                metas.append(meta)
        metas.sort(key=lambda m: m.last_active, reverse=True)
        return metas

    def resume(self, session_id: str) -> ResumeResult | None:
        """恢复指定会话。

        从 JSONL 文件加载记录，找到最后的 compact_boundary 标记并从中断处恢复，
        校验消息链完整性后重建 Message 列表。

        Args:
            session_id: 会话 ID。

        Returns:
            ResumeResult，含 Session 句柄和消息列表。会话不存在返回 None。
        """
        jsonl_path = self._sessions_dir / f"{session_id}.jsonl"
        meta_path = self._sessions_dir / f"{session_id}.meta"

        if not jsonl_path.exists():
            return None

        meta = SessionMeta.load(meta_path)
        if meta is None:
            return None

        records: list[SessionRecord] = []
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = SessionRecord.from_jsonl(line)
                if record is not None:
                    records.append(record)

        # 重建压缩后的状态：仅从最后一个 compact_boundary 开始重放。
        # 该标记之前的 record 是已被摘要过的原始前缀——保留在磁盘上供审计，
        # 但不再重放。标记本身内联了摘要 + 原样 keep 尾部，标记之后追加的
        # 普通消息（续写）照常重放。没有 boundary 则全量重放（兼容旧 session）。
        last_boundary = -1
        for i, rec in enumerate(records):
            if rec.type == RecordType.COMPACT_BOUNDARY:
                last_boundary = i
        if last_boundary >= 0:
            records = records[last_boundary:]

        valid_count = validate_message_chain(records)
        records = records[:valid_count]
        messages = records_to_messages(records)

        file = open(jsonl_path, "a", encoding="utf-8")  # noqa: SIM115
        session = Session(
            session_id=session_id,
            file=file,
            meta=meta,
            sessions_dir=self._sessions_dir,
        )

        return ResumeResult(
            session=session,
            messages=messages,
            last_active=meta.last_active,
        )

    def delete(self, session_id: str) -> bool:
        """删除指定会话的 JSONL 和 meta 文件。

        Args:
            session_id: 会话 ID。

        Returns:
            至少删除了一个文件返回 True。
        """
        jsonl_path = self._sessions_dir / f"{session_id}.jsonl"
        meta_path = self._sessions_dir / f"{session_id}.meta"

        deleted = False
        if jsonl_path.exists():
            jsonl_path.unlink()
            deleted = True
        if meta_path.exists():
            meta_path.unlink()
            deleted = True
        return deleted

    def cleanup(self, max_age_days: int = DEFAULT_MAX_AGE_DAYS) -> int:
        """清理超过指定天数的过期会话。

        Args:
            max_age_days: 最大保留天数，默认 30 天。

        Returns:
            清理的会话数量。
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        removed = 0

        for meta_path in list(self._sessions_dir.glob("*.meta")):
            meta = SessionMeta.load(meta_path)
            if meta is not None and meta.last_active < cutoff:
                self.delete(meta.id)
                removed += 1

        return removed
