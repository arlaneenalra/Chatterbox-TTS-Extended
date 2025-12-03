# Troubleshooting the Bulk TTS Client

## Understanding Gradio Endpoints

The script uses **named API endpoints** to call the TTS generation function.

### What is api_name="/lambda"?

When you create a Gradio button with `.click()`, Gradio automatically creates an API endpoint. If you don't specify a name, it defaults to "/lambda". This is the endpoint the script uses.

### Default Behavior (Recommended)

The script uses `api_name="/lambda"` by default, which should work automatically:

```bash
python bulk_tts_client.py \
  --input-dir ./example_texts \
  --output-dir ./example_outputs
```

No need to specify anything - it will use the correct endpoint automatically.

### If the Default Doesn't Work

#### Step 1: Discover Available Endpoints

Run the inspection script to see what endpoints exist:

```bash
python inspect_endpoint.py http://localhost:7860
```

This will show output like:

```
Named API endpoints: 4
 - /apply_settings_json
 - /update_audio_preview
 - /lambda (TTS generation - this is what we use)
 - /_vc_wrapper (Voice conversion)
```

#### Step 2: Try a Different Endpoint

If `/lambda` doesn't work, try specifying it explicitly:

```bash
python bulk_tts_client.py \
  --input-dir ./example_texts \
  --output-dir ./example_outputs \
  --api-name /lambda
```

Or use function index if needed:

```bash
python bulk_tts_client.py \
  --input-dir ./example_texts \
  --output-dir ./example_outputs \
  --fn-index 0
```

## Common Issues and Solutions

### Issue: "Error connecting to Gradio server"

**Solution:** Make sure the Gradio server is running:
```bash
python Chatter.py
```

The server should show a message like:
```
Running on local URL:  http://127.0.0.1:7860
```

### Issue: "Cannot find a function with api_name" or endpoint errors

**Solution:** The script now uses `api_name="/lambda"` by default, which should work automatically. If you still have issues:

1. Run the inspection script to see available endpoints:
   ```bash
   python inspect_endpoint.py http://localhost:7860
   ```

2. Try explicitly setting the api_name:
   ```bash
   python bulk_tts_client.py --input-dir ./texts --output-dir ./outputs --api-name /lambda
   ```

3. Or try using function index instead:
   ```bash
   python bulk_tts_client.py --input-dir ./texts --output-dir ./outputs --fn-index 0
   ```

### Issue: "gradio_client library not found"

**Solution:** Install the gradio_client library:
```bash
pip install gradio_client
```

### Issue: Generation produces no output

**Possible causes:**
1. Empty text files - check that your input files contain text
2. Server errors - check the Gradio server console for error messages
3. Wrong parameters - verify your settings.json file

**Solution:** Check the Gradio server console output for specific errors.

### Issue: Poor quality audio

**Solutions:**
1. Increase `num_candidates_slider` in settings (try 5-7)
2. Enable `use_faster_whisper_checkbox` for better validation
3. Adjust `temp_slider` (0.75 is a good default)
4. Enable `use_pyrnnoise_checkbox` for denoising
5. Enable `use_auto_editor_checkbox` to remove silence/stutters

### Issue: Processing is very slow

**Solutions:**
1. Increase `num_parallel_workers_slider` (if you have enough VRAM)
2. Enable `use_faster_whisper_checkbox` instead of OpenAI Whisper
3. Reduce `num_candidates_slider` for faster (but lower quality) generation
4. Use a smaller Whisper model (e.g., "tiny" or "small")

### Issue: Out of memory / CUDA errors

**Solutions:**
1. Reduce `num_parallel_workers_slider` to 1 or 2
2. Use a smaller Whisper model
3. Process fewer files at once
4. Close other GPU-using applications

## Testing the Setup

### Quick Test

Create a simple test file:
```bash
echo "Hello world, this is a test." > test.txt
```

Process it:
```bash
python bulk_tts_client.py \
  --input-dir . \
  --output-dir ./test_output \
  --pattern "test.txt"
```

If this works, your setup is correct!

### Using the Example Files

The repository includes example text files for testing:
```bash
./run_bulk_example.sh
```

This will process the files in `example_texts/` and save outputs to `example_outputs/`.

## Getting Help

If you continue to have issues:

1. Check the Gradio server console for error messages
2. Try the `--list-endpoints` flag to see available endpoints
3. Verify your settings.json file is valid JSON
4. Make sure all required dependencies are installed
5. Check that FFmpeg is available on your PATH (required for some features)

## Advanced: Manual API Testing

You can test the Gradio API directly in Python:

```python
from gradio_client import Client

client = Client("http://localhost:7860")

# List all endpoints
print(client.view_api(all_endpoints=True))

# Make a test call
result = client.predict(
    "Hello world",  # text_input
    None,           # text_file_input
    None,           # ref_audio_input
    0.5,            # exaggeration_slider
    0.75,           # temp_slider
    # ... (all other parameters)
)

print(result)
```
