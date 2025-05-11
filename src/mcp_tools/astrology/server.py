# src/mcp_tools/astrology/server.py
from js2py import require
Server = require('@modelcontextprotocol/server')
from .tools import AstrologyTool # Import from the same directory
import os
import asyncio

def main():
    # Configuration specific to this server (read from environment variables)
    # The API key is read directly in tools.py, but host/port are here
    host = os.environ.get("MCP_HOST", "0.0.0.0") # Listen on all interfaces inside container
    port = int(os.environ.get("MCP_PORT", 5001)) # Choose a unique port, e.g., 5001

    # Initialize the specific tool(s) this server hosts
    astrology_tool = AstrologyTool()

    # Create and start the MCP server instance
    server = Server(host=host, port=port)
    server.register_tool(astrology_tool)

    print(f"Starting {astrology_tool.tool_name} MCP server on {host}:{port}")

    try:
        asyncio.run(server.start()) # server.start() is async
    except KeyboardInterrupt:
        print("Shutting down server...")
        asyncio.run(server.stop()) # Call stop() when interrupted
    except Exception as e:
         print(f"Server crashed: {e}")


if __name__ == "__main__":
    main()
