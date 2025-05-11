# src/mcp_tools/image_search/tools.py
from mcp import ToolCall, ToolResponse, Tool
import requests
import os
from typing import Dict, Any, List

# Google Custom Search API Endpoint

                                   
# Read API Key and Custom Search Engine ID from environment variables
GOOGLE_CSE_API_URL =os.environ.get("GOOGLE_CSE_API_URL")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_SEARCH_LUMINA_ALPHA_ID")


class ImageSearchTool(Tool):
    """
    A Model Context Protocol Tool for searching for images using an external API
    like Google Custom Search.
    """

    @property
    def tool_name(self) -> str:
        """The name of the tool as it will be registered with the server."""
        return "ImageSearchTool"

    def search_images(self, call: ToolCall) -> ToolResponse:
        """
        Searches for images based on a query using Google Custom Search API.

        Expected parameters in ToolCall.parameters:
        - query: str (Required) - The search query (e.g., "Orion Nebula Hubble").
        - num_results: int (Optional) - The number of image results to return (max 10 per API call). Defaults to 5.
        - safe_search: str (Optional) - Safe search level ('active', 'off'). Defaults to 'active'.
        - site_restrict: str (Optional) - Limit search to a specific site (e.g., "hubblesite.org").

        Returns:
            A ToolResponse object containing a list of image results or an error.
            Success result is a list of dictionaries, each representing an image:
            [{"title": "...", "url": "...", "source_url": "...", "width": ..., "height": ...}]
        """
        if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
             return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=False,
                error="Google API Key or CSE ID is not configured in environment variables."
            )

        # 1. Validate and extract parameters from ToolCall
        params = call.parameters

        query = params.get("query")
        num_results = int(params.get("num_results", 5))
        safe_search = params.get("safe_search", "active")
        site_restrict = params.get("site_restrict")


        if not query:
             return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=False,
                error="Missing required parameter: query."
            )

        if not isinstance(num_results, int) or not (1 <= num_results <= 10):
             return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=False,
                error="Invalid num_results. Must be an integer between 1 and 10."
            )

        if safe_search not in ['active', 'off']:
             return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=False,
                error="Invalid safe_search. Must be 'active' or 'off'."
            )


        # 2. Prepare API request parameters
        api_params: Dict[str, Any] = {
            "key": GOOGLE_API_KEY,
            "cx": GOOGLE_CSE_ID,
            "q": query,
            "searchType": "image", # Specify image search
            "num": num_results, # Number of results (max 10 per API call)
            "safe": safe_search, # Safe search setting
        }

        if site_restrict:
            api_params["siteSearch"] = site_restrict


        try:
            # 3. Make the HTTP request to the API
            print(f"Searching for images with query: '{query}'")
            response = requests.get(GOOGLE_CSE_API_URL, params=api_params)
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

            # 4. Parse the JSON response
            data = response.json()

            # Check if 'items' (results) are present
            items = data.get("items", [])

            # Extract relevant information from results
            image_results: List[Dict[str, Any]] = []
            for item in items:
                image_results.append({
                    "title": item.get("title"),
                    "url": item.get("link"), # Direct image URL
                    "source_url": item.get("image", {}).get("contextLink"), # URL of the page the image is on
                    "width": item.get("image", {}).get("width"),
                    "height": item.get("image", {}).get("height"),
                    # Add other fields like thumbnail, file format if needed
                })


            # 5. Format and return the result in a ToolResponse
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=True,
                result={"images": image_results}
            )

        except requests.exceptions.RequestException as e:
            print(f"HTTP or network error fetching images: {e}")
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=False,
                error=f"Network or HTTP error fetching images: {e}"
            )
        except Exception as e:
            print(f"An unexpected error occurred in search_images: {e}")
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=False,
                error=f"An internal server error occurred: {e}"
            )

    # Add other methods related to image search if needed (e.g., reverse_image_search)