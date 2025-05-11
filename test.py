import os
import asyncio
import requests # Although not directly used in the tool call simulation, useful for debugging server accessibility
import uuid # To generate unique tool_call_id
import sys

# Assume the tool file is located at src/mcp_tools/text2speech/orpheus_tool.py
# Adjust the import path if your file structure is different
try:
    # Try importing from mcp.tools first, as this is a common location
    from mcp.tools import ToolCall, ToolResponse, Tool
    print("MCP SDK classes imported from mcp.tools.")
except ImportError:
    try:
        # Fallback to importing directly from mcp (less common for Tool classes)
        from mcp import ToolCall, ToolResponse, Tool
        print("MCP SDK classes imported directly from mcp.")
    except ImportError as e:
        print(f"Error importing MCP Python SDK Tool classes: {e}")
        print("Please ensure the 'mcp' package is installed correctly and includes ToolCall, ToolResponse, and Tool classes.")
        print("Using mock classes for ToolCall and ToolResponse.")
        # Define mock classes for testing if the MCP SDK Tool classes are not available
        class ToolCall:
            def __init__(self, tool_name: str, tool_call_id: str, parameters: dict):
                self.tool_name = tool_name
                self.tool_call_id = tool_call_id
                self.parameters = parameters

        class ToolResponse:
            def __init__(self, tool_call_id: str, is_successful: bool, result: dict = None, error: str = None):
                self.tool_call_id = tool_call_id
                self.is_successful = is_successful
                self.result = result
                self.error = error

            def __str__(self):
                status = "SUCCESS" if self.is_successful else "FAILURE"
                output = f"Tool Call ID: {self.tool_call_id}\nStatus: {status}\n"
                if self.is_successful:
                    output += f"Result: {self.result}"
                else:
                    output += f"Error: {self.error}"
                return output

        # Define a mock Tool class if the real one couldn't be imported
        class Tool:
            @property
            def tool_name(self) -> str:
                raise NotImplementedError("Mock Tool class requires tool_name property")

            # Note: Mock Tool does not implement __call__ as it's not needed for this test script's structure

# Import the OrpheusTTSTool from your project
try:
    # Assuming the tool file is at src/mcp_tools/text2speech/orpheus_tool.py
    # Add the src directory to the Python path to allow importing from src.mcp_tools
    # Get the directory of the current script (test.py)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Get the project root directory (assuming test.py is in the root)
    project_root = script_dir
    # Add the 'src' directory to the Python path
    src_path = os.path.join(project_root, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
        print(f"Added '{src_path}' to sys.path")

    from mcp_tools.text2speech.orpheus_tool import OrpheusTTSTool
    print("OrpheusTTSTool imported successfully.")

except ImportError as e:
    print(f"Error importing OrpheusTTSTool: {e}")
    print("Please ensure 'orpheus_tool.py' is in 'src/mcp_tools/text2speech/' relative to test.py")
    # Exit the script if the tool itself cannot be imported
    sys.exit("Failed to import OrpheusTTSTool. Exiting.")


async def main():
    """
    Main function to demonstrate calling the OrpheusTTSTool.
    """
    # --- Configuration ---
    # Ensure the ORPHEUS_FASTAPI_URL environment variable is set
    orpheus_api_url = os.environ.get("ORPHEUS_FASTAPI_URL")
    if not orpheus_api_url:
        print("Error: ORPHEUS_FASTAPI_URL environment variable is not set.")
        print("Please set it to the URL of your running Orpheus-FastAPI instance (e.g., http://localhost:5005).")
        return

    # Optional: Configure a base URL if you want to test the URL output
    # This URL should point to where your 'audio' directory is served statically.
    # If not set, the tool will only return the local file path.
    # Based on previous conversation, this should be http://localhost:8000/audio
    outputs_web_base_url = os.environ.get("OUTPUTS_WEB_BASE_URL", None)
    if not outputs_web_base_url:
        print("Note: OUTPUTS_WEB_BASE_URL environment variable is not set.")
        print("The tool will only return local file paths, not web URLs for audio.")
    else:
         print(f"Using OUTPUTS_WEB_BASE_URL: {outputs_web_base_url}")


    # --- Instantiate the Tool ---
    # Pass the outputs_web_base_url during initialization
    orpheus_tool = OrpheusTTSTool(outputs_web_base_url=outputs_web_base_url)
    print(f"Tool '{orpheus_tool.tool_name}' instantiated.")

    # --- Simulate a Tool Call ---
    # Define the parameters for the 'generate_speech' action
    test_parameters = {
        "text": "Hello world! This is a test of the Orpheus Text to Speech tool.",
        "voice": "tara", # Choose an available voice
        "speed": 1.0,    # Optional speed factor
        "response_format": "wav" # Optional format (Orpheus-FastAPI currently supports wav)
    }

    # Create a mock ToolCall object
    # The MCP framework would normally create this
    mock_tool_call = ToolCall(
        tool_name=orpheus_tool.tool_name, # Use the actual tool_name property
        tool_call_id=str(uuid.uuid4()), # Generate a unique ID for this call
        parameters=test_parameters
    )
    print(f"\nSimulating ToolCall with ID: {mock_tool_call.tool_call_id}")
    print(f"Parameters: {mock_tool_call.parameters}")

    # --- Call the Tool's Action ---
    # Await the asynchronous tool method
    print("\nCalling tool action 'generate_speech'...")
    # Call the specific action method on the tool instance
    response = await orpheus_tool.generate_speech(mock_tool_call)

    # --- Process and Print the Response ---
    print("\n--- Tool Response ---")
    print(response)
    print("---------------------")

    if response.is_successful:
        print("\nSpeech generation successful!")
        print(f"Audio saved to: {response.result.get('audio_path')}")
        if 'audio_url' in response.result and response.result['audio_url']:
            print(f"Audio URL: {response.result.get('audio_url')}")
        else:
             print("Audio URL not available (OUTPUTS_WEB_BASE_URL not set or error in construction).")
    else:
        print("\nSpeech generation failed.")
        print(f"Error: {response.error}")

    # Optional: Add another test call with different parameters or an expected error
    # For example, testing an invalid voice:
    # print("\nSimulating ToolCall with invalid voice...")
    # mock_tool_call_invalid = ToolCall(
    #     tool_name=orpheus_tool.tool_name,
    #     tool_call_id=str(uuid.uuid4()),
    #     parameters={"text": "This should fail.", "voice": "invalid_voice"}
    # )
    # response_invalid = await orpheus_tool.generate_speech(mock_tool_call_invalid)
    # print("\n--- Tool Response (Invalid Voice) ---")
    # print(response_invalid)
    # print("-----------------------------------")


if __name__ == "__main__":
    # Run the main async function
    asyncio.run(main())
