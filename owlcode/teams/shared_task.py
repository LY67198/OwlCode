from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SharedTask:
    """团队共享任务数据类，支持任务依赖（blocks/blocked_by）。"""
    id: str
    title: str
    description: str = ""
    status: str = "pending"  # pending | in_progress | completed | blocked
    assignee: str = ""
    blocks: list[str] = field(default_factory=list)
    blocked_by: list[str] = field(default_factory=list)
    created_by: str = ""


    def to_dict(self) -> dict[str, Any]:
        """将任务序列化为字典。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SharedTask:
        """从字典反序列化任务。

        Args:
            data: 任务字典。

        Returns:
            SharedTask 实例。
        """
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class SharedTaskStore:
    """团队共享任务持久化存储。

    基于 JSON 文件存储，支持任务的创建、查询和更新。
    """

    def __init__(self, path: str | Path) -> None:
        """初始化任务存储。

        Args:
            path: 存储文件路径（JSON）。
        """
        self._path = Path(path)
        self._next_id = 1
        self._tasks: dict[str, SharedTask] = {}
        self._load()

    def _load(self) -> None:
        """从磁盘加载任务数据。"""
        if not self._path.exists():
            return
        data = json.loads(self._path.read_text(encoding="utf-8"))
        self._next_id = data.get("next_id", 1)
        for t in data.get("tasks", []):
            task = SharedTask.from_dict(t)
            self._tasks[task.id] = task

    def _save(self) -> None:
        """将任务数据保存到磁盘。"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "next_id": self._next_id,
            "tasks": [t.to_dict() for t in self._tasks.values()],
        }
        self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def create(
        self,
        title: str,
        description: str = "",
        assignee: str = "",
        blocks: list[str] | None = None,
        blocked_by: list[str] | None = None,
        created_by: str = "",
    ) -> SharedTask:
        """创建新共享任务。

        Args:
            title: 任务标题。
            description: 任务描述。
            assignee: 负责人。
            blocks: 被此任务阻塞的其他任务 ID。
            blocked_by: 阻塞此任务的其他任务 ID。
            created_by: 创建者。

        Returns:
            新创建的 SharedTask 实例。
        """
        task_id = str(self._next_id)
        self._next_id += 1
        task = SharedTask(
            id=task_id,
            title=title,
            description=description,
            assignee=assignee,
            blocks=blocks or [],
            blocked_by=blocked_by or [],
            created_by=created_by,
        )
        self._tasks[task_id] = task
        self._save()
        return task

    def get(self, task_id: str) -> SharedTask | None:
        """获取指定 ID 的任务（先重新从磁盘加载）。

        Args:
            task_id: 任务 ID。

        Returns:
            SharedTask 实例，不存在则返回 None。
        """
        self._load()
        return self._tasks.get(task_id)


    def list_tasks(
        self,
        status: str | None = None,
        assignee: str | None = None,
    ) -> list[SharedTask]:
        """列出任务，可按状态和负责人筛选。

        Args:
            status: 按状态筛选（可选）。
            assignee: 按负责人筛选（可选）。

        Returns:
            符合条件的 SharedTask 列表。
        """
        self._load()
        result = list(self._tasks.values())
        if status:
            result = [t for t in result if t.status == status]
        if assignee:
            result = [t for t in result if t.assignee == assignee]
        return result


    def update(
        self,
        task_id: str,
        status: str | None = None,
        assignee: str | None = None,
        description: str | None = None,
        add_blocks: list[str] | None = None,
        add_blocked_by: list[str] | None = None,
    ) -> SharedTask | None:
        """更新指定任务的字段。

        Args:
            task_id: 任务 ID。
            status: 新状态（可选）。
            assignee: 新负责人（可选）。
            description: 新描述（可选）。
            add_blocks: 追加阻塞对象（可选）。
            add_blocked_by: 追加上游依赖（可选）。

        Returns:
            更新后的 SharedTask，任务不存在则返回 None。
        """
        self._load()
        task = self._tasks.get(task_id)
        if task is None:
            return None
        if status is not None:
            task.status = status
        if assignee is not None:
            task.assignee = assignee
        if description is not None:
            task.description = description
        if add_blocks:
            for bid in add_blocks:
                if bid not in task.blocks:
                    task.blocks.append(bid)
        if add_blocked_by:
            for bid in add_blocked_by:
                if bid not in task.blocked_by:
                    task.blocked_by.append(bid)
        self._save()
        return task

    def init_empty(self) -> None:
        """初始化空的任务存储（清空所有任务并重置 ID 计数器）。"""
        self._tasks.clear()
        self._next_id = 1
        self._save()
