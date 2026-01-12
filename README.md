# Multi-Tenant Amazon Bedrock Agent Core Application

A sample multi-tenant chat application demonstrating **Amazon Bedrock Agent Core Runtime**, **Cognito JWT authentication**, **DynamoDB session storage**, and **granular cost attribution**. This code serves as a reference implementation for building similar multi-tenant AI applications.

## 🎯 Core Concept

This application demonstrates how to leverage **Amazon Bedrock Agent Core Runtime** to serve multiple tenants from a single agent deployment by passing **tenant IDs at runtime**. The key innovation is using session attributes to:

1. **Dynamic Tenant Routing**: Pass tenant_id and subscription_tier to Bedrock Agent Core Runtime during each invocation, enabling one agent to serve multiple organizations
2. **Subscription-Based Access Control**: Control feature access (models, tools, limits) based on subscription tier passed in session attributes
3. **Granular Cost Attribution**: Track and attribute costs per tenant and user by capturing tenant context in all observability traces
4. **Multi-Tenant Isolation**: Ensure complete data separation while sharing the same Bedrock Agent Core Runtime infrastructure

### How It Works

```
User Login → JWT with tenant_id → Session Attributes → Bedrock Agent Core Runtime
                                                              ↓
                                    Tenant-specific response + cost tracking
```

**Key Benefits:**
- **Single Agent, Multiple Tenants**: One Bedrock Agent Core deployment serves all organizations
- **Runtime Tenant Context**: No need to deploy separate agents per tenant
- **Cost Transparency**: Automatic cost attribution per tenant for billing and analytics
- **Flexible Subscriptions**: Different feature sets and limits per tenant based on their tier

## ⚠️ Important Disclaimers

**This is a code sample for demonstration purposes only.** Do not use in production environments without:
- Comprehensive security review and penetration testing
- Proper error handling and input validation
- Rate limiting and DDoS protection
- Encryption at rest and in transit
- Compliance review (GDPR, HIPAA, etc.)
- Load testing and performance optimization
- Monitoring, alerting, and incident response procedures

**Responsible AI**: This system includes automated AWS operations capabilities. Users are responsible for ensuring appropriate safeguards, monitoring, and human oversight when deploying AI-driven infrastructure management tools. Learn more about [AWS Responsible AI practices](https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/responsible-ai.html).

**Guardrails for Foundation Models**: When deploying this application in production, implement [Amazon Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html) to:
- **Content Filtering**: Block harmful, inappropriate, or sensitive content based on your use case
- **Denied Topics**: Prevent the model from generating responses on specific topics
- **Word Filters**: Filter profanity, custom words, or phrases
- **PII Redaction**: Automatically detect and redact personally identifiable information
- **Contextual Grounding**: Reduce hallucinations by grounding responses in source documents
- **Safety Thresholds**: Configure hate, insults, sexual, violence, and misconduct filters

Guardrails can be applied at the model invocation level or integrated with Agent Core Runtime for comprehensive protection across all tenant interactions.

**Use Case**: This sample code demonstrates patterns for building multi-tenant SaaS AI applications where:
- Multiple organizations share the same Bedrock Agent Core Runtime infrastructure
- Each tenant gets isolated data and personalized experiences
- Costs are automatically tracked and attributed per tenant for billing
- Subscription tiers control access to features, models, and usage limits

Adapt and extend for your specific requirements.

## 📖 Overview

### Amazon Bedrock Agent Core Runtime

Amazon Bedrock Agent Core Runtime is an advanced orchestration layer that enables AI agents to:
- **Plan and Reason**: Break down complex queries into actionable steps
- **Execute Actions**: Invoke tools, APIs, and AWS services dynamically
- **Maintain Context**: Preserve conversation state and tenant-specific information across sessions
- **Orchestrate Workflows**: Coordinate multiple tool calls and decision-making processes

This application leverages Bedrock Agent Core Runtime to provide intelligent, context-aware responses while maintaining strict multi-tenant isolation.

### Bedrock Agent Core Observability

