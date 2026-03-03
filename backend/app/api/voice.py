"""
Voice API - Voice-to-Fixture Transcription Endpoints

Endpoints:
- POST /voice/transcribe - Transcribe audio blob
- POST /voice/to-fixture - Convert transcript to fixture data (text input)
- POST /voice/process - Full pipeline: audio to fixture (file upload)
"""
import base64
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.plugins.whisper import whisper_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class TranscriptRequest(BaseModel):
    """Request to convert transcript to fixture"""
    transcript: str


class AudioRequest(BaseModel):
    """Request with base64-encoded audio"""
    audio: str


class TranscriptionResponse(BaseModel):
    """Response from transcription"""
    success: bool
    text: Optional[str] = None
    language: Optional[str] = None
    error: Optional[str] = None


class ToFixtureResponse(BaseModel):
    """Response from transcript-to-fixture conversion"""
    success: bool
    fixture: Optional[dict] = None
    error: Optional[str] = None


class VoiceToFixtureResponse(BaseModel):
    """Response from voice-to-fixture (combined)"""
    success: bool
    transcription: Optional[dict] = None
    fixture: Optional[dict] = None
    error: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file (webm, mp3, wav, ogg)"),
):
    """
    Transcribe audio file to text.
    
    Accepts audio in various formats (webm, mp3, wav, ogg) and returns
    the transcribed text using local Ollama Whisper.
    """
    try:
        # Read audio data
        audio_data = await audio.read()
        
        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        if len(audio_data) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=400, detail="Audio file too large (max 10MB)")

        # Transcribe
        result = await whisper_service.transcribe_audio(audio_data)
        
        if "error" in result:
            return TranscriptionResponse(
                success=False,
                error=result["error"]
            )
        
        return TranscriptionResponse(
            success=True,
            text=result.get("text"),
            language=result.get("language", "en"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error transcribing audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/to-fixture", response_model=ToFixtureResponse)
async def transcript_to_fixture(request: TranscriptRequest):
    """
    Convert transcript text to fixture fields.
    
    Takes a text transcript and extracts maritime fixture data
    including vessel, cargo, ports, dates, and rates.
    """
    try:
        if not request.transcript or not request.transcript.strip():
            raise HTTPException(status_code=400, detail="Empty transcript")

        # Extract fixture using LLM
        fixture = await whisper_service.transcript_to_fixture(request.transcript)
        
        if not fixture:
            return ToFixtureResponse(
                success=False,
                error="Failed to extract fixture data"
            )

        return ToFixtureResponse(
            success=True,
            fixture=fixture,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error converting transcript to fixture: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process", response_model=VoiceToFixtureResponse)
async def process_voice_to_fixture(
    audio: UploadFile = File(..., description="Audio file to transcribe and convert"),
):
    """
    Complete voice-to-fixture pipeline.
    
    Takes audio, transcribes it, and extracts fixture data in one call.
    This is the main endpoint for voice input.
    """
    try:
        # Read audio data
        audio_data = await audio.read()
        
        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        if len(audio_data) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=400, detail="Audio file too large (max 10MB)")

        # Process audio
        result = await whisper_service.extract_fixture_from_voice(audio_data)
        
        if not result.get("success"):
            return VoiceToFixtureResponse(
                success=False,
                error=result.get("error", "Transcription failed")
            )

        return VoiceToFixtureResponse(
            success=True,
            transcription=result.get("transcription"),
            fixture=result.get("merged"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in voice-to-fixture: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Health Check
# ============================================================================


@router.get("/health")
async def voice_health():
    """Check voice service health"""
    return {
        "status": "healthy",
        "service": "whisper",
        "model": whisper_service.whisper_model,
    }
