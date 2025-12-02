# Voice Presets for Chatterbox TTS API

This directory contains voice preset audio files that serve as reference audio for the TTS model. When a voice is selected via the API, the corresponding WAV file is used to guide the voice characteristics of the generated speech.

## Voice Preset Requirements

- **Format**: WAV (24kHz, mono)
- **Duration**: 10-30 seconds recommended
- **Content**: Clear speech without background noise or music
- **Quality**: High-quality recording with consistent volume

## Available Voices

The following voices are configured in `voice_config.json`:

1. **alloy** - Neutral, balanced voice
2. **echo** - Clear, resonant voice (male)
3. **fable** - Expressive, narrative voice (female)
4. **onyx** - Deep, authoritative voice (male)
5. **nova** - Warm, friendly voice (female)
6. **shimmer** - Bright, energetic voice (female)

## Adding Voice Presets

To add voice preset WAV files, you have two options:

### Option 1: Manual Placement

1. Find or create a high-quality audio file (10-30 seconds of clear speech)
2. Convert it to 24kHz mono WAV format
3. Place it in this directory with the appropriate filename (e.g., `alloy.wav`)

### Option 2: Use the Helper Script

Use the `create_voice_preset.py` script in the project root to automatically prepare voice presets:

```bash
python create_voice_preset.py path/to/your/audio.mp3 alloy
```

This script will:
- Convert the audio to 24kHz mono WAV
- Trim silence from the beginning and end
- Limit duration to 20 seconds (center crop if longer)
- Normalize volume
- Save to `voice_presets/alloy.wav`

## Using Custom Voices

You can add your own custom voices by:

1. Adding a new voice preset WAV file to this directory
2. Updating `voice_config.json` with the new voice name and file path:

```json
{
  "voices": {
    ...
    "my_custom_voice": {
      "file": "my_custom_voice.wav",
      "description": "Description of the voice",
      "gender": "male/female/neutral",
      "tags": ["tag1", "tag2"]
    }
  }
}
```

3. The new voice will be available via the API automatically

## Fallback Behavior

If a voice preset file is missing or cannot be loaded, the API will fall back to the model's default voice (no reference audio). This ensures the API continues to work even if voice files are not yet populated.

## Voice Quality Tips

For best results:
- Use clean, studio-quality recordings
- Ensure consistent volume throughout
- Avoid background noise, music, or effects
- Use recordings that match the desired speaking style
- 15-20 seconds is the sweet spot for reference audio length
