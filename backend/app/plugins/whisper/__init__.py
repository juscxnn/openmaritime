from typing import Dict, Any, Optional
import os
import base64
import aiohttp
import json


class WhisperVoiceService:
    """Local Whisper for voice-to-fixture transcription"""
    
    def __init__(self):
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("WHISPER_MODEL", "whisper")
    
    async def transcribe_audio(self, audio_data: bytes) -> Dict[str, Any]:
        """Transcribe audio using local Whisper"""
        try:
            base64_audio = base64.b64encode(audio_data).decode("utf-8")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_base_url}/api/transcribe",
                    json={
                        "model": self.model,
                        "file": base64_audio,
                    },
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return {
                            "text": result.get("text", ""),
                            "language": result.get("language", "en"),
                        }
        except Exception as e:
            return {"error": str(e)}
    
    async def extract_fixture_from_voice(
        self, audio_data: bytes, fixture_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transcribe voice and extract fixture data"""
        
        transcription = await self.transcribe_audio(audio_data)
        
        if "error" in transcription:
            return transcription
        
        text = transcription.get("text", "")
        
        extracted = await self._extract_from_text(text)
        
        return {
            "transcription": transcription,
            "extracted": extracted,
            "merged": {**fixture_data, **extracted},
        }
    
    async def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """Extract fixture fields from transcribed text"""
        
        import re
        
        extracted = {}
        
        vessel_match = re.search(r"vessel[:\s]+([A-Za-z\s]+?)(?:\s|,|$)", text, re.IGNORECASE)
        if vessel_match:
            extracted["vessel_name"] = vessel_match.group(1).strip()
        
        cargo_match = re.search(r"(\d+(?:,\d+)?)\s*(?:k\s*)?(?:tons?|mt)", text, re.IGNORECASE)
        if cargo_match:
            qty = cargo_match.group(1).replace(",", "")
            extracted["cargo_quantity"] = float(qty)
        
        rate_match = re.search(r"\$?\s*(\d+(?:\.\d+)?)\s*(?:per|/)\s*(?:ton|mt)", text, re.IGNORECASE)
        if rate_match:
            extracted["rate"] = float(rate_match.group(1))
        
        for cargo in ["crude", "oil", "diesel", "jet", "fuel", "coal", "iron", "grain", "soy"]:
            if cargo in text.lower():
                extracted["cargo_type"] = cargo.capitalize()
                break
        
        return extracted


whisper_service = WhisperVoiceService()


async def on_voice_note(audio_data: bytes, fixture_id: str = None) -> Dict[str, Any]:
    """Process voice note for fixture"""
    fixture_data = {"fixture_id": fixture_id} if fixture_id else {}
    result = await whisper_service.extract_fixture_from_voice(audio_data, fixture_data)
    return result


hooks = {
    "on_voice_note": on_voice_note,
}
