"""权限规则引擎：基于模式匹配的工具权限控制。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Literal

import yaml

Effect = Literal["allow", "deny"]

_RULE_RE = re.compile(r"^(\w+)\((.+)\)$")

_CONTENT_FIELDS: dict[str, str] = {
    "Bash": "command",
    "ReadFile": "file_path",
    "WriteFile": "file_path",
    "EditFile": "file_path",
    "Glob": "pattern",
    "Grep": "pattern",
}


@dataclass(frozen=True)
class Rule:
    """单条权限规则，由工具名、匹配模式和效果组成。"""

    tool_name: str
    pattern: str
    effect: Effect

    def matches(self, tool_name: str, content: str) -> bool:
        """判断规则是否匹配指定的工具调用。

        同时比对工具名，并使用 fnmatch 进行内容模式匹配。

        Args:
            tool_name: 被调用的工具名。
            content: 工具的关键内容字段值。

        Returns:
            匹配成功返回 True。
        """
        if self.tool_name != tool_name:
            return False
        return fnmatch(content, self.pattern)


def parse_rule(raw: str, effect: Effect) -> Rule:
    """从规则字符串解析为 Rule 对象。

    格式：ToolName(pattern)，例如 Bash(ls *)。

    Args:
        raw: 原始规则字符串。
        effect: 规则效果（allow/deny）。

    Returns:
        解析出的 Rule 对象。

    Raises:
        ValueError: 规则语法无效时抛出。
    """
    m = _RULE_RE.match(raw.strip())
    if not m:
        raise ValueError(f"无效的规则语法: {raw}")
    return Rule(tool_name=m.group(1), pattern=m.group(2), effect=effect)


def extract_content(tool_name: str, arguments: dict[str, Any]) -> str:
    """从工具参数中提取用于规则匹配的内容字段。

    Args:
        tool_name: 工具名称。
        arguments: 工具调用参数。

    Returns:
        匹配用的内容字符串，无匹配字段返回空字符串。
    """
    field = _CONTENT_FIELDS.get(tool_name)
    if field is None:
        return ""
    return str(arguments.get(field, ""))


def _load_rules_file(path: Path) -> list[Rule]:
    if not path.is_file():
        return []
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return []
    if not isinstance(raw, list):
        return []
    rules: list[Rule] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        rule_str = entry.get("rule", "")
        effect = entry.get("effect", "")
        if effect not in ("allow", "deny"):
            continue
        try:
            rules.append(parse_rule(rule_str, effect))
        except ValueError:
            continue
    return rules


class RuleEngine:
    """规则引擎，按层级加载和评估权限规则。

    支持三级规则：用户级、项目级、本地（会话）级。评估时按用户级 -> 项目级 -> 本地级
    的顺序，每级内从最后一个规则向前匹配（后添加的规则优先级更高）。
    """

    def __init__(
        self,
        user_rules_path: Path | None = None,
        project_rules_path: Path | None = None,
        local_rules_path: Path | None = None,
    ) -> None:
        """初始化规则引擎。

        Args:
            user_rules_path: 用户级规则文件路径。
            project_rules_path: 项目级规则文件路径。
            local_rules_path: 本地（会话级）规则文件路径。
        """
        self._user_path = user_rules_path
        self._project_path = project_rules_path
        self._local_path = local_rules_path

    def _load_tiers(self) -> list[list[Rule]]:
        tiers: list[list[Rule]] = []
        for p in (self._user_path, self._project_path, self._local_path):
            tiers.append(_load_rules_file(p) if p else [])
        return tiers

    def evaluate(self, tool_name: str, content: str) -> Effect | None:
        """评估一次工具调用是否匹配任何规则。

        按用户 -> 项目 -> 本地三级顺序评估，每级内从后向前匹配。

        Args:
            tool_name: 工具名称。
            content: 工具的关键内容字段值。

        Returns:
            匹配到规则时返回其 effect（allow/deny），否则返回 None。
        """
        for rules in self._load_tiers():
            for rule in reversed(rules):
                if rule.matches(tool_name, content):
                    return rule.effect
        return None

    def append_local_rule(self, rule: Rule) -> None:
        """向本地规则文件追加一条新规则。

        Args:
            rule: 要追加的规则。
        """
        if self._local_path is None:
            return
        self._local_path.parent.mkdir(parents=True, exist_ok=True)
        existing = _load_rules_file(self._local_path)
        existing.append(rule)
        entries = [{"rule": f"{r.tool_name}({r.pattern})", "effect": r.effect} for r in existing]
        self._local_path.write_text(yaml.dump(entries, allow_unicode=True), encoding="utf-8")
