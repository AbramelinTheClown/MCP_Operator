# src/mcp_tools/astrology/tools.py

import os
import datetime
from typing import Dict, Any, List, Optional
import traceback # Import traceback for detailed error logging
from mcp import ToolCall, ToolResponse, Tool
# Import necessary parts from the MCP Python SDK
# Assuming these are available at the top level of the SDK
try:
    from mcp import ToolCall, ToolResponse, Tool
    print("MCP Python SDK imported successfully")
except ImportError as e:
    print(f"Error importing MCP Python SDK: {e}")
    print("Please ensure the package is installed correctly")
    raise
# Import the chosen astrology libraries
# Ensure 'immanuel' and 'kerykeion' are installed (as per consolidated_requirements.txt)
try:
    from immanuel import Planet, Chart, Settings, aspects, houses, signs, elements, modalities # Core Immanuel imports
    from immanuel.const import Planet as ImmanuelPlanet # Use Immanuel's Planet enum if needed for type hints or checks
    print("Immanuel library imported successfully.")
except ImportError:
    print("Error: immanuel library not found. Please install it.")
    # Depending on your mcp_operator's error handling, you might want to
    # raise an exception here or handle it during tool registration.
    Immanuel = None # Set to None if import fails

try:
    from kerykeion import Ker # Kerykeion's main class
    from kerykeion.aspects import KerykeionAspects # Kerykeion aspects if needed
    from kerykeion.charts import KerykeionChart, CompositeChart # Import CompositeChart based on docs
    from kerykeion.relationship_score.relationship_score_factory import RelationshipScoreFactory # Import for relationship score
    # Import Kerykeion types for validation/clarity
    from kerykeion.kr_types.kr_literals import HouseSystemLiteral # For house system validation
    from kerykeion.kr_types.settings_models import KerykeionSettings # If passing detailed settings
    # from kerykeion.kr_types.kr_models import ... # Import other types if needed

    # Import Kerykeion transit functionality
    from kerykeion.aspects.transits_time_range import TransitsTimeRange # Import for transit calculations

    print("Kerykeion library imported successfully.")
except ImportError:
    print("Error: kerykeion library not found. Please install it.")
    # Handle import error


# --- Configuration and Constants ---
# Default location from environment variables (for tools that require location)
DEFAULT_LATITUDE = float(os.environ.get("DEFAULT_LATITUDE", 42.48)) # Example default (Lynnfield, MA)
DEFAULT_LONGITUDE = float(os.environ.get("DEFAULT_LONGITUDE", -71.02)) # Example default (Lynnfield, MA)

# House system mapping for Immanuel (check Immanuel docs for supported systems)
# Immanuel uses codes like 'P', 'K', 'R', 'W', 'E', 'C'
IMMANUEL_HOUSE_SYSTEM_MAP = {
    "Placidus": 'P',
    "Koch": 'K',
    "Regiomontanus": 'R',
    "Whole Sign": 'W',
    "Equal": 'E',
    "Campanus": 'C',
    # Add other systems if needed and supported by Immanuel
}

# Aspect names mapping for Immanuel (check Immanuel docs)
# Immanuel uses names like 'conjunction', 'opposition', 'square', etc.
# We'll map our desired names to Immanuel's names
IMMANUEL_ASPECT_MAP = {
    "Conjunction": 'conjunction',
    "Opposition": 'opposition',
    "Square": 'square',
    "Trine": 'trine',
    "Sextile": 'sextile',
    "Semisextile": 'semisextile',
    "Quincunx": 'quincunx',
    "Semisquare": 'semisquare',
    "Sesquiquadrate": 'sesquiquadrate',
    "Quintile": 'quintile',
    "Biquintile": 'biquintile',
    # Add other aspects if needed and supported by Immanuel
}

# List of supported Kerykeion House Systems for validation
# Based on kerykeion.kr_types.kr_literals.HouseSystemLiteral
KERYKEION_HOUSE_SYSTEMS = list(HouseSystemLiteral.__args__)

# List of valid zodiac signs for validation
VALID_ZODIAC_SIGNS = [s.name for s in signs.Sign] # Use Immanuel's signs enum


