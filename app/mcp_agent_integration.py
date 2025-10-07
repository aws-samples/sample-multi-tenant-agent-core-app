"""
MCP-Agent Core Integration Service
Integrates Model Context Protocol with AWS Bedrock Agent Core runtime capabilities
"""
import json
import re
from typing import Dict, Any, List, Optional
from app.models import TenantContext, SubscriptionTier
from app.weather_mcp_service import WeatherMCPClient
from app.agentic_service import AgenticService
from app.runtime_context import RuntimeContextManager

class MCPAgentCoreIntegration:
    """Integrates MCP tools as Agent Core action groups"""
    
    def __init__(self, agentic_service: AgenticService):
        self.agentic_service = agentic_service
        self.weather_client = WeatherMCPClient()
        
    async def invoke_agent_with_mcp_tools(self, message: str, tenant_context: TenantContext, 
                                        subscription_tier: SubscriptionTier) -> Dict[str, Any]:
        """Invoke Agent Core with MCP tools available as action groups"""
        
        # Get available weather MCP tools for this tier
        weather_tools = await self.weather_client.get_available_weather_tools(subscription_tier)
        
        # Build enhanced session attributes with MCP context
        session_attributes = RuntimeContextManager.build_session_attributes(
            tenant_context.tenant_id,
            tenant_context.user_id,
            tenant_context.session_id,
            additional_context={
                "weather_tools_enabled": "true" if weather_tools else "false",
                "available_weather_tools": ",".join(weather_tools),
                "subscription_tier": subscription_tier.value
            }
        )
        
        # Build prompt attributes with MCP tool context
        prompt_attributes = RuntimeContextManager.build_prompt_session_attributes(
            tenant_context.tenant_id,
            tenant_context.user_id,
            message_context={
                "user_subscription_tier": subscription_tier.value,
                "available_weather_tools": ", ".join(weather_tools) if weather_tools else "none"
            }
        )
        
        # Check for weather queries and handle with MCP tools
        if self._is_weather_query(message) and weather_tools:
            return await self._handle_weather_query(message, tenant_context, subscription_tier)
        else:
            # Standard Agent Core invocation
            return self.agentic_service.invoke_agent_with_planning(message, tenant_context)
    
    def _merge_mcp_agent_results(self, agent_result: Dict[str, Any], mcp_result: Dict[str, Any], 
                               mcp_request: Dict[str, Any]) -> Dict[str, Any]:
        """Merge MCP tool results with Agent Core results"""
        
        # Enhance agent result with MCP context
        agent_result["mcp_integration"] = {
            "tool_used": mcp_request["tool_name"],
            "tool_result": mcp_result,
            "integration_success": True
        }
        
        # Add MCP trace to agentic trace
        if "agentic_trace" in agent_result:
            agent_result["agentic_trace"]["mcp_tools"] = [{
                "tool_name": mcp_request["tool_name"],
                "arguments": mcp_request["arguments"],
                "result": mcp_result
            }]
        
        # Update capabilities used
        if "capabilities_used" in agent_result:
            agent_result["capabilities_used"]["mcp_tools"] = True
            agent_result["capabilities_used"]["subscription_aware"] = True
        
        return agent_result
    

    

    
    def _is_weather_query(self, message: str) -> bool:
        """Check if message is asking about weather"""
        weather_keywords = [
            "weather", "temperature", "forecast", "rain", "sunny", "cloudy",
            "wind", "humidity", "storm", "snow", "hot", "cold", "climate"
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in weather_keywords)
    
    async def _handle_weather_query(self, message: str, tenant_context: TenantContext, subscription_tier: SubscriptionTier) -> Dict[str, Any]:
        """Handle weather queries using real-time MCP weather tools"""
        
        # Parse weather request with improved location extraction
        weather_request = self._parse_weather_request(message)
        
        # Determine weather tool based on query intent
        tool_name = "get_current_weather"  # default
        if any(word in message.lower() for word in ["forecast", "tomorrow", "next", "days", "week"]):
            tool_name = "get_weather_forecast"
        elif any(word in message.lower() for word in ["alert", "warning", "advisory", "severe"]):
            tool_name = "get_weather_alerts"
        
        # Execute real-time weather MCP tool
        mcp_result = await self.weather_client.execute_weather_tool(
            tool_name,
            weather_request,
            subscription_tier
        )
        
        # Handle MCP tool errors gracefully
        if "error" in mcp_result:
            enhanced_message = f"""
User asked about weather: {message}

There was an issue getting weather data: {mcp_result['error']}

Please apologize and suggest the user try again or check their location spelling."""
        else:
            # Format real-time weather data for Agent Core
            weather_data = mcp_result.get('result', {})
            enhanced_message = f"""
User asked about weather: {message}

Real-time weather data from OpenWeatherMap API:
{json.dumps(weather_data, indent=2)}

Please provide a helpful, conversational response about the weather using this real-time data. 
Make it natural and informative, highlighting key details like temperature, conditions, and any notable weather patterns."""
        
        # Invoke Agent Core with real weather context
        agent_result = self.agentic_service.invoke_agent_with_planning(
            enhanced_message, tenant_context
        )
        
        # Add MCP integration metadata
        agent_result["mcp_integration"] = {
            "tool_used": tool_name,
            "tool_result": mcp_result,
            "real_time_data": True,
            "data_source": "OpenWeatherMap API",
            "integration_success": "error" not in mcp_result
        }
        
        return agent_result
    
    def _parse_weather_request(self, message: str) -> Dict[str, Any]:
        """Parse weather request to extract location and parameters with improved accuracy"""
        import re
        
        args = {"location": "New York"}  # Default location
        message_lower = message.lower()
        
        # Enhanced location extraction
        # Look for "in [location]" or "for [location]" patterns
        location_patterns = [
            r'\b(?:in|for|at|near)\s+([a-zA-Z\s,]+?)(?:\s|$|\?|!)',
            r'\b([A-Z][a-zA-Z\s]+(?:,\s*[A-Z][A-Z])?)\b'  # Capitalized locations
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, message)
            if matches:
                location = matches[0].strip().rstrip(',').title()
                # Filter out common weather words
                weather_words = ['Weather', 'Temperature', 'Forecast', 'Today', 'Tomorrow']
                if location not in weather_words and len(location) > 2:
                    args["location"] = location
                    break
        
        # Enhanced forecast days parsing
        if re.search(r'\b(?:3|three)\s*days?\b', message_lower):
            args["days"] = 3
        elif re.search(r'\b(?:5|five)\s*days?\b', message_lower):
            args["days"] = 5
        elif re.search(r'\b(?:7|seven)\s*days?|week\b', message_lower):
            args["days"] = 5  # OpenWeatherMap free tier max
        elif 'tomorrow' in message_lower:
            args["days"] = 2
        
        return args
    
    def _format_subscription_response(self, mcp_result: Dict[str, Any], tier: SubscriptionTier) -> str:
        """Format subscription information into a user-friendly response"""
        if "result" in mcp_result and "tier_info" in mcp_result["result"]:
            tier_info = mcp_result["result"]["tier_info"]
            return f"""Your subscription details:
            
🏷️ **{tier_info['name']} Plan** ({tier_info['price']})
📊 **Daily Messages**: {tier_info['daily_messages']}
📈 **Monthly Messages**: {tier_info['monthly_messages']}
✨ **Features**: {', '.join(tier_info['features'])}

Your current tier is {tier.value.upper()} with access to all listed features."""
        else:
            return f"You are currently on the {tier.value.upper()} subscription tier."

