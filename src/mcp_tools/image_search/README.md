# MCP Image Search Tool (`mcp_operator`)

This document provides a detailed explanation of the `ImageSearchTool`, a component of the `mcp_tools` toolbox designed to perform image searches using an external API via the Model Context Protocol (MCP). This tool specifically integrates with the Google Custom Search Engine (CSE) API to find images based on a query.

## Table of Contents

- [Purpose](#purpose)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Tool Name](#tool-name)
  - [Available Actions](#available-actions)
    - [`search_images`](#search_images)
- [Error Handling](#error-handling)
- [Dependencies](#dependencies)

## Purpose

The `ImageSearchTool` serves as an MCP interface to external image search services, primarily the Google Custom Search Engine API. It allows an MCP operator (and the models or clients using it) to programmatically search for images based on textual queries, retrieving details like image URLs, titles, and dimensions.

## Features

The `ImageSearchTool` currently provides the following functionality:

-   Perform a keyword-based image search using the Google Custom Search API.
-   Control the number of results returned.
-   Filter results based on safe search settings.
-   Restrict searches to a specific website.
-   Return structured data for each image result.

## Installation

This tool requires access to the Google Custom Search API. You will need to:

1.  Obtain a Google Cloud Platform API Key and enable the Custom Search API.
2.  Set up a Google Custom Search Engine configured to search the web or specific sites, and obtain its Search Engine ID (CSE ID). Crucially, ensure the CSE is configured to perform **Image Search**.
3.  Ensure you have Python 3.8+ installed.
4.  Install the required Python libraries:
    -   `mcp` (the Model Context Protocol SDK)
    -   `requests` (for making HTTP requests)

    You can install them using pip:
    ```bash
    pip install mcp requests
    ```
    *(Note: The exact package names might vary slightly; refer to your project's requirements file if available.)*

5.  Place the `tools.py` file in the correct location within your `mcp_tools` structure, typically `src/mcp_tools/image_search/tools.py`.
6.  Configure the necessary environment variables (see Configuration section).
7.  Ensure your MCP operator environment is set up to discover and register tools from this directory.

## Configuration

The `ImageSearchTool` requires the following environment variables to be set:

-   `GOOGLE_CSE_API_URL`: The base URL for the Google Custom Search API. This is typically `https://www.googleapis.com/customsearch/v1`.
    ```bash
    export GOOGLE_CSE_API_URL="[https://www.googleapis.com/customsearch/v1](https://www.googleapis.com/customsearch/v1)"
    ```
-   `GOOGLE_API_KEY`: Your Google Cloud Platform API Key with the Custom Search API enabled.
    ```bash
    export GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
    ```
-   `Google Search_LUMINA_ALPHA_ID`: The Search Engine ID (CSE ID) of your configured Google Custom Search Engine. The code currently uses `Google Search_LUMINA_ALPHA_ID` but is assigned to `GOOGLE_CSE_ID`. Ensure consistency or update the code/documentation accordingly. Assuming `Google Search_LUMINA_ALPHA_ID` is the correct environment variable name used externally:
    ```bash
    export Google Search_LUMINA_ALPHA_ID="YOUR_GOOGLE_CSE_ID"
    ```
    *(Self-correction: The code reads `os.environ.get("Google Search_LUMINA_ALPHA_ID")` into the `GOOGLE_CSE_ID` variable. The documentation should reflect the environment variable name actually used in the code.)*
    ```bash
    # Correct Environment Variable Name
    export Google Search_LUMINA_ALPHA_ID="YOUR_GOOGLE_CSE_ID"
    ```

If these environment variables are not set when the tool action is called, the tool will return an error.

## Usage

The `ImageSearchTool` is designed to be used within an MCP operator framework. Once registered with an MCP server, models or other clients can invoke its methods using `ToolCall` objects.

### Tool Name

The tool is registered with the name:
`ImageSearchTool`

### Available Actions

The `ImageSearchTool` currently exposes one action:

#### `search_images`

Searches for images based on a text query.

-   **Purpose:** Find images relevant to a given search term.
-   **Parameters:**
    -   `query`: `str` (Required) - The search query (e.g., `"Andromeda galaxy"`).
    -   `num_results`: `int` (Optional) - The desired number of image results. The Google Custom Search API limits this to a maximum of `10` per request. The tool validates this to be between 1 and 10. Defaults to `5`.
    -   `safe_search`: `str` (Optional) - Controls the safe search level. Supported values are `'active'` and `'off'`. Defaults to `'active'`.
    -   `site_restrict`: `str` (Optional) - Limits the search to images found on a specific domain (e.g., `"nasa.gov"`).
-   **Successful Response (`ToolResponse.result`):** A dictionary containing a list of image result dictionaries under the key `"images"`.
    ```json
    {
      "images": [
        {
          "title": "Title of the image",
          "url": "[http://example.com/path/to/image.jpg](http://example.com/path/to/image.jpg)", // Direct URL to the image file
          "source_url": "[http://example.com/page-where-image-is-found](http://example.com/page-where-image-is-found)", // URL of the page containing the image
          "width": 1280, // Image width in pixels (if available)
          "height": 720  // Image height in pixels (if available)
        },
        {
          // ... another image result
        }
        // ... up to num_results images
      ]
    }
    ```
    If no images are found, the `"images"` list will be empty.
-   **Error Response:** See [Error Handling](#error-handling).

## Error Handling

The `ImageSearchTool` returns a `ToolResponse` with `is_successful=False` and an `error` message string in the following cases:

-   Required environment variables (`GOOGLE_API_KEY`, `Google Search_LUMINA_ALPHA_ID`) are not set.
-   Required parameters (`query`) are missing in the `ToolCall`.
-   Optional parameters (`num_results`, `safe_search`) have invalid formats or values.
-   An HTTP or network error occurs while communicating with the Google Custom Search API (e.g., invalid API key, invalid CSE ID, network connectivity issues, API rate limits).
-   An unexpected internal error occurs within the tool.

The `error` string will provide a description of the issue, which the consuming LLM or client should be able to interpret.

## Dependencies

This tool requires the following Python libraries:

-   `mcp`
-   `requests`

Ensure these are installed in the environment where the MCP operator hosting this tool is running.