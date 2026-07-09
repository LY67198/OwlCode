from __future__ import annotations

from typing import TYPE_CHECKING, Any

from owlcode.tools.base import Tool

if TYPE_CHECKING:
    from owlcode.cache import FileCache


class ToolRegistry:
    """工具注册表，管理所有工具的注册、启用/禁用和发现状态。

    支持延迟加载：标记为 should_defer 的工具不会立即暴露给 LLM，
    只有在被 ToolSearch 发现后才会出现在 schema 列表中。
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._disabled: set[str] = set()
        self._discovered: set[str] = set()

    def register(self, tool: Tool) -> None:
        """向注册表注册一个工具。

        Args:
            tool: 要注册的工具实例。
        """
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """根据名称获取工具实例。

        Args:
            name: 工具名称。

        Returns:
            找到的工具实例，未找到则返回 None。
        """
        return self._tools.get(name)


    def is_enabled(self, name: str) -> bool:
        """检查指定工具是否已启用。

        Args:
            name: 工具名称。

        Returns:
            工具存在且未被禁用返回 True。
        """
        return name in self._tools and name not in self._disabled

    def enable(self, name: str) -> None:
        """启用指定工具。

        Args:
            name: 工具名称。
        """
        self._disabled.discard(name)


    def disable(self, name: str) -> None:
        """禁用指定工具。

        Args:
            name: 工具名称。若工具不存在则忽略。
        """
        if name in self._tools:
            self._disabled.add(name)

    def enable_all(self) -> None:
        """启用所有已禁用的工具。"""
        self._disabled.clear()


    def mark_discovered(self, name: str) -> None:
        """将工具标记为已发现，使其在 get_all_schemas 中可见。

        Args:
            name: 工具名称。
        """
        self._discovered.add(name)

    def is_discovered(self, name: str) -> bool:
        """检查工具是否已被发现。

        Args:
            name: 工具名称。

        Returns:
            已发现返回 True。
        """
        return name in self._discovered


    def get_deferred_tool_names(self) -> list[str]:
        """获取所有尚未被发现且未被禁用的延迟工具名称列表。

        Returns:
            延迟工具名称列表。
        """
        return [
            name
            for name, tool in self._tools.items()
            if getattr(tool, "should_defer", False)
            and name not in self._discovered
            and name not in self._disabled
        ]

    def search_deferred(
        self, query: str, max_results: int, protocol: str = "anthropic"
    ) -> list[dict[str, Any]]:
        """在延迟工具中搜索匹配查询的工具。

        Args:
            query: 搜索关键词。
            max_results: 最大返回数量。
            protocol: 协议类型，默认 "anthropic"，也支持 "openai" 格式。

        Returns:
            按相关性排序的工具 schema 列表。
        """
        query_lower = query.lower()
        scored: list[tuple[int, str, Tool]] = []
        for name, tool in self._tools.items():
            if not getattr(tool, "should_defer", False):
                continue
            if name in self._disabled:
                continue
            score = 0
            name_lower = name.lower()
            desc_lower = (tool.description or "").lower()
            if query_lower in name_lower:
                score += 10
            if query_lower in desc_lower:
                score += 5
            for word in query_lower.split():
                if word in name_lower:
                    score += 3
                if word in desc_lower:
                    score += 1
            if score > 0:
                scored.append((score, name, tool))
        scored.sort(key=lambda x: x[0], reverse=True)
        results: list[dict[str, Any]] = []
        for _, _name, tool in scored[:max_results]:
            base = tool.get_schema()
            if protocol in ("openai", "openai-compat"):
                results.append({
                    "type": "function",
                    "name": base["name"],
                    "description": base["description"],
                    "parameters": base["input_schema"],
                })
            else:
                results.append(base)
        return results

    def find_deferred_by_names(
        self, names: list[str], protocol: str = "anthropic"
    ) -> list[dict[str, Any]]:
        """根据名称列表精确查找延迟工具的 schema。

        Args:
            names: 要查找的工具名称列表。
            protocol: 协议类型。

        Returns:
            匹配的工具 schema 列表。
        """
        results: list[dict[str, Any]] = []
        for name in names:
            tool = self._tools.get(name)
            if tool is None:
                continue
            if not getattr(tool, "should_defer", False):
                continue
            base = tool.get_schema()
            if protocol in ("openai", "openai-compat"):
                results.append({
                    "type": "function",
                    "name": base["name"],
                    "description": base["description"],
                    "parameters": base["input_schema"],
                })
            else:
                results.append(base)
        return results

    def list_tools(self) -> list[Tool]:
        """列出所有已注册的工具。

        Returns:
            工具实例列表。
        """
        return list(self._tools.values())


    def get_all_schemas(self, protocol: str = "anthropic") -> list[dict[str, Any]]:
        """获取所有已启用且已发现（非延迟）工具的 schema。

        Args:
            protocol: 协议类型。

        Returns:
            工具 schema 列表。
        """
        schemas: list[dict[str, Any]] = []
        for name, tool in self._tools.items():
            if name in self._disabled:
                continue
            if getattr(tool, "should_defer", False) and name not in self._discovered:
                continue
            base = tool.get_schema()
            if protocol in ("openai", "openai-compat"):
                schemas.append({
                    "type": "function",
                    "name": base["name"],
                    "description": base["description"],
                    "parameters": base["input_schema"],
                })
            else:
                schemas.append(base)
        return schemas


def create_default_registry(file_cache: FileCache | None = None, file_history: Any = None) -> ToolRegistry:
    """创建并返回包含默认工具的注册表。

    Args:
        file_cache: 文件缓存实例，用于 ReadFile 等工具。
        file_history: 文件历史记录实例，用于 EditFile 和 WriteFile。

    Returns:
        预注册了 ReadFile、WriteFile、EditFile、Bash、Glob、Grep 的 ToolRegistry。
    """
    from owlcode.tools.bash import Bash
    from owlcode.tools.edit_file import EditFile
    from owlcode.tools.file_state_cache import FileStateCache
    from owlcode.tools.glob import Glob
    from owlcode.tools.grep import Grep
    from owlcode.tools.read_file import ReadFile
    from owlcode.tools.write_file import WriteFile

    file_state_cache = FileStateCache()

    registry = ToolRegistry()
    registry.register(ReadFile(file_cache=file_cache, file_state_cache=file_state_cache))
    registry.register(WriteFile(file_cache=file_cache, file_history=file_history, file_state_cache=file_state_cache))
    registry.register(EditFile(file_cache=file_cache, file_history=file_history, file_state_cache=file_state_cache))
    registry.register(Bash())
    registry.register(Glob())
    registry.register(Grep())
    return registry
