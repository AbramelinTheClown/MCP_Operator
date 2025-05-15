import pathlib
import requests # Keep for now, though not directly used in provided async funcs
import os
import shutil
from gradio_client import Client
# from gradio_client.utils import huggingface_hub # Only if direct login is used
import datetime
import json
import logging
from datetime import timezone # Correct import
from skyfield.api import load, Loader
import numpy as np
import ollama
import asyncio
import aiohttp
import itertools # For cycling through servers

# Configure logging
log_filename = 'astrology_media_generation.log'
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s',
                    filename=log_filename,
                    filemode='w')

# --- Base Directory Paths ---
BASE_PROJECT_DIR = pathlib.Path(r"D:\AI\mcp_operator\projects\coffee_by_astrology_v1") # Adjust if needed
BASE_SCRIPTS_OUTPUT_DIR = BASE_PROJECT_DIR / "scripts_output"
SKYFIELD_DATA_PATH = BASE_PROJECT_DIR / "skyfield_data"
PERSONALITY_PROFILE_PATH = BASE_PROJECT_DIR / "prompt_style" / "lumina_alone.txt"

# --- Configuration for Current Run ---
# current_run_time_aware_utc and datetime_string_for_dirs will be defined in main_async

# --- TTS API Configuration ---
TTS_API_URL = "http://localhost:5005/v1/audio/speech"
TTS_FILE_ENCODING = 'utf-8'
TTS_VOICE = "leah"
TTS_MODEL = "orpheus"
TTS_RESPONSE_FORMAT = "wav"
TTS_SPEED = 1.0
TTS_TIMEOUT_SECONDS = 180
TTS_CONCURRENCY_LIMIT = 3 # Max concurrent TTS requests

# --- Image Generation API Configuration ---
IMAGE_API_SPACE = "NihalGazi/FLUX-Pro-Unlimited"
IMAGE_API_ENDPOINT_NAME = "/generate_image"
IMAGE_SEED = 0
IMAGE_RANDOMIZE = True
IMAGE_SERVER_CHOICES = [
    "Google US Server",
    "Azure Lite Supercomputer Server",
    "Artemis GPU Super cluster",
    "NebulaDrive Tensor Server",
    "NSFW-Core: Uncensored Server"
]
IMAGE_CONCURRENCY_LIMIT = 2 # Max concurrent Image requests (total, not per server)
# HUGGINGFACE_TOKEN = "hf_YOUR_TOKEN_HERE"

# --- NEW: Image Prompt Template ---
IMAGE_PROMPT_TEMPLATE = "{zodiac_sign_lower} art style: vibrant and dynamic die cut sticker design, the zodiac symbol {zodiac_sign_lower} interlaced with cosmic galaxies, AI, stickers, high contrast, bright neon colors, top-view, high resolution, vector art, detailed stylization, modern graphic art, unique, opaque, weather resistant, UV laminated, nebula like background"

# --- Image Size Configurations ---
TIKTOK_WIDTH = 1080
TIKTOK_HEIGHT = 1920
YOUTUBE_WIDTH = 1280
YOUTUBE_HEIGHT = 720

# --- Initialize Gradio Client ---
image_client = None
try:
    print(f"Initializing Gradio client for: {IMAGE_API_SPACE}")
    logging.info(f"Initializing Gradio client for: {IMAGE_API_SPACE}")
    image_client = Client(IMAGE_API_SPACE) #, hf_token=HUGGINGFACE_TOKEN if using a private space
    print("Gradio client initialized successfully.")
    logging.info("Gradio client initialized successfully.")
except Exception as e:
    print(f"Fatal Error: Could not initialize Gradio client: {e}")
    logging.critical(f"Fatal Error: Could not initialize Gradio client: {e}", exc_info=True)
    # Depending on requirements, you might want to exit here or let the script run without image generation
    # For now, it will continue and skip image generation if image_client is None.

# --- Astrological Constants ---
PLANET_KEYS = {
    'sun': 'SUN', 'moon': 'MOON', 'mercury': 'MERCURY BARYCENTER', 'venus': 'VENUS BARYCENTER',
    'mars': 'MARS BARYCENTER', 'jupiter': 'JUPITER BARYCENTER', 'saturn': 'SATURN BARYCENTER',
    'uranus': 'URANUS BARYCENTER', 'neptune': 'NEPTUNE BARYCENTER', 'pluto': 'PLUTO BARYCENTER'
}
ZODIAC_SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
ZODIAC_RULERS = {
    'Aries': 'Mars', 'Taurus': 'Venus', 'Gemini': 'Mercury', 'Cancer': 'Moon', 'Leo': 'Sun',
    'Virgo': 'Mercury', 'Libra': 'Venus', 'Scorpio': 'Mars', 'Sagittarius': 'Jupiter',
    'Capricorn': 'Saturn', 'Aquarius': 'Uranus', 'Pisces': 'Neptune'
}

