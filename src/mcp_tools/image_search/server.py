# src/mcp_tools/image_search/server.py
from mcp.server import Server
from .tools import ImageSearchTool # Import from the same directory
import os
import asyncio

def main():
    # Configuration specific to this server (read from environment variables)
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", 5003)) # Get port from environment

    # Initialize the specific tool(s) this server hosts
    image_search_tool = ImageSearchTool()

    # Create and start the MCP server instance
    server = Server(host=host, port=port)
    server.register_tool(image_search_tool)

    print(f"Starting {image_search_tool.tool_name} MCP server on {host}:{port}")

    try:
        asyncio.run(server.start()) # server.start() is async
    except KeyboardInterrupt:
        print("Shutting down server...")
        asyncio.run(server.stop()) # Call stop() when interrupted
    except Exception as e:
         print(f"Server crashed: {e}")

if __name__ == "__main__":
    main()