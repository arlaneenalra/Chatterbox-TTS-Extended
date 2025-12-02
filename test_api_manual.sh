#!/bin/bash
# Manual API testing script for Chatterbox TTS
# Run this after starting the server with: python Chatter.py --enable-api

set -e

BASE_URL="http://localhost:7860"
OUTPUT_DIR="./test_outputs"

echo "🧪 Chatterbox TTS API Manual Test Suite"
echo "========================================"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Test 1: Health Check
echo "Test 1: Health Check"
echo "--------------------"
curl -s "$BASE_URL/health" | jq .
echo ""
echo ""

# Test 2: List Voices
echo "Test 2: List Voices"
echo "-------------------"
curl -s "$BASE_URL/v1/voices" | jq .
echo ""
echo ""

# Test 3: Basic TTS Generation (MP3)
echo "Test 3: Basic TTS Generation (MP3)"
echo "----------------------------------"
curl -s "$BASE_URL/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "Hello, this is a test of the Chatterbox TTS API.",
    "voice": "alloy"
  }' \
  --output "$OUTPUT_DIR/test_basic.mp3"

if [ -f "$OUTPUT_DIR/test_basic.mp3" ]; then
  SIZE=$(ls -lh "$OUTPUT_DIR/test_basic.mp3" | awk '{print $5}')
  echo "✅ Generated: test_basic.mp3 ($SIZE)"
else
  echo "❌ Failed to generate test_basic.mp3"
fi
echo ""
echo ""

# Test 4: WAV Format
echo "Test 4: WAV Format"
echo "------------------"
curl -s "$BASE_URL/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "Testing WAV format output.",
    "voice": "echo",
    "response_format": "wav"
  }' \
  --output "$OUTPUT_DIR/test_wav.wav"

if [ -f "$OUTPUT_DIR/test_wav.wav" ]; then
  SIZE=$(ls -lh "$OUTPUT_DIR/test_wav.wav" | awk '{print $5}')
  echo "✅ Generated: test_wav.wav ($SIZE)"
else
  echo "❌ Failed to generate test_wav.wav"
fi
echo ""
echo ""

# Test 5: Speed Adjustment
echo "Test 5: Speed Adjustment (1.5x)"
echo "-------------------------------"
curl -s "$BASE_URL/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "This is being spoken at one point five times the normal speed.",
    "voice": "nova",
    "speed": 1.5
  }' \
  --output "$OUTPUT_DIR/test_speed_fast.mp3"

if [ -f "$OUTPUT_DIR/test_speed_fast.mp3" ]; then
  SIZE=$(ls -lh "$OUTPUT_DIR/test_speed_fast.mp3" | awk '{print $5}')
  echo "✅ Generated: test_speed_fast.mp3 ($SIZE)"
else
  echo "❌ Failed to generate test_speed_fast.mp3"
fi
echo ""
echo ""

# Test 6: HD Model
echo "Test 6: HD Model (tts-1-hd)"
echo "---------------------------"
curl -s "$BASE_URL/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1-hd",
    "input": "Testing the high definition model for better quality.",
    "voice": "fable"
  }' \
  --output "$OUTPUT_DIR/test_hd.mp3"

if [ -f "$OUTPUT_DIR/test_hd.mp3" ]; then
  SIZE=$(ls -lh "$OUTPUT_DIR/test_hd.mp3" | awk '{print $5}')
  echo "✅ Generated: test_hd.mp3 ($SIZE)"
else
  echo "❌ Failed to generate test_hd.mp3"
fi
echo ""
echo ""

# Test 7: Different Voice
echo "Test 7: Different Voice (shimmer)"
echo "---------------------------------"
curl -s "$BASE_URL/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "Testing a different voice preset.",
    "voice": "shimmer"
  }' \
  --output "$OUTPUT_DIR/test_voice_shimmer.mp3"

if [ -f "$OUTPUT_DIR/test_voice_shimmer.mp3" ]; then
  SIZE=$(ls -lh "$OUTPUT_DIR/test_voice_shimmer.mp3" | awk '{print $5}')
  echo "✅ Generated: test_voice_shimmer.mp3 ($SIZE)"
else
  echo "❌ Failed to generate test_voice_shimmer.mp3"
fi
echo ""
echo ""

# Test 8: Error Handling - Invalid Voice
echo "Test 8: Error Handling (Invalid Voice)"
echo "--------------------------------------"
RESPONSE=$(curl -s "$BASE_URL/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "This should fail",
    "voice": "invalid_voice"
  }')

echo "$RESPONSE" | jq .
echo ""
echo ""

# Summary
echo "📊 Test Summary"
echo "==============="
echo "Output files saved to: $OUTPUT_DIR"
echo ""
ls -lh "$OUTPUT_DIR"
echo ""
echo "✅ All tests complete!"
echo ""
echo "💡 Tips:"
echo "  - Play audio files with: mpv $OUTPUT_DIR/test_basic.mp3"
echo "  - View API docs at: $BASE_URL/docs"
echo "  - Access Gradio UI at: $BASE_URL/ui"
