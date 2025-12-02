# OpenAI-Compatible TTS API Usage Guide

This guide explains how to use the OpenAI-compatible text-to-speech API that has been added to Chatterbox TTS.

## Starting the Server

### With API Enabled

```bash
python Chatter.py --enable-api
```

This will start both the Gradio UI and the REST API on the same server (default port 7860).

### Available Endpoints

- **Gradio UI**: http://localhost:7860/
- **API Root**: http://localhost:7860/v1/audio/speech
- **API Docs**: http://localhost:7860/v1/docs (Interactive Swagger UI)
- **Health Check**: http://localhost:7860/v1/health
- **List Voices**: http://localhost:7860/v1/voices

### Custom Host/Port

```bash
# Custom port
python Chatter.py --enable-api --port 8080

# Bind to all interfaces
python Chatter.py --enable-api --host 0.0.0.0

# Both
python Chatter.py --enable-api --host 0.0.0.0 --port 8000
```

### Without API (Original Behavior)

```bash
# Just Gradio UI (no API)
python Chatter.py
```

## API Endpoints

### POST /v1/audio/speech

Generate speech from text input.

**Request Body**:

```json
{
  "model": "tts-1",
  "input": "The text to generate audio for",
  "voice": "alloy",
  "response_format": "mp3",
  "speed": 1.0
}
```

**Parameters**:

| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `model` | string | Yes | TTS model: `tts-1` (fast) or `tts-1-hd` (higher quality) | - |
| `input` | string | Yes | Text to synthesize (max 4096 characters) | - |
| `voice` | string | Yes | Voice name: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer` | - |
| `response_format` | string | No | Audio format: `mp3`, `opus`, `aac`, `flac`, `wav`, `pcm` | `mp3` |
| `speed` | number | No | Speed (0.25-4.0) | `1.0` |

**Response**: Binary audio file

**Example with curl**:

```bash
curl http://localhost:7860/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "Hello, world!",
    "voice": "alloy"
  }' \
  --output speech.mp3
```

### GET /v1/voices

List available voice presets.

**Response**:

```json
{
  "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
}
```

**Example with curl**:

```bash
curl http://localhost:7860/v1/voices
```

### GET /v1/health

Health check endpoint.

**Response**:

```json
{
  "status": "healthy",
  "model_loaded": true,
  "device": "cuda"
}
```

**Example with curl**:

```bash
curl http://localhost:7860/v1/health
```

## Usage Examples

### Basic cURL Examples

#### Generate MP3 (default)

```bash
curl http://localhost:7860/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "Hello, this is a test.",
    "voice": "alloy"
  }' \
  --output speech.mp3
```

#### Generate WAV

```bash
curl http://localhost:7860/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "Testing WAV format.",
    "voice": "echo",
    "response_format": "wav"
  }' \
  --output speech.wav
```

#### Adjust Speed

```bash
curl http://localhost:7860/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "This is spoken faster.",
    "voice": "nova",
    "speed": 1.5
  }' \
  --output fast_speech.mp3
```

#### Use HD Model

```bash
curl http://localhost:7860/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1-hd",
    "input": "Higher quality audio.",
    "voice": "fable"
  }' \
  --output hd_speech.mp3
```

### Python with OpenAI SDK

The API is compatible with the official OpenAI Python SDK:

```python
from openai import OpenAI

# Point to your local Chatterbox API
client = OpenAI(
    base_url="http://localhost:7860/v1",
    api_key="dummy"  # Not validated, but required by SDK
)

# Generate speech
response = client.audio.speech.create(
    model="tts-1",
    voice="alloy",
    input="Hello from Chatterbox TTS!"
)

# Save to file
response.stream_to_file("output.mp3")
```

**With parameters**:

```python
response = client.audio.speech.create(
    model="tts-1-hd",
    voice="nova",
    input="This is higher quality at 1.5x speed.",
    speed=1.5
)

response.stream_to_file("output_hd.mp3")
```

### Python with Requests

```python
import requests

url = "http://localhost:7860/v1/audio/speech"

payload = {
    "model": "tts-1",
    "input": "Hello from Python!",
    "voice": "alloy",
    "response_format": "mp3"
}

response = requests.post(url, json=payload)

if response.status_code == 200:
    with open("speech.mp3", "wb") as f:
        f.write(response.content)
    print("Audio saved to speech.mp3")
else:
    print(f"Error: {response.status_code}")
    print(response.json())
```

### JavaScript/TypeScript

```javascript
const response = await fetch('http://localhost:7860/v1/audio/speech', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model: 'tts-1',
    input: 'Hello from JavaScript!',
    voice: 'alloy',
    response_format: 'mp3'
  })
});

