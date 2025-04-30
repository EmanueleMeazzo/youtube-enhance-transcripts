import argparse
import os
import sys
import re
import json
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
import google.generativeai as genai
from dotenv import load_dotenv
import math # For floor function

# --- Configuration ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Helper Functions ---

def get_video_id(url):
    """Extracts the YouTube video ID from various URL formats."""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'youtu\.be\/([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def ensure_dir_exists(filename):
    """Creates the directory for the filename if it doesn't exist."""
    output_dir = os.path.dirname(filename)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
            print(f"Created directory: {output_dir}")
            return True
        except OSError as e:
            print(f"Error creating directory {output_dir}: {e}")
            return False
    return True

def save_json_transcript(data, filename):
    """Saves the transcript data (list of dicts) as a JSON file."""
    if not ensure_dir_exists(filename):
        return False
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        # Confirmation message logic moved to main()
        return True
    except IOError as e:
        print(f"Error saving JSON to file {filename}: {e}")
    except TypeError as e:
         print(f"Error serializing transcript data to JSON: {e}")
    return False

def format_srt_timestamp(seconds):
    """Converts seconds to SRT timestamp format HH:MM:SS,ms."""
    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)

    hours = math.floor(milliseconds / 3_600_000)
    milliseconds -= hours * 3_600_000

    minutes = math.floor(milliseconds / 60_000)
    milliseconds -= minutes * 60_000

    seconds = math.floor(milliseconds / 1_000)
    milliseconds -= seconds * 1_000

    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def generate_srt_content(transcript_data):
    """Generates SRT formatted string from transcript data."""
    srt_content = []
    for i, segment in enumerate(transcript_data):
        start_time = segment.get('start', 0)
        # Calculate end time, handling potential missing duration gracefully
        duration = segment.get('duration')
        if duration is None:
             # Estimate duration if missing (e.g., based on next segment start?)
             # For now, just use a small default or skip? Let's use start + small default
             print(f"Warning: Segment {i+1} missing duration. Using start time only for end.")
             end_time = start_time + 1 # Add 1 second default? Or handle differently?
             # A better approach might be needed if duration is often missing.
        else:
             end_time = start_time + duration

        text = segment.get('text', '').strip()
        if not text: # Skip empty segments
            continue

        srt_content.append(str(i + 1)) # Sequence number
        srt_content.append(f"{format_srt_timestamp(start_time)} --> {format_srt_timestamp(end_time)}")
        srt_content.append(text)
        srt_content.append("") # Blank line separator

    return "\n".join(srt_content)

def save_text_file(content, filename):
    """Saves plain text content to a file."""
    if not ensure_dir_exists(filename):
        return False
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except IOError as e:
        print(f"Error saving text file {filename}: {e}")
        return False


def get_transcript(video_id, preferred_language=None):
    """
    Fetches the transcript for a given video ID as a list of dictionaries.
    Returns the transcript data (list of dicts) and the detected language code.
    """
    # --- (Keep the existing get_transcript logic as it was) ---
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = None
        detected_language = None
        available_langs = {t.language_code: t for t in transcript_list}

        if preferred_language and preferred_language in available_langs:
            try:
                print(f"Attempting to fetch specified language: {preferred_language}")
                transcript = transcript_list.find_transcript([preferred_language])
                detected_language = preferred_language
            except NoTranscriptFound:
                print(f"Specified language '{preferred_language}' not found as a manual transcript.")
                pass

        if not transcript and preferred_language:
             try:
                 print(f"Attempting to find generated transcript for: {preferred_language}")
                 transcript = transcript_list.find_generated_transcript([preferred_language])
                 detected_language = preferred_language
             except NoTranscriptFound:
                 print(f"Generated transcript for '{preferred_language}' not found.")
                 pass

        if not transcript:
            print("Attempting to find any generated transcript...")
            try:
                generated_transcripts = [t for t in transcript_list if t.is_generated]
                if generated_transcripts:
                     transcript = generated_transcripts[0]
                     detected_language = transcript.language_code
                     print(f"Found generated transcript in: {detected_language}")
                else:
                     print("No generated transcripts found.")
            except Exception as e:
                 print(f"Error finding generated transcript: {e}")
                 pass

        if not transcript:
            print("Attempting to find any manual transcript...")
            try:
                manual_transcripts = [t for t in transcript_list if not t.is_generated]
                if manual_transcripts:
                    transcript = manual_transcripts[0]
                    detected_language = transcript.language_code
                    print(f"Found manual transcript in: {detected_language}")
                else:
                    print("No manual transcripts found.")
            except Exception as e:
                 print(f"Error finding manual transcript: {e}")
                 pass


        if not transcript:
            print(f"Error: No suitable transcript found for video ID: {video_id}")
            print(f"Available languages were: {list(available_langs.keys())}")
            return None, None

        transcript_data = transcript.fetch()
        return transcript_data, detected_language

    except TranscriptsDisabled:
        print(f"Error: Transcripts are disabled for video ID: {video_id}")
        return None, None
    except Exception as e:
        print(f"An unexpected error occurred fetching transcript for {video_id}: {e}")
        return None, None


