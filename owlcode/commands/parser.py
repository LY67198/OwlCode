"""斜杠命令解析与自动补全匹配。"""

from __future__ import annotations

from owlcode.commands.registry import CommandRegistry


def parse_command(text: str) -> tuple[str, str, bool]:
    """解析用户输入，提取斜杠命令的名称及其参数。

    Args:
        text: 用户输入的原始字符串。

    Returns:
        三元组 (命令名, 参数字符串, 是否为斜杠命令)。
        如果输入不是以 / 开头，前两项为空字符串，第三项为 False。
    """
    text = text.strip()
    if not text.startswith("/"):
        return "", "", False
    text = text[1:]
    if not text:
        return "", "", True
    parts = text.split(None, 1)
    name = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""
    return name, args, True


def complete(registry: CommandRegistry, prefix: str) -> list[tuple[str, str]]:
    """返回匹配命令的 (display_text, command_value) 列表。"""
    prefix = prefix.lstrip("/")
    seen: set[str] = set()
    matches: list[tuple[str, str]] = []
    for cmd in registry.list_commands():
        if cmd.name in seen:
            continue
        if cmd.name.startswith(prefix) or any(a.startswith(prefix) for a in cmd.aliases):
            seen.add(cmd.name)
            desc = cmd.description
            if len(desc) > 30:
                desc = desc[:28] + "\u2026"
            desc = desc.replace("[", "\\[")
            display = f"/{cmd.name:<16} \u2014 {desc}"
            matches.append((display, "/" + cmd.name))
    matches.sort(key=lambda x: x[1])
    return matches[:8]