Bedrock Agent Core Observability provides comprehensive visibility into agent behavior:
- **Trace Analysis**: Complete execution traces showing planning, reasoning, and action steps
- **Performance Monitoring**: Track response times, token usage, and API call patterns
- **Cost Attribution**: Granular tracking of costs per tenant, user, and service
- **Debug Insights**: Detailed logs of agent decision-making and tool invocations
- **Usage Analytics**: Real-time metrics on subscription tier consumption and limits

All traces and metrics are captured in DynamoDB for audit trails and cost optimization.

## 🏗️ Architecture Overview

![Architecture Diagram](architecuture.png)

### Core Components
- **Amazon Bedrock Agent Core Runtime**: Advanced AI orchestration with planning, reasoning, and tool execution
- **Bedrock Foundation Models**: Support for Claude, Titan, and other Bedrock models
- **Multi-Tenant Authentication**: Cognito JWT with tenant isolation and admin role management
- **Session Management**: DynamoDB-based persistent sessions with tenant-specific isolation
- **Bedrock Agent Core Observability**: Complete trace capture, cost attribution, and performance monitoring
- **Subscription Tiers**: Basic, Advanced, Premium with usage limits and feature access control

### System Flow
```
JWT Token → Tenant Context → Session Attributes → Bedrock Agent Core Runtime → Bedrock Models → Natural Response
                                                          ↓
                                                   Observability Traces
```

**Session ID Format**: `{tenant_id}-{user_id}-{session_id}`
**Session Attributes**: Tenant context, subscription tier, and user preferences passed to Bedrock Agent Core
**Trace Capture**: Complete orchestration, planning, reasoning, and tool execution traces
**Cost Tracking**: Real-time token usage and cost attribution per tenant/user/service

## 📋 Prerequisites

### AWS Account Requirements
1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
   ```bash
   aws configure
   ```
3. **Bedrock Model Access**: Request access to foundation models in AWS Console
   - Navigate to AWS Bedrock Console
   - Go to "Model access" section
   - Request access to desired models (Claude, Titan, etc.)
   - Wait for approval (usually instant)
4. **Bedrock Agent Core Runtime**: Ensure Bedrock Agent features are enabled in your region

### Required AWS Services
- **Amazon Bedrock**: Agent Core Runtime with foundation model access
  - Claude 3 Haiku: `anthropic.claude-3-haiku-20240307-v1:0`
  - Claude 3 Sonnet: `anthropic.claude-3-sonnet-20240229-v1:0`
  - Claude 3.5 Sonnet: `anthropic.claude-3-5-sonnet-20240620-v1:0`
  - Titan Text: `amazon.titan-text-express-v1`
- **Amazon Cognito**: User Pool with custom attributes (`tenant_id`, `subscription_tier`)
- **Amazon DynamoDB**: Two tables (`tenant-sessions`, `tenant-usage`)
- **AWS IAM**: Permissions for Bedrock Agent Runtime, Cognito, and DynamoDB

### Development Tools
- **Python 3.11+**
- **pip** (Python package manager)
- **Git** for version control

## 🚀 Deployment Guide

### Step 1: Clone Repository
```bash
git clone <repository-url>
cd Agent-Core
```

### Step 2: Deploy AWS Infrastructure with Terraform

```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

This will create:
- Cognito User Pool with custom attributes (tenant_id, subscription_tier)
- Cognito User Pool Client
- DynamoDB Tables (tenant-sessions, tenant-usage)
- IAM Roles and Policies for Bedrock, Cognito, and DynamoDB

**Note the outputs** from Terraform:
- `cognito_user_pool_id`
- `cognito_client_id`

### Step 3: Setup Application

#### 3.1 Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3.2 Install Dependencies
```bash
pip install -r requirements.txt
```

#### 3.3 Configure Environment Variables
```bash
# Create .env file with Terraform outputs
cat > .env << EOF
COGNITO_USER_POOL_ID=<FROM_TERRAFORM_OUTPUT>
COGNITO_CLIENT_ID=<FROM_TERRAFORM_OUTPUT>
BEDROCK_AGENT_ID=<BEDROCK_AGENT_ID>
SESSIONS_TABLE=tenant-sessions
USAGE_TABLE=tenant-usage
AWS_REGION=us-east-1
EOF
```

#### 3.4 Configure Frontend
Update `frontend/index.html` with your Cognito credentials:

```javascript
// Find the CONFIG object around line 529 and update:
const CONFIG = {
    userPoolId: 'YOUR_USER_POOL_ID',      // Replace with output from Terraform
    clientId: 'YOUR_CLIENT_ID',            // Replace with output from Terraform
    region: 'us-east-1',
    apiUrl: 'http://localhost:8000'
};
```

**Important**: Replace `YOUR_USER_POOL_ID` and `YOUR_CLIENT_ID` with the actual values from Terraform output.

### Step 4: Run Application
```bash
python run.py
```

Application will be available at: **http://localhost:8000**

### Step 5: Create First User
1. Open browser to `http://localhost:8000`
2. Click "Create Account"
3. Fill in registration details
4. Select organization and subscription tier
5. Choose "Admin" role for admin access
6. Verify email with code sent to your email
7. Login and start chatting!

