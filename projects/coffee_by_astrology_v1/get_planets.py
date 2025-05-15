import datetime
import json
import logging
import os
from datetime import timezone # Correct import for timezone
from skyfield.api import load, Loader
import numpy as np
import ollama # Official Ollama Python library
import shutil
from pathlib import Path

# Configure logging
log_filename = 'planet_positions.log'
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename=log_filename,
                    filemode='w') # Overwrite log file each run

# --- Base Directory Paths ---
# Ensure these are all Path objects for correct path manipulation
BASE_PROJECT_DIR = Path(r"D:\AI\mcp_operator\projects\coffee_by_astrology_v1")
BASE_CHARTS_DIR = BASE_PROJECT_DIR / "charts"  # This will be a Path object
BASE_SCRIPTS_OUTPUT_DIR = BASE_PROJECT_DIR / "scripts_output"  # This will be a Path object
SKYFIELD_DATA_PATH = BASE_PROJECT_DIR / "skyfield_data" # Store Skyfield data within the project
PERSONALITY_PROFILE_PATH = BASE_PROJECT_DIR / "prompt_style" / "lumina_alone.txt"


# Function to clear all files and subdirectories
def clear_folder(directory_path_str):
    """Clear all files and subdirectories in the specified folder."""
    directory_path = Path(directory_path_str) # Convert string to Path for robust operations
    try:
        if not directory_path.exists():
            logging.info(f"Directory {directory_path} does not exist, no files/folders to clear.")
            return
        if not directory_path.is_dir():
            logging.error(f"Path {directory_path} is not a directory. Cannot clear.")
            return
        logging.warning(f"--- Clearing all contents within: {directory_path} ---")
        for item in directory_path.iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink() # Removes a file or a symbolic link
                logging.info(f"Deleted file/link: {item}")
            elif item.is_dir():
                shutil.rmtree(item) # Recursively delete directory and its contents
                logging.info(f"Deleted directory: {item}")
        logging.info(f"Finished clearing contents in {directory_path}")
    except Exception as e:
        logging.error(f"Error clearing directory {directory_path}: {e}", exc_info=True)

# Custom JSON encoder for NumPy types
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.float32, np.float64)): return float(obj)
        if isinstance(obj, (np.int32, np.int64)): return int(obj)
        if isinstance(obj, np.bool_): return bool(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super().default(obj)

# Constants for astrological data
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

def get_zodiac_sign(longitude_degrees):
    """Determines the zodiac sign for a given ecliptic longitude."""
    signs = [('Aries', 0), ('Taurus', 30), ('Gemini', 60), ('Cancer', 90), ('Leo', 120),
             ('Virgo', 150), ('Libra', 180), ('Scorpio', 210), ('Sagittarius', 240),
             ('Capricorn', 270), ('Aquarius', 300), ('Pisces', 330)]
    lon = longitude_degrees % 360.0 # Normalize longitude
    for sign, start_deg in signs:
        if start_deg <= lon < start_deg + 30:
            return sign
    # Fallback for the very end of Pisces or if lon is exactly 360 (which % 360.0 makes 0)
    return 'Pisces' if lon >= 330 else 'Aries'


def get_planet_positions(aware_datetime_utc, skyfield_loader):
    """Calculates astrological data (positions, signs, retrograde, aspects) using Skyfield."""
    try:
        ts = skyfield_loader.timescale()
        t = ts.from_datetime(aware_datetime_utc)

        eph = skyfield_loader('de421.bsp') # Standard ephemeris
        planets_to_calculate = list(PLANET_KEYS.keys())
        
        cartesian_positions = {}
        planet_signs = {}
        planet_retrograde = {}
        planet_longitudes = {} # Store longitudes for aspect calculation
        aspects = []
        
        earth = eph['EARTH']

        for planet_name_lower in planets_to_calculate:
            planet_skyfield_key = PLANET_KEYS[planet_name_lower]
            celestial_body = eph[planet_skyfield_key]
            
            astrometric = earth.at(t).observe(celestial_body)
            
            ecliptic_lat, ecliptic_lon, _ = astrometric.ecliptic_latlon()
            current_longitude_degrees = ecliptic_lon.degrees

            planet_name_capitalized = planet_name_lower.capitalize()
            planet_signs[planet_name_capitalized] = get_zodiac_sign(current_longitude_degrees)
            planet_longitudes[planet_name_capitalized] = current_longitude_degrees

            ra, dec, distance = astrometric.radec()
            ra_rad, dec_rad, dist_au = ra.radians, dec.radians, distance.au
            x = dist_au * np.cos(dec_rad) * np.cos(ra_rad) * 100.0
            y = dist_au * np.cos(dec_rad) * np.sin(ra_rad) * 100.0
            z = dist_au * np.sin(dec_rad) * 100.0
            cartesian_positions[planet_name_capitalized] = {'x': float(x), 'y': float(y), 'z': float(z)}

            datetime_plus_1_min = aware_datetime_utc + datetime.timedelta(minutes=1)
            t_plus_1_min = ts.from_datetime(datetime_plus_1_min)
            astrometric_plus_1_min = earth.at(t_plus_1_min).observe(celestial_body)
            _, ecliptic_lon_plus_1_min, _ = astrometric_plus_1_min.ecliptic_latlon()

            delta_lon = ecliptic_lon_plus_1_min.degrees - current_longitude_degrees
            if delta_lon < -180.0: delta_lon += 360.0
            elif delta_lon > 180.0: delta_lon -= 360.0
            
            if planet_name_lower in ['sun', 'moon']:
                planet_retrograde[planet_name_capitalized] = False
            else:
                planet_retrograde[planet_name_capitalized] = delta_lon < 0

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
                            'sign1': planet_signs[p1_name], 'sign2': planet_signs[p2_name]
                        })
                        break 
        
        logging.info("Calculated planetary positions, signs, retrograde status, and aspects.")
        return cartesian_positions, planet_signs, planet_retrograde, aspects
    except Exception as e:
        logging.error(f"Error in get_planet_positions: {e}", exc_info=True)
        raise


