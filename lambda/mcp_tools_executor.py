import json
from typing import Dict, Any

class MCPToolsExecutor:
    def __init__(self):
        self.tier_info = {
            "basic": {
                "name": "Basic",
                "daily_messages": 50,
                "monthly_messages": 1000,
                "features": ["Basic chat", "Standard response time"],
                "price": "$0/month"
            },
            "advanced": {
                "name": "Advanced", 
                "daily_messages": 200,
                "monthly_messages": 5000,
                "features": ["Priority support", "Extended sessions", "MCP tools"],
                "price": "$29/month"
            },
            "premium": {
                "name": "Premium",
                "daily_messages": 1000,
                "monthly_messages": 25000,
                "features": ["Unlimited sessions", "Advanced analytics", "Custom integrations"],
                "price": "$99/month"
            }
        }
    
    def get_tier_info(self, tier: str) -> Dict[str, Any]:
        return {"tier_info": self.tier_info.get(tier, self.tier_info["basic"])}
    
    def get_usage_analytics(self, tenant_id: str) -> Dict[str, Any]:
        return {
            "tenant_id": tenant_id,
            "analytics": {
                "total_messages": 1250,
                "avg_session_duration": 15.5,
                "peak_usage_hour": "14:00"
            }
        }

def lambda_handler(event, context):
    action_group = event.get('actionGroup', '')
    api_path = event.get('apiPath', '')
    parameters = event.get('parameters', [])
    
    params = {}
    for param in parameters:
        params[param['name']] = param['value']
    
    executor = MCPToolsExecutor()
    
    try:
        if api_path == '/get_tier_info':
            result = executor.get_tier_info(params.get('tier', 'basic'))
        elif api_path == '/get_usage_analytics':
            result = executor.get_usage_analytics(params.get('tenant_id', 'unknown'))
        else:
            result = {"error": f"Unknown API path: {api_path}"}
        
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": action_group,
                "apiPath": api_path,
                "httpMethod": "POST",
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps(result)
                    }
                }
            }
        }
        
    except Exception as e:
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": action_group,
                "apiPath": api_path,
                "httpMethod": "POST",
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({"error": str(e)})
                    }
                }
            }
        }