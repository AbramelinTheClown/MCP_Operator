Markdown

# MCP Astrology Tool (`mcp_operator`)

This document provides a detailed explanation of the `AstrologyTool`, a component of the `mcp_tools` toolbox designed to interact with astrological libraries via the Model Context Protocol (MCP). This tool allows an MCP operator to perform astrological calculations, generate visual charts, calculate relationship compatibility, and provide (placeholder) generic horoscopes and detailed reports.

## Table of Contents

- [Purpose](#purpose)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Tool Name](#tool-name)
  - [Available Actions](#available-actions)
    - [`generate_birth_chart_data`](#generate_birth_chart_data)
    - [`generate_visual_chart`](#generate_visual_chart)
    - [`generate_composite_chart`](#generate_composite_chart)
    - [`get_relationship_score`](#get_relationship_score)
    - [`get_generic_horoscope`](#get_generic_horoscope)
    - [`get_transits_over_time_range`](#get_transits_over_time_range)
    - [`generate_detailed_report`](#generate_detailed_report)
- [Output Directory](#output-directory)
- [Limitations and Future Work](#limitations-and-future-work)

## Purpose

The `AstrologyTool` integrates the powerful `immanuel` and `kerykeion` Python libraries into the MCP ecosystem. It acts as a bridge, allowing models or other MCP components to request astrological calculations, chart generation, and related insights without needing direct knowledge of the underlying library implementations.

## Features

The `AstrologyTool` provides the following functionalities:

-   Calculate detailed birth chart data (planetary positions, house cusps, aspects, dignities).
-   Generate visual SVG images of natal (birth) charts.
-   Generate visual SVG images of composite charts for two individuals.
-   Calculate a relationship compatibility score between two individuals.
-   Provide a placeholder for generic daily horoscopes by sign.
-   Calculate transiting aspects to a natal chart over a specified time range.
-   Provide a placeholder for generating detailed astrological reports.

## Installation

This tool is part of the larger `mcp_tools` project. To install and use it, you need to:

1.  Ensure you have Python 3.8+ installed.
2.  Install the required libraries. The core requirements for this tool are listed in the `consolidated_requirements.txt` (or potentially a specific requirements file for `mcp_tools`). These include:
    -   `mcp` (the Model Context Protocol SDK)
    -   `immanuel`
    -   `kerykeion`

    You can install them using pip:
    ```bash
    pip install mcp immanuel kerykeion
    ```
    *(Note: The exact package names might vary slightly; refer to your project's requirements file.)*

3.  Place the `tools.py` file in the correct location within your `mcp_tools` structure, typically `src/mcp_tools/astrology/tools.py`.

4.  Ensure your MCP operator environment is set up to discover and register tools from this directory.

## Configuration

The `AstrologyTool` uses environment variables for default location data and configuration for serving visual chart outputs.

-   `DEFAULT_LATITUDE`: (Optional) Sets the default latitude (as a float) to use for calculations if latitude is not provided in a tool call's parameters.
    ```bash
    export DEFAULT_LATITUDE=42.48
    ```
-   `DEFAULT_LONGITUDE`: (Optional) Sets the default longitude (as a float) to use for calculations if longitude is not provided in a tool call's parameters.
    ```bash
    export DEFAULT_LONGITUDE=-71.02
    ```
-   `outputs_web_base_url`: (Optional but Recommended for visual charts) This parameter is passed during the tool's initialization. It should be the base URL where the `outputs/` directory (relative to your application root) is served statically via a web server. This allows the tool to return publicly accessible URLs for generated chart images.
    ```python
    # Example initialization within your MCP Operator main code
    from mcp_tools.astrology.tools import AstrologyTool
    import os

    # Get base URL from environment or config
    OUTPUTS_WEB_BASE_URL = os.environ.get("OUTPUTS_WEB_BASE_URL", None)

    astrology_tool = AstrologyTool(outputs_web_base_url=OUTPUTS_WEB_BASE_URL)

    # Register astrology_tool with your MCP Operator server...
    ```
    If `outputs_web_base_url` is not provided, the visual chart generation tools (`generate_visual_chart`, `generate_composite_chart`) will return an error indicating that the chart URL cannot be constructed.

## Usage

The `AstrologyTool` is designed to be used within an MCP operator framework. Once registered with an MCP server, models or other clients can invoke its methods using `ToolCall` objects.

### Tool Name

The tool is registered with the name:
`AstrologyTool`

### Available Actions

Each public method in the `AstrologyTool` class that takes a `ToolCall` and returns a `ToolResponse` can be exposed as an MCP tool action.

#### `generate_birth_chart_data`

Calculates detailed astrological data for a natal (birth) chart.

-   **Purpose:** Get precise planetary positions, house cusps, aspects, and dignities.
-   **Parameters:**
    -   `time_utc`: `str` (Required) - Birth time in ISO 8601 format (e.g., `"2000-01-15T12:30:00Z"` or `"1990-05-20T08:45:00+02:00"`). Must include timezone information (UTC 'Z' or offset).
    -   `latitude`: `float` (Optional) - Birth latitude. Defaults to `DEFAULT_LATITUDE` if not provided.
    -   `longitude`: `float` (Optional) - Birth longitude. Defaults to `DEFAULT_LONGITUDE` if not provided.
    -   `name`: `str` (Optional) - A name for the chart (e.g., "John Doe"). Defaults to "Unnamed".
    -   `house_system`: `str` (Optional) - The house system to use. Supported values (case-sensitive as per Immanuel mapping): `Placidus`, `Koch`, `Regiomontanus`, `Whole Sign`, `Equal`, `Campanus`. Defaults to `Placidus`.
    -   `aspect_orb`: `float` (Optional) - The maximum orb (in degrees) to consider for aspects. Defaults to `8.0`.
-   **Successful Response (`ToolResponse.result`):** A dictionary containing the calculated chart data.
    ```json
    {
      "name": "Chart Name",
      "datetime_utc": "YYYY-MM-DDTHH:mm:ssZ",
      "location": {
        "latitude": 12.34,
        "longitude": 56.78
      },
      "house_system": "Placidus",
      "aspect_orb_used": 8.0,
      "planetary_positions": {
        "sun": {
          "longitude_deg": 25.45,
          "latitude_deg": 0.12,
          "speed_deg_per_day": 1.01,
          "is_retrograde": false,
          "sign": "Capricorn",
          "sign_degree": 25.45,
          "house": 3,
          "dignity": null,
          "exaltation": null,
          "detriment": null,
          "fall": null
        },
        "moon": { ... },
        ... // other planets/points
      },
      "house_cusps": {
        "house_system": "Placidus",
        "ascendant_deg": 15.67,
        "midheaven_deg": 22.89,
        "house_cusps": [0.0, 15.67, 40.12, 75.34, 100.56, 125.78, 180.0, 195.67, 220.12, 255.34, 280.56, 305.78] // list of 12 cusp longitudes
      },
      "aspects": [
        {
          "body1": "sun",
          "body2": "moon",
          "aspect": "trine",
          "angle_deg": 119.87,
          "orb_applied_deg": 0.13,
          "ideal_angle_deg": 120.0
        },
        { ... },
        ... // other aspects
      ]
    }
    ```
-   **Error Response (`ToolResponse.error`):** An error message string if parameters are missing, invalid, or if an internal calculation error occurs.

#### `generate_visual_chart`

Generates an SVG image of a natal (birth) chart.

-   **Purpose:** Create a visual representation of a birth chart.
-   **Parameters:**
    -   `time_utc`: `str` (Required) - Birth time in ISO 8601 format. Must include timezone information (UTC 'Z' or offset).
    -   `latitude`: `float` (Optional) - Birth latitude. Defaults to `DEFAULT_LATITUDE` if not provided.
    -   `longitude`: `float` (Optional) - Birth longitude. Defaults to `DEFAULT_LONGITUDE` if not provided.
    -   `name`: `str` (Optional) - A name for the chart (e.g., "John Doe"). Defaults to "Unnamed".
    -   `house_system`: `str` (Optional) - The house system to use. Supported Kerykeion values (case-sensitive): `Placidus`, `Koch`, `Regiomontanus`, `Campanus`, `Equal`, `WholeSign`, `Porphyry`, `Morinus`, `Topocentric`, `Alcabitius`. Defaults to `Placidus`.
-   **Successful Response (`ToolResponse.result`):** A dictionary containing the URL of the generated chart image.
    ```json
    {
      "chart_url": "[https://your-outputs-server.com/tools/astrology/charts/natal_chart_john_doe_YYYYMMDD_HHMMSS_######.svg](https://your-outputs-server.com/tools/astrology/charts/natal_chart_john_doe_YYYYMMDD_HHMMSS_######.svg)"
    }
    ```
    The exact URL depends on the `outputs_web_base_url` configured for the tool.
-   **Error Response (`ToolResponse.error`):** An error message string if parameters are missing, invalid, `outputs_web_base_url` is not configured, or if chart generation fails.

#### `generate_composite_chart`

Generates an SVG image of a composite chart for two individuals.

-   **Purpose:** Create a visual representation of a composite chart, which represents the combined energy of a relationship.
-   **Parameters:**
    -   `person1_time_utc`: `str` (Required) - Birth time for the first person (ISO 8601).
    -   `person1_latitude`: `float` (Optional) - Birth latitude for the first person. Defaults to `DEFAULT_LATITUDE`.
    -   `person1_longitude`: `float` (Optional) - Birth longitude for the first person. Defaults to `DEFAULT_LONGITUDE`.
    -   `person1_name`: `str` (Optional) - Name for the first person. Defaults to "Person 1".
    -   `person2_time_utc`: `str` (Required) - Birth time for the second person (ISO 8601).
    -   `person2_latitude`: `float` (Optional) - Birth latitude for the second person. Defaults to `DEFAULT_LATITUDE`.
    -   `person2_longitude`: `float` (Optional) - Birth longitude for the second person. Defaults to `DEFAULT_LONGITUDE`.
    -   `person2_name`: `str` (Optional) - Name for the second person. Defaults to "Person 2".
    -   `house_system`: `str` (Optional) - The house system to use for component charts. Supported Kerykeion values (case-sensitive). Defaults to `Placidus`.
-   **Successful Response (`ToolResponse.result`):** A dictionary containing the URL of the generated composite chart image.
    ```json
    {
      "composite_chart_url": "[https://your-outputs-server.com/tools/astrology/charts/composite_chart_person1_and_person2_YYYYMMDD_HHMMSS_######.svg](https://your-outputs-server.com/tools/astrology/charts/composite_chart_person1_and_person2_YYYYMMDD_HHMMSS_######.svg)"
    }
    ```
-   **Error Response (`ToolResponse.error`):** An error message string if parameters are missing, invalid, `outputs_web_base_url` is not configured, or if chart generation fails.

#### `get_relationship_score`

Calculates a relationship compatibility score between two individuals.

-   **Purpose:** Obtain a numerical score representing the astrological compatibility between two people based on their birth charts.
-   **Parameters:**
    -   `person1_time_utc`: `str` (Required) - Birth time for the first person (ISO 8601).
    -   `person1_latitude`: `float` (Optional) - Birth latitude for the first person. Defaults to `DEFAULT_LATITUDE`.
    -   `person1_longitude`: `float` (Optional) - Birth longitude for the first person. Defaults to `DEFAULT_LONGITUDE`.
    -   `person1_name`: `str` (Optional) - Name for the first person. Defaults to "Person 1".
    -   `person2_time_utc`: `str` (Required) - Birth time for the second person (ISO 8601).
    -   `person2_latitude`: `float` (Optional) - Birth latitude for the second person. Defaults to `DEFAULT_LATITUDE`.
    -   `person2_longitude`: `float` (Optional) - Birth longitude for the second person. Defaults to `DEFAULT_LONGITUDE`.
    -   `person2_name`: `str` (Optional) - Name for the second person. Defaults to "Person 2".
    -   `house_system`: `str` (Optional) - The house system to use for component charts. Supported Kerykeion values (case-sensitive). Defaults to `Placidus`.
-   **Successful Response (`ToolResponse.result`):** A dictionary containing the names and the calculated relationship score.
    ```json
    {
      "person1_name": "Person 1",
      "person2_name": "Person 2",
      "relationship_score": 75.35 // Numerical score
    }
    ```
-   **Error Response (`ToolResponse.error`):** An error message string if parameters are missing, invalid, or if score calculation fails.

#### `get_generic_horoscope`

Provides a generic horoscope text for a given zodiac sign and date.

-   **Purpose:** Offer a simple, non-personalized horoscope reading.
-   **Note:** **This functionality is currently a placeholder.** It returns static text indicating that the feature requires further implementation (e.g., integration with a horoscope source or LLM).
-   **Parameters:**
    -   `sign`: `str` (Required) - The zodiac sign (e.g., `"Aries"`, `"Taurus"`). Case-insensitive.
    -   `date`: `str` (Optional) - The date for the horoscope in `YYYY-MM-DD` format. Defaults to the current date.
-   **Successful Response (`ToolResponse.result`):** A dictionary containing the sign, date, and placeholder horoscope text.
    ```json
    {
      "sign": "Aries",
      "date": "YYYY-MM-DD",
      "horoscope_text": "Generic horoscope for Aries on YYYY-MM-DD:\nThis functionality requires integration with a horoscope text source...",
      "status": "Partial Implementation: Horoscope text is a placeholder."
    }
    ```
-   **Error Response (`ToolResponse.error`):** An error message string if the sign is invalid or date format is incorrect.

#### `get_transits_over_time_range`

Calculates transiting aspects to a natal chart within a specified date/time range.

-   **Purpose:** Identify key astrological events (aspects between transiting planets and natal chart points) occurring during a period.
-   **Parameters:**
    -   `natal_time_utc`: `str` (Required) - Birth time for the natal chart (ISO 8601).
    -   `natal_latitude`: `float` (Optional) - Birth latitude for the natal chart. Defaults to `DEFAULT_LATITUDE`.
    -   `natal_longitude`: `float` (Optional) - Birth longitude for the natal chart. Defaults to `DEFAULT_LONGITUDE`.
    -   `natal_name`: `str` (Optional) - Name for the natal chart. Defaults to "Natal Chart".
    -   `start_time_utc`: `str` (Required) - The start date/time for the transit calculation range (ISO 8601). Must include timezone.
    -   `end_time_utc`: `str` (Required) - The end date/time for the transit calculation range (ISO 8601). Must include timezone.
    -   `house_system`: `str` (Optional) - House system for the natal chart. Supported Kerykeion values (case-sensitive). Defaults to `Placidus`.
    -   `orb`: `float` (Optional) - The maximum orb (in degrees) to consider for transiting aspects. Defaults to `1.0` (transits typically use tighter orbs than natal).
    -   `transiting_planets`: `List[str]` (Optional) - List of transiting planets to include (e.g., `["Sun", "Moon", "Jupiter"]`). If omitted, includes standard planets. Check Kerykeion docs for supported names.
    -   `natal_points`: `List[str]` (Optional) - List of natal points (planets, angles) to check transits against (e.g., `["Sun", "Moon", "Ascendant"]`). If omitted, includes standard natal planets/angles. Check Kerykeion docs for supported names.
    -   `aspect_list`: `List[str]` (Optional) - List of aspect types to include (e.g., `["conjunction", "square", "trine"]`). If omitted, includes standard major aspects. Check Kerykeion docs for supported names.
-   **Successful Response (`ToolResponse.result`):** A dictionary containing natal chart name, the time range, orb used, and a list of found transits.
    ```json
    {
      "natal_chart_name": "Natal Chart",
      "time_range_utc": {
        "start": "YYYY-MM-DDTHH:mm:ssZ",
        "end": "YYYY-MM-DDTHH:mm:ssZ"
      },
      "orb_used": 1.0,
      "transits": [
        {
          "transiting_planet": "Jupiter",
          "natal_point": "Sun",
          "aspect": "conjunction",
          "exact_datetime_utc": "YYYY-MM-DDTHH:mm:ssZ", // Exact time of the aspect
          "orb_at_exact": 0.0, // Orb is 0 at the exact time
          "ideal_angle_deg": 0.0,
          // ingress_datetime_utc (Optional, if provided by Kerykeion)
          // egress_datetime_utc (Optional, if provided by Kerykeion)
        },
        { ... },
        ... // other transits within the range and orb
      ]
    }
    ```
    The `transits` list is typically sorted by exact date/time.
-   **Error Response (`ToolResponse.error`):** An error message string if parameters are missing, invalid (including time formats or date range), or if transit calculation fails.

#### `generate_detailed_report`

Generates a detailed astrological report based on a birth chart.

-   **Purpose:** Provide a comprehensive textual interpretation of a birth chart.
-   **Note:** **This functionality is currently a placeholder.** Generating detailed, nuanced astrological interpretations requires complex logic, a knowledge base, or integration with an advanced text generation model. The current implementation returns static text stating that it's a placeholder.
-   **Parameters:**
    -   `time_utc`: `str` (Required) - Birth time in ISO 8601 format. Must include timezone information (UTC 'Z' or offset).
    -   `latitude`: `float` (Optional) - Birth latitude. Defaults to `DEFAULT_LATITUDE` if not provided.
    -   `longitude`: `float` (Optional) - Birth longitude. Defaults to `DEFAULT_LONGITUDE` if not provided.
    -   `name`: `str` (Optional) - A name for the chart (e.g., "John Doe"). Defaults to "Unnamed".
    -   `house_system`: `str` (Optional) - The house system to use. Supported Kerykeion values (case-sensitive). Defaults to `Placidus`.
    -   *(Future Parameters):* Parameters for report type, length, focus areas, etc. could be added here.
-   **Successful Response (`ToolResponse.result`):** A dictionary containing the chart name, and placeholder report text.
    ```json
    {
      "name": "Chart Name",
      "report_text": "This is a placeholder for a detailed astrological report for Chart Name...\nFull report generation requires astrological interpretation logic...",
      "status": "Partial Implementation: Report generation not fully implemented."
    }
    ```
-   **Error Response (`ToolResponse.error`):** An error message string if parameters are missing or invalid.

## Output Directory

Visual chart files generated by `generate_visual_chart` and `generate_composite_chart` are saved locally within the MCP operator's file system.

-   **Directory Path:** The charts are saved in the directory `outputs/tools/astrology/charts/` relative to the directory where the MCP operator application is run. The tool automatically creates this directory if it doesn't exist.

-   **Accessing Charts:** To make these charts accessible via the URLs returned by the tool, you *must* configure a web server to serve the `outputs/` directory statically. The `outputs_web_base_url` parameter (passed during tool initialization) should be the base URL of this web server. The tool constructs the full URL by appending the relative path (`tools/astrology/charts/filename.svg`) to this base URL.

## Limitations and Future Work

-   **Generic Horoscope:** The `get_generic_horoscope` action is a placeholder. It requires integration with a source for horoscope text (database, API, or LLM).
-   **Detailed Report:** The `generate_detailed_report` action is a placeholder. Generating meaningful astrological reports requires sophisticated interpretation logic which is not included. This is a significant development effort.
-   **Location Handling:** The tool currently relies on latitude/longitude and optional environment defaults. Integrating with a geocoding service would allow users to provide city/country names instead.
-   **Timezones:** While the tool *requires* UTC or offset ISO 8601 strings, handling timezones and daylight saving automatically based on location and date could be improved. Kerykeion's handling might simplify this if utilized fully.
-   **Astrology Library Features:** The tool currently exposes a subset of features from Immanuel and Kerykeion. More advanced features like specific fixed stars, asteroids, midpoints, planetary hours, etc., could be added as needed.
-   **Chart Customization:** The visual chart generation currently uses default Kerykeion styles. Adding parameters for visual customization (colors, displayed points, etc.) would be beneficial.
-   **Error Handling Detail:** While basic error handling exists, more specific error types and messages could be implemented for better diagnostics.

This `AstrologyTool` provides a solid foundation for incorporating astrological calculations and visual charts into an MCP-driven application. The placeholder methods (`get_generic_horoscope`, `generate_detailed_report`) represent significant areas for future development based on specific application requirements.