def enhance_with_gemini(transcript_data, target_language_code, original_language_code, api_key):
    """
    Sends structured transcript data to Gemini for enhancement, preserving structure.
    Expects and returns data as a list of dictionaries.
    """
    # --- (Keep the existing enhance_with_gemini logic as it was) ---
    if not api_key:
        print("Error: Gemini API key not found. Set the GEMINI_API_KEY environment variable.")
        return None

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-pro-latest')

    language_instruction = ""
    if target_language_code == original_language_code:
        language_instruction = f"The transcript text is in '{original_language_code}'. Please enhance the 'text' field in each object in the same language."
    else:
        language_instruction = f"The original transcript text is in '{original_language_code}'. Please translate and enhance the 'text' field in each object into '{target_language_code}'."

    try:
        transcript_json_string = json.dumps(transcript_data, ensure_ascii=False, indent=2)
    except TypeError as e:
        print(f"Error converting transcript data to JSON for Gemini prompt: {e}")
        return None

    prompt = f"""
You are an expert assistant tasked with enhancing YouTube video transcripts while preserving their original timing structure.
Please take the following transcript data, provided as a JSON list of objects (each with 'text', 'start', and 'duration'), and improve the quality of the 'text' field within each object. Focus on:
1.  Correcting punctuation and capitalization within each 'text' field.
2.  Improving sentence structure and flow for better readability within each 'text' field. Do NOT merge text content across different JSON objects in the list. Enhance text strictly within its original segment.
3.  Correcting grammatical errors within each 'text' field.
4.  Ensure the core meaning and information from the original transcript are preserved within each segment.
5.  Crucially, return the result as a valid JSON list of objects in the *exact same format* as the input, preserving the original 'start' and 'duration' values for each segment, modifying *only* the 'text' field values.

{language_instruction}

Return *only* the valid JSON output, starting with '[' and ending with ']'. Do not include any introductory text, explanations, or markdown formatting like ```json ... ``` before or after the JSON data.

Original Transcript Data (JSON):
---
{transcript_json_string}
---

Enhanced Transcript Data (JSON):
"""

    print(f"\nSending transcript structure to Gemini for enhancement (Original: {original_language_code}, Target: {target_language_code})...")

    try:
        # Optional: Configure safety settings if needed
        # safety_settings = [...]
        # response = model.generate_content(prompt, safety_settings=safety_settings)
        response = model.generate_content(prompt)

        if response.parts:
             response_text = response.text.strip()
             # Clean potential markdown fences
             if response_text.startswith("```json"):
                 response_text = response_text[7:]
             if response_text.startswith("```"):
                  response_text = response_text[3:]
             if response_text.endswith("```"):
                 response_text = response_text[:-3]
             response_text = response_text.strip()

             try:
                enhanced_data = json.loads(response_text)
                if not isinstance(enhanced_data, list):
                     print("Error: Gemini response was not a valid JSON list.")
                     print("--- Gemini Raw Response Text ---")
                     print(response_text)
                     print("------------------------------")
                     return None
                if enhanced_data and not all(isinstance(item, dict) and 'text' in item and 'start' in item for item in enhanced_data): # Duration might be optional from source
                      print("Warning: Gemini response is a list, but some items lack expected structure ('text', 'start').")

                print("Enhancement successful. Received structured data.")
                return enhanced_data
             except json.JSONDecodeError as e:
                 print(f"Error: Failed to parse Gemini response as JSON. Error: {e}")
                 print("--- Gemini Raw Response Text ---")
                 print(response_text)
                 print("------------------------------")
                 return None
        else:
             print("Error: Received an empty or invalid response from Gemini.")
             # print("Full Gemini Response:", response) # Debugging
             return None

    except Exception as e:
        print(f"An error occurred calling the Gemini API: {e}")
        # print("Full Gemini Response candidates (if available):", getattr(response, 'candidates', 'N/A')) # More Debugging
        return None

