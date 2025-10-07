# Multi-Tenant AWS Bedrock Agent Core Application

A production-ready multi-tenant chat application using **AWS Bedrock Agent Core Runtime** with **Claude 3 Haiku**, **Cognito JWT authentication**, **DynamoDB session storage**, **real-time weather MCP integration**, and **granular cost attribution**.

## 🏗️ Architecture Overview

### Core Components
- **AWS Bedrock Agent Core Runtime**: Advanced AI agent with planning, reasoning, and tool execution
- **Multi-Tenant Authentication**: Cognito JWT with tenant isolation and admin role management
- **Session Management**: DynamoDB-based persistent sessions with tenant-specific isolation
- **MCP Integration**: Model Context Protocol for real-time weather data via OpenWeatherMap API
- **Cost Attribution**: Granular cost tracking per tenant, user, and service with admin-only access
- **Subscription Tiers**: Basic, Advanced, Premium with usage limits and feature access control

### Agent Core Runtime Integration
```
JWT Token → Tenant Context → Session Attributes → Agent Core Runtime → Natural Response
```

**Session ID Format**: `{tenant_id}-{user_id}-{session_id}`
**Session Attributes**: Tenant context, subscription tier, and user preferences passed to Agent Core
**Trace Analysis**: Complete orchestration, planning, and reasoning trace capture

## 📋 Prerequisites

### AWS Services Required
- **AWS Bedrock**: Claude 3 Haiku model access
- **Amazon Cognito**: User Pool with custom attributes
- **Amazon DynamoDB**: Two tables for sessions and usage metrics
- **AWS IAM**: Proper permissions for Bedrock, Cognito, and DynamoDB

### External APIs
- **OpenWeatherMap API**: Free tier account for real-time weather data
  - Sign up: https://openweathermap.org/api
  - Get API key from dashboard

### Development Environment
- **Python 3.11+**
- **Node.js 18+** (for CDK deployment)
- **AWS CLI** configured with appropriate permissions
- **Git** for version control

## 🚀 Quick Deployment

### 1. Clone and Setup
```bash
git clone <repository-url>
cd Agent-Core
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your values:
COGNITO_USER_POOL_ID=your-cognito-user-pool-id
COGNITO_CLIENT_ID=your-cognito-client-id
BEDROCK_AGENT_ID=your-bedrock-agent-id
OPENWEATHER_API_KEY=your-openweathermap-api-key
SESSIONS_TABLE=tenant-sessions
USAGE_TABLE=tenant-usage
AWS_REGION=us-east-1
```

### 3. Deploy Infrastructure

**Option A: CDK (Recommended)**
```bash
cd infra/cdk
npm install -g aws-cdk
pip install -r requirements.txt
cdk bootstrap
cdk deploy
```

