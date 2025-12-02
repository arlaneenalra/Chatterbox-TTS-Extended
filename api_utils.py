"""
Utility functions for OpenAI-compatible TTS API

Handles parameter mapping, audio format conversion, voice preset loading,
and temporary file cleanup.
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Optional


# Voice preset configuration
VOICE_PRESETS_DIR = Path("voice_presets")
VOICE_CONFIG_PATH = VOICE_PRESETS_DIR / "voice_config.json"


def load_voice_config() -> dict:
    """
    Load voice preset configuration from JSON file

    Returns:
        dict: Voice configuration with 'voices' and 'default_voice' keys
    """
    if not VOICE_CONFIG_PATH.exists():
        print(f"[API WARNING] Voice config not found at {VOICE_CONFIG_PATH}")
        return {"voices": {}, "default_voice": None}

    try:
        with open(VOICE_CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"[API ERROR] Failed to load voice config: {e}")
        return {"voices": {}, "default_voice": None}


def get_voice_audio_path(voice_name: str) -> Optional[str]:
    """
    Map OpenAI voice name to reference audio file path

    Fallback chain:
    1. Voice not in config → return None (use model default)
    2. File doesn't exist → return None (use model default)

    Args:
        voice_name: OpenAI voice name (e.g., "alloy", "echo")

    Returns:
        str: Path to voice preset WAV file, or None for default voice
    """
    config = load_voice_config()

    # Voice not in config
    if voice_name not in config.get("voices", {}):
        print(f"[API WARNING] Voice '{voice_name}' not in config, using default voice")
        return None

    voice_info = config["voices"][voice_name]
    audio_path = VOICE_PRESETS_DIR / voice_info["file"]

    # Audio file not found
    if not audio_path.exists():
        print(f"[API WARNING] Voice preset file not found: {audio_path}, using default voice")
        return None

    return str(audio_path)


def map_openai_to_chatterbox_params(
    speed: float = 1.0,
    model: str = "tts-1",
    response_format: str = "mp3"
) -> dict:
    """
    Map OpenAI API parameters to Chatterbox TTS parameters

    OpenAI has 5 parameters, Chatterbox has 35+. This function maps the
    simplified OpenAI parameters to Gradio UI defaults for consistent quality.

    Both tts-1 and tts-1-hd use the same quality control features (multiple
    candidates + Whisper validation) to match the Gradio UI behavior.

    Args:
        speed: Speech speed (0.25-4.0, default 1.0)
        model: Model quality ("tts-1" or "tts-1-hd")
        response_format: Audio format (mp3, wav, flac, opus, aac, pcm)

    Returns:
        dict: Complete parameter dictionary for Chatterbox TTS
    """

    # Both models use same quality defaults as Gradio UI
    # Model difference is subtle: tts-1-hd uses slightly lower temperature for consistency
    if model == "tts-1-hd":
        temperature_base = 0.7  # Slightly more consistent
    else:  # tts-1
        temperature_base = 0.75  # Standard Gradio default

    # Speed affects temperature (inverse relationship)
    # Faster speed = lower temperature (more deterministic)
    # Slower speed = higher temperature (more variation)
    temperature = temperature_base * (1.0 / speed) ** 0.3
    temperature = max(0.5, min(1.2, temperature))  # Clamp to safe range

    # Map response_format to export format
    # For opus, aac, pcm we'll use mp3 initially then convert with FFmpeg
    if response_format in ["opus", "aac", "pcm"]:
        export_format = "mp3"  # Generate MP3, convert later
    else:
        export_format = response_format  # wav, mp3, flac supported natively

    return {
        # Core TTS parameters (matching Gradio defaults)
        "exaggeration_input": 0.5,
        "temperature_input": temperature,
        "seed_num_input": 0,  # 0 = random seed each time
        "cfgw_input": 1.0,

        # Post-processing (disabled for API speed, but quality control is enabled)
        "use_pyrnnoise": False,
        "use_auto_editor": False,
        "ae_threshold": 0.06,
        "ae_margin": 0.2,
        "normalize_audio": False,
        "normalize_method": "ebu",
        "normalize_level": -24,
        "normalize_tp": -2,
        "normalize_lra": 7,
        "keep_original_wav": False,

        # Export format
        "export_formats": [export_format],

        # Text processing (matching Gradio defaults)
        "enable_batching": False,  # Gradio default
        "to_lowercase": True,  # Gradio default
        "normalize_spacing": True,
        "fix_dot_letters": True,
        "remove_reference_numbers": True,
        "smart_batch_short_sentences": True,

        # Watermark
        "disable_watermark": True,  # No watermark for API

        # Generation settings (MATCHING GRADIO DEFAULTS FOR QUALITY)
        "num_generations": 1,
        "num_candidates_per_chunk": 3,  # Gradio default: generate 3 candidates
        "max_attempts_per_candidate": 3,  # Gradio default: retry up to 3 times
        "bypass_whisper_checking": False,  # Gradio default: enable validation
        "whisper_model_name": "medium (~5–8 GB OpenAI / ~2.5–4.5 GB faster-whisper)",

        # Parallel processing (matching Gradio defaults)
        "enable_parallel": True,
        "num_parallel_workers": 4,
        "use_longest_transcript_on_fail": True,  # Gradio default

        # Advanced
        "sound_words_field": "",
        "use_faster_whisper": True,  # Gradio default
    }


def convert_audio_format(input_file: str, target_format: str) -> str:
    """
    Convert audio file to target format using FFmpeg

    For mp3, wav, flac: Already handled by Chatterbox's process_text_for_tts
    For opus, aac, pcm: Convert using FFmpeg

    Args:
        input_file: Path to input audio file (typically MP3 or WAV)
        target_format: Desired output format

    Returns:
        str: Path to converted audio file

    Raises:
        subprocess.CalledProcessError: If FFmpeg conversion fails
        ValueError: If format is not recognized
    """
    input_path = Path(input_file)

    if target_format == "pcm":
        # PCM is raw audio data (16-bit signed little-endian, 24kHz, mono)
        output_file = str(input_path.with_suffix(".pcm"))
        subprocess.run([
            "ffmpeg", "-y", "-i", input_file,
            "-f", "s16le", "-ar", "24000", "-ac", "1",
            output_file
        ], check=True, capture_output=True)
        return output_file

    elif target_format == "opus":
        # Opus format in Ogg container
        output_file = str(input_path.with_suffix(".opus"))
        subprocess.run([
            "ffmpeg", "-y", "-i", input_file,
            "-c:a", "libopus", "-b:a", "128k",
            output_file
        ], check=True, capture_output=True)
        return output_file

    elif target_format == "aac":
        # AAC format in M4A container
        output_file = str(input_path.with_suffix(".m4a"))
        subprocess.run([
            "ffmpeg", "-y", "-i", input_file,
            "-c:a", "aac", "-b:a", "192k",
            output_file
        ], check=True, capture_output=True)
        return output_file

    elif target_format in ["mp3", "wav", "flac"]:
        # These formats are handled natively by Chatterbox
        # Just verify the file has the correct extension
        expected_ext = f".{target_format}"
        if str(input_file).endswith(expected_ext):
            return input_file
        else:
            # This shouldn't happen, but handle it gracefully
            raise ValueError(f"Expected {expected_ext} file, got {input_file}")

    else:
        raise ValueError(f"Unsupported audio format: {target_format}")


def get_content_type(format: str) -> str:
    """
    Get MIME type for audio format

    Args:
        format: Audio format (mp3, opus, aac, flac, wav, pcm)

    Returns:
        str: MIME type string
    """
    content_types = {
        "mp3": "audio/mpeg",
        "opus": "audio/opus",
        "aac": "audio/aac",
        "flac": "audio/flac",
        "wav": "audio/wav",
        "pcm": "application/octet-stream"
    }
    return content_types.get(format, "application/octet-stream")


def cleanup_temp_files(file_list: list[str]):
    """
    Clean up temporary audio files and associated metadata after serving

    Args:
        file_list: List of file paths to remove
    """
    for file_path in file_list:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)

                # Also remove associated settings files
                base = file_path.rsplit('.', 1)[0]
                for ext in [".settings.csv", ".settings.json"]:
                    settings_file = base + ext
                    if os.path.exists(settings_file):
                        os.remove(settings_file)
        except Exception as e:
            print(f"[API WARNING] Failed to clean up temp file {file_path}: {e}")