# --- Main Execution ---

def main():
    parser = argparse.ArgumentParser(description="Enhance YouTube video transcripts using Gemini, outputting SRT by default.")
    parser.add_argument("url", help="The URL of the YouTube video.")
    parser.add_argument("-l", "--language", help="Target language code (e.g., 'en', 'it', 'es', 'fr'). Enhances in original language if omitted.", default=None)
    parser.add_argument("-f", "--format", help="Output format for the enhanced transcript.", choices=['srt', 'json'], default='srt')
    parser.add_argument("-o", "--output", help="Optional: File path for the ENHANCED transcript. Overrides the default name based on video ID and format.", default=None)
    parser.add_argument("-s", "--save-original", help="Optional: File path to save the ORIGINAL transcript (JSON format with timestamps).", default=None)
    parser.add_argument("-k", "--api_key", help="Optional: Gemini API Key (overrides environment variable).", default=None)

    args = parser.parse_args()

    # Determine API Key
    api_key_to_use = args.api_key if args.api_key else GEMINI_API_KEY
    if not api_key_to_use:
         print("Error: Gemini API key not provided. Use -k or set GEMINI_API_KEY.")
         sys.exit(1)

    # Get Video ID
    video_id = get_video_id(args.url)
    if not video_id:
        print(f"Error: Could not extract video ID from URL: {args.url}")
        sys.exit(1)

    print(f"Processing Video ID: {video_id}")

    # --- Determine Output Filenames ---
    output_format = args.format.lower()
    file_extension = f".{output_format}"
    default_enhanced_filename = f"{video_id}_enhanced{file_extension}"
    enhanced_output_filepath = args.output if args.output else default_enhanced_filename
    # Ensure the provided output path has the correct extension if overriding
    if args.output and not args.output.lower().endswith(file_extension):
         print(f"Warning: Provided output filename '{args.output}' does not end with '{file_extension}'. Using it as is.")
         # Or force the extension: enhanced_output_filepath = f"{os.path.splitext(args.output)}{file_extension}"

    original_output_filepath = args.save_original # Stays JSON

    # Get Transcript Data
    original_transcript_data, detected_lang = get_transcript(video_id, args.language)

    if not original_transcript_data:
        sys.exit(1)

    print(f"Successfully fetched transcript data. Detected language: {detected_lang}. Segments: {len(original_transcript_data)}")

    # Save Original Transcript if requested (always saves as JSON)
    if original_output_filepath:
        if save_json_transcript(original_transcript_data, original_output_filepath):
             print(f"Original transcript data saved to: {original_output_filepath}")
        else:
             print(f"Failed to save original transcript to {original_output_filepath}")

    # Determine target language for Gemini
    target_language = args.language if args.language else detected_lang
    if not target_language:
         print("Error: Could not determine a target language for enhancement.")
         sys.exit(1)

    # Enhance Transcript Data
    enhanced_transcript_data = enhance_with_gemini(original_transcript_data, target_language, detected_lang, api_key_to_use)

    if enhanced_transcript_data:
        # --- Print Human-Readable Output to Terminal ---
        print("\n--- Enhanced Transcript (Human Readable) ---")
        human_readable_text = " ".join(segment.get('text', '') for segment in enhanced_transcript_data).strip()
        print(human_readable_text if human_readable_text else "(No text content)")
        print("------------------------------------------\n")

        # --- Save Enhanced Transcript to File (Based on Format) ---
        save_successful = False
        if output_format == 'srt':
            srt_content = generate_srt_content(enhanced_transcript_data)
            save_successful = save_text_file(srt_content, enhanced_output_filepath)
        elif output_format == 'json':
            save_successful = save_json_transcript(enhanced_transcript_data, enhanced_output_filepath)
        else: # Should not happen due to argparse choices
             print(f"Error: Unsupported output format '{output_format}' selected.")
             sys.exit(1)

        # Print confirmation message
        if save_successful:
             print(f"Enhanced Transcript saved to {enhanced_output_filepath}")
        else:
             print(f"Failed to save enhanced transcript to {enhanced_output_filepath}")
             # Optionally exit if saving is critical
             # sys.exit(1)

    else:
        print("Failed to enhance transcript data.")
        sys.exit(1)

if __name__ == "__main__":
    main()