# --- Helper Functions ---
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.float32, np.float64)): return float(obj)
        if isinstance(obj, (np.int32, np.int64)): return int(obj)
        if isinstance(obj, np.bool_): return bool(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super().default(obj)

def get_zodiac_sign_from_lon(longitude_degrees):
    signs = [('Aries', 0), ('Taurus', 30), ('Gemini', 60), ('Cancer', 90), ('Leo', 120),
             ('Virgo', 150), ('Libra', 180), ('Scorpio', 210), ('Sagittarius', 240),
             ('Capricorn', 270), ('Aquarius', 300), ('Pisces', 330)]
    lon = longitude_degrees % 360.0
    for sign, start_deg in signs:
        if start_deg <= lon < start_deg + 30:
            return sign
    return 'Pisces' if lon >= 330 else 'Aries'


def get_planet_positions(aware_datetime_utc, skyfield_loader):
    try:
        ts = skyfield_loader.timescale()
        t = ts.from_datetime(aware_datetime_utc)
        eph = skyfield_loader('de421.bsp') # This loads it if not already loaded by the loader instance
        planets_to_calculate = list(PLANET_KEYS.keys())

        cartesian_positions = {}
        planet_signs_map = {}
        planet_retrograde_map = {}
        planet_longitudes = {}
        aspects = []
        earth = eph['EARTH']

        for planet_name_lower in planets_to_calculate:
            planet_skyfield_key = PLANET_KEYS[planet_name_lower]
            celestial_body = eph[planet_skyfield_key]

            astrometric = earth.at(t).observe(celestial_body)
            ecliptic_lat, ecliptic_lon, _ = astrometric.ecliptic_latlon()
            current_longitude_degrees = ecliptic_lon.degrees
            planet_name_capitalized = planet_name_lower.capitalize()
            planet_signs_map[planet_name_capitalized] = get_zodiac_sign_from_lon(current_longitude_degrees)
            planet_longitudes[planet_name_capitalized] = current_longitude_degrees

            ra, dec, distance = astrometric.radec()
            ra_rad, dec_rad, dist_au = ra.radians, dec.radians, distance.au
            x = dist_au * np.cos(dec_rad) * np.cos(ra_rad) * 100.0 # Scaling factor
            y = dist_au * np.cos(dec_rad) * np.sin(ra_rad) * 100.0 # Scaling factor
            z = dist_au * np.sin(dec_rad) * 100.0 # Scaling factor
            cartesian_positions[planet_name_capitalized] = {'x': float(x), 'y': float(y), 'z': float(z)}

            datetime_plus_1_min = aware_datetime_utc + datetime.timedelta(minutes=1)
            t_plus_1_min = ts.from_datetime(datetime_plus_1_min)
            astrometric_plus_1_min = earth.at(t_plus_1_min).observe(celestial_body)
            _, ecliptic_lon_plus_1_min, _ = astrometric_plus_1_min.ecliptic_latlon()
            delta_lon = ecliptic_lon_plus_1_min.degrees - current_longitude_degrees
            if delta_lon < -180.0: delta_lon += 360.0
            elif delta_lon > 180.0: delta_lon -= 360.0
            planet_retrograde_map[planet_name_capitalized] = delta_lon < 0 if planet_name_lower not in ['sun', 'moon'] else False

        aspect_definitions = {
            'conjunction': (0, 10), 'semisextile': (30, 2), 'sextile': (60, 6),
            'square': (90, 8), 'trine': (120, 8), 'quincunx': (150, 2),
            'opposition': (180, 10)
        }
        planet_name_list_for_aspects = list(planet_longitudes.keys())
        for i in range(len(planet_name_list_for_aspects)):
            for j in range(i + 1, len(planet_name_list_for_aspects)):
                p1_name = planet_name_list_for_aspects[i]
                p2_name = planet_name_list_for_aspects[j]
                lon1_deg = planet_longitudes[p1_name]
                lon2_deg = planet_longitudes[p2_name]
                angle_diff = abs(lon1_deg - lon2_deg)
                angular_separation = min(angle_diff, 360.0 - angle_diff)
                for aspect_name, (target_angle, orb) in aspect_definitions.items():
                    if abs(angular_separation - target_angle) <= orb:
                        aspects.append({
                            'planet1': p1_name, 'planet2': p2_name, 'aspect': aspect_name,
                            'angle': round(angular_separation, 2),
                            'sign1': planet_signs_map[p1_name], 'sign2': planet_signs_map[p2_name]
                        })
                        break
        logging.info("Calculated planetary positions, signs, retrograde status, and aspects.")
        return cartesian_positions, planet_signs_map, planet_retrograde_map, aspects
    except Exception as e:
        logging.error(f"Error in get_planet_positions: {e}", exc_info=True)
        raise

def create_horoscope_prompt(json_data_dict, profile_content=""):
    try:
        zodiac_sign = json_data_dict.get('zodiac_sign', 'Unknown Zodiac Sign')
        time_utc_str = json_data_dict.get('time_utc', datetime.datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
        try:
            datetime_obj_utc = datetime.datetime.fromisoformat(time_utc_str.replace('Z', '+00:00'))
            date_str = datetime_obj_utc.strftime('%B %d, %Y') # More readable date
        except ValueError:
            date_str = datetime.datetime.now(timezone.utc).strftime('%B %d, %Y')
            logging.warning(f"Could not parse time_utc: {time_utc_str}, using current date {date_str} in prompt.")

        focus_planet = json_data_dict.get('focus_planet', 'an important celestial body')
        positions_summary_sentences = []
        if 'positions' in json_data_dict and isinstance(json_data_dict['positions'], dict):
            for planet_name, data in json_data_dict['positions'].items():
                zodiac_name = data.get('zodiac', 'an unknown sign')
                is_retrograde = data.get('retrograde', False)
                positions_summary_sentences.append(f"{planet_name} is in {zodiac_name}{' (Retrograde)' if is_retrograde else ''}.")

        aspect_phrasing_map = {
            "conjunction": "is conjunct with", "opposition": "is in opposition to",
            "trine": "is trine", "square": "is square to", "sextile": "is sextile",
            "semisextile": "forms a semisextile with", "quincunx": "forms a quincunx with"
        }
        aspects_summary_sentences = []
        if 'aspects' in json_data_dict and isinstance(json_data_dict['aspects'], list):
            for aspect in json_data_dict['aspects']:
                p1 = aspect.get('planet1', 'PlanetX')
                desc = aspect_phrasing_map.get(aspect.get('aspect', '').lower(), f"in a {aspect.get('aspect', 'mystery')} aspect with")
                p2 = aspect.get('planet2', 'PlanetY')
                angle = aspect.get('angle', 0)
                # Only include aspects involving the focus planet or Sun/Moon for brevity, if desired
                # if p1 == focus_planet or p2 == focus_planet or p1 == "Sun" or p2 == "Sun" or p1 == "Moon" or p2 == "Moon":
                aspects_summary_sentences.append(f"{p1} {desc} {p2} (approx. {angle:.0f}°).")

        data_narrative = f"Today, {date_str}, for those born under the sign of {zodiac_sign} (whose ruling planet is {focus_planet}):\nPlanetary Placements: {' '.join(positions_summary_sentences) if positions_summary_sentences else 'General cosmic energies prevail.'}\nKey Aspects: {' '.join(aspects_summary_sentences[:5]) if aspects_summary_sentences else 'The celestial bodies are in a relatively quiet dance today.'}" # Limit aspects shown
        effective_profile = profile_content.strip() or "Default Astrologer Profile: Insightful, wise, and slightly mysterious."

        prompt_text = f"""
You are an expert astrologer with a unique voice. Your task is to generate a daily horoscope for {zodiac_sign}.
Today's Date: {date_str}
Astrological Data Snapshot: {data_narrative}

Instructions:
1.  Focus primarily on the implications for {zodiac_sign}, considering its ruling planet, {focus_planet}.
2.  Briefly touch upon the general astrological weather suggested by the planetary placements and key aspects.
3.  Provide a detailed daily horoscope for {zodiac_sign} covering these (or other relevant) life domains: Love & Relationships, Career & Ambition, Personal Growth & Well-being.
4.  Offer a concise "Cosmic Tip" or "Mantra for the Day."
5.  Ensure the horoscope is engaging, insightful, and written in paragraph form. Avoid lists, bullet points, or excessive use of special characters like #, !, @, $, %, ^, &, (, ).
6.  Maintain a consistent persona as defined by the profile below. Infuse your writing with wit, perhaps a touch of cosmic humor or metaphor, but remain grounded in plausible astrological interpretation. Explain aspects in terms of their energetic meaning, not as a dry report.

--- ASTROLOGER PROFILE START ---
{effective_profile}
--- ASTROLOGER PROFILE END ---

Begin the horoscope for {zodiac_sign}:
"""
        return prompt_text.strip()
    except Exception as e:
        logging.error(f"Error creating horoscope prompt for {json_data_dict.get('zodiac_sign', 'Unknown')}: {e}", exc_info=True)
        return f"Error: Could not create prompt due to: {str(e)}"

def generate_horoscope_with_ollama(prompt: str):
    if not isinstance(prompt, str) or prompt.startswith("Error:"):
        logging.error(f"Skipping Ollama call due to invalid prompt: {prompt}")
        return str(prompt)
    try:
        # Prepare the loggable part of the prompt separately
        log_prompt_snippet = prompt[:150].replace('\n', ' ')
        # --- Re-added this important logging line ---
        logging.info(f"Attempting Ollama generation. Prompt starts: '{log_prompt_snippet}...'")

        api_response = ollama.generate(
            model='mistral-small:latest', # Ensure this model is available in your Ollama instance
            prompt=prompt,
            options={'temperature': 0.75, 'num_ctx': 4096, 'num_predict': 2000, 'top_p': 0.9}
        )
        logging.info("Ollama API call completed.") # This log appears if ollama.generate itself doesn't raise an exception

        # --- CRITICAL MODIFICATION HERE ---
        # Check if 'response' key exists AND if its value is not None before stripping
        if api_response and 'response' in api_response and api_response['response'] is not None:
            # Also check if the stripped response is non-empty
            stripped_response = api_response['response'].strip()
            if stripped_response: # Ensure the response isn't just whitespace
                return stripped_response
            else:
                logging.warning("Ollama returned an empty or whitespace-only response.")
                return "Error: Ollama returned an empty response."
        else:
            logging.warning(f"Ollama response was invalid or missing content. API Response: {api_response}")
            return "Error: No valid content or null response in Ollama response."

    except ollama.ResponseError as re:
        logging.error(f"Ollama API Response Error: {re.error}", exc_info=True)
        return f"Error: Ollama API error (Status {re.status_code}): {re.error}"
    except Exception as e:
        logging.error(f"Generic error during Ollama generation: {e}", exc_info=True)
        return f"Error: Unexpected error during Ollama generation: {e}"


def save_generated_content(content, base_filename, zodiac_sign_str, output_type_str, current_run_output_base_dir, file_extension="txt"):
    try:
        safe_zodiac_name = "".join(c for c in zodiac_sign_str if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
        zodiac_output_dir = current_run_output_base_dir / safe_zodiac_name
        zodiac_output_dir.mkdir(parents=True, exist_ok=True)

        final_filename = f"{base_filename}.{file_extension.lstrip('.')}"
        output_filepath = zodiac_output_dir / final_filename

        if isinstance(content, bytes):
            with open(output_filepath, 'wb') as f: f.write(content)
        elif isinstance(content, str) and not os.path.exists(content): # If content is string data
            with open(output_filepath, 'w', encoding='utf-8') as f: f.write(content)
        elif isinstance(content, (str, pathlib.Path)) and os.path.exists(content): # If content is a path to a file
            shutil.copy2(str(content), output_filepath)
            # More robust check for temporary files based on typical temp patterns
            temp_dir_patterns = [os.path.normcase("/tmp/"), os.path.normcase(os.getenv("TEMP", "/usually_not_exists/")), "gradio"]
            if any(pattern in os.path.normcase(str(content)) for pattern in temp_dir_patterns if pattern):
                try:
                    os.remove(str(content))
                    logging.info(f"Removed temporary file: {content}")
                except Exception as e_rm:
                    logging.warning(f"Could not remove temporary file {content}: {e_rm}")
        else:
            logging.warning(f"Cannot save {output_type_str} for {zodiac_sign_str}: unsupported content type {type(content)} or invalid path: {content}")
            return None
        logging.info(f"Saved {output_type_str} for {zodiac_sign_str} to {output_filepath}")
        return output_filepath
    except Exception as e:
        logging.error(f"Error saving {output_type_str} for {zodiac_sign_str} to {zodiac_output_dir}: {e}", exc_info=True)
        return None

# --- Asynchronous Functions ---
async def run_with_semaphore(semaphore: asyncio.Semaphore, awaitable_task_coro):
    """ Helper to run a coroutine under semaphore control. """
    async with semaphore:
        logging.debug(f"Semaphore acquired for {awaitable_task_coro.__name__}")
        result = await awaitable_task_coro
        logging.debug(f"Semaphore released for {awaitable_task_coro.__name__}")
        return result

async def generate_tts_async(session: aiohttp.ClientSession, horoscope_script, zodiac_sign, run_output_base_dir, current_time_str):
    if not horoscope_script or horoscope_script.startswith("Error:"):
        logging.error(f"Skipping TTS for {zodiac_sign} due to invalid script.")
        return f"Error: Invalid script for TTS for {zodiac_sign}"
    try:
        logging.info(f"Async TTS request for {zodiac_sign}...")
        tts_payload = {"input": horoscope_script, "model": TTS_MODEL, "voice": TTS_VOICE,
                       "response_format": TTS_RESPONSE_FORMAT, "speed": TTS_SPEED}
        timeout = aiohttp.ClientTimeout(total=TTS_TIMEOUT_SECONDS)
        async with session.post(TTS_API_URL, json=tts_payload, timeout=timeout) as response:
            if response.status != 200:
                error_text = await response.text()
                logging.error(f"Async TTS for {zodiac_sign} failed with status {response.status}: {error_text}")
                return f"Error: TTS API Error {response.status} for {zodiac_sign}"
            response.raise_for_status() # Still useful for other non-200 errors if not caught above
            audio_content = await response.read()
        audio_base_filename = f"horoscope_audio_{current_time_str}"
        saved_path = await asyncio.to_thread(
            save_generated_content,
            audio_content, audio_base_filename, zodiac_sign,
            "TTS Audio", run_output_base_dir, TTS_RESPONSE_FORMAT
        )
        if saved_path:
            logging.info(f"Async TTS for {zodiac_sign} completed and saved to {saved_path}.")
            return saved_path
        else:
            return f"Error: Failed to save TTS audio for {zodiac_sign}"

    except aiohttp.ClientResponseError as e_tts_client_resp:
        logging.error(f"Async TTS ClientResponseError for {zodiac_sign} (URL: {e_tts_client_resp.request_info.url}, Status: {e_tts_client_resp.status}): {e_tts_client_resp.message}", exc_info=True)
        return f"Error: TTS ClientResponseError for {zodiac_sign}: {e_tts_client_resp.message}"
    except aiohttp.ClientConnectionError as e_tts_conn:
        logging.error(f"Async TTS ClientConnectionError for {zodiac_sign} (URL: {e_tts_conn.request_info.url if e_tts_conn.request_info else 'N/A'}): {e_tts_conn}", exc_info=True)
        return f"Error: TTS Connection Error for {zodiac_sign}"
    except asyncio.TimeoutError:
        logging.error(f"Async TTS for {zodiac_sign} timed out after {TTS_TIMEOUT_SECONDS} seconds.")
        return f"Error: TTS Timeout for {zodiac_sign}"
    except Exception as e_tts:
        logging.error(f"Async TTS Error for {zodiac_sign}: {e_tts}", exc_info=True)
        return f"Error: Generic TTS Error for {zodiac_sign}: {e_tts}"

async def generate_image_async(image_prompt_text, zodiac_sign, img_type, width, height, run_output_base_dir, current_time_str, server_choice):
    if not image_client:
        logging.warning(f"Image client not initialized. Skipping image generation for {zodiac_sign}.")
        return f"Error: Image client not initialized for {zodiac_sign}"
    if not image_prompt_text or image_prompt_text.startswith("Error:"):
        logging.error(f"Skipping image generation for {zodiac_sign} due to invalid image prompt.")
        return f"Error: Invalid image prompt for {zodiac_sign}"

    try:
    
        print(f"Async Generating {img_type} image for {zodiac_sign} using server: {server_choice}...")

        # Gradio client predict call is blocking, so run in a thread
        img_path_result = await asyncio.to_thread(
            image_client.predict,
            prompt=image_prompt_text,
            width=width,
            height=height,
            seed=IMAGE_SEED,
            randomize=IMAGE_RANDOMIZE,
            server_choice=server_choice,
            api_name=IMAGE_API_ENDPOINT_NAME
        )

        temp_img_path = None
        if isinstance(img_path_result, str) and os.path.exists(img_path_result):
            temp_img_path = img_path_result
        elif isinstance(img_path_result, dict) and 'path' in img_path_result and os.path.exists(img_path_result['path']): # Some Gradio versions might return a dict
            temp_img_path = img_path_result['path']

        if temp_img_path:
            img_ext = pathlib.Path(temp_img_path).suffix.lstrip('.') or "png" # Default to png
            img_base_filename = f"{img_type.lower()}_image_{current_time_str}"
            saved_path = await asyncio.to_thread(
                save_generated_content,
                temp_img_path, img_base_filename, zodiac_sign,
                f"{img_type} Image", run_output_base_dir, img_ext
            )
            if saved_path:
                logging.info(f"Async {img_type} Image for {zodiac_sign} (server: {server_choice}) completed and saved to {saved_path}.")
                return saved_path
            else:
                return f"Error: Failed to save {img_type} image for {zodiac_sign}"
        else:
            logging.error(f"Async {img_type} Image Error for {zodiac_sign} (server: {server_choice}): Invalid result or path from Gradio: {img_path_result}")
            return f"Error: Invalid Gradio result for {img_type} image for {zodiac_sign}"
    except Exception as e_img: # Catch specific Gradio errors if known, otherwise generic
        logging.error(f"Async {img_type} Image Generation Error for {zodiac_sign} with server '{server_choice}': {e_img}", exc_info=True)
        return f"Error: Generic {img_type} Image Generation Error for {zodiac_sign}: {e_img}"


async def main_async():
    # --- Define run-specific directories and timestamps ---
    current_run_time_aware_utc = datetime.datetime.now(timezone.utc)
    datetime_string_for_dirs = current_run_time_aware_utc.strftime("%Y-%m-%d_%H%M%S")
    run_output_base_dir = BASE_SCRIPTS_OUTPUT_DIR / f"run_{datetime_string_for_dirs}"
    run_output_base_dir.mkdir(parents=True, exist_ok=True)
    # Consistent timestamp string for all filenames within this run
    current_run_time_filename_str = current_run_time_aware_utc.strftime('%Y%m%d_%H%M')

    logging.info(f"--- Starting Astrology Horoscope Generation Script --- Run ID: {datetime_string_for_dirs} ---")
    logging.info(f"Base output for this run: {run_output_base_dir}")

    PROFILE_CONTENT = ""
    try:
        if PERSONALITY_PROFILE_PATH.exists():
            PROFILE_CONTENT = PERSONALITY_PROFILE_PATH.read_text(encoding='utf-8')
            logging.info(f"Loaded personality profile: {PERSONALITY_PROFILE_PATH}")
        else:
            logging.warning(f"Personality profile not found: {PERSONALITY_PROFILE_PATH}. Using default.")
    except Exception as e:
        logging.error(f"Error reading profile {PERSONALITY_PROFILE_PATH}: {e}. Using default.", exc_info=True)

    skyfield_data_loader = None
    try:
        SKYFIELD_DATA_PATH.mkdir(parents=True, exist_ok=True)
        skyfield_data_loader = Loader(str(SKYFIELD_DATA_PATH), verbose=False) # verbose=False for less console noise
        # Ensure ephemeris is available (download if needed, load if present)
        # This is blocking, run in thread
        await asyncio.to_thread(skyfield_data_loader, 'de421.bsp')
        logging.info(f"Skyfield setup complete. Ephemeris: de421.bsp loaded from {SKYFIELD_DATA_PATH}")
    except Exception as e:
        logging.critical(f"Skyfield init failed from {SKYFIELD_DATA_PATH}: {e}", exc_info=True)
        print(f"CRITICAL: Skyfield init failed. Check logs at {log_filename}. Exiting.")
        return

    all_cartesian_pos, all_planet_signs, all_planet_retrograde, all_aspects_list = {}, {}, {}, []
    try:
        logging.info(f"Calculating planetary data for {current_run_time_aware_utc.isoformat()}...")
        all_cartesian_pos, all_planet_signs, all_planet_retrograde, all_aspects_list = await asyncio.to_thread(
            get_planet_positions, current_run_time_aware_utc, skyfield_data_loader
        )
    except Exception as e:
        logging.critical(f"Planetary data calculation failed: {e}", exc_info=True)
        print(f"CRITICAL: Planetary data calculation failed. Check logs at {log_filename}. Exiting.")
        return

    # --- Semaphores for API call concurrency control ---
    tts_semaphore = asyncio.Semaphore(TTS_CONCURRENCY_LIMIT)
    image_semaphore = asyncio.Semaphore(IMAGE_CONCURRENCY_LIMIT)

    all_pending_media_tasks = [] # Store all asyncio.create_task(run_with_semaphore(...)) calls
    image_server_cycle = itertools.cycle(IMAGE_SERVER_CHOICES)

    async with aiohttp.ClientSession() as http_session: # Single session for all TTS calls
        for current_zodiac_sign in ZODIAC_SIGNS:
            try:
                print(f"\n--- Processing Zodiac Sign: {current_zodiac_sign} ---")
                logging.info(f"--- Processing Zodiac Sign: {current_zodiac_sign} ---")

                # --- Prepare Data for this Zodiac Sign ---
                time_utc_for_json = current_run_time_aware_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                current_focus_planet = ZODIAC_RULERS.get(current_zodiac_sign, "Unknown Ruler")
                positions_for_json = {
                    p_name: {"x": c_pos['x'], "y": c_pos['y'], "z": c_pos['z'],
                             "zodiac": all_planet_signs.get(p_name, "N/A"),
                             "retrograde": all_planet_retrograde.get(p_name, False)}
                    for p_name, c_pos in all_cartesian_pos.items() if p_name in all_planet_signs # Ensure consistency
                }
                json_data_for_sign = {
                    "time_utc": time_utc_for_json, "zodiac_sign": current_zodiac_sign,
                    "focus_planet": current_focus_planet, "positions": positions_for_json,
                    "aspects": all_aspects_list, "zodiac_rulers": ZODIAC_RULERS
                }

                # Save Planetary Data JSON (threaded)
                json_base_filename = f"planetary_data_{current_run_time_filename_str}"
                json_str_content = await asyncio.to_thread(json.dumps, json_data_for_sign, indent=4, cls=NumpyEncoder)
                await asyncio.to_thread(
                    save_generated_content,
                    json_str_content, json_base_filename, current_zodiac_sign, "Planetary JSON",
                    run_output_base_dir, "json"
                )

                # Generate Horoscope Script (threaded Ollama call)
                horoscope_prompt_text = await asyncio.to_thread(create_horoscope_prompt, json_data_for_sign, PROFILE_CONTENT)
                generated_horoscope_script = await asyncio.to_thread(generate_horoscope_with_ollama, horoscope_prompt_text)

                if generated_horoscope_script and not generated_horoscope_script.startswith("Error:"):
                    script_base_filename = f"horoscope_script_{current_run_time_filename_str}"
                    await asyncio.to_thread(
                        save_generated_content,
                        generated_horoscope_script, script_base_filename, current_zodiac_sign,
                        "Horoscope Text", run_output_base_dir, "txt"
                    )
                  
                    # --- Script is ready, create media generation tasks immediately ---
                    logging.info(f"Creating TTS task for {current_zodiac_sign}")
                    tts_coro = generate_tts_async(
                        http_session, generated_horoscope_script, current_zodiac_sign,
                        run_output_base_dir, current_run_time_filename_str
                    )
                    all_pending_media_tasks.append(
                        asyncio.create_task(run_with_semaphore(tts_semaphore, tts_coro), name=f"TTS_{current_zodiac_sign}")
                    )

                    if image_client:
                        specific_image_prompt = IMAGE_PROMPT_TEMPLATE.format(zodiac_sign_lower=current_zodiac_sign.lower())
                        
                        # TikTok Image Task
                        tiktok_server = next(image_server_cycle)
                        logging.info(f"Creating TikTok image task for {current_zodiac_sign} via {tiktok_server}")
                        tiktok_image_coro = generate_image_async(
                            specific_image_prompt, current_zodiac_sign, "TikTok",
                            TIKTOK_WIDTH, TIKTOK_HEIGHT, run_output_base_dir,
                            current_run_time_filename_str, tiktok_server
                        )
                        all_pending_media_tasks.append(
                            asyncio.create_task(run_with_semaphore(image_semaphore, tiktok_image_coro), name=f"TikTokImage_{current_zodiac_sign}")
                        )

                        # YouTube Image Task
                        youtube_server = next(image_server_cycle)
                        logging.info(f"Creating YouTube image task for {current_zodiac_sign} via {youtube_server}")
                        youtube_image_coro = generate_image_async(
                            specific_image_prompt, current_zodiac_sign, "YouTube",
                            YOUTUBE_WIDTH, YOUTUBE_HEIGHT, run_output_base_dir,
                            current_run_time_filename_str, youtube_server
                        )
                        all_pending_media_tasks.append(
                            asyncio.create_task(run_with_semaphore(image_semaphore, youtube_image_coro), name=f"YouTubeImage_{current_zodiac_sign}")
                        )
                    else:
                        logging.warning(f"Image client not available. Skipping image generation for {current_zodiac_sign}.")
                else:
                    logging.error(f"Horoscope script generation failed for {current_zodiac_sign}: {generated_horoscope_script}. Dependent media will be skipped.")
                    print(f"ERROR: Horoscope script generation failed for {current_zodiac_sign}. Check logs at {log_filename}.")

            except Exception as e_sign_loop:
                logging.error(f"Major error during processing for Zodiac Sign {current_zodiac_sign}: {e_sign_loop}", exc_info=True)
                print(f"ERROR processing script for {current_zodiac_sign}. Check logs at {log_filename}. Continuing to next sign...")

    # --- Wait for all initiated media tasks to complete ---
    if all_pending_media_tasks:
        logging.info(f"Waiting for {len(all_pending_media_tasks)} media generation tasks to complete...")
        print(f"\n--- All scripts generated. Now processing {len(all_pending_media_tasks)} media tasks (TTS/Images)... ---")
        results = await asyncio.gather(*all_pending_media_tasks, return_exceptions=True)
        
        completed_count = 0
        failed_count = 0
        for i, result in enumerate(results):
            task_name = all_pending_media_tasks[i].get_name() if hasattr(all_pending_media_tasks[i], 'get_name') else f"Task_{i}"
            if isinstance(result, Exception) or (isinstance(result, str) and result.startswith("Error:")):
                failed_count +=1
                logging.error(f"Media task {task_name} failed: {result}", exc_info=result if isinstance(result, BaseException) else False)
                print(f"ERROR: Media task {task_name} failed. Check {log_filename}.")
            else:
                completed_count +=1
                logging.info(f"Media task {task_name} completed successfully. Result: {str(result)[:100]}")
        logging.info(f"Media generation summary: {completed_count} succeeded, {failed_count} failed.")
        print(f"Media generation summary: {completed_count} succeeded, {failed_count} failed.")
    else:
        logging.info("No media generation tasks were created or initiated.")

    logging.info(f"--- Astrology Horoscope Generation Script Finished --- Run ID: {datetime_string_for_dirs} ---")
    print(f"\n--- All processing finished. Outputs are in: {run_output_base_dir} ---")
    print(f"Log file: {log_filename}")

async def main_async():
    # ... (initial setup code as in your script) ...
    # --- Define run-specific directories and timestamps ---
    current_run_time_aware_utc = datetime.datetime.now(timezone.utc)
    datetime_string_for_dirs = current_run_time_aware_utc.strftime("%Y-%m-%d_%H%M%S")
    run_output_base_dir = BASE_SCRIPTS_OUTPUT_DIR / f"run_{datetime_string_for_dirs}"
    run_output_base_dir.mkdir(parents=True, exist_ok=True)
    # Consistent timestamp string for all filenames within this run
    current_run_time_filename_str = current_run_time_aware_utc.strftime('%Y%m%d_%H%M')

    logging.info(f"--- Starting Astrology Horoscope Generation Script --- Run ID: {datetime_string_for_dirs} ---")
    logging.info(f"Base output for this run: {run_output_base_dir}")

    PROFILE_CONTENT = ""
    try:
        if PERSONALITY_PROFILE_PATH.exists():
            PROFILE_CONTENT = PERSONALITY_PROFILE_PATH.read_text(encoding='utf-8')
            logging.info(f"Loaded personality profile: {PERSONALITY_PROFILE_PATH}")
        else:
            logging.warning(f"Personality profile not found: {PERSONALITY_PROFILE_PATH}. Using default.")
    except Exception as e:
        logging.error(f"Error reading profile {PERSONALITY_PROFILE_PATH}: {e}. Using default.", exc_info=True)

    skyfield_data_loader = None
    try:
        SKYFIELD_DATA_PATH.mkdir(parents=True, exist_ok=True)
        skyfield_data_loader = Loader(str(SKYFIELD_DATA_PATH), verbose=False) # verbose=False for less console noise
        await asyncio.to_thread(skyfield_data_loader, 'de421.bsp')
        logging.info(f"Skyfield setup complete. Ephemeris: de421.bsp loaded from {SKYFIELD_DATA_PATH}")
    except Exception as e:
        logging.critical(f"Skyfield init failed from {SKYFIELD_DATA_PATH}: {e}", exc_info=True)
        print(f"CRITICAL: Skyfield init failed. Check logs at {log_filename}. Exiting.")
        return

    all_cartesian_pos, all_planet_signs, all_planet_retrograde, all_aspects_list = {}, {}, {}, []
    try:
        logging.info(f"Calculating planetary data for {current_run_time_aware_utc.isoformat()}...")
        all_cartesian_pos, all_planet_signs, all_planet_retrograde, all_aspects_list = await asyncio.to_thread(
            get_planet_positions, current_run_time_aware_utc, skyfield_data_loader
        )
    except Exception as e:
        logging.critical(f"Planetary data calculation failed: {e}", exc_info=True)
        print(f"CRITICAL: Planetary data calculation failed. Check logs at {log_filename}. Exiting.")
        return

    tts_semaphore = asyncio.Semaphore(TTS_CONCURRENCY_LIMIT)
    image_semaphore = asyncio.Semaphore(IMAGE_CONCURRENCY_LIMIT)
    all_pending_media_tasks = []
    image_server_cycle = itertools.cycle(IMAGE_SERVER_CHOICES)

    async with aiohttp.ClientSession() as http_session:
        for current_zodiac_sign in ZODIAC_SIGNS:
            try:
                print(f"\n--- Processing Zodiac Sign: {current_zodiac_sign} ---")
                logging.info(f"--- Processing Zodiac Sign: {current_zodiac_sign} ---")

                time_utc_for_json = current_run_time_aware_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                current_focus_planet = ZODIAC_RULERS.get(current_zodiac_sign, "Unknown Ruler")
                positions_for_json = {
                    p_name: {"x": c_pos['x'], "y": c_pos['y'], "z": c_pos['z'],
                             "zodiac": all_planet_signs.get(p_name, "N/A"),
                             "retrograde": all_planet_retrograde.get(p_name, False)}
                    for p_name, c_pos in all_cartesian_pos.items() if p_name in all_planet_signs
                }
                json_data_for_sign = {
                    "time_utc": time_utc_for_json, "zodiac_sign": current_zodiac_sign,
                    "focus_planet": current_focus_planet, "positions": positions_for_json,
                    "aspects": all_aspects_list, "zodiac_rulers": ZODIAC_RULERS
                }

                json_base_filename = f"planetary_data_{current_run_time_filename_str}"
                json_str_content = await asyncio.to_thread(json.dumps, json_data_for_sign, indent=4, cls=NumpyEncoder)
                await asyncio.to_thread(
                    save_generated_content,
                    json_str_content, json_base_filename, current_zodiac_sign, "Planetary JSON",
                    run_output_base_dir, "json"
                )

                horoscope_prompt_text = await asyncio.to_thread(create_horoscope_prompt, json_data_for_sign, PROFILE_CONTENT)
                generated_horoscope_script = await asyncio.to_thread(generate_horoscope_with_ollama, horoscope_prompt_text)
                
                # --- This is the critical conditional logic ---
                if generated_horoscope_script and not generated_horoscope_script.startswith("Error:"):
                    # --- Script is considered good ---
                    script_base_filename = f"horoscope_script_{current_run_time_filename_str}"
                    await asyncio.to_thread(
                        save_generated_content,
                        generated_horoscope_script, script_base_filename, current_zodiac_sign,
                        "Horoscope Text", run_output_base_dir, "txt"
                    )
                    
                    # --- Re-added this print for successful script snippet ---
                    log_script_snippet = generated_horoscope_script[:100].replace('\n',' ')
                    print(f"Generated horoscope script for {current_zodiac_sign} (first 100 chars): {log_script_snippet}...\n")
                    logging.info(f"Horoscope script for {current_zodiac_sign} generated and saved.")

                    # --- Create media generation tasks ---
                    logging.info(f"Creating TTS task for {current_zodiac_sign}")
                    tts_coro = generate_tts_async(
                        http_session, generated_horoscope_script, current_zodiac_sign,
                        run_output_base_dir, current_run_time_filename_str
                    )
                    all_pending_media_tasks.append(
                        asyncio.create_task(run_with_semaphore(tts_semaphore, tts_coro), name=f"TTS_{current_zodiac_sign}")
                    )

                    if image_client:
                        specific_image_prompt = IMAGE_PROMPT_TEMPLATE.format(zodiac_sign_lower=current_zodiac_sign.lower())
                        tiktok_server = next(image_server_cycle)
                        logging.info(f"Creating TikTok image task for {current_zodiac_sign} via {tiktok_server}")
                        tiktok_image_coro = generate_image_async(
                            specific_image_prompt, current_zodiac_sign, "TikTok",
                            TIKTOK_WIDTH, TIKTOK_HEIGHT, run_output_base_dir,
                            current_run_time_filename_str, tiktok_server
                        )
                        all_pending_media_tasks.append(
                            asyncio.create_task(run_with_semaphore(image_semaphore, tiktok_image_coro), name=f"TikTokImage_{current_zodiac_sign}")
                        )

                        youtube_server = next(image_server_cycle)
                        logging.info(f"Creating YouTube image task for {current_zodiac_sign} via {youtube_server}")
                        youtube_image_coro = generate_image_async(
                            specific_image_prompt, current_zodiac_sign, "YouTube",
                            YOUTUBE_WIDTH, YOUTUBE_HEIGHT, run_output_base_dir,
                            current_run_time_filename_str, youtube_server
                        )
                        all_pending_media_tasks.append(
                            asyncio.create_task(run_with_semaphore(image_semaphore, youtube_image_coro), name=f"YouTubeImage_{current_zodiac_sign}")
                        )
                    else:
                        logging.warning(f"Image client not available. Skipping image generation for {current_zodiac_sign}.")
                else:
                    # --- Script is considered bad or an error string ---
                    logging.error(f"Horoscope script generation failed for {current_zodiac_sign}: {generated_horoscope_script}. Dependent media will be skipped.")
                    print(f"ERROR: Horoscope script generation failed for {current_zodiac_sign}. Check logs at {log_filename}.")

            except Exception as e_sign_loop:
                logging.error(f"Major error during processing for Zodiac Sign {current_zodiac_sign}: {e_sign_loop}", exc_info=True)
                print(f"ERROR processing script for {current_zodiac_sign}. Check logs at {log_filename}. Continuing to next sign...")
    
    # ... (rest of main_async, including asyncio.gather, etc.)
    if all_pending_media_tasks:
        logging.info(f"Waiting for {len(all_pending_media_tasks)} media generation tasks to complete...")
        print(f"\n--- All scripts generated. Now processing {len(all_pending_media_tasks)} media tasks (TTS/Images)... ---")
        results = await asyncio.gather(*all_pending_media_tasks, return_exceptions=True)
        
        completed_count = 0
        failed_count = 0
        for i, result in enumerate(results):
            task_name = all_pending_media_tasks[i].get_name() if hasattr(all_pending_media_tasks[i], 'get_name') else f"Task_{i}"
            if isinstance(result, Exception) or (isinstance(result, str) and result.startswith("Error:")):
                failed_count +=1
                logging.error(f"Media task {task_name} failed: {result}", exc_info=result if isinstance(result, BaseException) else False)
                print(f"ERROR: Media task {task_name} failed. Check {log_filename}.")
            else:
                completed_count +=1
                logging.info(f"Media task {task_name} completed successfully. Result: {str(result)[:100]}")
        logging.info(f"Media generation summary: {completed_count} succeeded, {failed_count} failed.")
        print(f"Media generation summary: {completed_count} succeeded, {failed_count} failed.")
    else:
        logging.info("No media generation tasks were created or initiated.")

    logging.info(f"--- Astrology Horoscope Generation Script Finished --- Run ID: {datetime_string_for_dirs} ---")
    print(f"\n--- All processing finished. Outputs are in: {run_output_base_dir} ---")
    print(f"Log file: {log_filename}")

if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except Exception as e_main_script:
        print(f"CRITICAL: Main script execution failed: {e_main_script}")
        logging.critical(f"Main script execution failed: {e_main_script}", exc_info=True)
        with open(log_filename, 'a') as f:
            import traceback
            f.write(f"\nCRITICAL ERROR in __main__: {e_main_script}\n")
            traceback.print_exc(file=f)