def save_planet_positions(cartesian_positions, planet_signs, planet_retrograde, aspects, now_aware_utc, sign, output_dir_path_obj):
    """Saves the calculated planetary data to a JSON file in the specified directory Path object."""
    try:
        time_utc_str = now_aware_utc.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        focus_planet = ZODIAC_RULERS.get(sign, "Unknown Ruler")
        
        final_positions_data = {}
        for planet_cap_name, pos_coords in cartesian_positions.items():
            if planet_cap_name in planet_signs and planet_cap_name in planet_retrograde:
                final_positions_data[planet_cap_name] = {
                    "x": pos_coords['x'], "y": pos_coords['y'], "z": pos_coords['z'],
                    "zodiac": planet_signs[planet_cap_name],
                    "retrograde": planet_retrograde[planet_cap_name]
                }
            else:
                logging.warning(f"Data for planet {planet_cap_name} (sign/retrograde) missing for {sign}, not included in JSON.")

        data_to_save = {
            "time_utc": time_utc_str, 
            "zodiac_sign": sign, 
            "focus_planet": focus_planet,
            "positions": final_positions_data, 
            "aspects": aspects, 
            "zodiac_rulers": ZODIAC_RULERS
        }
        
        date_time_file_str = now_aware_utc.strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"planet_positions_{date_time_file_str}_{sign}.json"
        filepath = output_dir_path_obj / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=4, cls=NumpyEncoder)
        logging.info(f"Saved planet positions for {sign} to {filepath}")
    except Exception as e:
        logging.error(f"Error saving planet positions for {sign} to {output_dir_path_obj}: {e}", exc_info=True)


