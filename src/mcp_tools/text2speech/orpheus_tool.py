import os
from mcp_tools.text2speech.orpheus_tool import generate_speech, is_tool_configured

# Ensure the environment variable is set before calling is_tool_configured or generate_speech
# This is typically handled by your Docker Compose setup or execution environment.
# os.environ['ORPHEUS_TTS_URL'] = 'http://orpheus-fastapi-mcp:5005/v1' # Example

if is_tool_configured():
    text = "Agent speaking. Task complete."
    voice = "dan"
    audio_bytes = generate_speech(text=text, voice=voice)

    if audio_bytes:
        # Do something with audio_bytes, e.g., save, stream, etc.
        with open("agent_output.wav", "wb") as f:
            f.write(audio_bytes)
        print("Agent speech saved.")
    else:
        print("Failed to generate agent speech.")
else:
    print("TTS tool not configured. Cannot generate speech.")