# youtube-enhance-transcripts
A command-line Python application to fetch transcripts from YouTube videos, enhance their quality (punctuation, grammar, structure), optionally translate them using Google's Gemini API, and save the result as an SRT caption file (or JSON).

## Description

This tool automates the process of obtaining a YouTube video's transcript and refining it for better readability and accuracy. It leverages the `youtube-transcript-api` library to retrieve available transcripts (including timestamps) and the `google-generativeai` library to send the structured text data to the Gemini 1.5 Pro model for enhancement and optional translation while preserving timing information.

The enhanced transcript is saved by default as an SRT (`.srt`) file, suitable for uploading directly to YouTube.

## Features

*   **Fetch Transcripts:** Retrieves available transcripts for a given YouTube video URL, preserving timing data (start, duration). It intelligently tries to find manual or generated transcripts.
*   **Enhance Quality:** Sends the structured transcript data to the Gemini API with instructions to:
    *   Correct punctuation and capitalization within each text segment.
    *   Improve sentence structure and flow within each text segment.
    *   Fix grammatical errors within each text segment.
    *   Preserve the original timing for each segment.
*   **Translate:** Optionally translate the transcript into a specified target language during the enhancement process.
*   **Output Formats:**
    *   **SRT (Default):** Saves the enhanced transcript as a `.srt` file, formatted correctly for direct upload to YouTube or use in video players.
    *   **JSON (Optional):** Saves the enhanced transcript as a `.json` file, preserving the structured list of segments with text, start time, and duration, useful for further programmatic use.
*   **Human-Readable Console Output:** Prints the full, enhanced transcript text (concatenated) to the terminal for quick review.
*   **Save Original:** Option to save the *original*, un-enhanced transcript data (including timestamps) as a JSON file for comparison or backup.
*   **Command-Line Interface:** Easy to use via terminal commands with arguments for URL, target language, output format, output file override, and saving the original.
*   **Flexible Language Handling:** Enhances in the original language by default or translates to a specified language code (e.g., `en`, `it`, `es`, `fr`).

## Requirements

*   Python 3.7+
*   Required Python libraries:
    *   `youtube-transcript-api`
    *   `google-generativeai`
    *   `python-dotenv` (for easy API key management)
    *   `argparse` (usually included with Python)
*   A package installer like `pip` (usually included with Python) or `uv`.

## Installation

1.  **Clone or Download:** Get the `enhance_transcript.py` script onto your local machine.

2.  **Install Dependencies:** Open your terminal or command prompt, navigate to the directory containing the script. You can use either `pip` or `uv`.

    *   **Using `pip` (standard Python package installer):**
        ```bash
        pip install youtube-transcript-api google-generativeai python-dotenv argparse
        ```

    *   **Using `uv` ([an extremely fast Python package installer and resolver](https://github.com/astral-sh/uv)):**
        If you have `uv` installed, you can use it for potentially faster installation:
        ```bash
        uv pip install youtube-transcript-api google-generativeai python-dotenv argparse
        ```
        *(Note: If you haven't installed `uv` yet, follow the instructions on the [uv GitHub page](https://github.com/astral-sh/uv))*

## Configuration

1.  **Get a Gemini API Key:** You need an API key from Google to use the Gemini API. You can obtain one from [Google AI Studio](https://aistudio.google.com/app/apikey).
2.  **Set Up API Key:** The recommended way is to create a file named `.env` in the same directory as the script and add your API key like this:
    ```
    GEMINI_API_KEY=YOUR_API_KEY_HERE
    ```
    Replace `YOUR_API_KEY_HERE` with your actual key. The script will automatically load this key.
    Alternatively, you can pass the API key directly using the `-k` command-line argument (see Usage below), but using `.env` is more secure.

## Usage

Run the script from your terminal using the following format:

```bash
python enhance_transcript.py <YOUTUBE_URL> [OPTIONS]
```

**Arguments:**

*   `<YOUTUBE_URL>` (Required): The full URL of the YouTube video.
*   `-l`, `--language <LANG_CODE>` (Optional): The target language code (e.g., `en`, `it`, `es`, `fr`) for enhancement and translation. If omitted, the script enhances the transcript in its original detected language.
*   `-f`, `--format <FORMAT>` (Optional): Output format for the enhanced transcript. Choices are `srt` or `json`. **Defaults to `srt`**.
*   `-o`, `--output <FILE_PATH>` (Optional): File path for the saved *enhanced* transcript. If omitted, the script saves to a default filename based on the video ID and chosen format (e.g., `VIDEO_ID_enhanced.srt` or `VIDEO_ID_enhanced.json`) in the current directory. Providing this overrides the default name.
*   `-s`, `--save-original <FILE_PATH>` (Optional): File path to save the *original*, un-enhanced transcript data. This is always saved in JSON format (with timestamps). If omitted, the original transcript is not saved to disk.
*   `-k`, `--api_key <API_KEY>` (Optional): Your Gemini API key. This overrides the key loaded from the `.env` file if provided.

**Output:**

*   The enhanced transcript text is printed to the terminal.
*   An enhanced transcript file (`.srt` by default, or `.json` if specified) is saved.
*   Optionally, the original transcript data (`.json`) is saved if requested via `-s`.

**Examples:**

1.  **Enhance transcript, save as default SRT file (`<video_id>_enhanced.srt`):**
    ```bash
    python enhance_transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    ```

2.  **Enhance and translate to French, save as default SRT:**
    ```bash
    python enhance_transcript.py "https://www.youtube.com/watch?v=some_english_video_id" -l fr
    ```

3.  **Enhance transcript, save as JSON format (`<video_id>_enhanced.json`):**
    ```bash
    python enhance_transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -f json
    ```

4.  **Enhance transcript, save as SRT with a custom name:**
    ```bash
    python enhance_transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -o my_cool_video.srt
    ```
    *(Note: Ensure the extension matches the desired format if using `-o`)*

5.  **Enhance, translate to Italian (saving as default .srt), AND save the original data:**
    ```bash
    python enhance_transcript.py "https://www.youtube.com/watch?v=some_english_video_id" -l it -s original_data.json
    ```

6.  **Enhance using JSON output with a custom name and saving original:**
    ```bash
    python enhance_transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -f json -o enhanced_structured.json -s original_structured.json
    ```

7.  **Enhance using a directly provided API key:**
    ```bash
    python enhance_transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -k YOUR_ACTUAL_GEMINI_API_KEY
    ```

## Uploading to YouTube

The `.srt` file generated by this script (using the default format or `-f srt`) is suitable for direct manual upload to the subtitles/captions section of your video in YouTube Studio. This script does *not* automate the upload process itself (yet)