**Option B: Terraform**
```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

### 4. Setup Weather API
```bash
# Interactive setup for OpenWeatherMap API
python scripts/setup_weather_api.py
```

### 5. Run Application
```bash
python run.py
```

Visit: **http://localhost:8000**

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
- **Agent Core Context**: Tenant information passed in session attributes
- **Admin Access**: Cognito Groups for tenant-specific admin privileges

### User Registration Flow
1. **Self-Service Registration**: Users register with tenant and subscription tier selection
2. **Admin Role Selection**: Optional admin role during registration
3. **Email Verification**: Cognito email verification required
4. **Automatic Group Assignment**: Admin users automatically added to `{tenant-id}-admins` group
5. **JWT Generation**: Login generates JWT with tenant context and group membership

## 🤖 Agent Core Runtime Integration

### Session State Management
```python
session_state = {
    "sessionAttributes": {
        "tenant_id": "acme-corp",
        "user_id": "user-123",
        "subscription_tier": "premium",
        "organization_type": "enterprise"
    },
    "promptSessionAttributes": {
        "request_type": "agentic_query",
        "enable_planning": "true",
        "tenant_context": "acme-corp enterprise user"
    }
}
```

### Agent Invocation
```python
response = bedrock_agent_runtime.invoke_agent(
    agentId=AGENT_ID,
    agentAliasId=ALIAS_ID,
    sessionId=f"{tenant_id}-{user_id}-{session_id}",
    inputText=message,
    sessionState=session_state,
    enableTrace=True
)
```

### Trace Analysis
- **Planning Steps**: Agent reasoning and decision-making process
- **Action Calls**: Tool and function executions
- **Knowledge Queries**: Knowledge base retrievals
- **Reasoning Chain**: Step-by-step thought process

## 🌤️ Model Context Protocol (MCP) Integration

### Real-Time Weather Data
- **OpenWeatherMap Integration**: Live weather API calls
- **MCP Server Architecture**: Weather tools as MCP servers
- **Agent Core Processing**: Weather data passed to Agent Core for natural language responses

### Weather Tools by Subscription Tier
```json
{
  "basic": [],
  "advanced": ["get_current_weather", "get_weather_forecast"],
  "premium": ["get_current_weather", "get_weather_forecast", "get_weather_alerts"]
}
```

### MCP-Agent Core Flow
```
User Query → MCP Detection → Weather API → Structured Data → Agent Core → Natural Response
```

**Example**:
- User: "What's the weather in London?"
- MCP: Calls OpenWeatherMap API for London weather
- Agent Core: Processes real weather data and generates conversational response
- Response: "The weather in London is currently 15°C with cloudy skies..."

## 💰 Cost Attribution System

### Granular Cost Tracking
- **Per-Tenant Costs**: Complete cost breakdown by tenant
- **Per-User Costs**: Individual user consumption within tenants
- **Service-Wise Costs**: Breakdown by Bedrock, Weather API, MCP Runtime, etc.
- **Admin-Only Access**: Cost reports restricted to tenant administrators

### Cost Categories
```json
{
  "bedrock_agent": {
    "input_tokens": "$0.25 per 1K tokens",
    "output_tokens": "$1.25 per 1K tokens",
    "invocation": "$0.001 per call"
  },
  "weather_api": {
    "api_call": "$0.0001 per call"
  },
  "mcp_runtime": {
    "tool_execution": "$0.0005 per execution"
  }
}
```

### Admin Cost Reports
- **Overall Tenant Cost**: Total costs with service breakdown
- **Per-User Analysis**: Individual user consumption patterns
- **Service-Wise Trends**: Daily usage patterns and peak analysis
- **Comprehensive Reports**: All cost dimensions in single view

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
# Chat with Agent Core
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

# MCP Weather Tools
GET /api/mcp/weather/tools
POST /api/mcp/weather/{tool_name}
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
  "model_id": "anthropic.claude-3-haiku-20240307-v1:0"
}
```

## 🌐 Frontend Features

### User Interface
- **Cognito Registration**: Self-service user registration with tenant selection
- **Admin Role Selection**: Optional admin privileges during signup
- **Real-time Chat**: WebSocket-like chat interface with Agent Core
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
- **Performance Monitoring**: Agent Core response times and success rates

### Trace Analysis
- **Agent Core Traces**: Complete orchestration and reasoning traces
- **MCP Integration Traces**: Weather API call success/failure tracking
- **Session Analytics**: User engagement and session duration patterns

## 🚀 Production Considerations

### Security
- ✅ **JWT Authentication**: Cognito-managed tokens with tenant isolation
- ✅ **Admin Access Control**: Cognito Groups for role-based access
- ✅ **API Rate Limiting**: Subscription-based usage enforcement
- ✅ **Cross-Tenant Prevention**: Complete data isolation

### Scalability
- ✅ **DynamoDB Auto-scaling**: Automatic capacity management
- ✅ **Stateless Architecture**: Horizontal scaling capability
- ✅ **Agent Core Runtime**: AWS-managed scaling and availability
- ✅ **Multi-Region Support**: Deploy across AWS regions

### Reliability
- ✅ **Error Handling**: Graceful degradation and retry logic
- ✅ **Session Persistence**: DynamoDB-backed session storage
- ✅ **Trace Logging**: Complete audit trail for debugging
- ✅ **Health Monitoring**: Application and service health checks

## 📈 Advanced Features

### Real-Time Weather Integration
- **Live API Data**: OpenWeatherMap real-time weather information
- **Natural Language Processing**: Agent Core converts weather data to conversational responses
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

## 🛠️ Development & Deployment

### Local Development
```bash
# Start development server
python run.py

# Run with debug logging
DEBUG=true python run.py

# Test weather API integration
python scripts/setup_weather_api.py
```

### Production Deployment
```bash
# Deploy infrastructure
cd infra/cdk && cdk deploy

# Configure environment variables in production
# Deploy application code
# Configure monitoring and alerting
```

### Testing
```bash
# Create test users
python scripts/create_test_users_with_tiers.py

# Test admin functionality
# Register user with admin role
# Verify cost reports access
```

This application provides a complete, production-ready multi-tenant AI chat system with advanced cost attribution, real-time integrations, and enterprise-grade security using AWS Bedrock Agent Core Runtime.