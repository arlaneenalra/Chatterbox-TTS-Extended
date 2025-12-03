# Bulk TTS Client for Chatterbox-TTS-Extended

This client script allows you to batch process a directory of text files into audio files using the Chatterbox TTS Gradio API.

## Prerequisites

1. **Install the Gradio client library:**
   ```bash
   pip install gradio_client
   ```

2. **Start the Chatterbox Gradio server:**
   ```bash
   python Chatter.py
   ```
   The server should be running at `http://localhost:7860`

## Basic Usage

### Process a directory of text files:
```bash
python bulk_tts_client.py --input-dir ./my_texts --output-dir ./my_outputs
```

### Use custom settings:
```bash
python bulk_tts_client.py \
  --input-dir ./my_texts \
  --output-dir ./my_outputs \
  --settings example_bulk_settings.json
```

### Use a reference audio for voice cloning:
```bash
python bulk_tts_client.py \
  --input-dir ./my_texts \
  --output-dir ./my_outputs \
  --reference-audio ./my_voice.wav
```

### Connect to a remote Gradio instance:
```bash
python bulk_tts_client.py \
  --input-dir ./my_texts \
  --output-dir ./my_outputs \
  --url http://192.168.1.100:7860
```

## Command Line Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--input-dir` | Yes* | - | Directory containing input text files (.txt) |
| `--output-dir` | Yes* | - | Directory to save output audio files |
| `--settings` | No | (defaults) | Path to settings.json file |
| `--reference-audio` | No | None | Path to reference audio for voice cloning |
| `--url` | No | `http://localhost:7860` | Gradio server URL |
| `--pattern` | No | `*.txt` | File pattern to match |
| `--api-name` | No | `/lambda` | Gradio API endpoint name |
| `--fn-index` | No | None | Gradio function index (alternative to api-name) |
| `--list-endpoints` | No | False | List available endpoints and exit |

*Not required when using `--list-endpoints`

**Note:** The script uses `api_name="/lambda"` by default, which is the TTS generation endpoint. You usually don't need to change this.

## Settings File Format

The settings file uses the same structure as the main Chatterbox application's `settings.json`. See `example_bulk_settings.json` for a complete example.

### Key Settings:

**Audio Quality:**
- `num_candidates_slider` (1-10): Number of generation attempts per chunk (higher = better quality, slower)
- `max_attempts_slider` (1-10): Maximum retry attempts for Whisper validation
- `temp_slider` (0.01-5.0): Temperature for generation (higher = more variation)

**Text Processing:**
- `to_lowercase_checkbox`: Convert text to lowercase
- `normalize_spacing_checkbox`: Remove extra whitespace
- `fix_dot_letters_checkbox`: Convert "J.R.R." to "J R R"
- `remove_reference_numbers_checkbox`: Remove inline citations

**Audio Post-Processing:**
- `use_pyrnnoise_checkbox`: Apply RNNoise denoising
- `use_auto_editor_checkbox`: Remove silence and stutters
- `normalize_audio_checkbox`: Normalize audio levels with FFmpeg

**Performance:**
- `enable_parallel_checkbox`: Enable parallel chunk processing
- `num_parallel_workers_slider` (1-8): Number of parallel workers
- `use_faster_whisper_checkbox`: Use faster Whisper backend

**Output:**
- `export_format_checkboxes`: List of formats, e.g., `["wav", "mp3", "flac"]`

## Example Workflow

1. **Create a directory with text files:**
   ```bash
   mkdir my_texts
   echo "Hello world, this is a test." > my_texts/test1.txt
   echo "Another sample text for TTS conversion." > my_texts/test2.txt
   ```

2. **Customize settings (optional):**
   ```bash
   cp example_bulk_settings.json my_settings.json
   # Edit my_settings.json as needed
   ```

3. **Start the Gradio server:**
   ```bash
   python Chatter.py
   ```

4. **Run the bulk processor:**
   ```bash
   python bulk_tts_client.py \
     --input-dir ./my_texts \
     --output-dir ./my_outputs \
     --settings my_settings.json
   ```

5. **Find your audio files:**
   ```bash
   ls -lh my_outputs/
   # Output: test1.mp3, test2.mp3
   ```

## Output Files

For each input text file, the script will generate audio files with the same base name:
- `input.txt` → `input.mp3` (or .wav, .flac depending on settings)

If multiple generations are requested (`num_generations_input` > 1) or multiple formats are selected, files will be numbered:
- `input_1.mp3`, `input_2.mp3`, etc.

## How It Works

The script connects to the Gradio server and calls the TTS generation endpoint using `api_name="/lambda"`. This is the endpoint automatically created by Gradio for the Generate button's click handler.

### If You Get Endpoint Errors

The default should work automatically. If you encounter issues, you can inspect available endpoints:

```bash
# See what endpoints are available
python inspect_endpoint.py http://localhost:7860
```

Or specify a different endpoint:
```bash
python bulk_tts_client.py \
  --input-dir ./texts \
  --output-dir ./outputs \
  --api-name /lambda
```

## Troubleshooting

For detailed troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

**Quick fixes:**

### "Error connecting to Gradio server"
- Make sure `Chatter.py` is running: `python Chatter.py`
- Check that the URL is correct (default: `http://localhost:7860`)

### "Cannot find a function" or endpoint errors
- The script uses `api_name="/lambda"` by default (should work automatically)
- Run `python inspect_endpoint.py http://localhost:7860` to see available endpoints
- Try explicitly: `--api-name /lambda` or use `--fn-index 0`

### "gradio_client library not found"
- Install it with: `pip install gradio_client`

### Generation fails or produces poor quality
- Increase `num_candidates_slider` for better quality
- Enable `use_faster_whisper_checkbox` for more reliable validation
- Adjust `temp_slider` (0.75 is a good default)
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more solutions

### Files processed but no output
- Check the Gradio server console for errors
- Verify the input text files are not empty
- Make sure the output directory is writable

## Performance Tips

1. **For faster processing:** Increase `num_parallel_workers_slider` (requires more VRAM)
2. **For better quality:** Increase `num_candidates_slider` and enable Whisper validation
3. **For cleaner audio:** Enable `use_pyrnnoise_checkbox` and `use_auto_editor_checkbox`
4. **For consistent output:** Set a non-zero `seed_input` value

## Advanced: Remote Processing

You can run the Gradio server on a powerful machine (with GPU) and connect to it from another computer:

**On the server machine:**
```bash
python Chatter.py --host 0.0.0.0 --port 7860
```

**On the client machine:**
```bash
python bulk_tts_client.py \
  --input-dir ./texts \
  --output-dir ./outputs \
  --url http://SERVER_IP:7860
```

## Notes

- The script preserves the original text filenames in the output audio files
- All settings from the main application are supported
- Multiple audio formats can be generated simultaneously
- Processing happens sequentially (one file at a time) to manage VRAM usage
- The Gradio server must remain running during processing
