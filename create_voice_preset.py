#!/usr/bin/env python3
"""
Voice Preset Creation Helper for Chatterbox TTS API

This script prepares voice preset audio files from various input formats.
It handles conversion to the required format (24kHz mono WAV), trimming,
duration limiting, and volume normalization.

Usage:
    python create_voice_preset.py input_audio.mp3 voice_name

Example:
    python create_voice_preset.py my_recording.wav alloy
"""

import argparse
import librosa
import soundfile as sf
from pathlib import Path
import sys


def prepare_voice_preset(
    input_audio: str,
    voice_name: str,
    output_dir: str = "voice_presets",
    target_duration: int = 20,
    sample_rate: int = 24000
) -> str:
    """
    Prepare a voice preset from an input audio file

    This function:
    1. Loads the audio file (any format supported by librosa)
    2. Converts to mono and 24kHz sample rate
    3. Trims silence from the beginning and end
    4. Limits duration to target_duration (center crop if longer)
    5. Normalizes volume
    6. Saves as WAV file

    Args:
        input_audio: Path to input audio file (any format)
        voice_name: Name for the voice preset (e.g., "alloy", "echo")
        output_dir: Directory to save the voice preset (default: "voice_presets")
        target_duration: Target duration in seconds (default: 20)
        sample_rate: Target sample rate in Hz (default: 24000)

    Returns:
        str: Path to the created voice preset file

    Raises:
        FileNotFoundError: If input audio file doesn't exist
        ValueError: If audio processing fails
    """
    input_path = Path(input_audio)
    if not input_path.exists():
        raise FileNotFoundError(f"Input audio file not found: {input_audio}")

    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(exist_ok=True)

    print(f"Loading audio from: {input_audio}")
    try:
        # Load audio with librosa (handles many formats automatically)
        audio, sr = librosa.load(input_audio, sr=sample_rate, mono=True)
        print(f"  Original duration: {len(audio) / sample_rate:.2f} seconds")
        print(f"  Sample rate: {sample_rate} Hz")
    except Exception as e:
        raise ValueError(f"Failed to load audio file: {e}")

    # Trim silence from start/end (top_db=30 means trim anything 30dB below peak)
    print("Trimming silence...")
    audio_trimmed, trim_indices = librosa.effects.trim(audio, top_db=30)
    trimmed_duration = len(audio_trimmed) / sample_rate
    print(f"  After trimming: {trimmed_duration:.2f} seconds")

    # Limit to target duration (take from middle if longer)
    target_samples = target_duration * sample_rate
    if len(audio_trimmed) > target_samples:
        print(f"Limiting to {target_duration} seconds (center crop)...")
        start_sample = (len(audio_trimmed) - target_samples) // 2
        audio_limited = audio_trimmed[start_sample:start_sample + target_samples]
    else:
        audio_limited = audio_trimmed

    final_duration = len(audio_limited) / sample_rate
    print(f"  Final duration: {final_duration:.2f} seconds")

    # Normalize volume to peak at -3dB (0.707 amplitude)
    print("Normalizing volume...")
    audio_normalized = librosa.util.normalize(audio_limited) * 0.707

    # Save as WAV
    output_path = output_dir_path / f"{voice_name}.wav"
    print(f"Saving to: {output_path}")
    sf.write(output_path, audio_normalized, sample_rate)

    print(f"✅ Voice preset created successfully!")
    print(f"   Name: {voice_name}")
    print(f"   Path: {output_path}")
    print(f"   Duration: {final_duration:.2f}s")
    print(f"   Sample rate: {sample_rate} Hz")
    print(f"   Channels: Mono")

    return str(output_path)


def main():
    """Command-line interface for voice preset creation"""
    parser = argparse.ArgumentParser(
        description="Create voice preset for Chatterbox TTS API",
        epilog="""
Examples:
  python create_voice_preset.py recording.mp3 alloy
  python create_voice_preset.py audio.wav echo --duration 15
  python create_voice_preset.py voice.m4a custom_voice --output-dir ./my_voices
        """
    )

    parser.add_argument(
        "input_audio",
        help="Path to input audio file (supports mp3, wav, flac, m4a, ogg, etc.)"
    )

    parser.add_argument(
        "voice_name",
        help="Name for the voice preset (e.g., 'alloy', 'echo', 'my_custom_voice')"
    )

    parser.add_argument(
        "--output-dir",
        default="voice_presets",
        help="Output directory for voice presets (default: voice_presets)"
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=20,
        help="Target duration in seconds (default: 20, recommended: 10-30)"
    )

    parser.add_argument(
        "--sample-rate",
        type=int,
        default=24000,
        help="Sample rate in Hz (default: 24000, must be 24000 for Chatterbox)"
    )

    args = parser.parse_args()

    # Validate sample rate
    if args.sample_rate != 24000:
        print("⚠️  WARNING: Sample rate must be 24000 Hz for Chatterbox TTS!")
        print("   Overriding to 24000 Hz...")
        args.sample_rate = 24000

    # Validate duration
    if args.duration < 5:
        print("⚠️  WARNING: Duration is very short (<5s). Recommended: 10-30s")
    elif args.duration > 60:
        print("⚠️  WARNING: Duration is very long (>60s). Recommended: 10-30s")

    try:
        prepare_voice_preset(
            input_audio=args.input_audio,
            voice_name=args.voice_name,
            output_dir=args.output_dir,
            target_duration=args.duration,
            sample_rate=args.sample_rate
        )

        print("\n📝 Next steps:")
        print("1. Test the voice preset by running the TTS API")
        print("2. If the voice is new, add it to voice_presets/voice_config.json")
        print("3. Adjust the source audio and regenerate if quality is not satisfactory")

    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
