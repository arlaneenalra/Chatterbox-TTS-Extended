"""
OpenAI-compatible TTS API for Chatterbox

Provides FastAPI endpoints that match OpenAI's text-to-speech API specification.
"""

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse
import os
import tempfile
from pathlib import Path
import traceback

# Import Pydantic models
from api_models import TTSRequest, VoiceListResponse, HealthResponse

# Import utility functions
from api_utils import (
    load_voice_config,
    get_voice_audio_path,
    map_openai_to_chatterbox_params,
    convert_audio_format,
    get_content_type,
    cleanup_temp_files
)

# Import Chatterbox functions
from Chatter import get_or_load_model, process_text_for_tts, DEVICE


# Initialize FastAPI app
app = FastAPI(
    title="Chatterbox TTS API",
    description="OpenAI-compatible text-to-speech API powered by Chatterbox TTS",
    version="1.0.0"
)


@app.post("/audio/speech", response_class=Response)
async def create_speech(request: TTSRequest):
    """
    Generate speech audio from input text

    OpenAI-compatible endpoint for text-to-speech synthesis.
    Supports multiple voices, formats, and speed adjustments.

    Args:
        request: TTS request matching OpenAI schema

    Returns:
        Binary audio file with appropriate Content-Type header

    Raises:
        HTTPException 400: Invalid voice or parameters
        HTTPException 500: TTS generation failure
    """
    try:
        # Validate voice exists
        config = load_voice_config()
        if request.voice not in config.get("voices", {}):
            valid_voices = list(config.get("voices", {}).keys())
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "message": f"Invalid voice '{request.voice}'. Valid voices: {valid_voices}",
                        "type": "invalid_request_error",
                        "param": "voice",
                        "code": "invalid_voice"
                    }
                }
            )

        # Get voice reference audio path
        voice_audio_path = get_voice_audio_path(request.voice)
        print(f"[API] Using voice preset: {request.voice} -> {voice_audio_path}")

        # Map OpenAI parameters to Chatterbox parameters
        chatterbox_params = map_openai_to_chatterbox_params(
            speed=request.speed,
            model=request.model,
            response_format=request.response_format
        )

        print(f"[API] Generating speech for {len(request.input)} characters")
        print(f"[API] Model: {request.model}, Voice: {request.voice}, Format: {request.response_format}, Speed: {request.speed}")

        # Ensure model is loaded
        model = get_or_load_model()
        if model is None:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "message": "TTS model failed to load",
                        "type": "internal_server_error",
                        "code": "model_load_failure"
                    }
                }
            )

        # Call Chatterbox TTS pipeline
        output_files = process_text_for_tts(
            text=request.input,
            input_basename="api_request",
            audio_prompt_path_input=voice_audio_path,
            **chatterbox_params
        )

        if not output_files or len(output_files) == 0:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "message": "TTS generation produced no output files",
                        "type": "internal_server_error",
                        "code": "generation_failure"
                    }
                }
            )

        # Get the generated audio file (first in list)
        audio_file = output_files[0]
        print(f"[API] Generated audio file: {audio_file}")

        # Convert to requested format if needed
        if request.response_format in ["opus", "aac", "pcm"]:
            print(f"[API] Converting to {request.response_format} format...")
            final_audio = convert_audio_format(audio_file, request.response_format)
            # Add converted file to cleanup list
            output_files.append(final_audio)
        else:
            final_audio = audio_file

        # Read audio file
        if not os.path.exists(final_audio):
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "message": f"Generated audio file not found: {final_audio}",
                        "type": "internal_server_error",
                        "code": "file_not_found"
                    }
                }
            )

        with open(final_audio, "rb") as f:
            audio_data = f.read()

        print(f"[API] Serving {len(audio_data)} bytes of {request.response_format} audio")

        # Clean up temporary files
        cleanup_temp_files(output_files)

        # Determine content type
        content_type = get_content_type(request.response_format)

        # Return audio file
        return Response(
            content=audio_data,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="speech.{request.response_format}"'
            }
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except Exception as e:
        # Log the full traceback for debugging
        print(f"[API ERROR] TTS generation failed: {e}")
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"TTS generation failed: {str(e)}",
                    "type": "internal_server_error",
                    "code": "generation_failure"
                }
            }
        )


@app.get("/voices", response_model=VoiceListResponse)
async def list_voices():
    """
    List available voice presets

    Extension to OpenAI API for discovering available voices.

    Returns:
        VoiceListResponse: List of available voice names
    """
    try:
        config = load_voice_config()
        voices = list(config.get("voices", {}).keys())

        return VoiceListResponse(voices=voices)

    except Exception as e:
        print(f"[API ERROR] Failed to list voices: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Failed to list voices: {str(e)}",
                    "type": "internal_server_error",
                    "code": "voice_list_failure"
                }
            }
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint

    Returns model status and device information.

    Returns:
        HealthResponse: Health status, model loaded state, and device
    """
    try:
        model = get_or_load_model()
        model_loaded = model is not None

        return HealthResponse(
            status="healthy" if model_loaded else "unhealthy",
            model_loaded=model_loaded,
            device=DEVICE
        )

    except Exception as e:
        print(f"[API ERROR] Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            model_loaded=False,
            device=DEVICE
        )


@app.get("/")
async def root():
    """
    API root endpoint

    Returns basic API information.
    """
    return {
        "name": "Chatterbox TTS API",
        "version": "1.0.0",
        "description": "OpenAI-compatible text-to-speech API",
        "endpoints": {
            "speech": "/audio/speech (POST)",
            "voices": "/voices (GET)",
            "health": "/health (GET)"
        },
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    print("[API] Starting Chatterbox TTS API server...")
    print("[API] Docs available at http://localhost:8000/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000)
