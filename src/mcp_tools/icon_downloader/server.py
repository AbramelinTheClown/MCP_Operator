from mcp import AgentServer
from .noun_project_tool import NounProjectTool

def create_server():
    # Initialize agent server with default configuration
    agent_server = AgentServer(
        host = os.environ.get("MCP_HOST", "0.0.0.0"),
        port = int(os.environ.get("MCP_PORT", 5002)),
        tool_modules=["mcp_tools.icon_downloader"]
    )
    
    # Create and register our tool instance
    icon_tool = NounProjectTool()
    agent_server.register_tool(icon_tool)
    
    return agent_server

if __name__ == "__main__":
    server = create_server()
    print("Starting Noun Project Icon Downloader server...")
    server.run()