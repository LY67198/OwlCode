"""技能文件解析器：解析 SKILL.md 的 YAML 前置元数据和正文内容。"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

log = logging.getLogger(__name__)

VALID_NAME_RE = re.compile(r"^[a-z][a-z0-9\-]*$")
VALID_MODES = {"inline", "fork"}
VALID_CONTEXTS = {"full", "recent", "none"}


class SkillParseError(Exception):
    """技能文件解析失败时抛出的异常。"""
    pass


@dataclass
class SkillDef:
    """技能定义数据结构，包含名称、描述、提示词等元数据。"""
    name: str
    description: str
    prompt_body: str = ""
    allowed_tools: list[str] = field(default_factory=list)
    mode: Literal["inline", "fork"] = "inline"
    model: str | None = None
    context: Literal["full", "recent", "none"] = "full"
    source_path: Path | None = None
    is_directory: bool = False


def parse_frontmatter(raw: str) -> tuple[dict, str]:
    """解析 SKILL.md 的 YAML 前置元数据。

    Args:
        raw: SKILL.md 文件的原始文本内容。

    Returns:
        (元数据字典, 正文内容) 的元组。

    Raises:
        SkillParseError: 前置元数据格式不合法时抛出。
    """
    stripped = raw.lstrip()
    if not stripped.startswith("---"):
        raise SkillParseError("Missing YAML frontmatter (must start with ---)")

    end = stripped.find("---", 3)
    if end == -1:
        raise SkillParseError("Unclosed YAML frontmatter (missing closing ---)")

    yaml_block = stripped[3:end]
    body = stripped[end + 3:].lstrip("\n")

    try:
        meta = yaml.safe_load(yaml_block)
    except yaml.YAMLError as e:
        raise SkillParseError(f"Invalid YAML in frontmatter: {e}") from e

    if not isinstance(meta, dict):
        raise SkillParseError("Frontmatter must be a YAML mapping")

    return meta, body


def _validate_meta(meta: dict, source: str = "") -> None:
    """验证元数据字段的合法性（名称格式、模式、上下文等）。

    Args:
        meta: 从 YAML 前置元数据解析出的字典。
        source: 来源标识，用于错误消息。

    Raises:
        SkillParseError: 字段缺失或值不合法时抛出。
    """
    ctx = f" in {source}" if source else ""

    if "name" not in meta:
        raise SkillParseError(f"Missing required field 'name'{ctx}")
    if "description" not in meta:
        raise SkillParseError(f"Missing required field 'description'{ctx}")

    name = meta["name"]
    if not isinstance(name, str) or not VALID_NAME_RE.match(name):
        raise SkillParseError(
            f"Invalid skill name '{name}'{ctx}: "
            "must be lowercase letters, digits, and hyphens, starting with a letter"
        )

    mode = meta.get("mode", "inline")
    if mode not in VALID_MODES:
        raise SkillParseError(f"Invalid mode '{mode}'{ctx}: must be one of {VALID_MODES}")

    context = meta.get("context", "full")
    if context not in VALID_CONTEXTS:
        raise SkillParseError(f"Invalid context '{context}'{ctx}: must be one of {VALID_CONTEXTS}")


def parse_skill_file(path: Path) -> SkillDef:
    """从文件路径读取并解析技能定义。

    Args:
        path: SKILL.md 文件的路径。

    Returns:
        解析出的 SkillDef 对象。

    Raises:
        SkillParseError: 读取或解析失败时抛出。
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        raise SkillParseError(f"Cannot read skill file {path}: {e}") from e

    meta, body = parse_frontmatter(raw)
    _validate_meta(meta, str(path))

    return SkillDef(
        name=meta["name"],
        description=meta["description"],
        prompt_body=body,
        allowed_tools=meta.get("allowedTools", []),
        mode=meta.get("mode", "inline"),
        model=meta.get("model"),
        context=meta.get("context", "full"),
        source_path=path,
        is_directory=False,
    )


def substitute_arguments(prompt_body: str, args: str) -> str:
    """将 prompt 正文中的 $ARGUMENTS 占位符替换为实际参数。

    Args:
        prompt_body: 包含 $ARGUMENTS 的提示词正文。
        args: 替换 $ARGUMENTS 的参数字符串。

    Returns:
        替换后的 prompt 正文。
    """
    return prompt_body.replace("$ARGUMENTS", args)
