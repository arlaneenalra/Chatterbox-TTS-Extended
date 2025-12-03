#!/bin/bash
# Example script demonstrating bulk TTS processing

echo "=================================================="
echo "Bulk TTS Client - Example Run"
echo "=================================================="
echo ""
echo "This script demonstrates how to use the bulk TTS client"
echo "to process multiple text files at once."
echo ""

# Check if Gradio server is running
if ! curl -s http://localhost:7860 > /dev/null 2>&1; then
    echo "ERROR: Gradio server is not running!"
    echo ""
    echo "Please start the server first:"
    echo "  python Chatter.py"
    echo ""
    exit 1
fi

echo "✓ Gradio server is running"
echo ""

# Check if gradio_client is installed
if ! python -c "import gradio_client" 2>/dev/null; then
    echo "ERROR: gradio_client library not found!"
    echo ""
    echo "Please install it:"
    echo "  pip install gradio_client"
    echo ""
    exit 1
fi

echo "✓ gradio_client library is installed"
echo ""

# Create output directory
OUTPUT_DIR="./example_outputs"
mkdir -p "$OUTPUT_DIR"

echo "Processing text files from: ./example_texts"
echo "Output directory: $OUTPUT_DIR"
echo ""

# Run the bulk client
python bulk_tts_client.py \
    --input-dir ./example_texts \
    --output-dir "$OUTPUT_DIR" \
    --settings example_bulk_settings.json

echo ""
echo "=================================================="
echo "Done! Check the output files in: $OUTPUT_DIR"
echo "=================================================="
