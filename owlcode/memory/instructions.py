"""指令加载模块：支持 @include 指令递归包含和 OWLCODE.md 配置加载。"""

from __future__ import annotations

from pathlib import Path

MAX_INCLUDE_DEPTH = 5
INCLUDE_PREFIX = "@include "


def process_includes(
    content: str,
    base_dir: Path,
    project_root: Path,
    depth: int = 0,
) -> str:
    """递归处理文本中的 @include 指令，将引用的文件内容内联。

    递归深度受 MAX_INCLUDE_DEPTH 限制，路径必须位于 project_root 以内。

    Args:
        content: 包含 @include 指令的文本。
        base_dir: @include 相对路径的基准目录。
        project_root: 项目根目录，用于安全边界检查。
        depth: 当前递归深度。

    Returns:
        处理后的文本，@include 行已替换为被引用文件的内容。
    """
    if depth >= MAX_INCLUDE_DEPTH:
        return content

    resolved_root = project_root.resolve()
    lines = content.split("\n")
    result: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith(INCLUDE_PREFIX):
            result.append(line)
            continue

        rel_path = stripped[len(INCLUDE_PREFIX) :].strip()
        abs_path = (base_dir / rel_path).resolve()

        try:
            abs_path.relative_to(resolved_root)
        except ValueError:
            result.append("<!-- @include blocked: path outside project -->")
            continue

        if not abs_path.exists() or not abs_path.is_file():
            result.append("<!-- @include skipped: file not found -->")
            continue

        included = abs_path.read_text(encoding="utf-8")
        processed = process_includes(included, abs_path.parent, project_root, depth + 1)
        result.append(processed)

    return "\n".join(result)


def load_instructions(project_root: str) -> str:
    """加载项目指令文件（OWLCODE.md），支持多路径回退和 @include。

    按优先级依次尝试：项目根目录 -> .owlcode/ -> ~/.owlcode/。
    多个文件的内容用 --- 分隔。

    Args:
        project_root: 项目根目录路径。

    Returns:
        合并后的指令文本。
    """
    root = Path(project_root)
    home = Path.home()

    paths = [
        root / "OWLCODE.md",
        root / ".owlcode" / "OWLCODE.md",
        home / ".owlcode" / "OWLCODE.md",
    ]

    sections: list[str] = []
    for path in paths:
        if path.exists() and path.is_file():
            content = path.read_text(encoding="utf-8")
            processed = process_includes(content, path.parent, root)
            sections.append(processed)

    return "\n---\n".join(sections)