## 🔐 Authentication & Multi-Tenancy

### JWT Token Structure
```json
{
  "sub": "user-uuid",
  "email": "user@company.com",
  "custom:tenant_id": "acme-corp",
  "custom:subscription_tier": "premium",
  "cognito:groups": ["acme-corp-admins"],
  "exp": 1703123456
}
```

### Tenant Isolation
- **Session IDs**: `{tenant_id}-{subscription_tier}-{user_id}-{session_id}`
- **DynamoDB Partitioning**: All data partitioned by tenant_id
- **Bedrock Agent Core Context**: Tenant information passed in session attributes
- **Admin Access**: Cognito Groups for tenant-specific admin privileges

### User Registration Flow
1. **Self-Service Registration**: Users register with tenant and subscription tier selection
2. **Admin Role Selection**: Optional admin role during registration
3. **Email Verification**: Cognito email verification required
4. **Automatic Group Assignment**: Admin users automatically added to `{tenant-id}-admins` group
5. **JWT Generation**: Login generates JWT with tenant context and group membership

## 🤖 Bedrock Agent Core Runtime Integration

### Tenant Context Passing

**The core mechanism**: Tenant context is passed to Bedrock Agent Core Runtime through session attributes at every invocation. This enables:
- **Multi-tenant routing**: Single agent serves multiple organizations
- **Subscription enforcement**: Agent behavior adapts based on tenant's subscription tier
- **Cost attribution**: All traces include tenant_id for accurate billing
- **Data isolation**: Agent maintains separate context per tenant

```python
session_state = {
    "sessionAttributes": {
        "tenant_id": "acme-corp",
        "user_id": "user-123",
        "subscription_tier": "premium",
        "organization_type": "enterprise",
        "user_role": "admin"
    },
    "promptSessionAttributes": {
        "request_type": "agentic_query",
        "enable_planning": "true",
        "tenant_context": "acme-corp enterprise user",
        "cost_tracking": "enabled"
    }
}
```

### Agent Invocation with Observability

```python
response = bedrock_agent_runtime.invoke_agent(
    agentId=AGENT_ID,
    agentAliasId=ALIAS_ID,
    sessionId=f"{tenant_id}-{user_id}-{session_id}",
    inputText=message,
    sessionState=session_state,
    enableTrace=True  # Enable observability traces
)

# Process response and extract traces
for event in response['completion']:
    if 'trace' in event:
        # Capture planning, reasoning, and action traces
        trace_data = event['trace']
        store_trace_for_observability(trace_data, tenant_id, user_id)
```

### Bedrock Agent Core Observability Features

#### Trace Capture
- **Planning Traces**: Agent's step-by-step reasoning process
- **Action Invocations**: Tool calls, API requests, and function executions
- **Knowledge Base Queries**: Retrieval augmented generation (RAG) operations
- **Orchestration Steps**: Multi-step workflow coordination
- **Error Handling**: Failure points and retry logic

#### Cost Attribution Per Tenant

**Critical for Multi-Tenancy**: Every trace and metric includes tenant_id, enabling accurate cost attribution:

```python
# Track costs per tenant and user
await cost_service.track_usage_cost(
    tenant_id=tenant_id,  # Identifies which organization to bill
    user_id=user_id,      # Tracks individual user consumption
    session_id=session_id,
    metric_type="bedrock_input_tokens",
    value=input_tokens,
    model_id=model_id,
    trace_id=trace_id
)
```