def create_horoscope_prompt(json_data_dict, profile_content=""):
    """Creates a horoscope prompt based on JSON data and a personality profile."""
    try:
        zodiac_sign = json_data_dict['zodiac_sign']
        datetime_obj_utc = datetime.datetime.strptime(json_data_dict['time_utc'], '%Y-%m-%dT%H:%M:%S.%fZ')
        date_str = datetime_obj_utc.strftime('%Y-%m-%d') # For display in prompt
        focus_planet = json_data_dict['focus_planet']
        
        positions_summary_sentences = []
        aspects_summary_sentences = []

        if 'positions' in json_data_dict and isinstance(json_data_dict['positions'], dict):
            for planet_name, data in json_data_dict['positions'].items():
                zodiac_name = data.get('zodiac', 'an unknown sign')
                is_retrograde = data.get('retrograde', False)
                if is_retrograde:
                    positions_summary_sentences.append(f"{planet_name} is in the sign of {zodiac_name} and is currently retrograde.")
                else:
                    positions_summary_sentences.append(f"{planet_name} is in the sign of {zodiac_name}.")

        aspect_phrasing_map = {
            "conjunction": "is conjunct with", "opposition": "is in opposition to",
            "trine": "is trine", "square": "is square to", "sextile": "is sextile",
        }

        if 'aspects' in json_data_dict and isinstance(json_data_dict['aspects'], list):
            for aspect in json_data_dict['aspects']:
                planet1_name = aspect.get('planet1', 'An unknown planet')
                aspect_name_raw = aspect.get('aspect', 'an unknown aspect') 
                planet2_name = aspect.get('planet2', 'another unknown planet')
                angle_value = aspect.get('angle', 'unknown') 
                
                aspect_description = aspect_phrasing_map.get(aspect_name_raw.lower(), f"is in a {aspect_name_raw} aspect with")
                
                try:
                    angle_degrees = float(angle_value)
                    angle_display = f"an orb of approximately {angle_degrees:.0f}°" 
                except ValueError:
                    angle_display = f"an orb of {angle_value}°" if angle_value != 'unknown' else "(orb not specified)"
                
                aspects_summary_sentences.append(f"{planet1_name} {aspect_description} {planet2_name}, with {angle_display}.")

        # Construct the narrative data section
        data_narrative = f"Today, {date_str}, the cosmos presents an interesting picture for {zodiac_sign}."
        if focus_planet:
            data_narrative += f" The focus planet for {zodiac_sign} is {focus_planet}."
        
        if positions_summary_sentences:
            data_narrative += f" Here's a look at the current planetary placements: {' '.join(positions_summary_sentences)}"
        else:
            data_narrative += " Planetary positions are not specifically highlighted for today's main focus."

        if aspects_summary_sentences:
            key_aspects_list = aspects_summary_sentences[:5] # Show first 5 aspects
            key_aspects_text = ' '.join(key_aspects_list)
            aspects_note = " (among other influences, we're noting these first few)" if len(aspects_summary_sentences) > 5 and key_aspects_list else ""
            if key_aspects_text:
                data_narrative += f" In terms of significant interactions, we're seeing these key aspects: {key_aspects_text}{aspects_note}."
            else:
                data_narrative += " No major planetary aspects are taking center stage for this reading."
        else:
            data_narrative += " No specific planetary aspects are being emphasized at this moment."


        effective_profile = profile_content.strip() if profile_content and profile_content.strip() else "Default Astrologer Profile: Insightful, wise, and slightly mysterious."

        # MODIFIED prompt_text to integrate data_narrative
        prompt_text = f"""
You are an expert astrologer. Your task is to generate a daily horoscope for {zodiac_sign}.
{data_narrative}

Based on this astrological backdrop, provide a deep, research-level astrological analysis rooted in the current planetary positions, with a primary focus on the Sun sign of the ruling planet of the featured zodiac sign.
Begin with a breakdown of today's astrological transits and planetary placements—especially the ruling planet of the zodiac sign in question.
Analyze how this planet's position and aspects (conjunctions, oppositions, squares, trines, sextiles, etc.) shape the day's energy.
Consider the energetic expression and elemental alignment of each planet within its current zodiac sign, especially in relation to:
The power and nature of the planet itself
The characteristics and modality of the sign it inhabits
The relational aspects between this ruling planet and other celestial bodies
Based on this astrological configuration, provide a detailed daily horoscope for the featured sign, covering key life domains:
Love & Relationships
Career & Ambition
Money & Finances
Spirituality & Inner Growth
Health & Physical Energy (if relevant)
Include a summary section that outlines:
The major themes or lessons of the day
Energetic “highs” and “lows”
Symbolic or archetypal interpretations if applicable (e.g., mythological resonance or planetary rulership myths)

Your monologue should be engaging, original, and character-consistent with the following profile:
--- PROFILE START ---
{effective_profile}
--- PROFILE END ---
Be sure to blend the astrological analysis with humor, wit, and a touch of cosmic chaos. Use metaphors and analogies to make complex astrological concepts relatable and entertaining. 
Point out the aspects but dont detail it like a science report mention and explain Make sure the whole thing can
be read in a paragraph form and not in bullet points. Dont use characters (#/!/@/#/$/%/^/&/()) or any other symbols to separate the text.
"""
        return prompt_text
    except KeyError as ke:
        logging.error(f"Missing key in JSON for prompt creation: {ke}", exc_info=True)
        return f"Error: Missing key '{ke}' in JSON data."
    except ValueError as ve:
        logging.error(f"Error parsing time_utc in JSON: {json_data_dict.get('time_utc')}. Error: {ve}", exc_info=True)
        return f"Error: Could not parse time_utc '{json_data_dict.get('time_utc')}'."
    except Exception as e:
        logging.error(f"Error creating horoscope prompt: {e}", exc_info=True)
        return f"Error: Could not create prompt: {str(e)}"


