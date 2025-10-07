from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from datetime import datetime
import os
from .models import ChatMessage, ChatResponse, TenantContext, UsageMetric, SubscriptionTier
from .bedrock_service import BedrockAgentService
from .agentic_service import AgenticService
from .dynamodb_store import DynamoDBStore
from .auth import get_current_user
from .runtime_context import RuntimeContextManager
from .subscription_service import SubscriptionService
from .mcp_service import MCPClient
from .mcp_agent_integration import MCPAgentCoreIntegration

app = FastAPI(title="Multi-Tenant Bedrock Chat", version="1.0.0")

# Initialize services
store = DynamoDBStore()
subscription_service = SubscriptionService(store)
mcp_client = MCPClient()

# Bedrock Agent configuration
AGENT_ID = os.getenv("BEDROCK_AGENT_ID", "BAUOKJ4UDH")
AGENT_ALIAS_ID = os.getenv("BEDROCK_AGENT_ALIAS_ID", "TSTALIASID")

# Initialize both basic and agentic services
bedrock_service = BedrockAgentService(AGENT_ID, AGENT_ALIAS_ID)
agentic_service = AgenticService(AGENT_ID, AGENT_ALIAS_ID)

# Initialize MCP-Agent Core integration
mcp_agent_integration = MCPAgentCoreIntegration(agentic_service, mcp_client)

@app.post("/api/chat", response_model=ChatResponse)
async def chat(message: ChatMessage, current_user: dict = Depends(get_current_user)):
    """Send message to Bedrock Agent with subscription tier limits and JWT auth"""
    
    # Verify tenant context matches authenticated user
    if message.tenant_context.tenant_id != current_user["tenant_id"]:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    
    if message.tenant_context.user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="User mismatch")
    
    # Check subscription tier limits
    tier = current_user["subscription_tier"]
    usage_limits = await subscription_service.check_usage_limits(current_user["tenant_id"], tier)
    
    if usage_limits["daily_limit_exceeded"]:
        raise HTTPException(status_code=429, detail="Daily message limit exceeded")
    
    if usage_limits["monthly_limit_exceeded"]:
        raise HTTPException(status_code=429, detail="Monthly message limit exceeded")
    
    # Validate tier-based tenant session
    session = store.get_session(
        message.tenant_context.tenant_id,
        message.tenant_context.user_id,
        message.tenant_context.session_id,
        tier
    )
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Always use MCP-Agent Core integration for proper tool handling
    result = await mcp_agent_integration.invoke_agent_with_mcp_tools(
        message.message, message.tenant_context, tier
    )
    
    # Update tier-based session activity and increment usage
    store.update_session_activity(
        message.tenant_context.tenant_id,
        message.tenant_context.user_id,
        message.tenant_context.session_id,
        tier
    )
    
    # Increment subscription usage
    await subscription_service.increment_usage(current_user["tenant_id"], tier)
    
    # Record enhanced usage metrics with trace data
    from decimal import Decimal
    usage_metric = UsageMetric(
        tenant_id=message.tenant_context.tenant_id,
        timestamp=datetime.utcnow(),
        metric_type="agent_invocation",
        value=Decimal('1.0'),
        session_id=message.tenant_context.session_id,
        agent_id=AGENT_ID
    )
    store.record_usage_metric(usage_metric)
    
    # Store enhanced trace data for tenant analytics
    if "trace_summary" in result:
        trace_metric = UsageMetric(
            tenant_id=message.tenant_context.tenant_id,
            timestamp=datetime.utcnow(),
            metric_type="trace_analysis",
            value=Decimal(str(result["trace_summary"].get("total_traces", 0))),
            session_id=message.tenant_context.session_id,
            agent_id=AGENT_ID
        )
        store.record_usage_metric(trace_metric)
    
    return ChatResponse(
        response=result["response"],
        session_id=result["session_id"],
        tenant_id=result["tenant_id"],
        usage_metrics=result["usage_metrics"]
    )

