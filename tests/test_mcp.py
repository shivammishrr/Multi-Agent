import json
import pytest
from multi_agent.integrations.mcp.client import MCPClient


class TestMCPClient:
    def test_init(self):
        client = MCPClient(command="python -m my_server")
        assert client._command == "python -m my_server"
        assert client._tools == []

    def test_init_http(self):
        client = MCPClient(url="http://localhost:8080")
        assert client._url == "http://localhost:8080"

    @pytest.mark.asyncio
    async def test_init_no_transport(self):
        client = MCPClient()
        with pytest.raises(ValueError, match="command or url"):
            await client.connect()

    def test_parse_tools(self):
        client = MCPClient(command="test")
        resp = {
            "result": {
                "tools": [
                    {
                        "name": "calculator",
                        "description": "Do math",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"x": {"type": "integer"}},
                        },
                    },
                    {
                        "name": "search",
                        "description": "Search the web",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                ]
            }
        }
        client._parse_tools(resp)
        assert len(client.tools) == 2
        assert client.tools[0].name == "calculator"
        assert client.tools[1].name == "search"

    def test_parse_tools_none(self):
        client = MCPClient(command="test")
        client._parse_tools(None)
        assert client.tools == []
