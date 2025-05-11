import os
import requests
from requests_oauthlib import OAuth1
from typing import Dict, Any, List, Optional
from mcp import ToolCall, ToolResponse, Tool, ToolFunction

NOUN_PROJECT_CLIENT_KEY = os.environ.get("NOUN_PROJECT_CLIENT_KEY")
NOUN_PROJECT_CLIENT_SECRET = os.environ.get("NOUN_PROJECT_CLIENT_SECRET")
NOUN_PROJECT_BASE_URL = "https://api.thenounproject.com"

class NounProjectTool(Tool):
    """
    A Model Context Protocol Tool for interacting with The Noun Project API
    to search for and download icons.
    """

    @property
    def tool_name(self) -> str:
        return "NounProjectIconDownloader"

    @property
    def functions(self) -> List[ToolFunction]:
        return [
            ToolFunction(
                name="search_icons",
                description="Search for icons by query and filter by style/line weight",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "styles": {"type": "array", "items": {"type": "string", "enum": ["solid", "line"]}},
                        "line_weight": {"type": "string", "description": "Line weight filter (1-60 or range)"},
                        "limit": {"type": "integer", "description": "Max results (default 20)"}
                    },
                    "required": ["query"]
                }
            ),
            ToolFunction(
                name="download_icon",
                description="Download icon by ID with format/color/size options",
                parameters={
                    "type": "object",
                    "properties": {
                        "icon_id": {"type": "integer", "description": "Numeric icon ID"},
                        "filetype": {"type": "string", "enum": ["png", "svg"]},
                        "color": {"type": "string", "description": "Hex color code"},
                        "size": {"type": "integer", "description": "PNG size (20-1200)"}
                    },
                    "required": ["icon_id", "filetype"]
                }
            )
        ]

    def _get_auth(self):
        if not NOUN_PROJECT_CLIENT_KEY or not NOUN_PROJECT_CLIENT_SECRET:
            return None
        return OAuth1(NOUN_PROJECT_CLIENT_KEY, NOUN_PROJECT_CLIENT_SECRET)

    def search_icons(self, call: ToolCall) -> ToolResponse:
        # Implementation matches provided spec
        auth = self._get_auth()
        if not auth:
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=False,
                error="Missing API credentials"
            )
        
        params = call.parameters
        try:
            response = requests.get(
                f"{NOUN_PROJECT_BASE_URL}/v2/icon",
                params=self._build_search_params(params),
                auth=auth
            )
            response.raise_for_status()
            return self._parse_search_response(response, call.tool_call_id)
        except Exception as e:
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=False,
                error=f"Search failed: {str(e)}"
            )

    def download_icon(self, call: ToolCall) -> ToolResponse:
        # Implementation matches provided spec
        auth = self._get_auth()
        if not auth:
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=False,
                error="Missing API credentials"
            )
        
        params = call.parameters
        try:
            response = requests.get(
                f"{NOUN_PROJECT_BASE_URL}/v2/icon/{params['icon_id']}/download",
                params=self._build_download_params(params),
                auth=auth
            )
            response.raise_for_status()
            return self._parse_download_response(response, call.tool_call_id, params)
        except Exception as e:
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=False,
                error=f"Download failed: {str(e)}"
            )

    def _build_search_params(self, params: Dict) -> Dict:
        api_params = {
            "query": params["query"],
            "limit": min(params.get("limit", 20), 100)
        }
        
        if styles := params.get("styles"):
            # Validate styles before joining
            valid_styles = [s for s in styles if s in ("solid", "line")]
            api_params["styles"] = ",".join(valid_styles)
            
            if "line" in valid_styles and (lw := params.get("line_weight")):
                # Validate line weight format
                if isinstance(lw, int) and 1 <= lw <= 60:
                    api_params["line_weight"] = str(lw)
                elif "-" in str(lw):
                    parts = str(lw).split("-")
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        api_params["line_weight"] = f"{parts[0]}-{parts[1]}"
        
        return api_params

    def _parse_search_response(self, response, tool_call_id) -> ToolResponse:
        data = response.json()
        icons = [{
            "id": icon["id"],
            "term": icon["term"],
            "preview_url": icon["thumbnail_url"],
            "permalink": icon["permalink"],
            "attribution": icon["attribution"],
            "styles": [s["style"] for s in icon.get("styles", [])],
            "tags": [t["term"] for t in icon.get("tags", [])],
            "license": icon["license_description"]
        } for icon in data.get("icons", [])]
        
        return ToolResponse(
            tool_call_id=tool_call_id,
            is_successful=True,
            result={
                "icons": icons,
                "count": len(icons),
                "total": data.get("total", 0)
            }
        )

    def _build_download_params(self, params: Dict) -> Dict:
        dl_params = {"filetype": params["filetype"]}
        if color := params.get("color"):
            dl_params["color"] = color
        if params["filetype"] == "png" and (size := params.get("size")):
            dl_params["size"] = size
        return dl_params

    def _parse_download_response(self, response, tool_call_id, params) -> ToolResponse:
        data = response.json()
        if not (b64_data := data.get("base64_encoded_file")):
            return ToolResponse(
                tool_call_id=tool_call_id,
                is_successful=False,
                error="No image data in response"
            )
            
        return ToolResponse(
            tool_call_id=tool_call_id,
            is_successful=True,
            result={
                "icon_id": params["icon_id"],
                "filetype": params["filetype"],
                "content_type": data.get("content_type", "image/png"),
                "data": b64_data
            }
        )