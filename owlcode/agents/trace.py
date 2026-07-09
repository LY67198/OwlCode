from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class TraceNode:
    """追踪节点，记录单个 Agent 执行的 Token 用量、耗时与状态。"""
    agent_id: str
    parent_id: str | None
    trace_id: str
    agent_type: str
    input_tokens: int = 0
    output_tokens: int = 0
    tool_call_count: int = 0
    start_time: float = field(default_factory=time.monotonic)
    end_time: float | None = None
    status: str = "running"


class TraceManager:
    """追踪管理器，维护一棵 Agent 执行追踪树。

    支持创建节点、更新属性、标记完成以及按 trace_id 汇总 Token 用量。
    """

    def __init__(self) -> None:
        """初始化追踪管理器。"""
        self._nodes: dict[str, TraceNode] = {}


    def create(
        self,
        agent_type: str,
        parent_id: str | None = None,
        trace_id: str | None = None,
    ) -> TraceNode:
        """创建新的追踪节点。

        Args:
            agent_type: Agent 类型名称。
            parent_id: 父节点 ID，None 表示根节点。
            trace_id: 追踪链 ID，None 则自动生成。

        Returns:
            新创建的 TraceNode 实例。
        """
        agent_id = uuid.uuid4().hex[:12]
        if trace_id is None:
            trace_id = uuid.uuid4().hex[:12]

        node = TraceNode(
            agent_id=agent_id,
            parent_id=parent_id,
            trace_id=trace_id,
            agent_type=agent_type,
        )
        self._nodes[agent_id] = node
        return node

    def update(self, agent_id: str, **kwargs: int | str) -> None:
        """更新节点的属性值。

        Args:
            agent_id: 节点 ID。
            **kwargs: 要更新的属性键值对。
        """
        node = self._nodes.get(agent_id)
        if node is None:
            return
        for key, value in kwargs.items():
            if hasattr(node, key):
                setattr(node, key, value)


    def complete(self, agent_id: str, status: str = "completed") -> None:
        """标记节点为完成状态并记录结束时间。

        Args:
            agent_id: 节点 ID。
            status: 完成状态，默认为 "completed"。
        """
        node = self._nodes.get(agent_id)
        if node is None:
            return
        node.end_time = time.monotonic()
        node.status = status


    def get(self, agent_id: str) -> TraceNode | None:
        """获取指定 ID 的追踪节点。

        Args:
            agent_id: 节点 ID。

        Returns:
            对应的 TraceNode，不存在则返回 None。
        """
        return self._nodes.get(agent_id)

    def get_tree(self, trace_id: str) -> list[TraceNode]:
        """获取同一追踪链下的所有节点。

        Args:
            trace_id: 追踪链 ID。

        Returns:
            TraceNode 列表。
        """
        return [n for n in self._nodes.values() if n.trace_id == trace_id]


    def remove(self, agent_id: str) -> None:
        """移除指定的追踪节点。

        Args:
            agent_id: 节点 ID。
        """
        self._nodes.pop(agent_id, None)

    def complete_all_running(self, parent_id: str) -> None:
        """将指定父节点下所有运行中的子节点标记为已完成。

        Args:
            parent_id: 父节点 ID。
        """
        for node in self._nodes.values():
            if node.parent_id == parent_id and node.status == "running":
                node.status = "completed"
                node.end_time = time.monotonic()

    def get_total_tokens(self, trace_id: str) -> tuple[int, int]:
        """汇总指定追踪链的总输入/输出 Token 数。

        Args:
            trace_id: 追踪链 ID。

        Returns:
            (input_tokens, output_tokens) 元组。
        """
        total_in = 0
        total_out = 0
        for node in self._nodes.values():
            if node.trace_id == trace_id:
                total_in += node.input_tokens
                total_out += node.output_tokens
        return total_in, total_out
