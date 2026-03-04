import contextlib
import os
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

class KaliMCPClient:
    def __init__(self, command: str, args: list):
        self.command = command
        self.args = args
        self.session = None
        self._exit_stack = contextlib.AsyncExitStack()
        self._initialized = False

    async def connect(self):
        if self._initialized:
            return
        
        try:
            server_params = StdioServerParameters(
                command=self.command,
                args=self.args,
                env=None
            )
            streams = await self._exit_stack.enter_async_context(stdio_client(server_params))
            self.session = await self._exit_stack.enter_async_context(ClientSession(streams[0], streams[1]))
            await self.session.initialize()
            self._initialized = True
            print(f"Connected to MCP Server via stdio: {self.command} {' '.join(self.args)}")
        except Exception as e:
            print(f"Failed to connect via stdio: {e}")
            raise

    async def get_tools(self):
        if not self._initialized:
            await self.connect()
        # Returns mcp.types.ListToolsResult
        return await self.session.list_tools()

    async def call_tool(self, name: str, arguments: dict):
        if not self._initialized:
            await self.connect()
        # Returns mcp.types.CallToolResult
        return await self.session.call_tool(name, arguments=arguments)

    async def close(self):
        await self._exit_stack.aclose()
        self._initialized = False