if (response.ok) {
  const audioBlob = await response.blob();
  const audioUrl = URL.createObjectURL(audioBlob);

  // Play in browser
  const audio = new Audio(audioUrl);
  audio.play();

  // Or download
  const a = document.createElement('a');
  a.href = audioUrl;
  a.download = 'speech.mp3';
  a.click();
}
```

## Voice Presets

The API supports six voice presets matching OpenAI's voice names:

| Voice | Description | Gender |
|-------|-------------|--------|
| `alloy` | Neutral, balanced voice | Neutral |
| `echo` | Clear, resonant voice | Male |
| `fable` | Expressive, narrative voice | Female |
| `onyx` | Deep, authoritative voice | Male |
| `nova` | Warm, friendly voice | Female |
| `shimmer` | Bright, energetic voice | Female |

### Adding Custom Voice Presets

To add or update voice presets:

1. **Prepare audio file** (10-30 seconds of clear speech)
2. **Use the helper script**:

```bash
python create_voice_preset.py path/to/audio.mp3 alloy
```

This will:
- Convert to 24kHz mono WAV
- Trim silence
- Normalize volume
- Save to `voice_presets/alloy.wav`

3. **Voice preset is ready** - The API will automatically use it

See `voice_presets/README.md` for more details on creating voice presets.

## Model Differences

Both models use the same quality control features as the Gradio UI:
- 3 candidates generated per chunk
- Whisper validation enabled for quality assurance
- 3 retry attempts per candidate
- Parallel processing with 4 workers

The difference between models is subtle:

### tts-1 (Standard)
- **Temperature**: 0.75 (standard variation)
- **Use case**: General purpose, balanced quality and consistency

### tts-1-hd (High Definition)
- **Temperature**: 0.70 (more consistent output)
- **Use case**: Production audio requiring maximum consistency

## Response Formats

| Format | MIME Type | Description |
|--------|-----------|-------------|
| `mp3` | audio/mpeg | Most compatible, good compression |
| `opus` | audio/opus | Best compression, lower latency |
| `aac` | audio/aac | Apple/iOS compatible |
| `flac` | audio/flac | Lossless compression |
| `wav` | audio/wav | Uncompressed, highest quality |
| `pcm` | application/octet-stream | Raw audio data (16-bit) |

## Testing

### Automated Tests

Run the test suite with pytest:

```bash
pytest test_api.py -v
```

### Manual Testing Script

Run the comprehensive manual test script:

```bash
./test_api_manual.sh
```

This will test all endpoints, formats, and voices, saving output files to `./test_outputs/`.

## Error Handling

### Common Errors

**400 Bad Request - Invalid Voice**:
```json
{
  "error": {
    "message": "Invalid voice 'unknown'. Valid voices: ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']",
    "type": "invalid_request_error",
    "param": "voice",
    "code": "invalid_voice"
  }
}
```

**422 Validation Error - Empty Input**:
```json
{
  "detail": [
    {
      "loc": ["body", "input"],
      "msg": "Input text cannot be empty or whitespace only",
      "type": "value_error"
    }
  ]
}
```

**500 Internal Server Error - Generation Failure**:
```json
{
  "error": {
    "message": "TTS generation failed: ...",
    "type": "internal_server_error",
    "code": "generation_failure"
  }
}
```

## Performance Tips

1. **Both models use quality control** - 3 candidates + Whisper validation enabled by default
2. **Generation takes time** - Quality validation requires ~30-60 seconds for typical requests
3. **Keep input text under 500 characters** - Longer text takes more time
4. **Use MP3 format** - Fastest format conversion
5. **Voice presets are optional** - If missing, uses model default voice
6. **Speed parameter affects quality** - Extreme speeds (0.25 or 4.0) may sound unnatural

## Limitations

- Maximum input length: 4096 characters
- Speed range: 0.25 to 4.0
- Voice presets must be pre-configured (no voice cloning endpoint yet)
- No streaming support (future enhancement)
- Single concurrent request processing (model is shared with Gradio UI)

## Troubleshooting

### API not accessible

Make sure you started with `--enable-api` flag:
```bash
python Chatter.py --enable-api
```

### Import errors

Install FastAPI dependencies:
```bash
pip install fastapi uvicorn[standard] python-multipart
```

### Voice preset not found

Check `voice_presets/` directory and `voice_config.json`:
```bash
ls -la voice_presets/
cat voice_presets/voice_config.json
```

Create missing voice presets:
```bash
python create_voice_preset.py your_audio.mp3 voice_name
```

### Model not loading

Check CUDA/GPU availability:
```bash
curl http://localhost:7860/v1/health
```

## API Documentation

Interactive API documentation (Swagger UI) is available at:

**http://localhost:7860/v1/docs**

This provides:
- Complete endpoint documentation
- Request/response schemas
- Try-it-out functionality
- Example requests and responses

## Comparison with OpenAI API

### Compatible Features ✅
- `/v1/audio/speech` endpoint
- Request/response format
- All 6 voice names
- Model parameter (tts-1, tts-1-hd)
- Speed parameter (0.25-4.0)
- Response formats: mp3, opus, aac, flac, wav, pcm

### Not Implemented ❌
- Streaming responses (`response_format: "stream"`)
- Authentication/API keys
- Rate limiting
- Usage tracking
- Voice cloning API

### Chatterbox Extensions 🚀
- `/v1/voices` endpoint (list available voices)
- `/health` endpoint (model status)
- Fully local (no external API calls)
- Customizable voice presets

## Support

For issues or questions:
- Check the interactive docs: http://localhost:7860/v1/docs
- Review test output: `./test_api_manual.sh`
- Check server logs for errors
- See `voice_presets/README.md` for voice preset issues
