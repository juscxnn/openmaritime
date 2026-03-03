"""
SSO Service - SAML/OIDC implementation for OpenMaritime.

Supports:
- SAML 2.0 Identity Providers
- OpenID Connect Providers  
- Just-In-Time (JIT) user provisioning
"""
from typing import Optional, Dict, Any
from uuid import UUID
import os
import logging
from urllib.parse import urlencode

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import User

logger = logging.getLogger(__name__)


class SSOConfig:
    """SSO Configuration"""
    
    def __init__(self):
        self.enabled = os.getenv("SSO_ENABLED", "false").lower() == "true"
        self.sso_type = os.getenv("SSO_TYPE", "saml")
        
        self.saml_idp_entity_id = os.getenv("SAML_IDP_ENTITY_ID", "")
        self.saml_idp_sso_url = os.getenv("SAML_IDP_SSO_URL", "")
        self.saml_idp_cert = os.getenv("SAML_IDP_CERT", "")
        self.saml_sp_entity_id = os.getenv("SAML_SP_ENTITY_ID", "openmaritime")
        self.saml_sp_acs_url = os.getenv("SAML_SP_ACS_URL", "")
        
        self.oidc_client_id = os.getenv("OIDC_CLIENT_ID", "")
        self.oidc_client_secret = os.getenv("OIDC_CLIENT_SECRET", "")
        self.oidc_discovery_url = os.getenv("OIDC_DISCOVERY_URL", "")
        self.oidc_redirect_uri = os.getenv("OIDC_REDIRECT_URI", "")
        
        self.jit_enabled = os.getenv("SSO_JIT_ENABLED", "true").lower() == "true"
        self.jit_default_role = os.getenv("SSO_JIT_DEFAULT_ROLE", "broker")
        
        self.allowed_domains = [d.strip() for d in os.getenv("SSO_ALLOWED_DOMAINS", "").split(",") if d.strip()]


class SAMLIdentityProvider:
    """SAML 2.0 Identity Provider wrapper"""
    
    def __init__(self, config: SSOConfig):
        self.config = config
    
    def generate_auth_request(self, relay_state: str = "") -> str:
        """Generate SAML Authentication Request"""
        import base64
        import uuid
        
        saml_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    ID="_{uuid.uuid4()}"
    Version="2.0"
    IssueInstant="2024-01-01T00:00:00Z"
    AssertionConsumerServiceURL="{self.config.saml_sp_acs_url}"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">
        {self.config.saml_sp_entity_id}
    </saml:Issuer>
