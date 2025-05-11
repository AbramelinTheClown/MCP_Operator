# Noun Project Icon Downloader MCP Tool

This repository contains a Python-based Model Context Protocol (MCP) tool designed to allow a Large Language Model (LLM) to interact with The Noun Project API for searching and downloading icons.

## What is this Tool?

This code implements a `Tool` class following the `mcp` framework conventions. It acts as an intermediary between an LLM capable of using MCP tools and the external API of The Noun Project. It exposes specific functionalities (searching and downloading icons) as structured functions that the LLM can call with specified parameters.

The tool handles:
* Receiving structured function calls from the LLM.
* Authenticating with The Noun Project API using OAuth1.
* Constructing and sending HTTP requests to the API.
* Parsing API responses (JSON).
* Returning results or detailed error messages back to the LLM in the `ToolResponse` format.

## Features

This tool exposes the following capabilities to the LLM:

1.  **`search_icons`**: Search The Noun Project library for icons based on a query and optional filters.
2.  **`download_icon`**: Download a specific icon by its unique ID, with options for file format, color, and size.

## Prerequisites

To use this MCP tool, you need:

1.  **Python 3.6+**: The code is written in Python.
2.  **Required Python Libraries**: `requests` and `requests-oauthlib`. These handle the HTTP communication and OAuth authentication.
3.  **An Noun Project API Account**: You need a developer account from The Noun Project to obtain API credentials (Client Key and Client Secret). You can sign up and find your keys on their developer website.
4.  **An MCP-compatible LLM Environment**: This tool is designed to be integrated into a larger system or framework that hosts the LLM and manages MCP tool calls.

## Installation

1.  **Save the Code:** Save the provided Python code as a file, for example, `noun_project_tool.py`.
2.  **Install Dependencies:** Install the required Python libraries using pip:
    ```bash
    pip install requests requests-oauthlib
    ```
    *(Note: The `mcp` library is assumed to be part of your LLM environment's infrastructure and typically doesn't need separate installation for the tool code itself, but is required for the tool definition classes like `Tool`, `ToolFunction`, `ToolCall`, `ToolResponse`.)*

## Configuration (API Credentials)

This tool requires your Noun Project API credentials (`Client Key` and `Client Secret`) for authentication. For security reasons, these are read from environment variables.

You **must** set the following environment variables:

* `NOUN_PROJECT_CLIENT_KEY`: Your Noun Project Client Key.
* `NOUN_PROJECT_CLIENT_SECRET`: Your Noun Project Client Secret.

**How to set environment variables:**

* **On Linux/macOS (Bash/Zsh):**
    ```bash
    export NOUN_PROJECT_CLIENT_KEY="YOUR_CLIENT_KEY"
    export NOUN_PROJECT_CLIENT_SECRET="YOUR_CLIENT_SECRET"
    # To make them permanent, add these lines to your shell's profile file (~/.bashrc, ~/.zshrc, etc.)
    ```
* **On Windows (Command Prompt):**
    ```cmd
    set NOUN_PROJECT_CLIENT_KEY="YOUR_CLIENT_KEY"
    set NOUN_PROJECT_CLIENT_SECRET="YOUR_CLIENT_SECRET"
    # For permanent variables, use System Properties -> Environment Variables
    ```
* **On Windows (PowerShell):**
    ```powershell
    $env:NOUN_PROJECT_CLIENT_KEY="YOUR_CLIENT_KEY"
    $env:NOUN_PROJECT_CLIENT_SECRET="YOUR_CLIENT_SECRET"
    # For permanent variables, use System Properties -> Environment Variables
    ```

Replace `"YOUR_CLIENT_KEY"` and `"YOUR_CLIENT_SECRET"` with your actual credentials obtained from The Noun Project developer portal.

## Usage (How the LLM Operates the Tool)

This tool is not run directly by a human user. Instead, it is integrated into an MCP-compatible LLM environment, which provides the code object (`NounProjectTool` instance) to the LLM. The LLM, when it determines a user's request requires interacting with The Noun Project, will generate a structured "tool call" referencing one of the defined functions (`search_icons` or `download_icon`) and providing the necessary parameters.

