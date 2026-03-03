from typing import Dict, Any, Optional
import os
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Handles notifications for auto-FIX and alerts"""
    
    def __init__(self):
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        self.slack_channel = os.getenv("SLACK_CHANNEL", "#chartering")
    
    async def send_auto_fix_alert(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Send auto-FIX alert to Slack"""
        
        if not self.slack_webhook:
            logger.warning("No Slack webhook configured")
            return {"error": "No Slack webhook"}
        
        fixture = state.get("fixture_data", {})
        ranking = state.get("ranking_data", {})
        decision = state.get("decision_data", {})
        
        message = {
            "channel": self.slack_channel,
            "username": "OpenMaritime Wake AI",
            "icon_emoji": ":anchor:",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚨 Auto-FIX Recommended",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Vessel:*\n{fixture.get('vessel_name', 'Unknown')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*IMO:*\n{fixture.get('imo_number', 'N/A')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Cargo:*\n{fixture.get('cargo_quantity', 0)} {fixture.get('cargo_type', '')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Rate:*\n{fixture.get('rate', 'TBD')} {fixture.get('rate_currency', 'USD')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Laycan:*\n{fixture.get('laycan_start', 'TBD')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Route:*\n{fixture.get('port_loading', '')} → {fixture.get('port_discharge', '')}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Wake Score:*\n{ranking.get('score', 0)}/100"
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Recommendation:*\n" + decision.get("recommendation", "N/A")
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Rationale:*\n{decision.get('rationale', ranking.get('reason', 'No explanation'))}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View in OpenMaritime"
                            },
                            "url": os.getenv("APP_URL", "http://localhost:3000"),
                            "style": "primary"
                        }
                    ]
                }
            ]
        }
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(self.slack_webhook, json=message) as resp:
                    if resp.status == 200:
                        return {"status": "sent", "channel": self.slack_channel}
                    else:
                        return {"error": f"Slack error: {resp.status}"}
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return {"error": str(e)}
    
    async def send_fixture_update(self, fixture_id: str, update_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send fixture update notification"""
        
        message = {
            "channel": self.slack_channel,
            "username": "OpenMaritime",
            "icon_emoji": ":ship:",
            "text": f"Fixture update: {update_type} - {data.get('vessel_name', 'Unknown')}"
        }
        
        return await self._send_to_slack(message)
    
    async def send_market_alert(self, alert_type: str, message: str) -> Dict[str, Any]:
        """Send market alert"""
        
        emoji = {
            "rate_spike": ":chart_with_upwards_trend:",
            "weather": ":cloud_rain:",
            "news": ":newspaper:",
            "default": ":bell:"
        }.get(alert_type, ":bell:")
        
        message_payload = {
            "channel": self.slack_channel,
            "username": "OpenMaritime Market",
            "icon_emoji": emoji,
            "text": f"*{alert_type.upper()}:* {message}"
        }
        
        return await self._send_to_slack(message_payload)
    
    async def _send_to_slack(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send message to Slack"""
        
        if not self.slack_webhook:
            return {"error": "No Slack webhook configured"}
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(self.slack_webhook, json=message) as resp:
                    return {"status": "sent" if resp.status == 200 else "error"}
        except Exception as e:
            return {"error": str(e)}


notification_service = NotificationService()