@app.post("/api/sessions")
async def create_session(current_user: dict = Depends(get_current_user)):
    """Create a new tier-based chat session for authenticated tenant user"""
    tier = current_user["subscription_tier"]
    
    # Check concurrent session limits
    usage_limits = await subscription_service.check_usage_limits(current_user["tenant_id"], tier)
    if usage_limits["concurrent_sessions_exceeded"]:
        raise HTTPException(status_code=429, detail="Concurrent session limit exceeded")
    
    session_id = store.create_session(current_user["tenant_id"], current_user["user_id"], tier)
    
    return {
        "tenant_id": current_user["tenant_id"],
        "user_id": current_user["user_id"],
        "session_id": session_id,
        "subscription_tier": tier.value,
        "created_at": datetime.utcnow().isoformat()
    }

@app.get("/api/tenants/{tenant_id}/usage")
async def get_tenant_usage(tenant_id: str, current_user: dict = Depends(get_current_user)):
    """Get usage metrics for authenticated tenant"""
    if tenant_id != current_user["tenant_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return store.get_tenant_usage(tenant_id)

@app.get("/api/tenants/{tenant_id}/subscription")
async def get_subscription_info(tenant_id: str, current_user: dict = Depends(get_current_user)):
    """Get subscription tier information and usage limits"""
    if tenant_id != current_user["tenant_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    tier = current_user["subscription_tier"]
    limits = subscription_service.get_tier_limits(tier)
    usage = await subscription_service.get_usage(tenant_id, tier)
    usage_limits = await subscription_service.check_usage_limits(tenant_id, tier)
    
    return {
        "tenant_id": tenant_id,
        "subscription_tier": tier.value,
        "limits": limits.dict(),
        "current_usage": usage.dict(),
        "limit_status": usage_limits
    }

@app.post("/api/mcp/tools/{tool_name}")
async def execute_mcp_tool(tool_name: str, arguments: dict, current_user: dict = Depends(get_current_user)):
    """Execute MCP tool if subscription tier allows it"""
    tier = current_user["subscription_tier"]
    
    result = await mcp_client.execute_mcp_tool(tool_name, arguments, tier)
    
    return {
        "tool_name": tool_name,
        "subscription_tier": tier.value,
        "result": result
    }

@app.get("/api/mcp/tools")
async def get_available_mcp_tools(current_user: dict = Depends(get_current_user)):
    """Get available MCP tools for current subscription tier"""
    tier = current_user["subscription_tier"]
    tools = await mcp_client.get_available_tools(tier)
    
    return {
        "subscription_tier": tier.value,
        "available_tools": tools
    }

@app.get("/api/tenants/{tenant_id}/sessions")
async def get_tenant_sessions(tenant_id: str, current_user: dict = Depends(get_current_user)):
    """Get all sessions for authenticated tenant"""
    if tenant_id != current_user["tenant_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "tenant_id": tenant_id,
        "sessions": store.get_tenant_sessions(tenant_id)
    }

@app.get("/api/tenants/{tenant_id}/analytics")
async def get_tenant_analytics(tenant_id: str, current_user: dict = Depends(get_current_user)):
    """Get enhanced analytics with trace data for authenticated tenant"""
    if tenant_id != current_user["tenant_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get usage data and build analytics
    usage_data = store.get_tenant_usage(tenant_id)
    tier = current_user["subscription_tier"]
    
    # Enhanced analytics following Agent Core patterns
    analytics = {
        "tenant_id": tenant_id,
        "subscription_tier": tier.value,
        "total_interactions": usage_data.get("total_messages", 0),
        "active_sessions": usage_data.get("sessions", 0),
        "processing_patterns": {
            "agent_invocations": len([m for m in usage_data.get("metrics", []) if m.get("metric_type") == "agent_invocation"]),
            "trace_analyses": len([m for m in usage_data.get("metrics", []) if m.get("metric_type") == "trace_analysis"])
        },
        "resource_breakdown": {
            "model_invocations": usage_data.get("total_messages", 0),
            "knowledge_base_queries": 0,  # Would be extracted from traces
            "action_group_calls": 0       # Would be extracted from traces
        },
        "runtime_context_usage": {
            "session_attributes_used": True,
            "prompt_attributes_used": True,
            "trace_analysis_enabled": True
        },
        "tier_specific_metrics": {
            "mcp_tools_available": subscription_service.get_tier_limits(tier).mcp_server_access,
            "usage_limits": subscription_service.get_tier_limits(tier).dict()
        }
    }
    
    return analytics

# Mount static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_chat_interface():
    """Serve the chat interface with Cognito registration"""
    with open("frontend/index.html", "r") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)