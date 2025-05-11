import os
import json
from typing import Dict, Any
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from mcp.server import Tool, ToolCall, ToolResponse
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

GOOGLE_API_KEY= os.getenv('GOOGLE_API_KEY')
                          


class YouTubeUploadTool(Tool):
    """MCP Tool for YouTube video management using YouTube Data API v3"""
    
    @property
    def tool_name(self) -> str:
        return "YouTubeUploader"
    
    def __init__(self):
        self.credentials = None
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize YouTube API service with OAuth2 credentials"""
        creds = None
        token_file = os.getenv('GOOGLE_TOKEN_PATH', 'token.json')
        
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    os.getenv('GOOGLE_CLIENT_SECRETS_PATH', 'client_secrets.json'),
                    scopes=['https://www.googleapis.com/auth/youtube.upload']
                )
                creds = flow.run_local_server(port=0)
            
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('youtube', 'v3', credentials=creds)
    
    def upload_video(self, call: ToolCall) -> ToolResponse:
        params = call.parameters
        try:
            request = self.service.videos().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": params.get("title"),
                        "description": params.get("description"),
                        "tags": params.get("tags", []),
                        "categoryId": params.get("categoryId", "22")
                    },
                    "status": {
                        "privacyStatus": params.get("privacyStatus", "private")
                    }
                },
                media_body=params["file_path"]
            )
            response = request.execute()
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=True,
                result=response
            )
        except Exception as e:
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=False,
                error=str(e)
            )
    
    def set_thumbnail(self, call: ToolCall) -> ToolResponse:
        params = call.parameters
        try:
            request = self.service.thumbnails().set(
                videoId=params["videoId"],
                media_body=params["thumbnail_path"]
            )
            response = request.execute()
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=True,
                result=response
            )
        except Exception as e:
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=False,
                error=str(e)
            )
    
    # Additional methods for playlist management and metadata updates