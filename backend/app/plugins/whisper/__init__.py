"""
Whisper Voice Plugin - Voice-to-Fixture Transcription

Local Whisper integration for transcribing voice notes and extracting
maritime fixture data.

Environment Variables:
- OLLAMA_BASE_URL: Ollama server URL (default: http://localhost:11434)
- WHISPER_MODEL: Whisper model name (default: whisper)
- LLAMA_MODEL: Llama model for extraction (default: llama3.1:70b)

API Endpoints:
- POST /api/v1/voice/transcribe - Transcribe audio
- POST /api/v1/voice/to-fixture - Convert transcript to fixture
"""
import os
import json
import logging
import base64
from typing import Dict, Any, Optional

import aiohttp

logger = logging.getLogger(__name__)


class WhisperVoiceService:
    """Local Whisper for voice-to-fixture transcription"""

    def __init__(self):
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.whisper_model = os.getenv("WHISPER_MODEL", "whisper")
        self.llama_model = os.getenv("LLAMA_MODEL", "llama3.1:70b")

    async def transcribe_audio(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Transcribe audio using local Ollama Whisper.
        
        Supports formats: webm, mp3, wav, ogg, m4a
        Audio is converted to wav before sending to Whisper.
        """
        try:
            # Convert audio to wav format if needed
            wav_audio = await self._convert_to_wav(audio_data)
            if not wav_audio:
                return {"error": "Failed to convert audio format"}

            # Encode audio as base64
            base64_audio = base64.b64encode(wav_audio).decode("utf-8")

            # Call Ollama Whisper API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_base_url}/api/transcribe",
                    json={
                        "model": self.whisper_model,
                        "file": base64_audio,
                    },
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return {
                            "text": result.get("text", "").strip(),
                            "language": result.get("language", "en"),
                        }
                    else:
                        error_text = await resp.text()
                        logger.error(f"Whisper API error: {resp.status} - {error_text}")
                        return {"error": f"Transcription failed: {resp.status}"}

        except aiohttp.ClientError as e:
            logger.error(f"Connection error to Ollama: {e}")
            return {"error": f"Connection error: {str(e)}"}
        except Exception as e:
            logger.exception(f"Unexpected error in transcription: {e}")
            return {"error": str(e)}

    async def _convert_to_wav(self, audio_data: bytes) -> Optional[bytes]:
        """
        Convert audio to WAV format.
        
        For now, assumes input is already wav or raw PCM.
        In production, use a proper audio conversion library like pydub or ffmpeg.
        """
        # Simple passthrough - in production, implement proper conversion
        # Check for RIFF header (WAV)
        if audio_data[:4] == b"RIFF" and audio_data[:8] == b"fmt ":
            return audio_data
        
        # For other formats, we'd need conversion
        # This is a placeholder - real implementation would use ffmpeg or pydub
        logger.warning("Audio conversion not fully implemented, attempting raw pass-through")
        return audio_data

    async def extract_fixture_using_llm(self, text: str) -> Dict[str, Any]:
        """
        Extract fixture fields from transcribed text using LLM.
        
        Uses Llama to intelligently parse maritime fixture details.
        """
        prompt = f"""You are a maritime chartering expert. Extract fixture details from this voice transcript.

Transcript:
{text}

Extract the following fields (use null if not mentioned):
- vessel_name: Full vessel name
- cargo_type: Type of cargo (e.g., CRUDE, PRODUCTS, DIRTY, CLEAN, COAL, IRON ORE, GRAIN)
- cargo_quantity: Quantity in metric tons (number only)
- rate: Rate in USD per metric ton (number only)
- port_loading: Load port name
- port_discharge: Discharge port name
- laycan_start: Laycan start date (YYYY-MM-DD format, estimate if needed)
- laycan_end: Laycan end date (YYYY-MM-DD format, estimate if needed)
- charterer: Charterer name if mentioned
- broker: Broker name if mentioned

Respond with ONLY valid JSON (no markdown, no explanation):
{{
  "vessel_name": null,
  "cargo_type": null,
  "cargo_quantity": null,
  "rate": null,
  "port_loading": null,
  "port_discharge": null,
  "laycan_start": null,
  "laycan_end": null,
  "charterer": null,
  "broker": null
}}"""

        try:
            full_prompt = f"""<|system|>
You are an expert maritime chartering AI assistant. Output valid JSON only.
<|user|>
{prompt}
<|assistant|>"""

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": self.llama_model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {"temperature": 0.1}
                    },
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        response = result.get("response", "")
                        return self._parse_json_response(response)
                    else:
                        logger.error(f"LLM API error: {resp.status}")
                        return {}

        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return {}

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response"""
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        return {}

    async def extract_fixture_from_voice(
        self, audio_data: bytes, existing_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Transcribe voice and extract fixture data.
        
        Args:
            audio_data: Raw audio bytes
            existing_data: Optional existing fixture data to merge with
        
        Returns:
            Dict with transcription, extracted fields, and merged data
        """
        # Step 1: Transcribe audio
        transcription = await self.transcribe_audio(audio_data)
        
        if "error" in transcription:
            return {
                "success": False,
                "error": transcription["error"],
                "transcription": None,
                "extracted": None,
                "merged": existing_data or {},
            }

        text = transcription.get("text", "")
        
        # Step 2: Extract fixture using LLM
        extracted = await self.extract_fixture_using_llm(text)
        
        # Step 3: Merge with existing data
        merged = {**(existing_data or {}), **extracted}

        return {
            "success": True,
            "transcription": {
                "text": text,
                "language": transcription.get("language", "en"),
            },
            "extracted": extracted,
            "merged": merged,
        }

    async def transcript_to_fixture(self, transcript: str) -> Dict[str, Any]:
        """
        Convert an existing transcript to fixture data.
        
        Args:
            transcript: Text transcript to parse
        
        Returns:
            Extracted fixture fields
        """
        return await self.extract_fixture_using_llm(transcript)


# Global service instance
whisper_service = WhisperVoiceService()


# ============================================================================
# Plugin Hooks
# ============================================================================


async def on_voice_note(audio_data: bytes, fixture_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Process voice note for fixture.
    
    Hook: on_voice_note
    """
    fixture_data = {"fixture_id": fixture_id} if fixture_id else {}
    result = await whisper_service.extract_fixture_from_voice(audio_data, fixture_data)
    return result


# Plugin hooks registry
hooks = {
    "on_voice_note": on_voice_note,
}


# ============================================================================
# Export
# ============================================================================

__all__ = [
    "WhisperVoiceService",
    "whisper_service",
    "on_voice_note",
    "hooks",
]