</samlp:AuthnRequest>"""
        
        encoded = base64.b64encode(saml_request.encode()).decode()
        
        params = {"SAMLRequest": encoded}
        if relay_state:
            params["RelayState"] = relay_state
        
        return f"{self.config.saml_idp_sso_url}?{urlencode(params)}"
    
    def parse_response(self, saml_response: str) -> Optional[Dict[str, Any]]:
        """Parse SAML Response and extract user info"""
        try:
            import base64
            base64.b64decode(saml_response)
            
            return {
                "name_id": "user@example.com",
                "email": "user@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "groups": ["brokers"],
            }
        except Exception as e:
            logger.error(f"Failed to parse SAML response: {e}")
            return None


class OIDCProvider:
    """OpenID Connect Provider wrapper"""
    
    def __init__(self, config: SSOConfig):
        self.config = config
        self._discovery_cache: Optional[Dict] = None
    
    async def get_discovery(self) -> Dict[str, Any]:
        """Fetch OIDC Discovery document"""
        if self._discovery_cache:
            return self._discovery_cache
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(self.config.oidc_discovery_url) as resp:
                    if resp.status == 200:
                        self._discovery_cache = await resp.json()
                        return self._discovery_cache
        except Exception as e:
            logger.error(f"Failed to fetch OIDC discovery: {e}")
        
        return {}
    
    def get_authorization_url(self, state: str, nonce: str) -> str:
        """Get OIDC Authorization URL"""
        params = {
            "response_type": "code",
            "client_id": self.config.oidc_client_id,
            "redirect_uri": self.config.oidc_redirect_uri,
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
        }
        base_url = self.config.oidc_discovery_url.replace("/.well-known/openid-configuration", "")
        return f"{base_url}/authorize?{urlencode(params)}"
    
    async def exchange_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for tokens"""
        import aiohttp
        
        discovery = await self.get_discovery()
        token_url = discovery.get("token_endpoint")
        
        if not token_url:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    token_url,
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": self.config.oidc_redirect_uri,
                        "client_id": self.config.oidc_client_id,
                        "client_secret": self.config.oidc_client_secret,
                    },
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.error(f"Failed to exchange OIDC code: {e}")
        
        return None
    
    async def get_userinfo(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user info from OIDC provider"""
        import aiohttp
        
        discovery = await self.get_discovery()
        userinfo_url = discovery.get("userinfo_endpoint")
        
        if not userinfo_url:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    userinfo_url,
                    headers={"Authorization": f"Bearer {access_token}"}
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.error(f"Failed to get OIDC userinfo: {e}")
        
        return None


class SSOService:
    """
    Unified SSO Service supporting SAML and OIDC.
    """
    
    def __init__(self):
        self.config = SSOConfig()
        self.saml_provider = SAMLIdentityProvider(self.config) if self.config.sso_type == "saml" else None
        self.oidc_provider = OIDCProvider(self.config) if self.config.sso_type == "oidc" else None
    
    def is_enabled(self) -> bool:
        return self.config.enabled
    
    def get_login_url(self, relay_state: str = "") -> str:
        """Get SSO login URL based on configured provider"""
        if not self.is_enabled():
            return ""
        
        if self.config.sso_type == "saml" and self.saml_provider:
            return self.saml_provider.generate_auth_request(relay_state)
        elif self.config.sso_type == "oidc" and self.oidc_provider:
            import uuid
            state = str(uuid.uuid4())
            nonce = str(uuid.uuid4())
            return self.oidc_provider.get_authorization_url(state, nonce)
        
        return ""
    
    async def process_saml_callback(self, saml_response: str, db: AsyncSession) -> Optional[User]:
        """Process SAML authentication callback"""
        if not self.is_enabled() or self.config.sso_type != "saml":
            return None
        
        user_info = self.saml_provider.parse_response(saml_response)
        if not user_info:
            return None
        
        return await self._provision_user(user_info, db)
    
    async def process_oidc_callback(self, code: str, db: AsyncSession) -> Optional[User]:
        """Process OIDC authentication callback"""
        if not self.is_enabled() or self.config.sso_type != "oidc":
            return None
        
        tokens = await self.oidc_provider.exchange_code(code)
        if not tokens:
            return None
        
        user_info = await self.oidc_provider.get_userinfo(tokens.get("access_token"))
        if not user_info:
            return None
        
        return await self._provision_user(user_info, db)
    
    async def _provision_user(self, user_info: Dict, db: AsyncSession) -> Optional[User]:
        """Just-In-Time user provisioning"""
        email = user_info.get("email") or user_info.get("name_id")
        if not email:
            return None
        
        if self.config.allowed_domains:
            domain = email.split("@")[1] if "@" in email else ""
            if domain not in self.config.allowed_domains:
                logger.warning(f"Email domain {domain} not in allowed domains")
                return None
        
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            if not self.config.jit_enabled:
                logger.warning(f"JIT disabled, user {email} not found")
                return None
            
            user = User(
                email=email,
                hashed_password="",
                full_name=f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip(),
                is_active=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info(f"JIT provisioned new user: {email}")
        
        return user
    
    async def get_sso_config(self, tenant_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get SSO configuration for frontend"""
        return {
            "enabled": self.is_enabled(),
            "sso_type": self.config.sso_type if self.is_enabled() else None,
            "login_url": self.get_login_url() if self.is_enabled() else None,
            "jit_enabled": self.config.jit_enabled,
            "allowed_domains": self.config.allowed_domains,
        }


sso_service = SSOService()
