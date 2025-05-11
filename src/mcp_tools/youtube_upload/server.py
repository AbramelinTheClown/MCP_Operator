from mcp import AgentServer
from .youtube_tool import YouTubeUploadTool

def create_server():
    agent_server = AgentServer(
        host="0.0.0.0",
        port=5004,
        tool_modules=["mcp_tools.youtube_upload"]
    )
    
    youtube_tool = YouTubeUploadTool()
    agent_server.register_tool(youtube_tool)
    
    return agent_server

if __name__ == "__main__":
    server = create_server()
    print("YouTube Upload MCP Server running on port 5004")
    server.run()