def generate_horoscope(prompt: str):
    """Generates a horoscope using the Ollama API."""
    response_content, api_response_data = None, None
    if not isinstance(prompt, str) or prompt.startswith("Error:"):
        logging.error(f"Skipping Ollama call due to invalid prompt: {prompt}")
        return str(prompt)
    try:
        logging.info("Attempting to generate horoscope with Ollama...")
        api_response_data = ollama.generate(
            model='mistral-small:latest', 
            prompt=prompt,
            options={'temperature': 0.7, 'num_ctx': 4096, 'num_predict': 2000 } 
        )
        logging.info("Ollama API call completed.")
        
        if api_response_data and 'response' in api_response_data and isinstance(api_response_data['response'], str):
            response_content = api_response_data['response']
            logging.info("Successfully received response from Ollama.")
        else:
            logging.warning(f"Ollama response missing expected content. Full response: {api_response_data}")
            response_content = "Error: No valid content in Ollama response."
            
    except ollama.ResponseError as re:
        logging.error(f"Ollama API Response Error: {str(re)}", exc_info=True)
        status_code_info = f" (Status code: {re.status_code})" if hasattr(re, 'status_code') else ""
        response_content = f"Error: Ollama API error: {str(re)}{status_code_info}"
    except Exception as e:
        connect_error_messages = ["Failed to connect", "Connection refused"]
        is_connect_error = any(msg.lower() in str(e).lower() for msg in connect_error_messages)
        if is_connect_error:
            logging.error(f"Failed to connect to Ollama: {str(e)}", exc_info=True)
            response_content = f"Error: Failed to connect to Ollama. Ensure it's running/accessible. Details: {str(e)}"
        else:
            logging.error(f"Generic error during horoscope generation: {str(e)}", exc_info=True)
            api_info = f" API response data: {api_response_data}" if api_response_data else ""
            response_content = f"Error: Unexpected error during generation: {str(e)}.{api_info}"
    return response_content


