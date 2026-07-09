"""MCP 客户端：管理与单个 MCP 服务器的连接和通信。"""

from __future__ import annotations

import logging
import os
from contextlib import AsyncExitStack
from typing import Any

import httpx
from mcp import ClientSession, types
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client

from owlcode.config import MCPServerConfig, build_child_env, resolve_env_vars

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP 客户端，负责建立和维护与一个 MCP 服务器的连接。

    支持 stdio（子进程）和 HTTP 两种传输方式。
    """

    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self.name = config.name
        self._session: ClientSession | None = None
        self._stack: AsyncExitStack | None = None
        self._alive = False

    @property
    def is_alive(self) -> bool:
        """连接是否处于活跃状态。"""
        return self._alive

    async def connect(self) -> None:
        """建立与 MCP 服务器的连接并初始化会话。

        根据配置自动选择 stdio 或 HTTP 传输方式。
        """
        if self._alive:
            return

        self._stack = AsyncExitStack()
        await self._stack.__aenter__()

        try:
            if self.config.is_stdio:
                read, write = await self._connect_stdio()
            else:
                read, write = await self._connect_http()

            session = await self._stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            self._session = session
            self._alive = True
            logger.info("MCP server '%s' connected", self.name)
        except Exception:
            await self._cleanup_stack()
            raise

    async def _connect_stdio(self) -> tuple[Any, Any]:
        """通过 stdio 子进程方式连接 MCP 服务器。

        Returns:
            (read_stream, write_stream) 元组。
        """
        assert self._stack is not None
        assert self.config.command is not None

        params = StdioServerParameters(
            command=self.config.command,
            args=self.config.args,
            env=build_child_env(self.config.env),
        )
        devnull = open(os.devnull, "w")
        self._stack.callback(devnull.close)
        read, write = await self._stack.enter_async_context(
            stdio_client(params, errlog=devnull)
        )
        return read, write

    async def _connect_http(self) -> tuple[Any, Any]:
        """通过 HTTP（streamable HTTP）方式连接 MCP 服务器。

        Returns:
            (read_stream, write_stream) 元组。
        """
        assert self._stack is not None
        assert self.config.url is not None

        resolved_headers = {
            k: resolve_env_vars(v) for k, v in self.config.headers.items()
        }
        http_client = httpx.AsyncClient(
            headers=resolved_headers,
            follow_redirects=True,
        )
        await self._stack.enter_async_context(http_client)

        result = await self._stack.enter_async_context(
            streamable_http_client(self.config.url, http_client=http_client)
        )
        read, write = result[0], result[1]
        return read, write

    async def list_tools(self) -> list[types.Tool]:
        """获取 MCP 服务器提供的工具列表。

        Returns:
            MCP Tool 对象列表。
        """
        assert self._session is not None
        result = await self._session.list_tools()
        return list(result.tools)

    async def call_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> types.CallToolResult:
        """调用 MCP 服务器上的指定工具。

        Args:
            name: 工具名称。
            arguments: 工具调用参数。

        Returns:
            MCP 工具调用结果。
        """
        assert self._session is not None
        return await self._session.call_tool(name, arguments)

    async def close(self) -> None:
        """关闭与 MCP 服务器的连接并清理资源。"""
        self._alive = False
        self._session = None
        await self._cleanup_stack()

    async def _cleanup_stack(self) -> None:
        """清理 AsyncExitStack，安全关闭所有异步上下文。"""
        if self._stack is not None:
            try:
                await self._stack.__aexit__(None, None, None)
            except RuntimeError as e:
                if "cancel scope" in str(e):
                    logger.debug("Cancel scope cleanup (expected during shutdown): %s", e)
                else:
                    raise
            except Exception:
                logger.debug("Error closing stack for '%s'", self.name, exc_info=True)
            self._stack = None
