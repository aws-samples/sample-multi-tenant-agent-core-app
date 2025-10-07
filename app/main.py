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
from .weather_mcp_service import WeatherMCPClient
from .mcp_agent_integration import MCPAgentCoreIntegration
from .cost_attribution import CostAttributionService
from .admin_cost_service import AdminCostService
from .admin_auth import get_admin_user, verify_tenant_admin, AdminAuthService

app = FastAPI(title="Multi-Tenant Bedrock Chat", version="1.0.0")

# Initialize services
store = DynamoDBStore()
subscription_service = SubscriptionService(store)
weather_client = WeatherMCPClient()

# Bedrock Agent configuration
AGENT_ID = os.getenv("BEDROCK_AGENT_ID", "BAUOKJ4UDH")
AGENT_ALIAS_ID = os.getenv("BEDROCK_AGENT_ALIAS_ID", "TSTALIASID")

# Initialize both basic and agentic services
bedrock_service = BedrockAgentService(AGENT_ID, AGENT_ALIAS_ID)
agentic_service = AgenticService(AGENT_ID, AGENT_ALIAS_ID)

# Initialize MCP-Agent Core integration
mcp_agent_integration = MCPAgentCoreIntegration(agentic_service)

# Initialize cost attribution service
cost_service = CostAttributionService()
admin_cost_service = AdminCostService()

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
    
    # Use MCP-Agent Core integration for weather tools
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

@app.get("/api/tenants/{tenant_id}/costs")
async def get_tenant_costs(tenant_id: str, days: int = 30, current_user: dict = Depends(get_current_user)):
    """Get cost attribution for tenant"""
    if tenant_id != current_user["tenant_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    from datetime import datetime, timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    costs = await cost_service.calculate_tenant_costs(tenant_id, start_date, end_date)
    return costs

@app.get("/api/tenants/{tenant_id}/users/{user_id}/costs")
async def get_user_costs(tenant_id: str, user_id: str, days: int = 30, current_user: dict = Depends(get_current_user)):
    """Get cost attribution for specific user"""
    if tenant_id != current_user["tenant_id"] or user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    from datetime import datetime, timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    costs = await cost_service.calculate_user_costs(tenant_id, user_id, start_date, end_date)
    return costs

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



@app.get("/api/mcp/weather/tools")
async def get_available_weather_tools(current_user: dict = Depends(get_current_user)):
    """Get available weather MCP tools for current subscription tier"""
    tier = current_user["subscription_tier"]
    weather_tools = await weather_client.get_available_weather_tools(tier)
    
    return {
        "subscription_tier": tier.value,
        "weather_tools": weather_tools
    }

@app.post("/api/mcp/weather/{tool_name}")
async def execute_weather_mcp_tool(tool_name: str, arguments: dict, current_user: dict = Depends(get_current_user)):
    """Execute weather MCP tool if subscription tier allows it"""
    tier = current_user["subscription_tier"]
    
    result = await weather_client.execute_weather_tool(tool_name, arguments, tier)
    
    return {
        "tool_name": tool_name,
        "subscription_tier": tier.value,
        "result": result
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

@app.get("/api/admin/cost-report")
async def get_cost_report(tenant_id: str = None, days: int = 30):
    """Generate comprehensive cost report (admin only)"""
    # In production, add admin authentication here
    report = await cost_service.generate_cost_report(tenant_id, days)
    return report

@app.get("/api/admin/tier-costs/{tier}")
async def get_tier_costs(tier: str, days: int = 30):
    """Get cost breakdown by subscription tier (admin only)"""
    # In production, add admin authentication here
    subscription_tier = SubscriptionTier(tier)
    costs = await cost_service.get_subscription_tier_costs(subscription_tier, days)
    return costs

# Admin-Only Granular Cost Endpoints
@app.get("/api/admin/tenants/{tenant_id}/overall-cost")
async def get_admin_tenant_overall_cost(tenant_id: str, days: int = 30, admin_user: dict = Depends(verify_tenant_admin)):
    """1. Overall Tenant Cost - Admin Only"""
    from datetime import datetime, timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    costs = await admin_cost_service.get_tenant_overall_cost(tenant_id, start_date, end_date)
    return costs

@app.get("/api/admin/tenants/{tenant_id}/per-user-cost")
async def get_admin_per_user_cost(tenant_id: str, days: int = 30, admin_user: dict = Depends(verify_tenant_admin)):
    """2. Per User Cost - Admin Only"""
    from datetime import datetime, timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    costs = await admin_cost_service.get_tenant_per_user_cost(tenant_id, start_date, end_date)
    return costs

@app.get("/api/admin/tenants/{tenant_id}/service-wise-cost")
async def get_admin_service_wise_cost(tenant_id: str, days: int = 30, admin_user: dict = Depends(verify_tenant_admin)):
    """3. Overall Tenant Service-wise Consumption Cost - Admin Only"""
    from datetime import datetime, timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    costs = await admin_cost_service.get_tenant_service_wise_cost(tenant_id, start_date, end_date)
    return costs

@app.get("/api/admin/tenants/{tenant_id}/users/{user_id}/service-cost")
async def get_admin_user_service_cost(tenant_id: str, user_id: str, days: int = 30, admin_user: dict = Depends(verify_tenant_admin)):
    """4. User Service-wise Consumption Cost - Admin Only"""
    from datetime import datetime, timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    costs = await admin_cost_service.get_user_service_wise_cost(tenant_id, user_id, start_date, end_date)
    return costs

@app.get("/api/admin/tenants/{tenant_id}/comprehensive-report")
async def get_comprehensive_admin_report(tenant_id: str, days: int = 30, admin_user: dict = Depends(verify_tenant_admin)):
    """Comprehensive Admin Cost Report - All 4 breakdowns"""
    report = await admin_cost_service.generate_comprehensive_admin_report(tenant_id, days)
    return report

@app.get("/api/admin/my-tenants")
async def get_admin_tenants(admin_user: dict = Depends(get_admin_user)):
    """Get tenants where current user has admin access"""
    return {
        "admin_email": admin_user["email"],
        "admin_tenants": admin_user["admin_tenants"]
    }

@app.post("/api/admin/add-to-group")
async def add_user_to_admin_group(request: dict):
    """Add user to admin group during registration"""
    from app.admin_auth import AdminAuthService
    
    email = request.get("email")
    tenant_id = request.get("tenant_id")
    
    if not email or not tenant_id:
        raise HTTPException(status_code=400, detail="Email and tenant_id required")
    
    admin_service = AdminAuthService()
    
    # Create admin groups if they don't exist
    try:
        group_name = f"{tenant_id}-admins"
        admin_service.cognito_client.create_group(
            GroupName=group_name,
            UserPoolId=admin_service.user_pool_id,
            Description=f"{tenant_id.title()} Administrators"
        )
    except Exception:
        pass  # Group may already exist
    
    # Add user to admin group
    try:
        admin_service.cognito_client.admin_add_user_to_group(
            UserPoolId=admin_service.user_pool_id,
            Username=email,
            GroupName=f"{tenant_id}-admins"
        )
        return {"success": True, "message": f"Added {email} to {tenant_id}-admins group"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add user to admin group: {str(e)}")

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