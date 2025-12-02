"""
Pydantic models for OpenAI-compatible TTS API

Defines request and response schemas matching OpenAI's TTS API specification.
"""

from pydantic import BaseModel, Field, validator
from typing import Literal


class TTSRequest(BaseModel):
    """OpenAI TTS API request schema"""

    model: Literal["tts-1", "tts-1-hd"] = Field(
        default="tts-1",
        description="TTS model to use. tts-1 is faster, tts-1-hd has higher quality."
    )

    input: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="The text to generate audio for. Maximum 4096 characters."
    )

    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = Field(
        default="alloy",
        description="The voice to use for generation"
    )

    response_format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] = Field(
        default="mp3",
        description="The audio format of the output. Defaults to mp3."
    )

    speed: float = Field(
        default=1.0,
        ge=0.25,
        le=4.0,
        description="Speed of generated audio. Range: 0.25 to 4.0. Defaults to 1.0."
    )

    @validator("input")
    def validate_input(cls, v):
        """Ensure input text is not empty after stripping whitespace"""
        if not v.strip():
            raise ValueError("Input text cannot be empty or whitespace only")
        return v

    class Config:
        schema_extra = {
            "example": {
                "model": "tts-1",
                "input": "Hello, this is a test of the Chatterbox TTS API.",
                "voice": "alloy",
                "response_format": "mp3",
                "speed": 1.0
            }
        }


class ErrorResponse(BaseModel):
    """Error response schema matching OpenAI format"""

    error: dict

    class Config:
        schema_extra = {
            "example": {
                "error": {
                    "message": "Invalid voice 'unknown'. Valid voices: ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']",
                    "type": "invalid_request_error",
                    "param": "voice",
                    "code": "invalid_voice"
                }
            }
        }


class VoiceListResponse(BaseModel):
    """Response for listing available voices"""

    voices: list[str] = Field(
        ...,
        description="List of available voice names"
    )

    class Config:
        schema_extra = {
            "example": {
                "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = Field(..., description="Health status")
    model_loaded: bool = Field(..., description="Whether the TTS model is loaded")
    device: str = Field(..., description="Device the model is running on (cuda/cpu/mps)")

    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "model_loaded": True,
                "device": "cuda"
            }
        }
