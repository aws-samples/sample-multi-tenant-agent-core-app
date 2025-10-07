import boto3
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from .models import TenantContext, UsageMetric

class BedrockAgentService:
    def __init__(self, agent_id: str, agent_alias_id: str = "TSTALIASID"):
        self.bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
        self.bedrock_runtime = boto3.client('bedrock-runtime')
        self.agent_id = agent_id
        self.agent_alias_id = agent_alias_id
        self.model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        
    def invoke_agent(self, message: str, tenant_context: TenantContext) -> Dict[str, Any]:
        """Invoke Bedrock Agent with proper runtime context"""
        session_id = f"{tenant_context.tenant_id}-{tenant_context.subscription_tier}-{tenant_context.user_id}-{tenant_context.session_id}"
        
        session_state = {
            "sessionAttributes": {
                "tenant_id": tenant_context.tenant_id,
                "user_id": tenant_context.user_id,
                "subscription_tier": tenant_context.subscription_tier
            },
            "promptSessionAttributes": {
                "tenant_context": f"{tenant_context.tenant_id} {tenant_context.subscription_tier} user"
            }
        }
        
        try:
            if self.agent_id and self.agent_id != "your-agent-id":
                response = self.bedrock_agent_runtime.invoke_agent(
                    agentId=self.agent_id,
                    agentAliasId=self.agent_alias_id,
                    sessionId=session_id,
                    inputText=message,
                    sessionState=session_state,
                    enableTrace=True
                )
                return self._process_agent_response(response, session_id, tenant_context.tenant_id)
            else:
                return self._invoke_claude_direct(message, session_id, tenant_context.tenant_id)
            
        except Exception as e:
            return {
                "response": f"Error: {str(e)}",
                "session_id": session_id,
                "usage_metrics": {"error": True},
                "tenant_id": tenant_context.tenant_id
            }
    
    def _process_agent_response(self, response, session_id: str, tenant_id: str) -> Dict[str, Any]:
        """Process Bedrock Agent response with trace analysis"""
        agent_response = ""
        usage_data = {
            "tenant_id": tenant_id,
            "session_id": session_id,
            "invocation_time": datetime.utcnow().isoformat()
        }
        
        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    agent_response += chunk['bytes'].decode('utf-8')
            elif 'trace' in event:
                trace = event['trace']
                if 'orchestrationTrace' in trace:
                    orchestration = trace['orchestrationTrace']
                    if 'modelInvocationOutput' in orchestration:
                        model_output = orchestration['modelInvocationOutput']
                        if 'metadata' in model_output:
                            metadata = model_output['metadata']
                            usage_data['input_tokens'] = metadata.get('usage', {}).get('inputTokens', 0)
                            usage_data['output_tokens'] = metadata.get('usage', {}).get('outputTokens', 0)
        
        return {
            "response": agent_response,
            "session_id": session_id,
            "usage_metrics": usage_data,
            "tenant_id": tenant_id
        }
    
    def _invoke_claude_direct(self, message: str, session_id: str, tenant_id: str) -> Dict[str, Any]:
        """Direct Claude invocation fallback"""
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": message}]
            }
            
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            
            return {
                "response": response_body['content'][0]['text'],
                "session_id": session_id,
                "usage_metrics": {
                    "tenant_id": tenant_id,
                    "input_tokens": response_body.get('usage', {}).get('input_tokens', 0),
                    "output_tokens": response_body.get('usage', {}).get('output_tokens', 0),
                    "invocation_time": datetime.utcnow().isoformat()
                },
                "tenant_id": tenant_id
            }
            
        except Exception as e:
            return {
                "response": f"Claude Error: {str(e)}",
                "session_id": session_id,
                "usage_metrics": {"error": True, "tenant_id": tenant_id},
                "tenant_id": tenant_id
            }