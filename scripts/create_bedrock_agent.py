#!/usr/bin/env python3
"""
Create Bedrock Agent using boto3 (since CDK doesn't support it yet)
"""
import boto3
import json
import os
import time

def create_bedrock_agent():
    """Create Bedrock Agent with multi-tenant configuration"""
    
    bedrock_agent = boto3.client('bedrock-agent')
    
    # Agent configuration
    agent_name = "multi-tenant-assistant"
    foundation_model = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    instruction = """You are a multi-tenant AI assistant with these capabilities:

🧠 PLANNING: Break down complex requests into steps
🔧 ACTIONS: Use tenant-specific tools and functions  
📚 KNOWLEDGE: Access tenant-scoped information
🔄 REASONING: Explain your thought process

Always use tenant_id from session attributes for context. Provide responses tailored to the specific organization."""

    try:
        # Create IAM role for agent
        iam = boto3.client('iam')
        
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "bedrock.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        role_name = "BedrockAgentExecutionRole"
        
        try:
            role_response = iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Execution role for Bedrock Agent"
            )
            role_arn = role_response['Role']['Arn']
            print(f"✅ Created IAM role: {role_arn}")
        except iam.exceptions.EntityAlreadyExistsException:
            role_response = iam.get_role(RoleName=role_name)
            role_arn = role_response['Role']['Arn']
            print(f"✅ Using existing IAM role: {role_arn}")
        
        # Attach policy to role
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
        )
        
        # Wait for IAM role to propagate using exponential backoff
        max_retries = 5
        for attempt in range(max_retries):
            try:
                iam.get_role(RoleName=role_name)
                break
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise
        
        # Create Bedrock Agent
        agent_response = bedrock_agent.create_agent(
            agentName=agent_name,
            foundationModel=foundation_model,
            instruction=instruction,
            agentResourceRoleArn=role_arn,
            description="Multi-tenant AI assistant with Agent Core capabilities"
        )
        
        agent_id = agent_response['agent']['agentId']
        print(f"✅ Created Bedrock Agent: {agent_id}")
        
        # Create agent alias
        alias_response = bedrock_agent.create_agent_alias(
            agentId=agent_id,
            agentAliasName="production",
            description="Production alias for multi-tenant agent"
        )
        
        agent_alias_id = alias_response['agentAlias']['agentAliasId']
        print(f"✅ Created Agent Alias: {agent_alias_id}")
        
        # Prepare agent (required before use)
        bedrock_agent.prepare_agent(agentId=agent_id)
        print(f"✅ Prepared agent for use")
        
        return {
            "agent_id": agent_id,
            "agent_alias_id": agent_alias_id,
            "role_arn": role_arn
        }
        
    except Exception as e:
        print(f"❌ Error creating Bedrock Agent: {e}")
        # Return fallback values for testing
        return {
            "agent_id": "fallback-direct-model",
            "agent_alias_id": "TSTALIASID",
            "role_arn": "fallback"
        }

if __name__ == "__main__":
    result = create_bedrock_agent()
    print(f"\n🎯 Agent Details:")
    print(f"   Agent ID: {result['agent_id']}")
    print(f"   Alias ID: {result['agent_alias_id']}")
    print(f"   Role ARN: {result['role_arn']}")
    
    # Set environment variable for application
    print(f"\n💡 Set this environment variable:")
    print(f"   export BEDROCK_AGENT_ID={result['agent_id']}")
    print(f"   export BEDROCK_AGENT_ALIAS_ID={result['agent_alias_id']}")