def save_generated_text_file(content, filename_prefix, zodiac_sign, date_obj, output_directory_path_obj, file_format="txt"):
    """Saves the given text content to a file in the specified output directory Path object."""
    try:
        safe_zodiac_sign = "".join(c for c in zodiac_sign if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
        date_str_filename = date_obj.strftime('%Y-%m-%d')

        filename = f"{filename_prefix}_{safe_zodiac_sign}_{date_str_filename}.{file_format}"
        file_path = output_directory_path_obj / filename
        
        logging.info(f"Attempting to save file to: {file_path}")
        with open(file_path, mode='w', encoding='utf-8') as f:
            f.write(content if content else f"Error: No content provided for {filename}")
        logging.info(f"Successfully saved file: {file_path}")
        return file_path

    except OSError as oe:
        logging.error(f"OSError saving file {filename if 'filename' in locals() else 'unknown'} to {output_directory_path_obj}: {oe}", exc_info=True)
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred while saving file {filename if 'filename' in locals() else 'unknown'} to {output_directory_path_obj}: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    logging.info("--- Starting Astrology Horoscope Generation Script ---")

    # --- Load Personality Profile ---
    PROFILE_CONTENT = "" 
    try:
        with open(PERSONALITY_PROFILE_PATH, 'r', encoding='utf-8') as pf:
            PROFILE_CONTENT = pf.read()
        logging.info(f"Successfully loaded personality profile from: {PERSONALITY_PROFILE_PATH}")
    except FileNotFoundError:
        logging.error(f"Personality profile file not found at: {PERSONALITY_PROFILE_PATH}. Using default profile in prompt function.")
    except Exception as e_profile_load:
        logging.error(f"Error reading personality profile: {e_profile_load}. Using default profile in prompt function.", exc_info=True)

    # --- Get Current Time and Format for Directory Names ---
    current_run_time_aware_utc = datetime.datetime.now(timezone.utc)
    datetime_string_for_dirs = current_run_time_aware_utc.strftime("%Y-%m-%d_%H%M%S") 

    # --- Construct Date-Stamped Directory Paths ---
    # These are now Path objects due to the definitions at the top
    run_charts_dir = BASE_CHARTS_DIR / f"planet_positions_{datetime_string_for_dirs}"
    run_scripts_output_dir = BASE_SCRIPTS_OUTPUT_DIR / f"scripts_for_{datetime_string_for_dirs}"

    # --- Skyfield Loader Initialization ---
    skyfield_data_loader = None
    try:
        SKYFIELD_DATA_PATH.mkdir(parents=True, exist_ok=True) 
        skyfield_data_loader = Loader(str(SKYFIELD_DATA_PATH), verbose=True) 
        skyfield_data_loader('de421.bsp') 
        logging.info(f"Skyfield loader initialized and ephemeris loaded from: {SKYFIELD_DATA_PATH}")
    except Exception as e_load:
        logging.critical(f"Failed to initialize Skyfield Loader or load ephemeris: {e_load}", exc_info=True)
        print(f"CRITICAL ERROR: Could not initialize Skyfield Loader. Exiting. Check path: {SKYFIELD_DATA_PATH}")
        exit(1)

    # --- Main Script Logic ---
    try:
        # Optional: Clear base directories before creating new run-specific folders
        # logging.warning(f"Attempting to clear base charts directory: {BASE_CHARTS_DIR}")
        # clear_folder(str(BASE_CHARTS_DIR))
        # logging.warning(f"Attempting to clear base scripts output directory: {BASE_SCRIPTS_OUTPUT_DIR}")
        # clear_folder(str(BASE_SCRIPTS_OUTPUT_DIR))

        run_charts_dir.mkdir(parents=True, exist_ok=True)
        run_scripts_output_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Run charts directory: {run_charts_dir}")
        logging.info(f"Run scripts output directory: {run_scripts_output_dir}")

        logging.info(f"Calculating planetary data for: {current_run_time_aware_utc.isoformat()}")
        all_positions, all_signs, all_retrograde, all_aspects = get_planet_positions(current_run_time_aware_utc, skyfield_data_loader)

        logging.info(f"Saving planetary data JSON files to {run_charts_dir}...")
        for zodiac_s in ZODIAC_SIGNS:
            save_planet_positions(all_positions, all_signs, all_retrograde, all_aspects, 
                                  current_run_time_aware_utc, zodiac_s, run_charts_dir)
        logging.info("JSON data files for all signs saved.")

        logging.info(f"Processing JSON files from {run_charts_dir} to generate horoscopes...")
        json_files_processed_count = 0
        for chart_json_filepath in run_charts_dir.glob('*.json'):
            json_files_processed_count += 1
            logging.info(f"Processing JSON file: {chart_json_filepath.name}")
            try:
                with open(chart_json_filepath, 'r', encoding='utf-8') as chart_file:
                    loaded_json_data = json.load(chart_file)

                horoscope_prompt = create_horoscope_prompt(loaded_json_data, PROFILE_CONTENT)
                generated_horoscope_text = generate_horoscope(horoscope_prompt)

                output_zodiac_sign = loaded_json_data.get('zodiac_sign', 'UnknownSign')
                time_utc_from_json_str = loaded_json_data.get('time_utc', current_run_time_aware_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
                
                datetime_for_filename = current_run_time_aware_utc 
                display_date_str = current_run_time_aware_utc.strftime('%Y-%m-%d')
                try:
                    dt_from_json = datetime.datetime.strptime(time_utc_from_json_str, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
                    datetime_for_filename = dt_from_json
                    display_date_str = dt_from_json.strftime('%Y-%m-%d')
                except ValueError as ve_parse_json_time:
                    logging.warning(f"Could not parse date '{time_utc_from_json_str}' from JSON {chart_json_filepath.name}: {ve_parse_json_time}. Using current run time for filename date.")
                
                print(f"\n--- Horoscope for {output_zodiac_sign} on {display_date_str} ---")
                print(generated_horoscope_text if generated_horoscope_text else "No horoscope generated or error occurred.")
                print("--- End Horoscope ---")

                save_generated_text_file(
                    content=generated_horoscope_text,
                    filename_prefix="horoscope",
                    zodiac_sign=output_zodiac_sign,
                    date_obj=datetime_for_filename, 
                    output_directory_path_obj=run_scripts_output_dir, 
                    file_format="txt"
                )

            except json.JSONDecodeError as jde:
                logging.error(f"Error reading/decoding JSON file {chart_json_filepath.name}: {jde}", exc_info=True)
            except KeyError as ke:
                logging.error(f"Missing key while processing data from {chart_json_filepath.name}: {ke}", exc_info=True)
            except Exception as e_file_processing:
                logging.error(f"General error processing file {chart_json_filepath.name}: {e_file_processing}", exc_info=True)

        if json_files_processed_count == 0:
            logging.warning(f"No JSON files found in {run_charts_dir} to process.")
        
        logging.info("--- Astrology Horoscope Generation Script Finished ---")

    except Exception as e_main_script:
        print(f"CRITICAL: Main script execution failed: {e_main_script}")
        logging.critical(f"Main script execution failed: {e_main_script}", exc_info=True)