Here's a description of the functions the LLM can call and their parameters:

### 1. `search_icons`

* **Description:** Search for icons by query and filter by style/line weight.
* **Parameters:**
    * `query` (string, **required**): The main search terms for the icons.
    * `styles` (array of strings, optional): Filter results by style. Accepted values are `"solid"` or `"line"`. Can provide one or both in an array (e.g., `["solid", "line"]`).
    * `line_weight` (string, optional): Filter line icons by weight. This parameter is only considered if `"line"` is included in the `styles` array. Accepts an integer (1-60) or a range string (e.g., `"5-10"`).
    * `limit` (integer, optional): Maximum number of search results to return. Defaults to 20. The tool caps this at 100 to avoid excessively large responses.

* **LLM Call Example (Conceptual):**
    ```json
    {
      "tool_name": "NounProjectIconDownloader",
      "function_name": "search_icons",
      "parameters": {
        "query": "cat",
        "styles": ["line"],
        "line_weight": "3",
        "limit": 10
      }
    }
    ```

* **Tool Response:** If successful, returns a `ToolResponse` with `is_successful=True` and a `result` dictionary containing:
    * `icons` (list): A list of dictionaries, where each dictionary represents an icon with details like `id`, `term`, `preview_url`, `permalink`, `attribution`, `styles`, `tags`, and `license`.
    * `count` (integer): The number of icons returned in the current response.
    * `total` (integer): The total number of icons matching the search query (according to the API).

### 2. `download_icon`

* **Description:** Download an icon by its numeric ID, with options for format, color, and size.
* **Parameters:**
    * `icon_id` (integer, **required**): The unique numeric ID of the icon to download. This ID is typically obtained from the results of a `search_icons` call.
    * `filetype` (string, **required**): The desired file format. Accepted values are `"png"` or `"svg"`.
    * `color` (string, optional): A hexadecimal color code (e.g., `"FF0000"` for red) to recolor the icon.
    * `size` (integer, optional): The size in pixels for PNG downloads. Only applicable if `filetype` is `"png"`. Accepted range is typically 20-1200.

* **LLM Call Example (Conceptual):**
    ```json
    {
      "tool_name": "NounProjectIconDownloader",
      "function_name": "download_icon",
      "parameters": {
        "icon_id": 12345,
        "filetype": "png",
        "color": "0000FF",
        "size": 200
      }
    }
    ```

* **Tool Response:** If successful, returns a `ToolResponse` with `is_successful=True` and a `result` dictionary containing:
    * `icon_id` (integer): The ID of the downloaded icon.
    * `filetype` (string): The requested file type.
    * `content_type` (string): The MIME type of the returned data (e.g., `image/png`, `image/svg+xml`).
    * `data` (string): The base64 encoded content of the icon file.

## Error Handling

The tool returns a `ToolResponse` with `is_successful=False` and an `error` string when an operation fails. The LLM should be capable of checking the `is_successful` flag and presenting the `error` message to the user or attempting corrective actions.

Possible errors reported by the tool include:

* `Missing API credentials`: The `NOUN_PROJECT_CLIENT_KEY` or `NOUN_PROJECT_CLIENT_SECRET` environment variables are not set.
* `Search failed: [error details]`: An error occurred during the search API request (e.g., network issue, invalid parameters not caught by LLM validation, API error). The details from the underlying exception are included.
* `Download failed: [error details]`: An error occurred during the download API request.
* `No image data in response`: The download API call was successful according to HTTP status, but the expected base64 encoded image data was missing from the response body.

The LLM is responsible for interpreting these errors and responding appropriately to the user.

## Integration

To integrate this tool into your MCP environment:

1.  Ensure the `noun_project_tool.py` file is accessible to your MCP runner.
2.  Set the required environment variables (`NOUN_PROJECT_CLIENT_KEY`, `NOUN_PROJECT_CLIENT_SECRET`) in the environment where the MCP runner operates.
3.  Instantiate the `NounProjectTool` class and register it with your MCP framework's tool discovery or registration mechanism.
4.  The LLM should then be able to see and utilize the `NounProjectIconDownloader` tool with its `search_icons` and `download_icon` functions based on the schema definition.