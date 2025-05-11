# MCP Text-to-Speech Tool

This tool provides a simple Python interface for generating speech using the Orpheus-FastAPI service within the Multi-Component Project (MCP) framework. It acts as a client library, abstracting away the direct API calls to the Orpheus-FastAPI server and allowing other MCP components (like agentic LLM projects) to easily add text-to-speech capabilities.

## Purpose

The primary goal of this tool is to make it easy for any Python application or agent running within the MCP environment to convert text into audio using the high-performance Orpheus-FastAPI service. By using this tool, projects don't need to implement the API calling logic themselves, promoting code reusability, consistency, and simplifying development.

## Prerequisites

Before using this tool in your MCP component, ensure the following are in place:

1.  **Orpheus-FastAPI Service Running:** The Orpheus-FastAPI server, along with its required external LLM inference server (running the Orpheus model), must be running and accessible from where your MCP component is executing. The recommended way to achieve this is by running the integrated Docker Compose setup described in the main `mcp_operator` `docker-compose.yml` file.
2.  **Tool Code Available:** This tool's code (located within the `src/mcp_tools/text2speech/` directory in the `mcp_operator` repository) must be accessible and importable by your project. If your project is also part of the same Docker Compose setup, ensure the necessary source code is available within its container (e.g., via a `COPY` instruction in its Dockerfile or a volume mount).
3.  **Python Dependencies:** The tool uses the `requests` library to make HTTP calls. Ensure `requests` is installed in your project's Python environment:
    ```bash
    pip install requests
    ```

## Configuration

The tool needs to know the network address of the running Orpheus-FastAPI service. This is configured by setting the following environment variable in the environment where your MCP component runs:

* `ORPHEUS_TTS_URL`: The base URL of the Orpheus-FastAPI service's OpenAI-compatible endpoint.
    * If using the recommended Docker Compose setup with service name `orpheus-fastapi-mcp` in your root `docker-compose.yml`, the URL will typically be the service name and port followed by `/v1`, i.e., `http://orpheus-fastapi-mcp:5005/v1`.
    * If running Orpheus-FastAPI natively (outside of Docker Compose) on the same machine, the URL might be `http://localhost:5005/v1` or `http://127.0.0.1:5005/v1`.
    * If running Orpheus-FastAPI on a different machine, use its IP address or hostname.

Ensure this `ORPHEUS_TTS_URL` environment variable is set correctly in your component's execution environment (e.g., in the `environment` section of its service definition in the root `docker-compose.yml`, or in a `.env` file loaded by your component).

## Usage

To use the tool, import the main speech generation function (assuming it's named `generate_speech` within `orpheus_tts_tool.py` inside the `mcp_tools.text2speech` package) and call it with the text you want to convert.

```python
import os
import requests # Needed for exception handling
# Adjust the import path based on the actual location of the tool code
from mcp_tools.text2speech.orpheus_tts_tool import generate_speech

# --- Configuration (usually handled externally by environment variables in Docker) ---
# Ensure the ORPHEUS_TTS_URL environment variable is set in your project's environment.
# Example if running this script directly for testing (replace with your actual URL):
# os.environ['ORPHEUS_TTS_URL'] = 'http://localhost:5005/v1'

# --- Example Usage ---
if __name__ == "__main__":
    # Define the text and desired voice
    text_to_speak = "Hello, this is a test of the MCP Text-to-Speech tool using Orpheus-FastAPI."
    voice_name = "tara" # Choose from the available voices listed below

    # Check if the configuration is missing early
    if 'ORPHEUS_TTS_URL' not in os.environ:
        print("Error: ORPHEUS_TTS_URL environment variable is not set.")
        print("Please configure the tool by setting this variable.")
    else:
        try:
            print(f"Attempting to generate speech for text: '{text_to_speak}' using voice: '{voice_name}'")

            # Call the tool function to get the audio data
            # The function returns bytes (the audio file content) or None if an error occurred.
            audio_data = generate_speech(text=text_to_speak, voice=voice_name)

            if audio_data:
                # Process the audio_data bytes (e.g., save to a file, send over network)
                output_filename = "generated_speech.wav"
                with open(output_filename, "wb") as f:
                    f.write(audio_data)
                print(f"Speech generated successfully. Audio saved to {output_filename}")
            else:
                print("Speech generation failed. See logs for details.")

        except requests.exceptions.RequestException as e:
            print(f"Error communicating with the Orpheus-FastAPI server: {e}")
            print("Please ensure the Orpheus-FastAPI service is running and ORPHEUS_TTS_URL is set correctly.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

# --- Example with different parameters and emotion tags ---
# try:
#     text_with_emotion = "Wow, that's really surprising! <gasp>"
#     voice_leo = "leo" # Use a different voice
#     output_filename_emotion = "surprised_leo.wav"
#
#     if 'ORPHEUS_TTS_URL' in os.environ:
#         print(f"\nAttempting to generate speech with emotion: '{text_with_emotion}' using voice: '{voice_leo}'")
#
#         # Call the tool function with more parameters
#         audio_data_emotion = generate_speech(
#             text=text_with_emotion,
#             voice=voice_leo,
#             response_format="wav", # Orpheus-FastAPI currently primarily supports 'wav'
#             speed=1.05 # Slightly faster speed
#         )
#
#         if audio_data_emotion:
#             with open(output_filename_emotion, "wb") as f:
#                 f.write(audio_data_emotion)
#             print(f"Speech with emotion generated successfully. Audio saved to {output_filename_emotion}")
#         else:
#             print("Speech generation with emotion failed. See logs for details.")
#     else:
#          print("\nSkipping emotion example: ORPHEUS_TTS_URL not configured.")
#
# except requests.exceptions.RequestException as e:
#     print(f"Error communicating with the Orpheus-FastAPI server: {e}")
# except Exception as e:
#     print(f"An unexpected error occurred: {e}")