**Cost Attribution Flow:**
1. User makes request with JWT containing tenant_id
2. Tenant context passed to Agent Core Runtime
3. Agent processes request and generates traces
4. All traces tagged with tenant_id and user_id
5. Costs automatically calculated and attributed per tenant
6. Admin dashboards show per-tenant and per-user costs

#### Performance Monitoring
- **Response Times**: End-to-end latency per request
- **Token Usage**: Input/output tokens per tenant and user
- **API Call Patterns**: Frequency and distribution of agent invocations
- **Subscription Compliance**: Real-time tier limit enforcement

### Session Management
- **Tenant Isolation**: Each session tied to specific tenant with complete data separation
- **User Tracking**: Individual user sessions within tenants
- **Context Preservation**: Session attributes maintained across conversation turns
- **Trace Storage**: All agent traces stored in DynamoDB for audit and analysis
- **Subscription Limits**: Real-time enforcement of tier-based usage limits

### Multi-Tenant Benefits

**Why pass tenant_id at runtime?**
1. **Cost Efficiency**: One Bedrock Agent Core deployment instead of one per tenant
2. **Simplified Management**: Single agent to maintain and update
3. **Flexible Scaling**: Add new tenants without infrastructure changes
4. **Accurate Billing**: Automatic cost attribution per tenant
5. **Subscription Control**: Different features/limits per tenant tier
6. **Audit Trail**: Complete trace of which tenant accessed what



## 💰 Cost Attribution System

### Why Cost Attribution Matters for Multi-Tenancy

When multiple tenants share the same Bedrock Agent Core Runtime, accurate cost attribution is critical for:
- **Billing**: Charge each tenant for their actual usage
- **Analytics**: Understand which tenants consume most resources
- **Optimization**: Identify cost-saving opportunities per tenant
- **Transparency**: Show customers exactly what they're paying for

### Granular Cost Tracking
- **Per-Tenant Costs**: Complete cost breakdown by tenant (enabled by tenant_id in traces)
- **Per-User Costs**: Individual user consumption within tenants
- **Service-Wise Costs**: Breakdown by Bedrock models, Agent Runtime orchestration, etc.
- **Admin-Only Access**: Cost reports restricted to tenant administrators
- **Real-Time Attribution**: Costs tracked as requests are processed

### Cost Categories
```json
{
  "bedrock_models": {
    "input_tokens": "Varies by model (Claude, Titan, etc.)",
    "output_tokens": "Varies by model (Claude, Titan, etc.)"
  },
  "agent_runtime": {
    "orchestration": "$0.001 per invocation",
    "tool_execution": "$0.0005 per action"
  },
  "observability": {
    "trace_storage": "DynamoDB costs",
    "metrics_tracking": "Included"
  }
}
```

### Admin Cost Reports
- **Overall Tenant Cost**: Total costs with service breakdown (Bedrock models, Agent Runtime, etc.)
- **Per-User Analysis**: Individual user consumption patterns with trace correlation
- **Service-Wise Trends**: Daily usage patterns and peak analysis
- **Trace-Based Attribution**: Cost tracking linked to agent execution traces
- **Comprehensive Reports**: All cost dimensions in single view with observability insights

## 📊 Subscription Tiers & Usage Limits

### Tier Comparison
| Feature | Basic (Free) | Advanced ($29/mo) | Premium ($99/mo) |
|---------|--------------|-------------------|------------------|
| Daily Messages | 50 | 200 | 1,000 |
| Monthly Messages | 1,000 | 5,000 | 25,000 |
| Concurrent Sessions | 1 | 3 | 10 |
| Weather Tools | ❌ | ✅ Basic | ✅ Full |
| Cost Reports | ❌ | ❌ | ✅ Admin |
| Session Duration | 30 min | 60 min | 240 min |

### Usage Enforcement
- **Real-time Limits**: API endpoints check usage before processing
- **Tier-based Features**: MCP tools and admin access controlled by subscription
- **Usage Tracking**: All consumption stored in DynamoDB for billing

## 🔧 API Endpoints

