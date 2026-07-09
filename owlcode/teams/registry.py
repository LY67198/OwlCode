from __future__ import annotations

import threading


class AgentNameRegistry:
    """Agent 名称注册表（线程安全单例）。

    维护 Agent 名称到 Agent ID 的双向映射，支持注册、解析和注销。
    """

    _instance: AgentNameRegistry | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        """初始化名称注册表。"""
        self._names: dict[str, str] = {}  # name -> agent_id


    @classmethod
    def instance(cls) -> AgentNameRegistry:
        """获取全局单例实例。

        Returns:
            AgentNameRegistry 实例。
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance


    @classmethod
    def reset(cls) -> None:
        """重置单例（用于测试清理）。"""
        with cls._lock:
            cls._instance = None


    def register(self, name: str, agent_id: str) -> None:
        """注册名称到 Agent ID 的映射。

        Args:
            name: Agent 名称。
            agent_id: Agent 唯一 ID。
        """
        self._names[name] = agent_id

    def resolve(self, name_or_id: str) -> str | None:
        """解析名称或 ID，返回对应的 Agent ID。

        Args:
            name_or_id: Agent 名称或 ID。

        Returns:
            Agent ID，未找到则返回 None。
        """
        if name_or_id in self._names:
            return self._names[name_or_id]
        if name_or_id in self._names.values():
            return name_or_id
        return None

    def unregister(self, name: str) -> None:
        """注销名称映射。

        Args:
            name: Agent 名称。
        """
        self._names.pop(name, None)


    def list_all(self) -> dict[str, str]:
        """列出所有已注册的名称到 ID 的映射。

        Returns:
            name -> agent_id 字典的副本。
        """
        return dict(self._names)
