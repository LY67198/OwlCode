from __future__ import annotations

import threading


class FileCache:
    """线程安全的文件内容缓存，用于缓存文件读取结果。"""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._lock = threading.Lock()

    def get(self, path: str) -> str | None:
        """根据文件路径获取缓存的内容。

        Args:
            path: 文件路径。

        Returns:
            缓存的文件内容，未命中则返回 None。
        """
        with self._lock:
            return self._store.get(path)

    def put(self, path: str, content: str) -> None:
        """将文件内容存入缓存。

        Args:
            path: 文件路径。
            content: 文件内容字符串。
        """
        with self._lock:
            self._store[path] = content

    def invalidate(self, path: str) -> None:
        """使指定路径的缓存条目失效。

        Args:
            path: 要移除缓存的文件的路径。
        """
        with self._lock:
            self._store.pop(path, None)

    def clear(self) -> None:
        """清空所有缓存条目。"""
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)