class AstrologyTool(Tool):
    """
    A Model Context Protocol Tool for performing astrological calculations,
    generating visual charts, and providing astrological insights using
    Immanuel and Kerykeion libraries.
    """

    def __init__(self, outputs_web_base_url: str = None):
        """
        Initializes the AstrologyTool.

        Args:
            outputs_web_base_url: The base URL where the tool's output files (like charts) are served.
                                  Used to construct URLs in the response.
        """
        self.outputs_web_base_url = outputs_web_base_url # Store the outputs base URL

        # Define the specific output directory for this tool's visual outputs
        self.outputs_chart_dir = os.path.join("outputs", "tools", "astrology", "charts")
        os.makedirs(self.outputs_chart_dir, exist_ok=True) # Ensure the directory exists

        print("AstrologyTool initialized.")
        print(f"  Chart output directory: {self.outputs_chart_dir}")
        if self.outputs_web_base_url:
             print(f"  Chart files will be served under: {self.outputs_web_base_url}/tools/astrology/charts/")
        else:
             print("  Warning: outputs_web_base_url not provided. Chart URLs may not be fully accessible externally.")


    @property
    def tool_name(self) -> str:
        """The name of the tool as it will be registered with the server."""
        return "AstrologyTool" # Keeping the existing name


    # --- Helper method to parse birth data ---
    def _parse_birth_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Parses and validates common birth data parameters."""
        time_str = parameters.get("time_utc")
        latitude = parameters.get("latitude")
        longitude = parameters.get("longitude")
        name = parameters.get("name", "Unnamed") # Optional name for the chart

        if not time_str:
             raise ValueError("Missing required parameter: time_utc.")

        # Determine location: prioritize parameter, then environment default
        use_latitude = latitude if latitude is not None else DEFAULT_LATITUDE
        use_longitude = longitude if longitude is not None else DEFAULT_LONGITUDE

        # Check if we ultimately have a valid location for location-dependent calculations
        if use_latitude is None or use_longitude is None:
             raise ValueError("Latitude and longitude are required for this calculation and are missing. No default location is set.")

        if not isinstance(use_latitude, (int, float)) or not isinstance(use_longitude, (int, float)):
             raise ValueError("Invalid latitude or longitude value (from parameters or default). Must be numbers.")

        try:
            # Immanuel's Chart class often takes datetime objects directly
            # Need to parse the ISO 8601 string into a datetime object
            # Handle optional timezone 'Z'
            if time_str.endswith('Z'):
                time_str = time_str[:-1] + '+00:00' # Convert Z to +00:00 for fromisoformat
            observation_datetime = datetime.datetime.fromisoformat(time_str)

        except (ValueError, TypeError) as e:
             raise ValueError(f"Invalid time format or value: {e}")

        return {
            "name": name,
            "datetime": observation_datetime,
            "latitude": use_latitude,
            "longitude": use_longitude
        }


    # --- Callable Actions (Methods) ---

    def generate_birth_chart_data(self, call: ToolCall) -> ToolResponse:
        """
        Calculates detailed birth chart data (positions, houses, aspects, dignities)
        for a given time and location using Immanuel.

        Expected parameters in ToolCall.parameters:
        - time_utc: str (Required) - Birth time in ISO 8601 format.
        - latitude: float (Optional) - Birth latitude. Defaults to environment variable.
        - longitude: float (Optional) - Birth longitude. Defaults to environment variable.
        - name: str (Optional) - Name for the chart (e.g., "John Doe").
        - house_system: str (Optional) - House system (e.g., 'Placidus', 'Whole Sign'). Defaults to 'Placidus'.
        - aspect_orb: float (Optional) - Orb for aspects. Defaults to 8.0.
        """
        try:
            # Parse and validate input data using the helper
            birth_data = self._parse_birth_data(call.parameters)
            house_system_name = call.parameters.get("house_system", "Placidus")
            aspect_orb = float(call.parameters.get("aspect_orb", 8.0))

            # Get Immanuel house system code
            house_system_code = IMMANUEL_HOUSE_SYSTEM_MAP.get(house_system_name)
            if not house_system_code:
                 return ToolResponse(
                     tool_call_id=call.tool_call_id,
                     is_successful=False,
                     error=f"Invalid house system '{house_system_name}'. Available systems: {', '.join(IMMANUEL_HOUSE_SYSTEM_MAP.keys())}"
                 )

            if not isinstance(aspect_orb, (int, float)) or aspect_orb < 0:
                 return ToolResponse(
                     tool_call_id=call.tool_call_id,
                     is_successful=False,
                     error="Invalid aspect_orb parameter. Must be a non-negative number."
                 )


            # --- Use Immanuel to calculate chart data ---
            # Immanuel's Chart class calculates positions, houses, etc. upon creation
            chart = Chart(
                birth_data["datetime"],
                birth_data["longitude"],
                birth_data["latitude"],
                house_system=house_system_code # Pass the Immanuel house system code
            )

            # Extract planetary positions
            positions_data = {}
            for planet_enum in ImmanuelPlanet: # Iterate through Immanuel's Planet enum
                planet_obj = chart.planets[planet_enum]
                positions_data[planet_enum.name.lower()] = { # Use lower case name for consistency
                    "longitude_deg": round(planet_obj.longitude, 4),
                    "latitude_deg": round(planet_obj.latitude, 4), # Ecliptic latitude
                    "speed_deg_per_day": round(planet_obj.speed, 4), # Speed in longitude
                    "is_retrograde": planet_obj.is_retrograde,
                    "sign": planet_obj.sign.name, # Sign by name
                    "sign_degree": round(planet_obj.sign_degree, 4), # Degree within the sign
                    # Immanuel might have other properties like house, dignity, etc. directly on the planet object
                    "house": planet_obj.house.number if planet_obj.house else None, # House number
                    "dignity": planet_obj.dignity.name if planet_obj.dignity else None, # Dignity by name
                    "exaltation": planet_obj.exaltation.name if planet_obj.exaltation else None, # Exaltation by name
                    "detriment": planet_obj.detriment.name if planet_obj.detriment else None, # Detriment by name
                    "fall": planet_obj.fall.name if planet_obj.fall else None, # Fall by name
                }

            # Extract house cusps
            house_cusps_data = {
                "house_system": house_system_name,
                "ascendant_deg": round(chart.ascendant.longitude, 4),
                "midheaven_deg": round(chart.midheaven.longitude, 4),
                "house_cusps": [round(h.longitude, 4) for h in chart.houses] # List of 12 house cusp longitudes
            }

            # Calculate and extract aspects
            # Immanuel's chart.aspects property might already calculate major aspects
            # Or you might need to call a specific function. Check Immanuel docs.
            # Assuming chart.aspects provides a list of found aspects:
            found_aspects_data = []
            # Immanuel's aspect objects might have properties like .p1, .p2, .type, .angle, .orb
            # You might need to iterate through chart.aspects or call a function like aspects.find_all()
            # Let's use immanuel.aspects.find_all() for more control over orb and types
            chart_aspects = aspects.find_all(
                chart.planets.values(), # Pass all planet objects
                chart.planets.values(), # Check aspects between all planets
                orb=aspect_orb,
                # You could filter by aspect types if needed, e.g., types=[aspects.AspectType.CONJUNCTION, ...]
            )

            for aspect_obj in chart_aspects:
                # Ensure aspect_obj has the expected properties based on Immanuel docs
                found_aspects_data.append({
                    "body1": aspect_obj.p1.type.name.lower(), # Planet 1 name
                    "body2": aspect_obj.p2.type.name.lower(), # Planet 2 name
                    "aspect": aspect_obj.type.name.lower(), # Aspect type name
                    "angle_deg": round(aspect_obj.angle, 4), # Exact angle
                    "orb_applied_deg": round(aspect_obj.orb, 4), # Orb for this specific aspect instance
                    "ideal_angle_deg": round(aspect_obj.type.angle, 4) # Ideal angle for this aspect type
                })


            # Combine all data into the result dictionary
            result_data = {
                "name": birth_data["name"],
                "datetime_utc": birth_data["datetime"].isoformat().replace('+00:00', 'Z'),
                "location": {
                    "latitude": birth_data["latitude"],
                    "longitude": birth_data["longitude"]
                },
                "house_system": house_system_name,
                "aspect_orb_used": aspect_orb,
                "planetary_positions": positions_data,
                "house_cusps": house_cusps_data,
                "aspects": found_aspects_data,
                # You could add other calculations here if Immanuel provides them
                # e.g., "midpoints": ..., "fixed_stars": ...
            }


            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=True,
                result=result_data
            )

        except ValueError as ve:
             print(f"Input error in generate_birth_chart_data: {ve}")
             return ToolResponse(tool_call_id=call.tool_call_id, is_successful=False, error=f"Input error: {ve}")
        except Exception as e:
            print(f"An unexpected error occurred in generate_birth_chart_data: {e}")
            traceback.print_exc() # Print traceback for debugging
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=False,
                error=f"An internal server error occurred: {e}"
            )


    async def generate_visual_chart(self, call: ToolCall) -> ToolResponse:
        """
        Generates a visual astrological natal chart (SVG image) for a given time and location
        using Kerykeion.

        Expected parameters in ToolCall.parameters:
        - time_utc: str (Required) - Birth time in ISO 8601 format.
        - latitude: float (Optional) - Birth latitude. Defaults to environment variable.
        - longitude: float (Optional) - Birth longitude. Defaults to environment variable.
        - name: str (Optional) - Name for the chart (e.g., "John Doe").
        - house_system: str (Optional) - House system (e.g., 'Placidus', 'Whole Sign'). Defaults to 'Placidus'.
        # Kerykeion might support other visual parameters, add them here if needed
        # e.g., "chart_style": str, "show_aspects": bool
        """
        try:
            # Parse and validate input data using the helper
            birth_data = self._parse_birth_data(call.parameters)
            house_system_name = call.parameters.get("house_system", "Placidus")

            # Validate house system against Kerykeion's supported literals
            if house_system_name not in KERYKEION_HOUSE_SYSTEMS:
                 return ToolResponse(
                     tool_call_id=call.tool_call_id,
                     is_successful=False,
                     error=f"Invalid house system '{house_system_name}'. Available Kerykeion systems: {', '.join(KERYKEION_HOUSE_SYSTEMS)}"
                 )


            # --- Use Kerykeion to generate the chart image ---
            # Kerykeion's Ker class is the main entry point
            # The constructor takes name, year, month, day, hour, minute, city, nation, latitude, longitude
            # We need to extract components from the datetime object
            dt = birth_data["datetime"]
            year, month, day = dt.year, dt.month, dt.day
            hour, minute = dt.hour, dt.minute
            # Kerykeion might also need seconds, check docs
            second = dt.second # Use seconds if available/needed

            # Kerykeion often works with place names (city, nation) for timezone lookup,
            # but can also use lat/lon. Using lat/lon is more precise if available.
            # Kerykeion constructor: Ker(name, year, month, day, hour, minute, city, nation, lat=None, lon=None, h_sys="Placidus")
            # Let's pass lat/lon directly and a placeholder city/nation if needed by Kerykeion
            # Check Kerykeion docs on how to best handle location without city/nation lookup.
            # Example assuming lat/lon override city/nation for calculations:
            kerykeion_chart = Ker(
                 birth_data["name"],
                 year, month, day, hour, minute,
                 city="Unknown", # Placeholder city
                 nation="Unknown", # Placeholder nation
                 lat=birth_data["latitude"],
                 lon=birth_data["longitude"],
                 h_sys=house_system_name # Pass house system name to Kerykeion
                 # Pass other Kerykeion specific parameters if supported and needed
             )

            # Generate the SVG chart
            # Kerykeion's Ker object likely has a method to generate the chart file or data
            # Check Kerykeion docs for charting methods, e.g., .make_chart_svg(), .make_full_chart_svg()
            # The docs show make_full_chart_svg() returns a string
            # make_chart_svg() also returns a string

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f") # Unique filename
            safe_name = "".join(c for c in birth_data["name"] if c.isalnum() or c in ('_', '-')).replace(' ', '_').lower()[:20] # Sanitize name
            chart_filename = f"natal_chart_{safe_name}_{timestamp}.svg" # More specific filename
            chart_file_path_absolute = os.path.join(self.outputs_chart_dir, chart_filename) # Use instance's outputs_chart_dir

            print(f"Generating visual natal chart to: {chart_file_path_absolute}")

            try:
                 # Call Kerykeion's chart generation method that returns SVG data
                 svg_data = kerykeion_chart.make_full_chart_svg() # Returns SVG string

                 # Write the SVG data to the file
                 with open(chart_file_path_absolute, "w", encoding="utf-8") as f: # Use 'w' for text/svg
                      f.write(svg_data)
                 print("Natal chart SVG saved successfully.")

            except Exception as chart_error:
                 print(f"Error generating natal chart SVG: {chart_error}")
                 traceback.print_exc()
                 return ToolResponse(
                     tool_call_id=call.tool_call_id,
                     is_successful=False,
                     error=f"Failed to generate visual natal chart: {chart_error}"
                 )


            # --- Construct the accessible URL ---
            # Use the outputs_web_base_url provided during initialization
            if not self.outputs_web_base_url:
                 error_msg = "Tool outputs base URL not configured. Cannot provide chart URL."
                 print(f"Error: {error_msg}")
                 # Decide if this should be an error or return a path
                 return ToolResponse(tool_call_id=call.tool_call_id, is_successful=False, error=error_msg)
            else:
                 # Construct the full URL. Assumes the web server serves the 'outputs' directory
                 # and the path relative to 'outputs' is 'tools/astrology/charts/filename.svg'
                 chart_url = f"{self.outputs_web_base_url}/tools/astrology/charts/{chart_filename}"
                 print(f"Constructed chart URL: {chart_url}")


            # --- Return the result ---
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=True,
                result={"chart_url": chart_url}
            )

        except ValueError as ve:
             print(f"Input error in generate_visual_chart: {ve}")
             return ToolResponse(tool_call_id=call.tool_call_id, is_successful=False, error=f"Input error: {ve}")
        except Exception as e:
            print(f"An unexpected error occurred in generate_visual_chart: {e}")
            traceback.print_exc()
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=False,
                error=f"An internal server error occurred: {e}"
            )

    async def generate_composite_chart(self, call: ToolCall) -> ToolResponse:
        """
        Generates a visual astrological composite chart (SVG image) for two individuals
        using Kerykeion.

        Expected parameters in ToolCall.parameters:
        - person1_time_utc: str (Required) - Birth time for the first person (ISO 8601).
        - person1_latitude: float (Optional) - Birth latitude for the first person. Defaults to environment variable.
        - person1_longitude: float (Optional) - Birth longitude for the first person. Defaults to environment variable.
        - person1_name: str (Optional) - Name for the first person.

        - person2_time_utc: str (Required) - Birth time for the second person (ISO 8601).
        - person2_latitude: float (Optional) - Birth latitude for the second person. Defaults to environment variable.
        - person2_longitude: float (Optional) - Birth longitude for the second person. Defaults to environment variable.
        - person2_name: str (Optional) - Name for the second person.

        - house_system: str (Optional) - House system for charts. Defaults to 'Placidus'.
        # Kerykeion might support other visual parameters, add them here if needed
        """
        try:
            # Parse and validate birth data for both individuals
            person1_data = self._parse_birth_data({
                "time_utc": call.parameters.get("person1_time_utc"),
                "latitude": call.parameters.get("person1_latitude"),
                "longitude": call.parameters.get("person1_longitude"),
                "name": call.parameters.get("person1_name", "Person 1")
            })

            person2_data = self._parse_birth_data({
                "time_utc": call.parameters.get("person2_time_utc"),
                "latitude": call.parameters.get("person2_latitude"),
                "longitude": call.parameters.get("person2_longitude"),
                "name": call.parameters.get("person2_name", "Person 2")
            })

            house_system_name = call.parameters.get("house_system", "Placidus")

            # Validate house system against Kerykeion's supported literals
            if house_system_name not in KERYKEION_HOUSE_SYSTEMS:
                 return ToolResponse(
                     tool_call_id=call.tool_call_id,
                     is_successful=False,
                     error=f"Invalid house system '{house_system_name}'. Available Kerykeion systems: {', '.join(KERYKEION_HOUSE_SYSTEMS)}"
                 )


            # --- Use Kerykeion to generate the composite chart ---
            # Kerykeion's Ker class can likely be used to create chart objects,
            # and there should be a method or function for composite charts.
            # The example shows creating two Ker objects and then passing them to a composite function.

            # Create Kerykeion chart objects for both individuals
            dt1 = person1_data["datetime"]
            kerykeion_chart1 = Ker(
                 person1_data["name"],
                 dt1.year, dt1.month, dt1.day, dt1.hour, dt1.minute, dt1.second, # Include seconds
                 city="Unknown", nation="Unknown", # Placeholder
                 lat=person1_data["latitude"], lon=person1_data["longitude"],
                 h_sys=house_system_name
             )

            dt2 = person2_data["datetime"]
            kerykeion_chart2 = Ker(
                 person2_data["name"],
                 dt2.year, dt2.month, dt2.day, dt2.hour, dt2.minute, dt2.second, # Include seconds
                 city="Unknown", nation="Unknown", # Placeholder
                 lat=person2_data["latitude"], lon=person2_data["longitude"],
                 h_sys=house_system_name
             )

            # Generate the composite chart SVG
            # The example composite_chart.py shows creating a CompositeChart object and then generating SVG
            from kerykeion.charts import CompositeChart # Import CompositeChart

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f") # Unique filename
            safe_name1 = "".join(c for c in person1_data["name"] if c.isalnum() or c in ('_', '-')).replace(' ', '_').lower()[:10] # Sanitize name
            safe_name2 = "".join(c for c in person2_data["name"] if c.isalnum() or c in ('_', '-')).replace(' ', '_').lower()[:10] # Sanitize name
            chart_filename = f"composite_chart_{safe_name1}_and_{safe_name2}_{timestamp}.svg"
            chart_file_path_absolute = os.path.join(self.outputs_chart_dir, chart_filename)

            print(f"Generating visual composite chart to: {chart_file_path_absolute}")

            try:
                 # Create the CompositeChart object
                 composite_chart_obj = CompositeChart(kerykeion_chart1, kerykeion_chart2)
                 # Generate the SVG data (Assuming CompositeChart has make_full_chart_svg method)
                 # Check Kerykeion docs for CompositeChart methods
                 composite_svg_data = composite_chart_obj.make_full_chart_svg() # Assuming this method exists and returns SVG string

                 with open(chart_file_path_absolute, "w", encoding="utf-8") as f:
                      f.write(composite_svg_data)
                 print("Composite chart SVG saved successfully.")


            except Exception as chart_error:
                 print(f"Error generating composite chart SVG: {chart_error}")
                 traceback.print_exc()
                 return ToolResponse(
                     tool_call_id=call.tool_call_id,
                     is_successful=False,
                     error=f"Failed to generate visual composite chart: {chart_error}"
                 )


            # --- Construct the accessible URL ---
            if not self.outputs_web_base_url:
                 error_msg = "Tool outputs base URL not configured. Cannot provide chart URL."
                 print(f"Error: {error_msg}")
                 return ToolResponse(tool_call_id=call.tool_call_id, is_successful=False, error=error_msg)
            else:
                 chart_url = f"{self.outputs_web_base_url}/tools/astrology/charts/{chart_filename}"
                 print(f"Constructed chart URL: {chart_url}")


            # --- Return the result ---
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=True,
                result={"composite_chart_url": chart_url} # Use a specific key for composite
            )

        except ValueError as ve:
             print(f"Input error in generate_composite_chart: {ve}")
             return ToolResponse(tool_call_id=call.tool_call_id, is_successful=False, error=f"Input error: {ve}")
        except Exception as e:
            print(f"An unexpected error occurred in generate_composite_chart: {e}")
            traceback.print_exc()
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=False,
                error=f"An internal server error occurred: {e}"
            )


    def get_relationship_score(self, call: ToolCall) -> ToolResponse:
        """
        Calculates a relationship compatibility score between two individuals
        using Kerykeion's relationship score factory.

        Expected parameters in ToolCall.parameters:
        - person1_time_utc: str (Required) - Birth time for the first person (ISO 8601).
        - person1_latitude: float (Optional) - Birth latitude for the first person. Defaults to environment variable.
        - person1_longitude: float (Optional) - Birth longitude for the first person. Defaults to environment variable.
        - person1_name: str (Optional) - Name for the first person.

        - person2_time_utc: str (Required) - Birth time for the second person (ISO 8601).
        - person2_latitude: float (Optional) - Birth latitude for the second person. Defaults to environment variable.
        - person2_longitude: float (Optional) - Birth longitude for the second person. Defaults to environment variable.
        - person2_name: str (Optional) - Name for the second person.

        - house_system: str (Optional) - House system for charts. Defaults to 'Placidus'.
        # Kerykeion might have parameters for score weighting or focus, add if needed
        """
        try:
            # Parse and validate birth data for both individuals
            person1_data = self._parse_birth_data({
                "time_utc": call.parameters.get("person1_time_utc"),
                "latitude": call.parameters.get("person1_latitude"),
                "longitude": call.parameters.get("person1_longitude"),
                "name": call.parameters.get("person1_name", "Person 1")
            })

            person2_data = self._parse_birth_data({
                "time_utc": call.parameters.get("person2_time_utc"),
                "latitude": call.parameters.get("person2_latitude"),
                "longitude": call.parameters.get("person2_longitude"),
                "name": call.parameters.get("person2_name", "Person 2")
            })

            house_system_name = call.parameters.get("house_system", "Placidus")

            # Validate house system against Kerykeion's supported literals
            if house_system_name not in KERYKEION_HOUSE_SYSTEMS:
                 return ToolResponse(
                     tool_call_id=call.tool_call_id,
                     is_successful=False,
                     error=f"Invalid house system '{house_system_name}'. Available Kerykeion systems: {', '.join(KERYKEION_HOUSE_SYSTEMS)}"
                 )


            # --- Use Kerykeion to calculate relationship score ---
            # The documentation points to RelationshipScoreFactory.
            # You likely create Ker objects for both people and pass them to the factory.

            # Create Kerykeion chart objects for both individuals
            dt1 = person1_data["datetime"]
            kerykeion_chart1 = Ker(
                 person1_data["name"],
                 dt1.year, dt1.month, dt1.day, dt1.hour, dt1.minute, dt1.second, # Include seconds
                 city="Unknown", nation="Unknown", # Placeholder
                 lat=person1_data["latitude"], lon=person1_data["longitude"],
                 h_sys=house_system_name
             )

            dt2 = person2_data["datetime"]
            kerykeion_chart2 = Ker(
                 person2_data["name"],
                 dt2.year, dt2.month, dt2.day, dt2.hour, dt2.minute, dt2.second, # Include seconds
                 city="Unknown", nation="Unknown", # Placeholder
                 lat=person2_data["latitude"], lon=person2_data["longitude"],
                 h_sys=house_system_name
             )

            # Calculate the relationship score
            # Check Kerykeion docs for RelationshipScoreFactory usage
            # Assuming you instantiate the factory and call a method like .get_score()
            # The factory might take charts and return a score object or value.

            try:
                 # Example based on docs:
                 score_factory = RelationshipScoreFactory(kerykeion_chart1, kerykeion_chart2)
                 relationship_score = score_factory.get_score() # Assuming this returns a numerical score

                 # Kerykeion might provide more detailed score breakdown, check docs
                 # e.g., score_details = score_factory.get_details()


            except Exception as score_error:
                 print(f"Error calculating relationship score: {score_error}")
                 traceback.print_exc()
                 return ToolResponse(
                     tool_call_id=call.tool_call_id,
                     is_successful=False,
                     error=f"Failed to calculate relationship score: {score_error}"
                 )


            # --- Return the result ---
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=True,
                result={
                    "person1_name": person1_data["name"],
                    "person2_name": person2_data["name"],
                    "relationship_score": round(relationship_score, 2), # Return the score
                    # Add score details if available and desired
                }
            )

        except ValueError as ve:
             print(f"Input error in get_relationship_score: {ve}")
             return ToolResponse(tool_call_id=call.tool_call_id, is_successful=False, error=f"Input error: {ve}")
        except Exception as e:
            print(f"An unexpected error occurred in get_relationship_score: {e}")
            traceback.print_exc()
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=False,
                error=f"An internal server error occurred: {e}"
            )


    def get_generic_horoscope(self, call: ToolCall) -> ToolResponse:
        """
        Provides a generic horoscope for a given zodiac sign and date.
        Note: This tool provides generic text, not a personalized horoscope
        based on a full birth chart. Full implementation requires external text generation.

        Expected parameters in ToolCall.parameters:
        - sign: str (Required) - The zodiac sign (e.g., 'Aries', 'Taurus'). Case-insensitive.
        - date: str (Optional) - The date for the horoscope in YYYY-MM-DD format. Defaults to today.
        """
        try:
            sign = call.parameters.get("sign")
            date_str = call.parameters.get("date")

            if not sign:
                 return ToolResponse(
                     tool_call_id=call.tool_call_id,
                     is_successful=False,
                     error="Missing required parameter: sign."
                 )

            # Validate sign name (case-insensitive check against Immanuel's signs)
            valid_signs_lower = [s.name.lower() for s in signs.Sign]
            if sign.lower() not in valid_signs_lower:
                 return ToolResponse(
                     tool_call_id=call.tool_call_id,
                     is_successful=False,
                     error=f"Invalid zodiac sign '{sign}'. Available signs: {', '.join(VALID_ZODIAC_SIGNS)}"
                 )
            # Use the capitalized version for consistent output
            validated_sign = sign.capitalize()


            # Determine the date
            if date_str:
                try:
                    horoscope_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    return ToolResponse(
                        tool_call_id=call.tool_call_id,
                        is_successful=False,
                        error="Invalid date format. Please use YYYY-MM-DD."
                    )
            else:
                horoscope_date = datetime.date.today() # Default to today

            print(f"Attempting to get generic horoscope for {validated_sign} on {horoscope_date.isoformat()}")

            # --- Placeholder: Implement Generic Horoscope Text Generation ---
            # This section needs to be replaced with actual logic to generate
            # or retrieve the horoscope text. This is NOT provided by Immanuel or Kerykeion.
            # Possible implementations:
            # 1. Lookup in an internal database of pre-written horoscopes.
            # 2. Call an external API that provides horoscopes.
            # 3. Use another LLM (e.g., via LM Studio API) to generate the text
            #    based on the sign and date, potentially incorporating current transits
            #    (which you could calculate using Kerykeion's TransitsTimeRange if needed).
            #
            # For now, return a placeholder response indicating this is not fully implemented.
            # A slightly more informative placeholder:
            placeholder_text = (
                f"Generic horoscope for {validated_sign} on {horoscope_date.isoformat()}:\n"
                "This functionality requires integration with a horoscope text source (database, API, or LLM) "
                "and is currently a placeholder. Astrological calculations for specific charts are available via other actions."
            )

            # --- Return the result ---
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=True,
                result={
                    "sign": validated_sign,
                    "date": horoscope_date.isoformat(),
                    "horoscope_text": placeholder_text,
                    "status": "Partial Implementation: Horoscope text is a placeholder."
                }
            )

        except Exception as e:
            print(f"An unexpected error occurred in get_generic_horoscope: {e}")
            traceback.print_exc()
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=False,
                error=f"An internal server error occurred: {e}"
            )


    # --- New Transit Calculation Method ---
    async def get_transits_over_time_range(self, call: ToolCall) -> ToolResponse:
        """
        Calculates transiting aspects to a natal chart over a specified time range
        using Kerykeion's TransitsTimeRange.

        Expected parameters in ToolCall.parameters:
        - natal_time_utc: str (Required) - Birth time for the natal chart (ISO 8601).
        - natal_latitude: float (Optional) - Birth latitude for the natal chart. Defaults to environment variable.
        - natal_longitude: float (Optional) - Birth longitude for the natal chart. Defaults to environment variable.
        - natal_name: str (Optional) - Name for the natal chart.

        - start_time_utc: str (Required) - The start date/time for the transit calculation range (ISO 8601).
        - end_time_utc: str (Required) - The end date/time for the transit calculation range (ISO 8601).

        - house_system: str (Optional) - House system for the natal chart. Defaults to 'Placidus'.
        - orb: float (Optional) - Orb for transiting aspects. Defaults to 1.0 (transits often use tighter orbs).
        # Kerykeion TransitsTimeRange might support other parameters like specific
        # transiting/natal planets to check, or specific aspects. Add if needed.
        # e.g., "transiting_planets": List[str], "natal_planets": List[str], "aspect_list": List[str]
        """
        try:
            # Parse and validate natal chart data
            natal_data = self._parse_birth_data({
                "time_utc": call.parameters.get("natal_time_utc"),
                "latitude": call.parameters.get("natal_latitude"),
                "longitude": call.parameters.get("natal_longitude"),
                "name": call.parameters.get("natal_name", "Natal Chart")
            })

            start_time_str = call.parameters.get("start_time_utc")
            end_time_str = call.parameters.get("end_time_utc")
            house_system_name = call.parameters.get("house_system", "Placidus")
            orb = float(call.parameters.get("orb", 1.0)) # Default orb for transits

            if not start_time_str or not end_time_str:
                 return ToolResponse(
                     tool_call_id=call.tool_call_id,
                     is_successful=False,
                     error="Missing required parameters: start_time_utc and end_time_utc."
                 )

            # Validate house system against Kerykeion's supported literals
            if house_system_name not in KERYKEION_HOUSE_SYSTEMS:
                 return ToolResponse(
                     tool_call_id=call.tool_call_id,
                     is_successful=False,
                     error=f"Invalid house system '{house_system_name}'. Available Kerykeion systems: {', '.join(KERYKEION_HOUSE_SYSTEMS)}"
                 )

            if not isinstance(orb, (int, float)) or orb < 0:
                 return ToolResponse(
                     tool_call_id=call.tool_call_id,
                     is_successful=False,
                     error="Invalid orb parameter. Must be a non-negative number."
                 )


            try:
                # Parse start and end times into datetime objects
                if start_time_str.endswith('Z'):
                    start_time_str = start_time_str[:-1] + '+00:00'
                start_datetime = datetime.datetime.fromisoformat(start_time_str)

                if end_time_str.endswith('Z'):
                    end_time_str = end_time_str[:-1] + '+00:00'
                end_datetime = datetime.datetime.fromisoformat(end_time_str)

                if start_datetime >= end_datetime:
                     return ToolResponse(
                         tool_call_id=call.tool_call_id,
                         is_successful=False,
                         error="start_time_utc must be before end_time_utc."
                     )


            except (ValueError, TypeError) as e:
                 return ToolResponse(
                     tool_call_id=call.tool_call_id,
                     is_successful=False,
                     error=f"Invalid time format or value for start/end times: {e}"
                 )


            print(f"Calculating transits for {natal_data['name']} from {start_datetime.isoformat()} to {end_datetime.isoformat()}")

            # --- Use Kerykeion to calculate transits ---
            # Create the natal chart object using Kerykeion
            natal_kerykeion_chart = Ker(
                 natal_data["name"],
                 natal_data["datetime"].year, natal_data["datetime"].month, natal_data["datetime"].day,
                 natal_data["datetime"].hour, natal_data["datetime"].minute, natal_data["datetime"].second, # Include seconds
                 city="Unknown", nation="Unknown", # Placeholder
                 lat=natal_data["latitude"], lon=natal_data["longitude"],
                 h_sys=house_system_name
             )

            # Use TransitsTimeRange to find transits
            # Check Kerykeion docs for TransitsTimeRange usage.
            # It likely takes the natal chart, start/end datetimes, orb, and potentially lists of planets/aspects.

            try:
                 # Example based on TransitsTimeRange documentation:
                 transits_calculator = TransitsTimeRange(
                     natal_kerykeion_chart,
                     start_date=start_datetime.date(), # TransitsTimeRange might work with dates or datetimes, check docs
                     end_date=end_datetime.date(), # Assuming it works with dates for the range
                     orb=orb
                     # Pass specific transiting/natal planets or aspects if needed and supported
                     # transiting_planets=['Sun', 'Moon', 'Mercury'], # Example
                     # natal_planets=['Sun', 'Moon', 'Ascendant'], # Example
                     # aspects=['conjunction', 'square', 'trine'] # Example (using Kerykeion's aspect names)
                 )

                 # Get the list of transits found within the range
                 # Check docs for the method to get results, e.g., .get_transits() or similar
                 found_transits = transits_calculator.get_transits() # Assuming this method exists

                 # Format the transit results
                 transit_results_list: List[Dict[str, Any]] = []
                 # The format of 'found_transits' depends on Kerykeion's output.
                 # It might be a list of objects, dictionaries, or tuples.
                 # Iterate through found_transits and extract relevant data.
                 # Example assuming each transit object has properties like .transiting_planet, .natal_planet, .aspect, .exact_date, .orb_on_exact
                 for transit in found_transits:
                     # Ensure these properties exist based on Kerykeion's TransitsTimeRange output
                     transit_results_list.append({
                         "transiting_planet": transit.transiting_planet.name, # Assuming name property
                         "natal_point": transit.natal_planet.name, # Assuming name property (can be planet or angle like Asc/MC)
                         "aspect": transit.aspect.name, # Assuming name property
                         "exact_datetime_utc": transit.exact_date.isoformat().replace('+00:00', 'Z'), # Assuming exact_date is a datetime
                         "orb_at_exact": round(transit.orb_on_exact, 4), # Assuming orb_on_exact property
                         "ideal_angle_deg": round(transit.aspect.angle, 4) # Assuming aspect object has angle
                         # Kerykeion might provide ingress/egress dates, add if available and desired
                         # "ingress_datetime_utc": transit.ingress_date.isoformat().replace('+00:00', 'Z') if hasattr(transit, 'ingress_date') else None,
                         # "egress_datetime_utc": transit.egress_date.isoformat().replace('+00:00', 'Z') if hasattr(transit, 'egress_date') else None,
                     })

                 # Optionally, sort transits by date
                 transit_results_list.sort(key=lambda x: x['exact_datetime_utc'])


            except Exception as transit_error:
                 print(f"Error calculating transits: {transit_error}")
                 traceback.print_exc()
                 return ToolResponse(
                     tool_call_id=call.tool_call_id,
                     is_successful=False,
                     error=f"Failed to calculate transits: {transit_error}"
                 )


            # --- Return the result ---
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=True,
                result={
                    "natal_chart_name": natal_data["name"],
                    "time_range_utc": {
                        "start": start_datetime.isoformat().replace('+00:00', 'Z'),
                        "end": end_datetime.isoformat().replace('+00:00', 'Z')
                    },
                    "orb_used": orb,
                    "transits": transit_results_list
                }
            )

        except ValueError as ve:
             print(f"Input error in get_transits_over_time_range: {ve}")
             return ToolResponse(tool_call_id=call.tool_call_id, is_successful=False, error=f"Input error: {ve}")
        except Exception as e:
            print(f"An unexpected error occurred in get_transits_over_time_range: {e}")
            traceback.print_exc()
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=False,
                error=f"An internal server error occurred: {e}"
            )

    # --- Placeholder for Detailed Report Generation ---
    # This functionality is complex and would likely involve:
    # 1. Calculating all chart data (positions, aspects, houses, dignities, etc. - using generate_birth_chart_data internally).
    # 2. Interpreting this data based on astrological rules and principles.
    # 3. Generating coherent, human-readable text.
    # This is a significant task that often requires a large knowledge base or integration with an LLM.
    # We'll define the tool method structure here as a placeholder.

    def generate_detailed_report(self, call: ToolCall) -> ToolResponse:
        """
        Generates a detailed astrological report based on a birth chart.
        Note: This is a complex task and the implementation here is a placeholder.
        Full implementation requires astrological interpretation logic and text generation.

        Expected parameters in ToolCall.parameters:
        - time_utc: str (Required) - Birth time in ISO 8601 format.
        - latitude: float (Optional) - Birth latitude. Defaults to environment variable.
        - longitude: float (Optional) - Birth longitude. Defaults to environment variable.
        - name: str (Optional) - Name for the chart.
        - house_system: str (Optional) - House system. Defaults to 'Placidus'.
        # Add parameters for report type, length, focus areas if needed
        """
        try:
            # Parse and validate input data using the helper
            birth_data = self._parse_birth_data(call.parameters)
            house_system_name = call.parameters.get("house_system", "Placidus")

            print(f"Generating detailed report for {birth_data['name']}")

            # --- Placeholder: Implement Report Generation Logic ---
            # This would involve:
            # 1. Calculating chart data (call generate_birth_chart_data's internal logic).
            # 2. Interpreting the chart data.
            # 3. Generating text.
            # This is a significant development effort.
            # For now, return a placeholder response.

            report_text = (
                f"This is a placeholder for a detailed astrological report for {birth_data['name']} born on {birth_data['datetime'].isoformat()} at Lat {birth_data['latitude']}, Lon {birth_data['longitude']} using the {house_system_name} house system.\n\n"
                "Full report generation requires astrological interpretation logic and text generation, which are not yet implemented in this tool."
            )


            # --- Return the result ---
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=True,
                result={
                    "name": birth_data["name"],
                    "report_text": report_text,
                    "status": "Partial Implementation: Report generation not fully implemented."
                }
            )

        except ValueError as ve:
             print(f"Input error in generate_detailed_report: {ve}")
             return ToolResponse(tool_call_id=call.tool_call_id, is_successful=False, error=f"Input error: {ve}")
        except Exception as e:
            print(f"An unexpected error occurred in generate_detailed_report: {e}")
            traceback.print_exc()
            return ToolResponse(
                tool_call_id=call.tool_call_id,
                is_successful=False,
                error=f"An internal server error occurred: {e}"
            )