class MCPActionGroupSimulator:
    """Simulates MCP tools as Bedrock Agent Action Groups"""
    
    def __init__(self, weather_client: WeatherMCPClient):
        self.weather_client = weather_client
    
    def generate_action_group_schema(self, subscription_tier: SubscriptionTier) -> Dict[str, Any]:
        """Generate OpenAPI schema for MCP tools as action groups"""
        
        if subscription_tier == SubscriptionTier.BASIC:
            return {"openapi": "3.0.0", "info": {"title": "No MCP Tools", "version": "1.0.0"}, "paths": {}}
        
        schema = {
            "openapi": "3.0.0",
            "info": {
                "title": "MCP Tools Action Group",
                "version": "1.0.0",
                "description": f"MCP tools available for {subscription_tier.value} tier"
            },
            "paths": {
                "/get_tier_info": {
                    "post": {
                        "summary": "Get subscription tier information",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "tier": {"type": "string", "description": "Subscription tier"}
                                        }
                                    }
                                }
                            }
                        },
                        "responses": {"200": {"description": "Tier information"}}
                    }
                },
                "/get_usage_analytics": {
                    "post": {
                        "summary": "Get usage analytics",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "tenant_id": {"type": "string", "description": "Tenant ID"},
                                            "period": {"type": "string", "description": "Analytics period"}
                                        }
                                    }
                                }
                            }
                        },
                        "responses": {"200": {"description": "Usage analytics"}}
                    }
                }
            }
        }
        
        if subscription_tier == SubscriptionTier.PREMIUM:
            # Add premium-only tools
            schema["paths"]["/upgrade_tier"] = {
                "post": {
                    "summary": "Upgrade subscription tier",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "tenant_id": {"type": "string"},
                                        "new_tier": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Upgrade result"}}
                }
            }
        
        return schema