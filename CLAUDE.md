# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chatterbox-TTS-Extended is an advanced text-to-speech (TTS) pipeline built on top of [Chatterbox-TTS](https://github.com/resemble-ai/chatterbox). It features batch processing, quality validation, audio post-processing, voice conversion, and an OpenAI-compatible REST API.

**Requirements:** Python 3.10.x, FFmpeg (on PATH), CUDA-capable GPU recommended

## Running the Application

### Gradio UI (Default)
```bash
python Chatter.py
```

### With OpenAI-Compatible API
```bash
python Chatter.py --enable-api
# UI at: http://localhost:7860/
# API at: http://localhost:7860/v1/audio/speech
# Docs at: http://localhost:7860/v1/docs
```

### Custom Host/Port
```bash
python Chatter.py --enable-api --host 0.0.0.0 --port 8000
```

## Installation Commands

```bash
# Clone and install dependencies
git clone https://github.com/petermg/Chatterbox-TTS-Extended
pip install --force-reinstall -r requirements.txt

# Alternative requirement files if needed:
# requirements.base.with.versions.txt
# requirements_frozen.txt
```

## Architecture Overview

### Core Components

**1. Main Application (`Chatter.py`)**
- 27k+ line orchestrator file that coordinates all TTS functionality
- Implements Gradio UI with two tabs: TTS generation and Voice Conversion (VC)
- Contains `process_text_for_tts()` - the main TTS pipeline entry point called by both UI and API
- Manages model loading via global `MODEL` variable (lazy-loaded singleton pattern)
- Handles settings persistence (JSON/CSV per output)

**2. OpenAI-Compatible REST API**
Three-file FastAPI implementation added for OpenAI SDK compatibility:

- `api.py` - FastAPI app with endpoints: `/v1/audio/speech`, `/health`, `/v1/voices`
- `api_models.py` - Pydantic request/response schemas matching OpenAI spec
- `api_utils.py` - Parameter mapping (OpenAI's 5 params → Chatterbox's 35+ params), audio format conversion, voice preset loading

The API reuses `Chatter.py`'s `process_text_for_tts()` and shares the global MODEL instance.

**3. Chatterbox Library (`chatterbox/src/chatterbox/`)**
Modular neural TTS implementation from ResembleAI:

- `tts.py` - `ChatterboxTTS` class, main inference interface, loads T3/S3Gen/VoiceEncoder models
- `vc.py` - `ChatterboxVC` class for voice conversion (input audio → target voice)
- `models/t3/` - T3 model (text-to-speech semantic encoder based on Llama architecture)
- `models/s3gen/` - S3Gen model (audio generation with flow matching and HiFi-GAN vocoder)
- `models/s3tokenizer/` - Speech tokenizer for encoding/decoding audio
- `models/voice_encoder/` - Voice embedding encoder for conditioning
- `models/tokenizers/` - Text tokenization (English tokenizer)

Models are loaded from HuggingFace Hub (`ResembleAI/chatterbox`) or local checkpoints.

**4. Voice Presets System**
- `voice_presets/` - Directory containing reference audio files for voice cloning
- `voice_presets/voice_config.json` - Maps OpenAI voice names (alloy, echo, fable, etc.) to WAV files
- `create_voice_preset.py` - Helper script to prepare voice preset audio (24kHz mono WAV, trimmed, normalized)

### Key Processing Pipeline

The TTS generation flow in `Chatter.py::process_text_for_tts()`:

1. **Text Preprocessing** - Lowercase, whitespace normalization, dot-letter fix, reference number removal, sound word removal/replacement
2. **Sentence Splitting** - Uses NLTK's `sent_tokenize()`, with smart batching option to group short sentences
3. **Chunk Generation (Parallel)** - For each chunk:
   - Generate N candidates (configurable)
   - Optionally validate with Whisper (OpenAI or faster-whisper)
   - Select best candidate based on transcript similarity
   - Retry with fallback strategies if validation fails
4. **Audio Post-Processing**:
   - Optional pyrnnoise denoising (removes TTS artifacts)
   - Optional Auto-Editor silence/stutter trimming
   - Optional FFmpeg normalization (EBU R128 or peak)
5. **Concatenation & Export** - Stitch chunks, export in requested formats (WAV/MP3/FLAC)

Parallel processing uses `ThreadPoolExecutor` with configurable worker count.

### Whisper Integration

Two backends for transcript validation:
- **OpenAI Whisper** - Standard PyTorch implementation
- **faster-whisper** - SYSTRAN's faster implementation with int8 quantization

Model sizes: tiny, base, small, medium, large (trading off VRAM vs accuracy)

Whisper model is loaded per-generation and unloaded after validation to manage VRAM.

### Device Management

Device selection priority (in `Chatter.py`):
1. `cuda` if NVIDIA GPU available
2. `cpu` fallback

MPS (Apple Silicon) support exists in `vc.py` but is commented out in main application. The codebase uses deterministic mode for CUDA (reproducible generation with fixed seeds).

## API Testing

```bash
# Run automated pytest tests
pytest test_api.py -v

# Run comprehensive manual tests (all formats, voices)
./test_api_manual.sh
# Outputs saved to: ./test_outputs/
```

## Bulk TTS Client - Watch Mode

The `bulk_tts_client.py` script supports two modes for processing text files:

### Batch Mode (Default)
Process all existing files in a directory once and exit:
```bash
python bulk_tts_client.py --input-dir ./texts --output-dir ./outputs
```

### Watch Mode (Continuous Processing)
Continuously monitor a directory for new files and process them automatically:

