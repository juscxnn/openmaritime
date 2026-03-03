from typing import List, Dict, Any, Optional
import os
import re
from datetime import datetime
from email import message_from_bytes
from email.header import decode_header
import aioimaplib
import aiohttp
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import base64

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Fixture, EmailSync, User


SCOPES = ["https://mail.google.com/"]


class EmailSyncService:
    def __init__(self):
        self.credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
        self.token_path = os.getenv("GOOGLE_TOKEN_PATH", "token.json")
    
    async def get_gmail_credentials(self, user_id: str) -> Optional[Credentials]:
        """Get Gmail API credentials for user"""
        creds = None
        
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                return None
        
        return creds
    
    async def sync_gmail(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Sync emails from Gmail and extract fixtures"""
        creds = await self.get_gmail_credentials(user_id)
        if not creds:
            return {"error": "No valid credentials", "fixtures_extracted": 0}
        
        result = await db.execute(select(EmailSync).where(EmailSync.user_id == user_id))
        email_sync = result.scalar_one_or_none()
        
        if not email_sync:
            return {"error": "No email sync configured", "fixtures_extracted": 0}
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {creds.token}"}
                
                query = "subject:(fixture OR charter OR cargo OR vessel)"
                if email_sync.last_sync_at:
                    query += f" after:{int(email_sync.last_sync_at.timestamp())}"
                
                async with session.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                    params={"q": query, "maxResults": 50},
                    headers=headers,
                ) as resp:
                    if resp.status != 200:
                        return {"error": "Failed to fetch emails", "fixtures_extracted": 0}
                    
                    data = await resp.json()
                    messages = data.get("messages", [])
            
            fixtures_created = 0
            for msg in messages:
                fixture_data = await self._extract_fixture_from_gmail(session, headers, msg["id"])
                if fixture_data:
                    await self._create_fixture(user_id, fixture_data, db)
                    fixtures_created += 1
            
            if email_sync.last_sync_at:
                email_sync.last_sync_at = datetime.utcnow()
            else:
                email_sync.last_sync_at = datetime.utcnow()
            
            await db.commit()
            
            return {
                "emails_processed": len(messages),
                "fixtures_extracted": fixtures_created,
                "last_sync": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            return {"error": str(e), "fixtures_extracted": 0}
    
    async def _extract_fixture_from_gmail(
        self, session: aiohttp.ClientSession, headers: Dict, msg_id: str
    ) -> Optional[Dict[str, Any]]:
        """Extract fixture data from email body"""
        try:
            async with session.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    return None
                
                msg_data = await resp.json()
                payload = msg_data.get("payload", {})
                headers_dict = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
                
                body = ""
                if "parts" in payload:
                    for part in payload["parts"]:
                        if part.get("mimeType") == "text/plain":
                            body = part.get("body", {}).get("data", "")
                            break
                        elif "parts" in part:
                            for subpart in part["parts"]:
                                if subpart.get("mimeType") == "text/plain":
                                    body = subpart.get("body", {}).get("data", "")
                                    break
                
                if not body and "body" in payload:
                    body = payload["body"].get("data", "")
                
                if body:
                    body = base64.urlsafe_b64decode(body).decode("utf-8")
                
                subject = headers_dict.get("subject", "")
                from_addr = headers_dict.get("from", "")
                
                return self._parse_fixture_from_text(subject, body, from_addr, msg_id)
                
        except Exception as e:
            print(f"Error extracting email {msg_id}: {e}")
            return None
    
    def _parse_fixture_from_text(
        self, subject: str, body: str, from_addr: str, email_id: str
    ) -> Optional[Dict[str, Any]]:
        """Parse fixture data from email text using regex patterns"""
        text = f"{subject}\n{body}"
        
        vessel_name = self._extract_pattern(text, r"(?:MV|M/V|vessel|name)[:\s]+([A-Za-z\s]+?)(?:\/|,|\n|IMO)")
        if not vessel_name:
            vessel_match = re.search(r"^([A-Z][A-Za-z\s]{4,20})", text, re.MULTILINE)
            if vessel_match:
                vessel_name = vessel_match.group(1).strip()
        
        imo_match = re.search(r"IMO[:\s#]*(\d{7})", text, re.IGNORECASE)
        imo_number = imo_match.group(1) if imo_match else None
        
        cargo_match = re.search(r"(\d+(?:,\d+)?)\s*(?:k\s*)?(?:mt|tons?|tonnes?)", text, re.IGNORECASE)
        cargo_qty = float(cargo_match.group(1).replace(",", "")) if cargo_match else 0
        
        cargo_type = self._extract_pattern(text, r"(?:cargo|commodity)[:\s]+([A-Za-z\s]+?)(?:\/|,|\n)")
        if not cargo_type:
            for cargo in ["crude", "oil", "diesel", "gasoline", "jet", "fuel", "coal", "iron", "grain", "soy", "wheat", "phosphate"]:
                if cargo in text.lower():
                    cargo_type = cargo.capitalize()
                    break
        
        laycan_match = re.search(r"laycan[:\s]+(\d{1,2})\s*[-–]\s*(\d{1,2})\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", text, re.IGNORECASE)
        laycan_start = None
        laycan_end = None
        if laycan_match:
            try:
                month_map = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
                month_name = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", text[laycan_match.end():], re.IGNORECASE)
                if month_name:
                    month = month_map.get(month_name.group(1).lower(), 1)
                    year = datetime.now().year
                    laycan_start = datetime(year, month, int(laycan_match.group(1)))
                    laycan_end = datetime(year, month, int(laycan_match.group(2)))
            except:
                pass
        
        rate_match = re.search(r"\$?\s*(\d+(?:\.\d+)?)\s*(?:per|/)\s*(?:mt|ton)", text, re.IGNORECASE)
        rate = float(rate_match.group(1)) if rate_match else None
        
        port_loading = self._extract_pattern(text, r"(?:load|loading|origin)[:\s]+([A-Za-z\s,\-]+?)(?:\s+to|\s*[,/]|\n)")
        port_discharge = self._extract_pattern(text, r"(?:discharge|discharging|destination)[:\s]+([A-Za-z\s,\-]+?)(?:\n|$)")
        
        if not cargo_qty or not vessel_name:
            return None
        
        return {
            "vessel_name": vessel_name.strip() if vessel_name else "Unknown",
            "imo_number": imo_number,
            "cargo_type": cargo_type or "General Cargo",
            "cargo_quantity": cargo_qty,
            "cargo_unit": "MT",
            "laycan_start": laycan_start.isoformat() if laycan_start else None,
            "laycan_end": laycan_end.isoformat() if laycan_end else None,
            "rate": rate,
            "rate_currency": "USD",
            "rate_unit": "/mt",
            "port_loading": port_loading.strip() if port_loading else "TBD",
            "port_discharge": port_discharge.strip() if port_discharge else "TBD",
            "charterer": None,
            "broker": from_addr,
            "source_email_id": email_id,
            "source_subject": subject,
        }
    
    def _extract_pattern(self, text: str, pattern: str) -> Optional[str]:
        """Extract text matching pattern"""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else None
    
    async def _create_fixture(self, user_id: str, data: Dict[str, Any], db: AsyncSession):
        """Create fixture from extracted data"""
        from datetime import datetime
        
        fixture = Fixture(
            user_id=user_id,
            vessel_name=data.get("vessel_name", "Unknown"),
            imo_number=data.get("imo_number"),
            cargo_type=data.get("cargo_type", "General Cargo"),
            cargo_quantity=data.get("cargo_quantity", 0),
            cargo_unit=data.get("cargo_unit", "MT"),
            laycan_start=datetime.fromisoformat(data["laycan_start"]) if data.get("laycan_start") else datetime.utcnow(),
            laycan_end=datetime.fromisoformat(data["laycan_end"]) if data.get("laycan_end") else datetime.utcnow(),
            rate=data.get("rate"),
            rate_currency=data.get("rate_currency", "USD"),
            rate_unit=data.get("rate_unit", "/mt"),
            port_loading=data.get("port_loading", "TBD"),
            port_discharge=data.get("port_discharge", "TBD"),
            charterer=data.get("charterer"),
            broker=data.get("broker"),
            source_email_id=data.get("source_email_id"),
            source_subject=data.get("source_subject"),
            status="new",
        )
        
        db.add(fixture)
    
    async def setup_gmail_connection(self, user_id: str, auth_code: str, db: AsyncSession) -> Dict[str, Any]:
        """Setup Gmail connection with auth code"""
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_path, SCOPES
            )
            creds = flow.run_local_server(port=0)
            
            with open(self.token_path, "w") as token:
                token.write(creds.to_json())
            
            result = await db.execute(select(EmailSync).where(EmailSync.user_id == user_id))
            email_sync = result.scalar_one_or_none()
            
            if email_sync:
                email_sync.access_token = creds.token
                email_sync.is_active = True
            else:
                email_sync = EmailSync(
                    user_id=user_id,
                    provider="gmail",
                    access_token=creds.token,
                    is_active=True,
                )
                db.add(email_sync)
            
            await db.commit()
            
            return {"status": "connected", "provider": "gmail"}
        except Exception as e:
            return {"error": str(e)}


email_sync_service = EmailSyncService()
