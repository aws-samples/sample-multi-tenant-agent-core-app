#!/usr/bin/env python3
"""
Create Bedrock Agent with MCP Tools as Action Groups
"""
import boto3
import json
import os
from datetime import datetime

def create_agent_with_mcp_tools():
    """Create Bedrock Agent with MCP tools configured as Action Groups"""
    
    bedrock_agent = boto3.client('bedrock-agent')
    
    # MCP Tools Action Group Schema
    mcp_action_group_schema = {
        "openapi": "3.0.0",
        "info": {
            "title": "MCP Subscription Tools",
            "version": "1.0.0",
            "description": "MCP tools for subscription management"
        },
        "paths": {
            "/get_tier_info": {
                "post": {
                    "summary": "Get subscription tier information",
                    "description": "Retrieve detailed information about the user's subscription tier",
                    "operationId": "get_tier_info",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "tier": {
                                            "type": "string",
                                            "description": "Subscription tier (basic, advanced, premium)"
                                        }
                                    },
                                    "required": ["tier"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Subscription tier information",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "tier_info": {
                                                "type": "object",
                                                "properties": {
                                                    "name": {"type": "string"},
                                                    "price": {"type": "string"},
                                                    "daily_messages": {"type": "integer"},
                                                    "monthly_messages": {"type": "integer"},
                                                    "features": {"type": "array", "items": {"type": "string"}}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/get_usage_analytics": {
                "post": {
                    "summary": "Get usage analytics",
                    "description": "Retrieve usage analytics for the tenant",
                    "operationId": "get_usage_analytics",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "tenant_id": {"type": "string"},
                                        "period": {"type": "string"}
                                    },
                                    "required": ["tenant_id"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Usage analytics data"
                        }
                    }
                }
            }
        }
    }
    
    try:
        # Create the agent
        agent_response = bedrock_agent.create_agent(
            agentName='mcp-subscription-agent',
            description='Multi-tenant agent with MCP subscription tools',
            foundationModel='anthropic.claude-3-haiku-20240307-v1:0',
            instruction="""You are a helpful assistant for a multi-tenant subscription service. 
            You have access to subscription management tools through MCP (Model Context Protocol).
            
            When users ask about their subscription details, use the get_tier_info tool.
            When users ask about usage analytics, use the get_usage_analytics tool.
            
            Always provide helpful, accurate information about their subscription tier and usage.""",
            idleSessionTTLInSeconds=1800
        )
        
        agent_id = agent_response['agent']['agentId']
        print(f"✅ Agent created: {agent_id}")
        
        # Create Action Group for MCP Tools
        action_group_response = bedrock_agent.create_agent_action_group(
            agentId=agent_id,
            agentVersion='DRAFT',
            actionGroupName='mcp-subscription-tools',
            description='MCP tools for subscription management',
            actionGroupExecutor={
                'lambda': f'arn:aws:lambda:{os.getenv("AWS_REGION", "us-east-1")}:123456789012:function:mcp-tools-executor'
            },
            apiSchema={
                'payload': json.dumps(mcp_action_group_schema)
            }
        )
        
        print(f"✅ Action Group created: {action_group_response['agentActionGroup']['actionGroupId']}")
        
        # Prepare the agent
        prepare_response = bedrock_agent.prepare_agent(
            agentId=agent_id
        )
        
        print(f"✅ Agent prepared: {prepare_response['agentStatus']}")
        
        # Create alias
        alias_response = bedrock_agent.create_agent_alias(
            agentId=agent_id,
            agentAliasName='mcp-subscription-alias',
            description='Alias for MCP subscription agent'
        )
        
        alias_id = alias_response['agentAlias']['agentAliasId']
        print(f"✅ Agent Alias created: {alias_id}")
        
        print(f"\n🎯 Agent Configuration:")
        print(f"   Agent ID: {agent_id}")
        print(f"   Alias ID: {alias_id}")
        print(f"   Foundation Model: anthropic.claude-3-haiku-20240307-v1:0")
        print(f"   MCP Tools: get_tier_info, get_usage_analytics")
        
        return agent_id, alias_id
        
    except Exception as e:
        print(f"❌ Error creating agent: {str(e)}")
        print("\n💡 Note: This requires:")
        print("   1. Bedrock Agent service enabled")
        print("   2. Lambda function for MCP tool execution")
        print("   3. Proper IAM permissions")
        print("\n🔄 Falling back to direct model invocation")
        return None, None

if __name__ == "__main__":
    create_agent_with_mcp_tools()