### Authentication Required Endpoints
```bash
# Chat with Bedrock Agent Core
POST /api/chat
Authorization: Bearer <jwt-token>

# Session Management
POST /api/sessions
GET /api/tenants/{tenant_id}/sessions

# Usage & Analytics
GET /api/tenants/{tenant_id}/usage
GET /api/tenants/{tenant_id}/subscription

# Cost Reports (User Level)
GET /api/tenants/{tenant_id}/costs
GET /api/tenants/{tenant_id}/users/{user_id}/costs


```

### Admin-Only Endpoints
```bash
# Granular Cost Attribution (Admin Only)
GET /api/admin/tenants/{tenant_id}/overall-cost
GET /api/admin/tenants/{tenant_id}/per-user-cost
GET /api/admin/tenants/{tenant_id}/service-wise-cost
GET /api/admin/tenants/{tenant_id}/users/{user_id}/service-cost
GET /api/admin/tenants/{tenant_id}/comprehensive-report

# Admin Management
GET /api/admin/my-tenants
POST /api/admin/add-to-group
```

## 🗄️ Data Storage

### DynamoDB Tables

**Sessions Table** (`tenant-sessions`)
```json
{
  "session_key": "acme-corp-premium-user123-uuid",
  "tenant_id": "acme-corp",
  "user_id": "user123",
  "subscription_tier": "premium",
  "created_at": "2024-01-01T00:00:00Z",
  "message_count": 15
}
```

**Usage Metrics Table** (`tenant-usage`)
```json
{
  "tenant_id": "acme-corp",
  "timestamp": "2024-01-01T00:00:00Z",
  "user_id": "user123",
  "metric_type": "bedrock_input_tokens",
  "value": 150,
  "session_id": "uuid",
  "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
  "agent_id": "BAUOKJ4UDH"
}
```

### Supported Bedrock Models

This application supports all AWS Bedrock foundation models including:
- **Anthropic Claude Models**: Claude 3 Haiku, Claude 3 Sonnet, Claude 3.5 Sonnet, Claude 3 Opus, Claude Sonnet 4, Claude Sonnet 4.5
- **Amazon Titan Models**: Titan Text Express, Titan Text Lite, Titan Embeddings
- **AI21 Labs Models**: Jurassic-2 Ultra, Jurassic-2 Mid
- **Cohere Models**: Command, Command Light
- **Meta Models**: Llama 2, Llama 3
- **Stability AI Models**: Stable Diffusion (for image generation)

Configure the model ID in your application based on your use case and cost requirements.

## 🌐 Frontend Features

### User Interface
- **Cognito Registration**: Self-service user registration with tenant selection
- **Admin Role Selection**: Optional admin privileges during signup
- **Real-time Chat**: WebSocket-like chat interface with Bedrock Agent Core
- **Usage Dashboard**: Subscription limits and current usage display
- **Cost Reports**: User-level cost visibility
- **Weather Integration**: Natural language weather queries

### Admin Interface
- **Cost Analytics**: Granular cost reports and trends
- **User Management**: View all tenant users and their consumption
- **Service Analysis**: Breakdown by AWS service usage
- **Comprehensive Reports**: Multi-dimensional cost analysis

## 🔍 Monitoring & Analytics

### Usage Tracking
- **Real-time Metrics**: Every API call, token usage, and service consumption tracked
- **Tenant Analytics**: Aggregated usage patterns per tenant
- **Cost Attribution**: Automatic cost calculation and attribution
- **Performance Monitoring**: Bedrock Agent Core orchestration times, model inference latency, and success rates
- **Trace Analysis**: Complete visibility into agent planning, reasoning, and execution steps

### Trace Analysis
- **Bedrock Agent Core Traces**: Complete orchestration, planning, and reasoning traces
- **Action Execution Traces**: Tool invocations, API calls, and function executions
- **Knowledge Base Traces**: RAG operations and retrieval patterns
- **Performance Traces**: Latency breakdown by orchestration step
- **Session Analytics**: User engagement and session duration patterns
- **Error Traces**: Failure analysis and debugging insights



## 📈 Advanced Features

### Real-Time Weather Integration
- **Live API Data**: OpenWeatherMap real-time weather information
- **Natural Language Processing**: Bedrock Agent Core converts weather data to conversational responses
- **Subscription-Based Access**: Weather tools available based on subscription tier
- **Error Handling**: Graceful fallbacks for API failures

