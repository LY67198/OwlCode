"""文件编辑历史跟踪：自动备份编辑的文件并支持回退到历史快照。"""

from __future__ import annotations

import hashlib
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

MAX_SNAPSHOTS = 100


@dataclass
class Backup:
    """单次文件备份记录。"""
    backup_path: str
    version: int
    timestamp: float


@dataclass
class Snapshot:
    """一次对话轮次的文件快照集合。"""
    message_index: int
    user_text: str
    backups: dict[str, Backup] = field(default_factory=dict)
    timestamp: float = 0.0


class FileHistory:
    """文件历史管理器，跟踪文件编辑并支持快照回退。

    每次 track_edit 会保存文件的新版本，make_snapshot 会创建设定点。
    可通过 rewind 回退到历史快照。
    """

    def __init__(self, base_dir: str, session_id: str) -> None:
        self._session_dir = Path(base_dir) / ".owlcode" / "file-history" / session_id
        self._session_dir.mkdir(parents=True, exist_ok=True)
        self._tracked: dict[str, int] = {}
        self._snapshots: list[Snapshot] = []
        self._lock = threading.Lock()

    def _backup_name(self, file_path: str, version: int) -> str:
        """为文件备份生成唯一名称。

        Args:
            file_path: 原始文件路径。
            version: 版本号。

        Returns:
            格式为 "{hash}@v{version}" 的备份文件名。
        """
        h = hashlib.sha256(file_path.encode()).hexdigest()[:16]
        return f"{h}@v{version}"

    def track_edit(self, path: str) -> None:
        """记录一次文件编辑，自动创建备份。

        Args:
            path: 被编辑的文件路径。
        """
        with self._lock:
            abs_path = str(Path(path).resolve())
            ver = self._tracked.get(abs_path, 0)
            new_ver = ver + 1

            try:
                data = Path(abs_path).read_bytes()
                bp = self._session_dir / self._backup_name(abs_path, new_ver)
                bp.write_bytes(data)
            except FileNotFoundError:
                pass

            self._tracked[abs_path] = new_ver

    def make_snapshot(self, msg_index: int, user_text: str) -> None:
        """为当前所有跟踪的文件创建一个快照。

        Args:
            msg_index: 消息索引，用于关联对话轮次。
            user_text: 用户输入的文本内容。
        """
        with self._lock:
            backups: dict[str, Backup] = {}
            for path, ver in self._tracked.items():
                bp = self._session_dir / self._backup_name(path, ver)
                if not bp.exists():
                    try:
                        data = Path(path).read_bytes()
                        bp.write_bytes(data)
                    except (FileNotFoundError, OSError):
                        pass
                backups[path] = Backup(
                    backup_path=str(bp), version=ver, timestamp=time.time(),
                )

            self._snapshots.append(Snapshot(
                message_index=msg_index,
                user_text=user_text,
                backups=backups,
                timestamp=time.time(),
            ))
            if len(self._snapshots) > MAX_SNAPSHOTS:
                self._snapshots = self._snapshots[-MAX_SNAPSHOTS:]

    def get_snapshots(self) -> list[Snapshot]:
        """获取所有快照的列表。

        Returns:
            Snapshot 对象列表，按时间排序。
        """
        with self._lock:
            return list(self._snapshots)

    def has_snapshots(self) -> bool:
        """检查是否存在任何快照。

        Returns:
            存在快照时返回 True。
        """
        with self._lock:
            return len(self._snapshots) > 0

    def rewind(self, snapshot_index: int) -> list[str]:
        """回退到指定的快照，恢复目标快照中所有文件的版本。

        当前快照索引之后的所有快照将被丢弃，文件跟踪状态也会同步回退。

        Args:
            snapshot_index: 目标快照在列表中的索引。

        Returns:
            被修改的文件路径列表。
        """
        with self._lock:
            if snapshot_index < 0 or snapshot_index >= len(self._snapshots):
                return []

            target = self._snapshots[snapshot_index]
            changed: list[str] = []

            for file_path, backup in target.backups.items():
                bp = Path(backup.backup_path)
                try:
                    backup_data = bp.read_bytes()
                except FileNotFoundError:
                    fp = Path(file_path)
                    if fp.exists():
                        fp.unlink()
                        changed.append(file_path)
                    continue

                fp = Path(file_path)
                try:
                    current_data = fp.read_bytes()
                except FileNotFoundError:
                    current_data = b""

                if current_data != backup_data:
                    fp.parent.mkdir(parents=True, exist_ok=True)
                    fp.write_bytes(backup_data)
                    changed.append(file_path)

            self._snapshots = self._snapshots[: snapshot_index + 1]
            for file_path, backup in target.backups.items():
                self._tracked[file_path] = backup.version

            return changed
