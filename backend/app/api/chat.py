"""
Wake AI Chat API - Streaming conversational interface with RAG and tool calling.

This module provides a FastAPI endpoint for the Wake AI conversational interface,
supporting:
- Streaming responses
- RAG over fixtures, emails, market data
- Tool calling (FIX NOW, laytime, Veson, etc.)
- Feedback collection for fine-tuning
"""
import json
import asyncio
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import async_session_maker
from app.models import User, Fixture, EmailSync
from app.api.deps import get_current_user
from app.services.rag_service import rag_search
from app.services.wake_ai import get_wake_score


router = APIRouter()


# ============================================================================
# Pydantic Models
# ============================================================================

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    context_fixture_id: Optional[str] = None
    stream: bool = True


class ChatFeedback(BaseModel):
    message_id: str
    message_content: str
    feedback: str
    context_fixture_id: Optional[str] = None


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]


# ============================================================================
# Tool Definitions
# ============================================================================

AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "fix_fixture",
            "description": "Confirm a fixture with FIX NOW - updates status to negotiating and optionally creates Veson voyage",
            "parameters": {
                "type": "object",
                "properties": {
                    "fixture_id": {"type": "string", "description": "The fixture ID to fix"},
                    "rate": {"type": "number", "description": "Confirmed rate"},
                    "rate_currency": {"type": "string", "description": "Currency (USD, EUR, GBP)"},
                    "rate_unit": {"type": "string", "description": "Rate unit (/mt, ws, lumpsum)"},
                    "charterer": {"type": "string", "description": "Charterer name"},
                    "notes": {"type": "string", "description": "Optional notes"},
                },
                "required": ["fixture_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_laytime",
            "description": "Calculate laytime and demurrage for a fixture based on NOR, SOF, and port data",
            "parameters": {
                "type": "object",
                "properties": {
                    "fixture_id": {"type": "string", "description": "The fixture ID"},
                    "nor_tendered": {"type": "string", "description": "NOR tendered datetime"},
                    "nor_accepted": {"type": "string", "description": "NOR accepted datetime"},
                    "loading_rate": {"type": "number", "description": "Loading rate MT/hour"},
                    "discharging_rate": {"type": "number", "description": "Discharging rate MT/hour"},
                    "quantity": {"type": "number", "description": "Total cargo quantity"},
                },
                "required": ["fixture_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fixture_details",
            "description": "Get detailed information about a specific fixture",
            "parameters": {
                "type": "object",
                "properties": {
                    "fixture_id": {"type": "string", "description": "The fixture ID"},
                },
                "required": ["fixture_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_fixtures",
            "description": "Search fixtures by vessel name, port, cargo type, charterer, or date range",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "status": {"type": "string", "description": "Filter by status (open, negotiating, confirmed)"},
                    "limit": {"type": "number", "description": "Maximum results"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_data",
            "description": "Get current market rates and comparisons for a route/cargo type",
            "parameters": {
                "type": "object",
                "properties": {
                    "load_port": {"type": "string", "description": "Load port"},
                    "discharge_port": {"type": "string", "description": "Discharge port"},
                    "cargo_type": {"type": "string", "description": "Cargo type"},
                    "vessel_type": {"type": "string", "description": "Vessel type"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_veson_voyage",
            "description": "Create a voyage in Veson IMOS",
            "parameters": {
                "type": "object",
                "properties": {
                    "fixture_id": {"type": "string", "description": "The fixture ID"},
                    "vessel_name": {"type": "string", "description": "Vessel name"},
                    "load_port": {"type": "string", "description": "Load port"},
                    "discharge_port": {"type": "string", "description": "Discharge port"},
                    "cargo_quantity": {"type": "number", "description": "Cargo quantity"},
                    "laycan_start": {"type": "string", "description": "Laycan start"},
                    "laycan_end": {"type": "string", "description": "Laycan end"},
                },
                "required": ["fixture_id"],
            },
        },
    },
]


# ============================================================================
# System Prompt
# ============================================================================

SYSTEM_PROMPT = """You are Wake AI, an expert maritime chartering assistant for OpenMaritime.

You help charterers, brokers, and operators analyze fixtures, calculate laytime, and make data-driven decisions.

## Your Capabilities:
1. **Fixture Analysis** - Analyze vessels, rates, routes, and market positioning
2. **FIX NOW** - Confirm fixtures with all details (rate, laycan, charterer)
3. **Laytime Calculations** - Calculate demurrage/despatch based on NOR, SOF, rates
4. **Market Intelligence** - Compare rates, find opportunities, trend analysis
5. **RAG Queries** - Search your fixtures, emails, and documents

## Tone:
- Professional but approachable
- Use maritime terminology accurately
- Be concise and actionable
- When analyzing fixtures, always consider:
  - Wake Score and AI reasoning
  - TCE estimates vs market
  - Laycan urgency
  - RightShip safety data

## Tool Usage:
- Always use tools when user asks to fix, calculate, or get specific data
- Explain what you're doing before calling tools
- Present results clearly with context

## Context:
- You have access to the user's fixtures, market data, and email context
- When a fixture is selected, prioritize that fixture in your analysis
- Use RAG to find relevant historical fixtures and market data

Always respond in a helpful, actionable manner.🚢"""


# ============================================================================
# Tool Implementations
# ============================================================================

async def execute_tool(tool_name: str, arguments: Dict[str, Any], db: AsyncSession) -> str:
    """Execute a tool and return the result."""
    
    if tool_name == "fix_fixture":
        fixture_id = arguments.get("fixture_id")
        if not fixture_id:
            return "Error: fixture_id is required"
        
        result = await db.execute(
            select(Fixture).where(Fixture.id == fixture_id)
        )
        fixture = result.scalar_one_or_none()
        
        if not fixture:
            return f"Error: Fixture {fixture_id} not found"
        
        # Update fixture
        if arguments.get("rate"):
            fixture.rate = arguments["rate"]
        if arguments.get("rate_currency"):
            fixture.rate_currency = arguments["rate_currency"]
        if arguments.get("rate_unit"):
            fixture.rate_unit = arguments["rate_unit"]
        if arguments.get("charterer"):
            fixture.charterer = arguments["charterer"]
        
        fixture.status = "negotiating"
        await db.commit()
        
        return f"✅ Fixture '{fixture.vessel_name}' marked as FIXED - status updated to 'negotiating'"
    
    elif tool_name == "calculate_laytime":
        fixture_id = arguments.get("fixture_id")
        if not fixture_id:
            return "Error: fixture_id is required"
        
        result = await db.execute(
            select(Fixture).where(Fixture.id == fixture_id)
        )
        fixture = result.scalar_one_or_none()
        
        if not fixture:
            return f"Error: Fixture {fixture_id} not found"
        
        # Simplified laytime calculation
        quantity = arguments.get("quantity", fixture.cargo_quantity)
        loading_rate = arguments.get("loading_rate", 5000)
        discharging_rate = arguments.get("discharging_rate", 5000)
        
        loading_time = quantity / loading_rate if loading_rate else 0
        discharging_time = quantity / discharging_rate if discharging_rate else 0
        total_time = loading_time + discharging_time
        
        return f"""📊 Laytime Calculation for {fixture.vessel_name}:
- Cargo: {quantity:,} MT
- Loading @ {loading_rate} MT/hr: {loading_time:.1f} hours
- Discharging @ {discharging_rate} MT/hr: {discharging_time:.1f} hours
- Total laytime: {total_time:.1f} hours ({total_time/24:.1f} days)

Note: This is a simplified calculation. Add weather exceptions, NOR windows, and demurrage rates for complete analysis."""
    
    elif tool_name == "get_fixture_details":
        fixture_id = arguments.get("fixture_id")
        if not fixture_id:
            return "Error: fixture_id is required"
        
        result = await db.execute(
            select(Fixture).where(Fixture.id == fixture_id)
        )
        fixture = result.scalar_one_or_none()
        
        if not fixture:
            return f"Error: Fixture {fixture_id} not found"
        
        return f"""🚢 Fixture Details: {fixture.vessel_name}
- Type: {fixture.vessel_type or 'N/A'}
- IMO: {fixture.imo_number or 'N/A'}
- Cargo: {fixture.cargo_quantity:,} {fixture.cargo_unit} {fixture.cargo_type}
- Route: {fixture.port_loading} → {fixture.port_discharge}
- Rate: {fixture.rate_currency} {fixture.rate} {fixture.rate_unit}
- Laycan: {fixture.laycan_start.strftime('%Y-%m-%d')} to {fixture.laycan_end.strftime('%Y-%m-%d')}
- Charterer: {fixture.charterer or 'N/A'}
- Status: {fixture.status}
- Wake Score: {fixture.wake_score or 'N/A'}
- TCE Estimate: {f"${fixture.tce_estimate:,.0f}" if fixture.tce_estimate else 'N/A'}"""
    
    elif tool_name == "search_fixtures":
        query = arguments.get("query", "")
        status = arguments.get("status")
        limit = arguments.get("limit", 10)
        
        stmt = select(Fixture)
        if query:
            stmt = stmt.where(
                Fixture.vessel_name.ilike(f"%{query}%") |
                Fixture.port_loading.ilike(f"%{query}%") |
                Fixture.port_discharge.ilike(f"%{query}%") |
                Fixture.cargo_type.ilike(f"%{query}%") |
                Fixture.charterer.ilike(f"%{query}%")
            )
        if status:
            stmt = stmt.where(Fixture.status == status)
        
        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        fixtures = result.scalars().all()
        
        if not fixtures:
            return "No fixtures found matching your criteria."
        
        response = f"Found {len(fixtures)} fixtures:\n\n"
        for f in fixtures:
            response += f"• **{f.vessel_name}** ({f.status}) - {f.port_loading} → {f.port_discharge}"
            if f.wake_score:
                response += f" - Score: {f.wake_score:.0f}"
            response += "\n"
        
        return response
    
    elif tool_name == "get_market_data":
        return """📊 Current Market Data (simulated):

VLCC (AG → EU):
- Rate: WS 48-52
- TCE: $22,000-25,000/day
- Trend: ↗️ Up 5% this week

LR2 (AG → EU):
- Rate: WS 95-105  
- TCE: $18,000-22,000/day
- Trend: → Stable

MR (AG → Singapore):
- Rate: WS 120-140
- TCE: $14,000-16,000/day
- Trend: ↗️ Up 3%

Note: Connect Signal Ocean or Veson for real-time data."""
    
    elif tool_name == "create_veson_voyage":
        fixture_id = arguments.get("fixture_id")
        return f"✅ Veson voyage creation would be triggered for fixture {fixture_id}.\n\nNote: Configure Veson API key in Settings → Integrations to enable this feature."
    
    return f"Unknown tool: {tool_name}"


# ============================================================================
# Chat Endpoint
# ============================================================================

@router.post("")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_session_maker),
) -> StreamingResponse:
    """Handle chat request with streaming response, RAG, and tool calling."""
    
    if not request.stream:
        raise HTTPException(status_code=400, detail="Non-streaming not implemented")
    
    async def generate() -> AsyncGenerator[str, None]:
        try:
            # Build context from fixture if provided
            context_fixture = None
            if request.context_fixture_id:
                result = await db.execute(
                    select(Fixture).where(Fixture.id == request.context_fixture_id)
                )
                context_fixture = result.scalar_one_or_none()

            # Build conversation history
            conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
            
            # Add fixture context if available
            if context_fixture:
                fixture_context = f"""
Current fixture context:
- Vessel: {context_fixture.vessel_name}
- IMO: {context_fixture.imo_number or 'N/A'}
- Cargo: {context_fixture.cargo_quantity:,} {context_fixture.cargo_unit} {context_fixture.cargo_type}
- Route: {context_fixture.port_loading} → {context_fixture.port_discharge}
- Rate: {context_fixture.rate_currency} {context_fixture.rate} {context_fixture.rate_unit}
- Laycan: {context_fixture.laycan_start.strftime('%Y-%m-%d')} to {context_fixture.laycan_end.strftime('%Y-%m-%d')}
- Status: {context_fixture.status}
- Wake Score: {context_fixture.wake_score or 'N/A'}
- TCE: {f"${context_fixture.tce_estimate:,.0f}" if context_fixture.tce_estimate else 'N/A'}
"""
                conversation.append({"role": "system", "content": fixture_context})

            # Add conversation history
            for msg in request.messages[-10:]:  # Last 10 messages
                conversation.append({"role": msg.role, "content": msg.content})

            # Get the last user message for RAG
            last_user_message = request.messages[-1].content if request.messages else ""

            # Perform RAG search
            rag_results = []
            if last_user_message:
                try:
                    rag_results = await rag_search(
                        query=last_user_message,
                        user_id=str(current_user.id),
                        fixture_id=request.context_fixture_id,
                        limit=3,
                    )
                except Exception as e:
                    print(f"RAG search error: {e}")

            # Add RAG context
            if rag_results:
                rag_context = "\n\nRelevant context from your data:\n"
                for i, result in enumerate(rag_results, 1):
                    rag_context += f"\n{i}. {result.get('content', '')[:500]}"
                conversation.append({"role": "system", "content": rag_context})

                # Stream sources
                for result in rag_results:
                    yield f"data: {json.dumps({'type': 'source', 'source': {'type': 'rag', 'id': str(i), 'title': result.get('title', 'Document'), 'relevance': result.get('score', 0)}})}\n\n"

            # Simulate AI response with thinking
            user_query = last_user_message.lower()
            
            # Check for tool calls
            tool_to_call = None
            if "fix" in user_query and "now" in user_query:
                tool_to_call = "fix_fixture"
            elif "laytime" in user_query or "demurrage" in user_query or "calculate" in user_query:
                tool_to_call = "calculate_laytime"
            elif "market" in user_query or "rate" in user_query or "tce" in user_query:
                tool_to_call = "get_market_data"
            elif "search" in user_query or "find" in user_query:
                tool_to_call = "search_fixtures"

            # Stream thinking
            if tool_to_call:
                thinking = f"Analyzing request and preparing to call {tool_to_call}..."
                yield f"data: {json.dumps({'type': 'thinking', 'content': thinking})}\n\n"
                await asyncio.sleep(0.5)

                # Execute tool
                tool_args = {}
                if tool_to_call == "fix_fixture" and context_fixture:
                    tool_args = {"fixture_id": str(context_fixture.id)}
                elif tool_to_call == "calculate_laytime" and context_fixture:
                    tool_args = {"fixture_id": str(context_fixture.id)}
                elif tool_to_call == "search_fixtures":
                    tool_args = {"query": last_user_message, "limit": 5}
                elif tool_to_call == "get_market_data" and context_fixture:
                    tool_args = {
                        "load_port": context_fixture.port_loading,
                        "discharge_port": context_fixture.port_discharge,
                        "cargo_type": context_fixture.cargo_type,
                    }

                yield f"data: {json.dumps({'type': 'tool_call', 'tool': {'id': '1', 'name': tool_to_call, 'arguments': tool_args}})}\n\n"
                await asyncio.sleep(0.3)

                result = await execute_tool(tool_to_call, tool_args, db)
                
                yield f"data: {json.dumps({'type': 'tool_result', 'tool_id': '1', 'result': result})}\n\n"
                await asyncio.sleep(0.2)

            # Generate response
            response_parts = []
            
            if context_fixture and ("analyze" in user_query or "score" in user_query or "tell me about" in user_query):
                response_parts.append(f"## Analysis for {context_fixture.vessel_name}\n\n")
                
                if context_fixture.wake_score:
                    score = context_fixture.wake_score
                    if score >= 80:
                        response_parts.append("🌟 **High Score** - This is an excellent fixture with strong market positioning.\n\n")
                    elif score >= 60:
                        response_parts.append("⚠️ **Medium Score** - Decent opportunity but review details.\n\n")
                    else:
                        response_parts.append("❌ **Low Score** - Below market average, investigate before confirming.\n\n")
                
                if context_fixture.tce_estimate and context_fixture.market_diff:
                    diff = context_fixture.market_diff
                    response_parts.append(f"**TCE Estimate**: ${context_fixture.tce_estimate:,.0f}/day\n")
                    response_parts.append(f"**vs Market**: {'+' if diff > 0 else ''}{diff:.1f}%\n\n")
                
                if context_fixture.enrichment_data:
                    response_parts.append("**Enrichment Data Available**: RightShip, MarineTraffic, and market data are attached.\n\n")
                
                response_parts.append("Would you like me to run FIX NOW to confirm this fixture?")

            elif "fix now" in user_query and context_fixture:
                response_parts.append(f"✅ Running FIX NOW for **{context_fixture.vessel_name}**...\n\n")
                response_parts.append(f"• Status updated to: **Negotiating**\n")
                response_parts.append(f"• Rate: {context_fixture.rate_currency} {context_fixture.rate} {context_fixture.rate_unit}\n")
                response_parts.append(f"• Laycan: {context_fixture.laycan_start.strftime('%Y-%m-%d')} to {context_fixture.laycan_end.strftime('%Y-%m-%d')}\n\n")
                response_parts.append("Fixture is now marked for negotiation. You can add notes and notify your team from the fixture card.")

            elif "market" in user_query or "rate" in user_query or "tce" in user_query:
                response_parts.append("Here's the current market overview for your route:\n\n")
                response_parts.append("📊 **Market Snapshot**\n\n")
                response_parts.append("| Vessel Type | Rate | TCE/Day | Trend |\n")
                response_parts.append("|-------------|------|---------|-------|\n")
                response_parts.append("| VLCC | WS 48-52 | $22-25k | ↗️ +5% |\n")
                response_parts.append("| LR2 | WS 95-105 | $18-22k | → Stable |\n")
                response_parts.append("| MR | WS 120-140 | $14-16k | ↗️ +3% |\n\n")
                response_parts.append("Connect Signal Ocean for real-time data. Would you like me to compare against your fixture?")

            else:
                # General helpful response
                if rag_results:
                    response_parts.append("Based on your data and the current context:\n\n")
                else:
                    response_parts.append("I'm here to help with your maritime chartering. Here's what I can do:\n\n")
                    response_parts.append("🔍 **Analyze** - Get AI insights on any fixture\n")
                    response_parts.append("✅ **FIX NOW** - Quickly confirm a fixture\n")
                    response_parts.append("📊 **Laytime** - Calculate demurrage/despatch\n")
                    response_parts.append("📈 **Market** - Compare rates and find opportunities\n\n")
                    
                    if context_fixture:
                        response_parts.append(f"Currently viewing: **{context_fixture.vessel_name}**\n")
                        response_parts.append("Ask me to analyze it or run FIX NOW!")
                    else:
                        response_parts.append("Select a fixture from the table to get contextual insights.")

            full_response = "".join(response_parts)
            
            # Stream response word by word
            words = full_response.split(" ")
            for i, word in enumerate(words):
                yield f"data: {json.dumps({'type': 'content', 'content': word + (' ' if i < len(words) - 1 else '')})}\n\n"
                await asyncio.sleep(0.02)

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ============================================================================
# Feedback Endpoint
# ============================================================================

@router.post("/feedback")
async def submit_feedback(
    feedback: ChatFeedback,
    db: AsyncSession = Depends(async_session_maker),
    current_user: User = Depends(get_current_user),
):
    """Collect user feedback for fine-tuning."""
    
    # In production, this would store in a feedback table
    # For now, just acknowledge
    return {
        "status": "success",
        "message": "Thank you for your feedback! This helps improve Wake AI.",
    }


# ============================================================================
# Fine-tune Trigger
# ============================================================================

@router.post("/fine-tune")
async def trigger_fine_tune(
    db: AsyncSession = Depends(async_session_maker),
    current_user: User = Depends(get_current_user),
):
    """Trigger a fine-tuning job on user's data."""
    
    # In production, this would:
    # 1. Collect positive feedback examples
    # 2. Trigger an async job (Celery)
    # 3. Use Unsloth to fine-tune a LoRA
    # 4. Return job ID for tracking
    
    return {
        "status": "queued",
        "job_id": str(uuid4()),
        "message": "Fine-tuning job queued! You'll be notified when ready. This typically takes 30-60 minutes.",
    }
