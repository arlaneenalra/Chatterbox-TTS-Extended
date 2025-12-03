#!/usr/bin/env python3
"""
Bulk TTS Client for Chatterbox-TTS-Extended

This script uses the Gradio API to batch process a directory of text files
into MP3 audio files using the Chatterbox TTS system.

Usage:
    python bulk_tts_client.py --input-dir ./texts --output-dir ./outputs --settings settings.json

Requirements:
    - Chatterbox Gradio app must be running (python Chatter.py)
    - gradio_client library (pip install gradio_client)
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import time

try:
    from gradio_client import Client, handle_file
except ImportError:
    print("Error: gradio_client library not found.")
    print("Please install it with: pip install gradio_client")
    sys.exit(1)


def load_settings(settings_path: str) -> Dict[str, Any]:
    """Load settings from JSON file."""
    if not os.path.exists(settings_path):
        print(f"Error: Settings file not found: {settings_path}")
        sys.exit(1)

    with open(settings_path, 'r', encoding='utf-8') as f:
        settings = json.load(f)

    return settings


def get_default_settings() -> Dict[str, Any]:
    """Return default settings matching Chatterbox defaults."""
    return {
        "exaggeration_slider": 0.5,
        "temp_slider": 0.75,
        "seed_input": 0,
        "cfg_weight_slider": 1.0,
        "use_pyrnnoise_checkbox": False,
        "use_auto_editor_checkbox": False,
        "threshold_slider": 0.06,
        "margin_slider": 0.2,
        "export_format_checkboxes": ["mp3"],
        "enable_batching_checkbox": False,
        "to_lowercase_checkbox": True,
        "normalize_spacing_checkbox": True,
        "fix_dot_letters_checkbox": True,
        "remove_reference_numbers_checkbox": True,
        "keep_original_checkbox": False,
        "smart_batch_short_sentences_checkbox": True,
        "disable_watermark_checkbox": True,
        "num_generations_input": 1,
        "normalize_audio_checkbox": False,
        "normalize_method_dropdown": "ebu",
        "normalize_level_slider": -24,
        "normalize_tp_slider": -2,
        "normalize_lra_slider": 7,
        "num_candidates_slider": 3,
        "max_attempts_slider": 3,
        "bypass_whisper_checkbox": False,
        "whisper_model_dropdown": "medium (~5–8 GB OpenAI / ~2.5–4.5 GB faster-whisper)",
        "use_faster_whisper_checkbox": True,
        "enable_parallel_checkbox": True,
        "num_parallel_workers_slider": 4,
        "use_longest_transcript_on_fail_checkbox": True,
        "sound_words_field": "",
        "separate_files_checkbox": False,
    }


def process_text_file(
    client: Client,
    text_file_path: str,
    output_dir: str,
    settings: Dict[str, Any],
    audio_prompt_path: str = None,
    api_name: str = None,
    fn_index: int = None,
) -> List[str]:
    """
    Process a single text file using the Gradio API.

    Args:
        client: Gradio client instance
        text_file_path: Path to input text file
        output_dir: Directory to save output files
        settings: Settings dictionary
        audio_prompt_path: Optional path to reference audio file

    Returns:
        List of generated audio file paths
    """
    # Read the text content
    with open(text_file_path, 'r', encoding='utf-8') as f:
        text_content = f.read().strip()

    if not text_content:
        print(f"Warning: Empty file skipped: {text_file_path}")
        return []

    print(f"\nProcessing: {text_file_path}")
    print(f"Text length: {len(text_content)} characters")

    # Prepare API call parameters for the /lambda endpoint
    # Based on actual endpoint signature from gradio client inspection
    api_params = [
        text_content,                                           # 0: param_0 - Text Input (str)
        [],                                                     # 1: param_1 - Text File(s) (.txt) - empty list for no files
        handle_file(audio_prompt_path) if audio_prompt_path else None,  # 2: param_2 - Reference Audio (Optional)
        settings.get("exaggeration_slider", 0.5),              # 3: param_3 - Emotion Exaggeration
        settings.get("temp_slider", 0.75),                     # 4: param_4 - Temperature
        settings.get("seed_input", 0),                         # 5: param_5 - Random Seed
        settings.get("cfg_weight_slider", 1.0),                # 6: param_6 - CFG Weight/Pace
        settings.get("use_pyrnnoise_checkbox", False),         # 7: param_7 - Denoise with RNNoise
        settings.get("use_auto_editor_checkbox", False),       # 8: param_8 - Post-process with Auto-Editor
        settings.get("threshold_slider", 0.06),                # 9: param_9 - Auto-Editor Volume Threshold
        settings.get("margin_slider", 0.2),                    # 10: param_10 - Auto-Editor Margin
        settings.get("export_format_checkboxes", ["mp3"]),     # 11: param_11 - Export Format(s)
        settings.get("enable_batching_checkbox", False),       # 12: param_12 - Enable Sentence Batching
        settings.get("to_lowercase_checkbox", True),           # 13: param_13 - Convert to lowercase
        settings.get("normalize_spacing_checkbox", True),      # 14: param_14 - Normalize spacing
        settings.get("fix_dot_letters_checkbox", True),        # 15: param_15 - Convert 'J.R.R.'
        settings.get("remove_reference_numbers_checkbox", True),  # 16: param_16 - Remove reference numbers
        settings.get("keep_original_checkbox", False),         # 17: param_17 - Keep original WAV
        settings.get("smart_batch_short_sentences_checkbox", True),  # 18: param_18 - Smart-append short sentences
        settings.get("disable_watermark_checkbox", True),      # 19: param_19 - Disable Perth Watermark
        settings.get("num_generations_input", 1),              # 20: param_20 - Number of Generations
        settings.get("normalize_audio_checkbox", False),       # 21: param_21 - Normalize with ffmpeg
        settings.get("normalize_method_dropdown", "ebu"),      # 22: param_22 - Normalization Method
        settings.get("normalize_level_slider", -24),           # 23: param_23 - EBU Target Integrated Loudness
        settings.get("normalize_tp_slider", -2),               # 24: param_24 - EBU True Peak
        settings.get("normalize_lra_slider", 7),               # 25: param_25 - EBU Loudness Range
        settings.get("num_candidates_slider", 3),              # 26: param_26 - Number of Candidates
        settings.get("max_attempts_slider", 3),                # 27: param_27 - Max Attempts
        settings.get("bypass_whisper_checkbox", False),        # 28: param_28 - Bypass Whisper Checking
        settings.get("whisper_model_dropdown", "medium (~5–8 GB OpenAI / ~2.5–4.5 GB faster-whisper)"),  # 29: param_29 - Whisper Model
        settings.get("enable_parallel_checkbox", True),        # 30: param_30 - Enable Parallel Chunk Processing
        settings.get("num_parallel_workers_slider", 4),        # 31: param_31 - Parallel Workers
        settings.get("use_longest_transcript_on_fail_checkbox", True),  # 32: param_32 - Use longest transcript on fail
        settings.get("sound_words_field", ""),                 # 33: param_33 - Remove/Replace Words/Sounds
        settings.get("use_faster_whisper_checkbox", True),     # 34: param_34 - Use faster-whisper
        settings.get("separate_files_checkbox", False),        # 35: param_35 - Generate separate audio files
    ]

    try:
        # Call the Gradio API
        print("Sending request to Gradio API...")
        start_time = time.time()

        # Determine which endpoint to use
        if api_name:
            # Use named endpoint if specified
            result = client.predict(*api_params, api_name=api_name)
        elif fn_index is not None:
            # Use function index if specified
            result = client.predict(*api_params, fn_index=fn_index)
        else:
            # Default to api_name="/lambda" (the TTS generation endpoint)
            result = client.predict(*api_params, api_name="/lambda")

        elapsed = time.time() - start_time
        print(f"Generation completed in {elapsed:.1f} seconds")

        # The result should be a tuple: (output_paths, dropdown_update, dropdown_value)
        # We need the first element which is the list of output file paths
        if isinstance(result, tuple) and len(result) > 0:
            output_files = result[0]
        else:
            output_files = result

        if not output_files:
            print(f"Warning: No output files generated for {text_file_path}")
            return []

        # Copy/move files to output directory with appropriate naming
        output_basename = Path(text_file_path).stem
        saved_files = []

        os.makedirs(output_dir, exist_ok=True)

        for i, file_path in enumerate(output_files):
            if not os.path.exists(file_path):
                print(f"Warning: Generated file not found: {file_path}")
                continue

            # Get the file extension
            ext = Path(file_path).suffix

            # Create output filename
            if len(output_files) == 1:
                output_filename = f"{output_basename}{ext}"
            else:
                output_filename = f"{output_basename}_{i+1}{ext}"

            output_path = os.path.join(output_dir, output_filename)

            # Copy the file
            import shutil
            shutil.copy2(file_path, output_path)
            saved_files.append(output_path)
            print(f"Saved: {output_path}")

        return saved_files

    except Exception as e:
        print(f"Error processing {text_file_path}: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Bulk TTS processing client for Chatterbox-TTS-Extended",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all .txt files in 'texts' directory using default settings
  python bulk_tts_client.py --input-dir ./texts --output-dir ./outputs

  # Use custom settings file
  python bulk_tts_client.py --input-dir ./texts --output-dir ./outputs --settings my_settings.json

  # Connect to remote Gradio instance
  python bulk_tts_client.py --input-dir ./texts --output-dir ./outputs --url http://192.168.1.100:7860

  # Use a reference audio for voice cloning
  python bulk_tts_client.py --input-dir ./texts --output-dir ./outputs --reference-audio voice.wav
        """
    )

    parser.add_argument(
        '--input-dir',
        type=str,
        required=False,
        help='Directory containing input text files (.txt)'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        required=False,
        help='Directory to save output audio files'
    )

    parser.add_argument(
        '--settings',
        type=str,
        default=None,
        help='Path to settings.json file (optional, uses defaults if not provided)'
    )

    parser.add_argument(
        '--reference-audio',
        type=str,
        default=None,
        help='Path to reference audio file for voice cloning (optional)'
    )

    parser.add_argument(
        '--url',
        type=str,
        default='http://localhost:7860',
        help='Gradio server URL (default: http://localhost:7860)'
    )

    parser.add_argument(
        '--pattern',
        type=str,
        default='*.txt',
        help='File pattern to match (default: *.txt)'
    )

    parser.add_argument(
        '--api-name',
        type=str,
        default=None,
        help='Gradio API endpoint name (optional, e.g., "/predict")'
    )

    parser.add_argument(
        '--fn-index',
        type=int,
        default=None,
        help='Gradio endpoint function index (default: 0 for first endpoint)'
    )

    parser.add_argument(
        '--list-endpoints',
        action='store_true',
        help='List available API endpoints and exit'
    )

    args = parser.parse_args()

    # If --list-endpoints is specified, we don't need input/output dirs
    # Otherwise, validate required arguments
    if not args.list_endpoints:
        if not args.input_dir:
            parser.error("--input-dir is required (unless using --list-endpoints)")
        if not args.output_dir:
            parser.error("--output-dir is required (unless using --list-endpoints)")

        # Validate input directory
        if not os.path.isdir(args.input_dir):
            print(f"Error: Input directory not found: {args.input_dir}")
            sys.exit(1)

    # Load settings (skip if just listing endpoints)
    if not args.list_endpoints:
        if args.settings:
            print(f"Loading settings from: {args.settings}")
            settings = load_settings(args.settings)
        else:
            print("Using default settings")
            settings = get_default_settings()

        # Validate reference audio if provided
        if args.reference_audio and not os.path.exists(args.reference_audio):
            print(f"Error: Reference audio file not found: {args.reference_audio}")
            sys.exit(1)

        # Find all text files
        input_path = Path(args.input_dir)
        text_files = sorted(input_path.glob(args.pattern))

        if not text_files:
            print(f"No text files found matching pattern '{args.pattern}' in {args.input_dir}")
            sys.exit(1)

        print(f"\nFound {len(text_files)} text file(s) to process")
        print(f"Output directory: {args.output_dir}")
        print(f"Gradio URL: {args.url}")

    # Connect to Gradio API
    print(f"\nConnecting to Gradio server at {args.url}...")
    try:
        client = Client(args.url)
        print("Successfully connected to Gradio API")
    except Exception as e:
        print(f"Error connecting to Gradio server: {str(e)}")
        print("\nMake sure the Chatterbox Gradio app is running:")
        print("  python Chatter.py")
        sys.exit(1)

    # Handle --list-endpoints
    if args.list_endpoints:
        print("\n" + "="*70)
        print("AVAILABLE API ENDPOINTS")
        print("="*70)
        try:
            api_info = client.view_api(all_endpoints=True)
            print(api_info)
        except Exception as e:
            print(f"Could not retrieve API info: {e}")
            print("\nTry accessing the API docs at: {}/docs".format(args.url))
        sys.exit(0)

    # If we're not just listing endpoints, proceed with processing
    if not args.list_endpoints:
        # Set up endpoint parameters
        api_name = args.api_name if args.api_name else "/lambda"
        fn_index = args.fn_index

        if args.api_name:
            print(f"\nUsing API endpoint: {api_name}")
        elif fn_index is not None:
            print(f"\nUsing function index: {fn_index}")
            api_name = None  # Clear api_name when using fn_index
        else:
            print(f"\nUsing API endpoint: {api_name} (default)")

        # Process each file
        total_files = len(text_files)
        successful = 0
        failed = 0
        all_outputs = []

        print("\n" + "="*70)
        print("Starting batch processing...")
        print("="*70)

        for idx, text_file in enumerate(text_files, 1):
            print(f"\n[{idx}/{total_files}] Processing: {text_file.name}")

            try:
                output_files = process_text_file(
                    client=client,
                    text_file_path=str(text_file),
                    output_dir=args.output_dir,
                    settings=settings,
                    audio_prompt_path=args.reference_audio,
                    api_name=api_name,
                    fn_index=fn_index,
                )

                if output_files:
                    successful += 1
                    all_outputs.extend(output_files)
                else:
                    failed += 1

            except KeyboardInterrupt:
                print("\n\nProcessing interrupted by user")
                break
            except Exception as e:
                print(f"Unexpected error: {str(e)}")
                failed += 1

        # Summary
        print("\n" + "="*70)
        print("PROCESSING COMPLETE")
        print("="*70)
        print(f"Total files: {total_files}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Output files: {len(all_outputs)}")
        print(f"Output directory: {args.output_dir}")
        print("="*70)

        if all_outputs:
            print("\nGenerated files:")
            for output_file in all_outputs:
                print(f"  - {output_file}")


if __name__ == "__main__":
    main()
