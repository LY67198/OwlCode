from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

VALID_MODELS = {"inherit", "sonnet", "opus", "haiku", ""}
VALID_PERMISSION_MODES = {"default", "acceptEdits", "dontAsk", ""}


class AgentParseError(Exception):
    """Agent 文件解析错误，如 YAML 格式不正确或缺少必要字段时抛出。"""
    pass


VALID_ISOLATION_MODES = {"", "worktree"}


@dataclass
class AgentDef:
    """Agent 定义数据类，描述 Agent 的类型、提示词、工具集与行为配置。"""
    agent_type: str
    when_to_use: str
    system_prompt: str = ""
    tools: list[str] = field(default_factory=list)
    disallowed_tools: list[str] = field(default_factory=list)
    model: str = "inherit"
    max_turns: int = 50
    permission_mode: str = "default"
    background: bool = False
    isolation: str = ""
    file_path: Path | None = None
    source: str = "builtin"


def parse_frontmatter(raw: str) -> tuple[dict, str]:
    """从原始文本中提取 YAML frontmatter 与正文。

    Args:
        raw: 包含 frontmatter 的原始 Markdown 文本。

    Returns:
        (元数据字典, 正文内容) 元组。

    Raises:
        AgentParseError: frontmatter 缺失或 YAML 格式错误。
    """
    stripped = raw.lstrip()
    if not stripped.startswith("---"):
        raise AgentParseError("Missing YAML frontmatter (must start with ---)")

    end = stripped.find("---", 3)
    if end == -1:
        raise AgentParseError("Unclosed YAML frontmatter (missing closing ---)")

    yaml_block = stripped[3:end]
    body = stripped[end + 3 :].lstrip("\n")

    try:
        meta = yaml.safe_load(yaml_block)
    except yaml.YAMLError as e:
        raise AgentParseError(f"Invalid YAML in frontmatter: {e}") from e

    if not isinstance(meta, dict):
        raise AgentParseError("Frontmatter must be a YAML mapping")

    return meta, body


def _validate_agent_meta(meta: dict, source: str = "") -> None:
    """校验 Agent frontmatter 元数据的必填字段与值合法性。

    检查 name、description 是否存在，model、permissionMode、
    maxTurns、isolation 等值是否在允许范围内。

    Args:
        meta: frontmatter 解析后的字典。
        source: 文件来源标识（用于错误信息上下文）。

    Raises:
        AgentParseError: 校验不通过。
    """
    ctx = f" in {source}" if source else ""

    if "name" not in meta:
        raise AgentParseError(f"Missing required field 'name'{ctx}")
    if "description" not in meta:
        raise AgentParseError(f"Missing required field 'description'{ctx}")

    model = str(meta.get("model", "inherit"))
    if model not in VALID_MODELS:
        raise AgentParseError(
            f"Invalid model '{model}'{ctx}: must be one of {VALID_MODELS - {''}}"
        )

    pm = str(meta.get("permissionMode", "default"))
    if pm not in VALID_PERMISSION_MODES:
        raise AgentParseError(
            f"Invalid permissionMode '{pm}'{ctx}: "
            f"must be one of {VALID_PERMISSION_MODES - {''}}"
        )

    max_turns = meta.get("maxTurns")
    if max_turns is not None:
        if not isinstance(max_turns, int) or max_turns <= 0:
            raise AgentParseError(
                f"Invalid maxTurns '{max_turns}'{ctx}: must be a positive integer"
            )

    isolation = str(meta.get("isolation", ""))
    if isolation not in VALID_ISOLATION_MODES:
        raise AgentParseError(
            f"Invalid isolation '{isolation}'{ctx}: "
            f"must be one of {VALID_ISOLATION_MODES - {''}}"
        )


def parse_agent_file(path: Path) -> AgentDef:
    """解析单个 Agent 定义文件（.md），返回 AgentDef。

    读取文件内容，提取 YAML frontmatter 与正文，校验后构建 AgentDef。

    Args:
        path: Agent 定义文件的路径（.md 文件）。

    Returns:
        解析得到的 AgentDef 实例。

    Raises:
        AgentParseError: 文件读取失败或解析/校验错误。
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        raise AgentParseError(f"Cannot read agent file {path}: {e}") from e

    meta, body = parse_frontmatter(raw)
    _validate_agent_meta(meta, str(path))

    return AgentDef(
        agent_type=meta["name"],
        when_to_use=meta["description"],
        system_prompt=body,
        tools=meta.get("tools", []),
        disallowed_tools=meta.get("disallowedTools", []),
        model=str(meta.get("model", "inherit")),
        max_turns=meta.get("maxTurns", 50),
        permission_mode=str(meta.get("permissionMode", "default")),
        background=bool(meta.get("background", False)),
        isolation=str(meta.get("isolation", "")),
        file_path=path,
        source="builtin",
    )
