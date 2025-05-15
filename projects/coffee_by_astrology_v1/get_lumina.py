import numpy as np
import ollama
import shutil
from pathlib import Path
import datetime




# create_horoscope_prompt (no changes needed, parsing format adjusted in save_planet_positions)
def create_horoscope_prompt(folder, json_data_dict):
    
    try:
        for file in Path(folder).glob('*.txt'):
        
            zodiac_sign = json_data_dict['zodiac_sign']
            # Adjust parsing format to match the saved format (milliseconds + Z)
            datetime_obj_utc = datetime.datetime.strptime(json_data_dict['time_utc'], '%Y-%m-%dT%H:%M:%S.%fZ')
            date_str = datetime_obj_utc.strftime('%Y-%m-%d')
            focus_planet = json_data_dict['focus_planet']
            positions_summary, aspects_summary = [], []
            if 'positions' in json_data_dict and isinstance(json_data_dict['positions'], dict):
                for name, data in json_data_dict['positions'].items():
                    retro = " (R)" if data.get('retrograde', False) else ""
                    positions_summary.append(f"{name} in {data.get('zodiac', '?')}{retro}")
            if 'aspects' in json_data_dict and isinstance(json_data_dict['aspects'], list):
                for aspect in json_data_dict['aspects']:
                    aspects_summary.append(f"{aspect.get('planet1','?')} {aspect.get('aspect','?')} {aspect.get('planet2','?')} ({aspect.get('angle','?')}°)")
            prompt_text = f"""
            You are an expert astrologer. Generate a daily horoscope for {zodiac_sign} on {date_str}.
            Consider the following astrological data:
            - Focus planet: {focus_planet}
            - Planetary positions: {', '.join(positions_summary) if positions_summary else "N/A"}
            - Key aspects: {', '.join(aspects_summary[:5]) if aspects_summary else "N/A"}{" (showing first 5)" if len(aspects_summary) > 5 else ""}
        You are the lead monologue writer for a popular animated astrology web cartoon. Your task is to write an engaging, original, and character-consistent monologue for the show’s central figure:

        CHARACTER PROFILE:
        Name: Lumina

        Vibe: Bubbly, loud, and unapologetically caffeinated — like someone who just drank five cosmic lattes and saw their birth chart come to life.

        Tone: Sarcastic, witty, warm-hearted but with a sharp tongue. Think astrologer meets stand-up comic meets chaos gremlin.

        Quirks: Tends to interrupt herself mid-thought. Talks to her pet as if it understands astrology. Always walks the line between “mystical insight” and “comedic meltdown.”

       
        MONOLOGUE STRUCTURE:
        Opening: Begins with an over-the-top reaction to the featured sign or the astrological mood of the day. Imagine she just burst through the cosmic curtain yelling, “Buckle up, Scorpio—it’s going to be a full-throttle Pluto day!”

        Core Astrology Breakdown (In-character):

        Focus on the ruling planet of the day’s featured sign.

        Discuss the current planetary aspects (conjunctions, squares, etc.) in simple, punchy, hilarious metaphors (“Mars is sextile Venus today, which means someone’s probably going to flirt-slash-fight over oat milk again.”)

        Tie in themes like love, money, career, and spiritual drama—but with sass.

        Story or Analogy:

        Include a brief, funny anecdote or ridiculous metaphor that illustrates today’s planetary mood. (“This morning, I spilled coffee on my chart and now Neptune’s clearly in my 6th house of chaos.”)

        Closing Call to Action:

        End with a playful wink to the audience.

        Example: “Drop a comment if Mercury ruined your morning. Again. And hit that like and follow before my familiar eats my moon water.”

        ADDITIONAL STYLE NOTES:
        Dialogue should sound like it’s being delivered to camera, breaking the fourth wall often.

        Use strong comedic timing, exaggerated pauses, fake whispers, sudden shouting—all in text form.


        Language should feel signature, like no other astrologer on the internet—equal parts cosmic guru and caffeinated rockstar.
        Avoid jargon unless it’s immediately explained in a funny way.

            🌌 [ASTRO INSIGHT BREAKDOWN]
            “So {sign_name}'s ruling planet is currently moonwalking through a sign it absolutely does *not* pay rent in. Add a square from Mars and boom—you’ve got emotional karaoke in your career zone and maybe a little flirty text from an ex who’s ‘found themselves.’ Again.”

            💸 [CAREER / MONEY / LOVE]
            - Love? Risky, like trying to use Mercury Retrograde to schedule a wedding.
            - Career? Great day to *pretend* to be productive.
            - Finances? Don’t buy another crystal. You’re still paying off the last one.
            - Spiritual Growth? Depends—are you gonna finish that shadow work journal or just light another candle and hope for the best?

            ☕ [OUTRO - THE CTA]
            “Drop a comment if today’s vibes are too real, be sure and like and follow me for more cosmic chaos breakdowns!”

            """
            return prompt_text
    except KeyError as ke:
        logging.error(f"Missing key in JSON for prompt creation: {ke}", exc_info=True)
        return f"Error: Missing key '{ke}' in JSON data."
    except ValueError as ve: # Catch potential strptime errors
         logging.error(f"Error parsing time_utc in JSON: {json_data_dict.get('time_utc')}. Error: {ve}", exc_info=True)
         return f"Error: Could not parse time_utc '{json_data_dict.get('time_utc')}'."
    except Exception as e:
        logging.error(f"Error creating horoscope prompt: {e}", exc_info=True)
        return f"Error: Could not create prompt: {str(e)}"