```bash
# Basic watch mode
python bulk_tts_client.py --watch --input-dir ./inbox --output-dir ./outputs

# Watch with custom settings
python bulk_tts_client.py --watch --input-dir ./inbox --output-dir ./outputs \
    --settings my_settings.json --reference-audio voice.wav

# Watch with longer stability delay (for slow network drives)
python bulk_tts_client.py --watch --input-dir ./inbox --output-dir ./outputs \
    --watch-delay 5.0 --stability-checks 5 --stability-interval 2.0

# Reprocess files when modified
python bulk_tts_client.py --watch --input-dir ./inbox --output-dir ./outputs \
    --reprocess-modified
```

**Watch Mode Features:**
- **Queue-Based Processing** - Files are queued and processed sequentially (one at a time) to prevent overwhelming the API server
- **File Stability Detection** - Waits for files to finish being written before processing
- **State Tracking** - Tracks processed files to avoid reprocessing (stored in `watch_state.json`)
- **Configurable Delays** - Adjust wait times and stability checks for different environments
- **Queue Status Visibility** - Periodic status updates show queue size and current file being processed
- **Graceful Shutdown** - Press Ctrl+C to stop (drains queue and completes pending files before exit)

**Watch Mode Arguments:**
- `--watch` - Enable watch mode
- `--watch-delay SECONDS` - Initial delay after file detection (default: 2.0)
- `--stability-checks N` - Consecutive stability checks required (default: 3)
- `--stability-interval SECONDS` - Interval between checks (default: 1.0)
- `--watch-state-file PATH` - Custom state file location
- `--reprocess-modified` - Reprocess files when content changes
- `--watch-recursive` - Monitor subdirectories recursively
- `--max-queue-size N` - Maximum queue size, 0 = unlimited (default: 0)
- `--shutdown-timeout SECONDS` - Max seconds to wait for queue drain on shutdown (default: 300)

**State Management:**
Processed files are tracked in `<output-dir>/watch_state.json`. To reprocess all files, delete this file.

**Requirements:**
Watch mode requires the `watchdog` library:
```bash
uv sync  # or: uv add watchdog
```

## Common Development Patterns

### Adding New Voice Presets
```bash
python create_voice_preset.py path/to/audio.mp3 voice_name
# Output: voice_presets/voice_name.wav
# Update: voice_presets/voice_config.json with new voice mapping
```

### Model Loading Pattern
The codebase uses lazy singleton pattern for models:
```python
MODEL = None  # Global

def get_or_load_model():
    global MODEL
    if MODEL is None:
        MODEL = ChatterboxTTS.from_pretrained(DEVICE)
    return MODEL
```

Same pattern for `VC_MODEL` in voice conversion.

### Settings Persistence
Settings are saved in three locations:
1. `settings.json` - Global UI settings (loaded on startup)
2. `{output_base}.settings.json` - Per-generation settings (full config)
3. `{output_base}.settings.csv` - Per-generation settings (one-row CSV for easy batch analysis)

The settings system uses `save_settings()`, `load_settings()`, and `default_settings()` functions.

## Important Implementation Details

### Text Preprocessing Features
- **Dot-letter fix**: Converts "J.R.R." → "J R R" for better pronunciation
- **Reference number removal**: Removes inline citations like ".188" or "."3"
- **Sound word mapping**: Replace/remove patterns like "um", "ahh", or custom mappings like "zzz=>sigh"

### Audio Format Conversion
- Native formats (handled by Chatterbox): WAV, MP3, FLAC
- FFmpeg-converted formats (handled by `api_utils.py`): opus, aac, pcm
- All audio is generated at 24kHz sample rate (S3GEN_SR)

### Quality Control System
Multiple validation layers:
- Candidate generation (N attempts per chunk)
- Whisper transcript validation with similarity scoring
- Retry logic with deterministic per-attempt seeding
- Fallback strategies (longest transcript or highest similarity)

### Queue-Based Processing (Watch Mode)
The bulk TTS client uses a queue-based architecture in watch mode to ensure sequential processing:
- `TTSProcessingQueue` class manages a thread-safe FIFO queue with a single worker thread
- Detected files are enqueued instead of spawning concurrent threads
- Only one file is processed at a time, respecting the single MODEL instance limitation
- Queue status is displayed periodically (every 10 seconds) showing pending files and current file
- Graceful shutdown drains the queue before exit (configurable timeout via `--shutdown-timeout`)

### Known Issues
- faster-whisper may silently crash during validation (mentioned in README)
- Single concurrent request limitation (shared MODEL between Gradio and API) - addressed by queue-based processing in watch mode
- MPS (Apple Silicon GPU) support is incomplete/commented out

## File Output Naming Convention

Generated files use this pattern:
```
{basename}_{timestamp}_gen{generation_num}_seed{seed}.{format}
```

Example: `text_input_20250102_123045_gen1_seed42.mp3`

## Environment Variables

```python
# Set in Chatter.py for deterministic behavior
os.environ["CUDA_LAUNCH_BLOCKING"] = "0"
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":16:8"
```

## Integration Points

When extending the codebase:

1. **New audio post-processing** - Add to pipeline in `process_text_for_tts()` after chunk concatenation
2. **New API endpoints** - Add to `api.py` and reuse `Chatter.py` functions
3. **New UI controls** - Add to Gradio interface in `Chatter.py` main block, update `default_settings()`
4. **New voice presets** - Use `create_voice_preset.py`, update `voice_config.json`
5. **Custom validation** - Modify Whisper validation logic in chunk generation loop

## Branch Information

Current branch: `openai-api`
Main branch for PRs: `main`