### Cost Optimization
- **Usage-Based Billing**: Pay only for actual consumption
- **Tier-Based Limits**: Prevent runaway costs with subscription limits
- **Admin Visibility**: Complete cost transparency for tenant administrators
- **Service Attribution**: Understand costs by AWS service usage

### Multi-Tenant Architecture
- **Complete Isolation**: No cross-tenant data access possible
- **Scalable Design**: Add new tenants without infrastructure changes
- **Admin Segregation**: Tenant-specific administrative access
- **Usage Analytics**: Per-tenant usage patterns and optimization opportunities

## 🎥 Demo Video

Watch the application in action:

![Demo](Demo.gif)

The demo showcases:
- User registration and authentication with Cognito
- Multi-tenant chat interface with Bedrock Agent Core Runtime
- Real-time weather queries using MCP tools
- Subscription tier management and usage tracking
- Admin cost attribution and analytics dashboards

## 🧹 Cleanup

To remove all AWS resources and avoid charges:

### Destroy Terraform Infrastructure
```bash
cd infra/terraform
terraform destroy
```

This will delete:
- Cognito User Pool and Client
- DynamoDB Tables
- IAM Roles and Policies

### Stop Application
```bash
# Press Ctrl+C in terminal running the application
# Deactivate virtual environment
deactivate
```

## 🛠️ Local Development

```bash
# Start development server
python run.py

# Run with debug logging
DEBUG=true python run.py

# Change Bedrock model (edit app/bedrock_service.py)
# Update MODEL_ID to any supported Bedrock model
# Check AWS Bedrock Console for available models in your region
```

## 📝 Notes

- **Development Only**: Application runs on `localhost:8000` - not production-ready
- **Sample Code**: Use as reference for building your own multi-tenant AI applications
- **Bedrock Pricing**: Varies by model - Claude 3 Haiku (~$0.25/1M input tokens), Sonnet (~$3/1M input tokens)
- **Bedrock Agent Core Runtime**: Additional orchestration costs apply
- **DynamoDB**: On-demand billing (pay per request)
- **Cognito**: Free for first 50,000 monthly active users
- **Data Storage**: All data stored in your AWS account with tenant isolation
- **Model Selection**: Configure model ID in `app/bedrock_service.py`

### Example Model IDs
```python
# Example Bedrock Model IDs (check AWS Bedrock Console for latest versions)
CLAUDE_3_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"
CLAUDE_3_SONNET = "anthropic.claude-3-sonnet-20240229-v1:0"
CLAUDE_3_5_SONNET = "anthropic.claude-3-5-sonnet-20240620-v1:0"
TITAN_TEXT_EXPRESS = "amazon.titan-text-express-v1"
LLAMA_2_13B = "meta.llama2-13b-chat-v1"
COMMAND = "cohere.command-text-v14"
```

## 🎯 Use Cases

This sample code demonstrates patterns for:

### Multi-Tenant SaaS AI Applications
- **Single Agent, Multiple Customers**: One Bedrock Agent Core Runtime serves all organizations
- **Tenant-Specific Experiences**: Personalized responses based on tenant context
- **Subscription Tiers**: Basic, Advanced, Premium with different feature access
- **Usage-Based Billing**: Accurate cost attribution per tenant for invoicing

### Enterprise AI Platforms
- **Department Isolation**: Different departments as separate tenants
- **Cost Center Attribution**: Track AI costs per department/team
- **Role-Based Access**: Admin vs regular user capabilities per tenant
- **Compliance & Audit**: Complete trace of tenant data access

### AI Service Marketplaces
- **White-Label AI**: Same agent, different branding per tenant
- **Flexible Pricing**: Different subscription tiers with usage limits
- **Cost Transparency**: Show customers their exact AI consumption
- **Scalable Onboarding**: Add new customers without infrastructure changes

**Key Advantage**: By passing tenant_id at runtime to Bedrock Agent Core, you can serve unlimited tenants from a single agent deployment while maintaining complete isolation and accurate cost attribution.

Adapt and extend this code for your specific requirements. This is a starting point, not a production-ready solution.