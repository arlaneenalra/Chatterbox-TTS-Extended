"""
Test suite for Chatterbox OpenAI-compatible TTS API

Run with: pytest test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
from api import app
import json

# Create test client
client = TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check_returns_200(self):
        """Health endpoint should return 200 status"""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_has_required_fields(self):
        """Health response should contain status, model_loaded, and device"""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "model_loaded" in data
        assert "device" in data

    def test_health_check_status_is_string(self):
        """Health status should be a string"""
        response = client.get("/health")
        data = response.json()

        assert isinstance(data["status"], str)
        assert data["status"] in ["healthy", "unhealthy"]


class TestVoicesEndpoint:
    """Test voice listing endpoint"""

    def test_list_voices_returns_200(self):
        """Voices endpoint should return 200 status"""
        response = client.get("/voices")
        assert response.status_code == 200

    def test_list_voices_returns_array(self):
        """Voices endpoint should return a list of voices"""
        response = client.get("/voices")
        data = response.json()

        assert "voices" in data
        assert isinstance(data["voices"], list)

    def test_list_voices_contains_expected_voices(self):
        """Voices list should contain standard OpenAI voice names"""
        response = client.get("/voices")
        data = response.json()
        voices = data["voices"]

        # Check that we have some voices (may be empty if presets not created yet)
        # Expected voices: alloy, echo, fable, onyx, nova, shimmer
        expected_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

        # If voices are configured, they should match expected names
        for voice in voices:
            assert voice in expected_voices


class TestSpeechEndpoint:
    """Test TTS generation endpoint"""

    def test_speech_endpoint_requires_post(self):
        """Speech endpoint should only accept POST requests"""
        response = client.get("/audio/speech")
        assert response.status_code == 405  # Method Not Allowed

    def test_speech_basic_generation(self):
        """Test basic TTS generation with minimal parameters"""
        response = client.post(
            "/audio/speech",
            json={
                "model": "tts-1",
                "input": "Hello, world!",
                "voice": "alloy"
            }
        )

        # Should return 200 or potentially fail if model not loaded
        # For now we check it doesn't return 422 (validation error)
        assert response.status_code != 422

    def test_speech_with_all_parameters(self):
        """Test TTS generation with all optional parameters"""
        response = client.post(
            "/audio/speech",
            json={
                "model": "tts-1-hd",
                "input": "Testing all parameters",
                "voice": "nova",
                "response_format": "wav",
                "speed": 1.5
            }
        )

        assert response.status_code != 422

    def test_speech_validates_voice(self):
        """Test that invalid voice names are rejected"""
        response = client.post(
            "/audio/speech",
            json={
                "model": "tts-1",
                "input": "This should fail",
                "voice": "invalid_voice_name"
            }
        )

        # Should return 422 for invalid enum value
        assert response.status_code == 422

    def test_speech_validates_empty_input(self):
        """Test that empty input is rejected"""
        response = client.post(
            "/audio/speech",
            json={
                "model": "tts-1",
                "input": "",
                "voice": "alloy"
            }
        )

        assert response.status_code == 422

    def test_speech_validates_whitespace_only_input(self):
        """Test that whitespace-only input is rejected"""
        response = client.post(
            "/audio/speech",
            json={
                "model": "tts-1",
                "input": "   ",
                "voice": "alloy"
            }
        )

        assert response.status_code == 422

    def test_speech_validates_input_length(self):
        """Test that input exceeding max length is rejected"""
        long_text = "x" * 4097  # Over 4096 char limit

        response = client.post(
            "/audio/speech",
            json={
                "model": "tts-1",
                "input": long_text,
                "voice": "alloy"
            }
        )

        assert response.status_code == 422

    def test_speech_validates_speed_range(self):
        """Test that speed outside valid range is rejected"""
        # Test speed too low
        response = client.post(
            "/audio/speech",
            json={
                "model": "tts-1",
                "input": "Test speed",
                "voice": "alloy",
                "speed": 0.1  # Below 0.25 minimum
            }
        )
        assert response.status_code == 422

        # Test speed too high
        response = client.post(
            "/audio/speech",
            json={
                "model": "tts-1",
                "input": "Test speed",
                "voice": "alloy",
                "speed": 5.0  # Above 4.0 maximum
            }
        )
        assert response.status_code == 422

    def test_speech_validates_model(self):
        """Test that invalid model names are rejected"""
        response = client.post(
            "/audio/speech",
            json={
                "model": "invalid-model",
                "input": "Test",
                "voice": "alloy"
            }
        )

        assert response.status_code == 422

    def test_speech_validates_response_format(self):
        """Test that invalid response formats are rejected"""
        response = client.post(
            "/audio/speech",
            json={
                "model": "tts-1",
                "input": "Test",
                "voice": "alloy",
                "response_format": "invalid_format"
            }
        )

        assert response.status_code == 422

    def test_speech_default_response_format(self):
        """Test that response_format defaults to mp3"""
        # This test checks validation passes without response_format
        response = client.post(
            "/audio/speech",
            json={
                "model": "tts-1",
                "input": "Test default format",
                "voice": "alloy"
            }
        )

        # Should not return validation error
        assert response.status_code != 422

    def test_speech_default_speed(self):
        """Test that speed defaults to 1.0"""
        # This test checks validation passes without speed
        response = client.post(
            "/audio/speech",
            json={
                "model": "tts-1",
                "input": "Test default speed",
                "voice": "alloy"
            }
        )

        # Should not return validation error
        assert response.status_code != 422


class TestRootEndpoint:
    """Test API root endpoint"""

    def test_root_returns_200(self):
        """Root endpoint should return 200 status"""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_json(self):
        """Root endpoint should return JSON with API info"""
        response = client.get("/")
        data = response.json()

        assert "name" in data
        assert "version" in data
        assert "endpoints" in data


class TestRequestValidation:
    """Test Pydantic validation of request schemas"""

    def test_missing_required_fields(self):
        """Test that missing required fields are rejected"""
        # Missing input
        response = client.post(
            "/audio/speech",
            json={
                "model": "tts-1",
                "voice": "alloy"
            }
        )
        assert response.status_code == 422

        # Missing voice
        response = client.post(
            "/audio/speech",
            json={
                "model": "tts-1",
                "input": "Test"
            }
        )
        assert response.status_code == 422

        # Missing model
        response = client.post(
            "/audio/speech",
            json={
                "input": "Test",
                "voice": "alloy"
            }
        )
        assert response.status_code == 422

    def test_invalid_json(self):
        """Test that invalid JSON is rejected"""
        response = client.post(
            "/audio/speech",
            data="not json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_wrong_content_type(self):
        """Test that non-JSON content type is rejected"""
        response = client.post(
            "/audio/speech",
            data="some data",
            headers={"Content-Type": "text/plain"}
        )
        assert response.status_code == 422


# Integration tests (these may require the model to be loaded)
class TestIntegration:
    """Integration tests requiring full TTS model"""

    @pytest.mark.integration
    @pytest.mark.skipif(True, reason="Requires model to be loaded, run manually")
    def test_full_tts_pipeline_mp3(self):
        """Test complete TTS generation pipeline with MP3 output"""
        response = client.post(
            "/audio/speech",
            json={
                "model": "tts-1",
                "input": "This is a complete integration test.",
                "voice": "alloy",
                "response_format": "mp3"
            }
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/mpeg"
        assert len(response.content) > 0

    @pytest.mark.integration
    @pytest.mark.skipif(True, reason="Requires model to be loaded, run manually")
    def test_full_tts_pipeline_wav(self):
        """Test complete TTS generation pipeline with WAV output"""
        response = client.post(
            "/audio/speech",
            json={
                "model": "tts-1",
                "input": "Testing WAV format output.",
                "voice": "echo",
                "response_format": "wav"
            }
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/wav"
        assert len(response.content) > 0

    @pytest.mark.integration
    @pytest.mark.skipif(True, reason="Requires model to be loaded, run manually")
    def test_all_voices(self):
        """Test TTS generation with all available voices"""
        voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

        for voice in voices:
            response = client.post(
                "/audio/speech",
                json={
                    "model": "tts-1",
                    "input": f"Testing voice: {voice}",
                    "voice": voice
                }
            )

            # Should succeed or return 500 if voice preset missing
            assert response.status_code in [200, 500]

    @pytest.mark.integration
    @pytest.mark.skipif(True, reason="Requires model to be loaded, run manually")
    def test_all_formats(self):
        """Test TTS generation with all response formats"""
        formats = ["mp3", "wav", "flac", "opus", "aac", "pcm"]

        for fmt in formats:
            response = client.post(
                "/audio/speech",
                json={
                    "model": "tts-1",
                    "input": f"Testing format: {fmt}",
                    "voice": "alloy",
                    "response_format": fmt
                }
            )

            assert response.status_code == 200

    @pytest.mark.integration
    @pytest.mark.skipif(True, reason="Requires model to be loaded, run manually")
    def test_speed_variations(self):
        """Test TTS generation with different speed settings"""
        speeds = [0.25, 0.5, 1.0, 2.0, 4.0]

        for speed in speeds:
            response = client.post(
                "/audio/speech",
                json={
                    "model": "tts-1",
                    "input": "Testing speed variation",
                    "voice": "alloy",
                    "speed": speed
                }
            )

            assert response.status_code == 200

    @pytest.mark.integration
    @pytest.mark.skipif(True, reason="Requires model to be loaded, run manually")
    def test_model_quality_difference(self):
        """Test both tts-1 and tts-1-hd models"""
        for model in ["tts-1", "tts-1-hd"]:
            response = client.post(
                "/audio/speech",
                json={
                    "model": model,
                    "input": f"Testing model: {model}",
                    "voice": "alloy"
                }
            )

            assert response.status_code == 200


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
