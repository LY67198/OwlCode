"""MCP 管理器：管理多个 MCP 服务器的配置、连接和工具注册。"""

from __future__ import annotations

import logging

from owlcode.config import MCPServerConfig
from owlcode.mcp.client import MCPClient
from owlcode.mcp.tool_wrapper import MCPToolWrapper
from owlcode.tools import ToolRegistry

logger = logging.getLogger(__name__)


class MCPManager:
    """MCP 管理器，负责加载配置、连接多个 MCP 服务器并注册其工具。"""

    def __init__(self) -> None:
        self._configs: dict[str, MCPServerConfig] = {}
        self._clients: dict[str, MCPClient] = {}

    def load_configs(self, configs: list[MCPServerConfig]) -> None:
        """加载 MCP 服务器配置列表。

        Args:
            configs: MCPServerConfig 配置对象列表。
        """
        for cfg in configs:
            self._configs[cfg.name] = cfg

    async def register_all_tools(self, registry: ToolRegistry) -> list[str]:
        """连接所有已配置的 MCP 服务器并将其工具注册到 ToolRegistry。

        Args:
            registry: 目标工具注册表。

        Returns:
            连接或注册过程中遇到的错误信息列表。
        """
        errors: list[str] = []
        for name, config in self._configs.items():
            try:
                client = MCPClient(config)
                await client.connect()
                self._clients[name] = client

                tools = await client.list_tools()
                for tool_def in tools:
                    wrapper = MCPToolWrapper(name, tool_def, client)
                    registry.register(wrapper)
                    logger.info("Registered MCP tool: %s", wrapper.name)

            except Exception as e:
                msg = f"MCP server '{name}': {e}"
                logger.warning(msg)
                errors.append(msg)

        return errors

    async def get_client(self, name: str) -> MCPClient | None:
        """获取或懒创建指定名称的 MCP 客户端。

        如果连接已断开会自动重连。

        Args:
            name: MCP 服务器名称。

        Returns:
            MCPClient 实例，配置不存在时返回 None。
        """
        client = self._clients.get(name)
        if client is None:
            config = self._configs.get(name)
            if config is None:
                return None
            client = MCPClient(config)
            await client.connect()
            self._clients[name] = client
            return client

        if not client.is_alive:
            logger.info("Reconnecting MCP server '%s'", name)
            await client.close()
            client = MCPClient(self._configs[name])
            await client.connect()
            self._clients[name] = client

        return client

    async def shutdown(self) -> None:
        """关闭所有 MCP 客户端连接并清理资源。"""
        for name, client in self._clients.items():
            try:
                await client.close()
                logger.info("MCP server '%s' closed", name)
            except Exception:
                logger.debug("Error closing MCP server '%s'", name, exc_info=True)
        self._clients.clear()
