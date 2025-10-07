# Multi-Tenant Bedrock Chat Application

A production-ready multi-tenant chat application using AWS Bedrock Agent Core services with **Claude 3.5 Sonnet**, **Cognito JWT authentication**, and **DynamoDB session storage**.

## 🏗️ Architecture

- **Tenant Isolation**: JWT-based authentication with tenant context
- **Bedrock Integration**: Claude 3.5 Sonnet with Agent Core Runtime API
- **Session Storage**: DynamoDB for persistent session management
- **Authentication**: Cognito User Pool with custom tenant attributes
- **Usage Tracking**: Tenant-specific metrics in DynamoDB

## 🚀 Quick Deployment Steps

### 1. Deploy Infrastructure

**Option A: Using CDK**
```bash
cd infra/cdk
pip install -r requirements.txt
cdk bootstrap
cdk deploy
```

**Option B: Using Terraform**
```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

**Option C: Automated Script**
```bash
./scripts/deploy_infra.sh
```

### 2. Create Test Users
```bash
# Set environment variables from deployment outputs
export COGNITO_USER_POOL_ID="your-pool-id"
export COGNITO_CLIENT_ID="your-client-id"

# Create test users with JWT tokens
python scripts/create_test_user.py
```

### 3. Run Application
```bash
pip install -r requirements.txt
python run.py
```

Visit: http://localhost:8000

## 🔐 Authentication Flow

### JWT Token Structure
```json
{
  "sub": "tenant1-user1",
  "email": "tenant1-user1@example.com", 
  "tenant_id": "tenant-001",
  "exp": 1234567890
}
```

### API Authentication
All endpoints require `Authorization: Bearer <jwt-token>` header.

## 📋 API Endpoints

### Create Session (Authenticated)
```bash
POST /api/sessions
Authorization: Bearer <jwt-token>
```

### Send Chat Message (Authenticated)
```bash
POST /api/chat
Authorization: Bearer <jwt-token>
Content-Type: application/json

{
  "message": "Hello, how can you help?",
  "tenant_context": {
    "tenant_id": "tenant-001",
    "user_id": "user-001", 
    "session_id": "session-uuid"
  }
}
```

### Get Tenant Usage (Authenticated)
```bash
GET /api/tenants/{tenant_id}/usage
Authorization: Bearer <jwt-token>
```

## 🔍 Session Storage (DynamoDB)

### Sessions Table Structure
```json
{
  "session_key": "tenant-001-user-001-uuid",
  "tenant_id": "tenant-001",
  "user_id": "user-001", 
  "session_id": "uuid",
  "created_at": "2024-01-01T00:00:00Z",
  "last_activity": "2024-01-01T00:05:00Z",
  "message_count": 5
}
```

### Usage Metrics Table Structure
```json
{
  "tenant_id": "tenant-001",
  "timestamp": "2024-01-01T00:00:00Z",
  "metric_type": "agent_invocation",
  "value": 1.0,
  "session_id": "uuid",
  "agent_id": "agent-123"
}
```

## 🤖 Claude 3 Haiku Integration

### Model Configuration
- **Model ID**: `anthropic.claude-3-haiku-20240307-v1:0`
- **Agent Core Runtime**: AWS Bedrock Agent Core API integration
- **Tenant Context**: Injected into session attributes for tenant-aware responses

### Usage Tracking
```json
{
  "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
  "input_tokens": 150,
  "output_tokens": 300,
  "invocation_time": "2024-01-01T00:00:00Z"
}
```

## 🌤️ Real-Time Weather MCP Integration

### OpenWeatherMap API Integration
- **Real-time Data**: Live weather data from OpenWeatherMap API
- **MCP Architecture**: Weather tools integrated as Model Context Protocol servers
- **Agent Core Integration**: Weather data passed to Agent Core runtime for natural responses

### Weather Tools Available
```json
{
  "basic_tier": [],
  "advanced_tier": ["get_current_weather", "get_weather_forecast"],
  "premium_tier": ["get_current_weather", "get_weather_forecast", "get_weather_alerts"]
}
```

### Setup Weather API
```bash
# Get free API key from https://openweathermap.org/api
python scripts/setup_weather_api.py

# Or manually set in .env
OPENWEATHER_API_KEY=your-api-key
```

### Weather Query Examples
- "What's the weather in London?"
- "Show me the 5-day forecast for Tokyo"
- "Any weather alerts for New York?"
- "How's the weather in Paris tomorrow?"

## 🏢 Multi-Tenant Features

### Tenant Isolation
- JWT-based authentication with tenant validation
- DynamoDB partition keys include tenant ID
- Session IDs: `{tenant_id}-{user_id}-{session_id}`

### Cognito Integration
- Custom attribute: `custom:tenant_id`
- Email-based authentication
- JWT token generation with tenant context

### Security
- All endpoints require valid JWT tokens
- Tenant context validation on every request
- Cross-tenant access prevention

## 🧪 Testing Multi-Tenancy

### 1. Get JWT Tokens
```bash
python scripts/create_test_user.py
# Copy JWT tokens from output
```

### 2. Test in Web Interface
1. Visit http://localhost:8000
2. Paste JWT token in "JWT Token" field
3. Click "Set Auth" then "Create Session"
4. Send messages and verify tenant isolation

### 3. Test Different Tenants
Use different JWT tokens to verify complete isolation between tenants.

## 📊 Infrastructure Components

### AWS Services Used
- **Amazon Bedrock**: Claude 3.5 Sonnet model
- **Amazon Cognito**: User authentication with custom attributes
- **Amazon DynamoDB**: Session and usage metrics storage
- **AWS IAM**: Role-based access control

### CDK Stack Outputs
- `UserPoolId`: Cognito User Pool ID
- `UserPoolClientId`: Cognito Client ID  
- `SessionsTableName`: DynamoDB sessions table
- `UsageTableName`: DynamoDB usage metrics table

## 🔧 Configuration

### Environment Variables
```bash
# Cognito (Required)
COGNITO_USER_POOL_ID=your-pool-id
COGNITO_CLIENT_ID=your-client-id

# DynamoDB (Required)
SESSIONS_TABLE=tenant-sessions
USAGE_TABLE=tenant-usage

# Bedrock (Optional - uses Claude 3 Haiku directly)
BEDROCK_AGENT_ID=your-agent-id
AWS_REGION=us-east-1

# Security
JWT_SECRET=your-secret-key

# Real-time Weather API (Required for MCP Weather Tools)
OPENWEATHER_API_KEY=your-openweathermap-api-key
```

## 📈 Production Considerations

### Security
- ✅ JWT authentication with Cognito
- ✅ Tenant context validation
- ✅ IAM role-based permissions
- ✅ Cross-tenant access prevention

### Storage
- ✅ DynamoDB for persistent sessions
- ✅ Usage metrics with time-series data
- ✅ Point-in-time recovery enabled

### Monitoring
- ✅ Bedrock usage metrics per tenant
- ✅ Session activity tracking
- ✅ Error handling and logging

### Scaling
- ✅ DynamoDB auto-scaling
- ✅ Stateless application design
- ✅ JWT-based authentication (no server sessions)

This implementation provides a complete, production-ready multi-tenant chat application with proper authentication, persistent storage, and comprehensive usage tracking using AWS Bedrock Agent Core services.