"""
Cost Attribution Service for Multi-Tenant Bedrock Usage
Calculates costs per tenant and user based on consumption metrics
"""

from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import boto3
from app.dynamodb_store import DynamoDBStore
from app.models import SubscriptionTier

class CostAttributionService:
    """Calculate and track costs per tenant and user"""
    
    def __init__(self):
        self.dynamodb_store = DynamoDBStore()
        
        # AWS Bedrock pricing (per 1K tokens)
        self.bedrock_pricing = {
            "anthropic.claude-3-haiku-20240307-v1:0": {
                "input_tokens": Decimal("0.00025"),   # $0.25 per 1K input tokens
                "output_tokens": Decimal("0.00125")   # $1.25 per 1K output tokens
            }
        }
        
        # Weather API costs (OpenWeatherMap)
        self.weather_api_cost = Decimal("0.0001")  # $0.0001 per API call
        
        # Agent Core runtime overhead
        self.agent_runtime_cost = Decimal("0.001")  # $0.001 per invocation

    async def calculate_tenant_costs(self, tenant_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Calculate total costs for a tenant within date range"""
        
        # Get all usage metrics for tenant
        usage_metrics = await self.dynamodb_store.get_tenant_usage_metrics(
            tenant_id, start_date, end_date
        )
        
        total_cost = Decimal("0")
        cost_breakdown = {
            "bedrock_costs": Decimal("0"),
            "weather_api_costs": Decimal("0"),
            "agent_runtime_costs": Decimal("0"),
            "total_invocations": 0,
            "total_tokens": {"input": 0, "output": 0},
            "users": {}
        }
        
        for metric in usage_metrics:
            user_id = metric.get("user_id", "unknown")
            metric_type = metric["metric_type"]
            value = Decimal(str(metric["value"]))
            
            # Initialize user costs if not exists
            if user_id not in cost_breakdown["users"]:
                cost_breakdown["users"][user_id] = {
                    "bedrock_cost": Decimal("0"),
                    "weather_api_cost": Decimal("0"),
                    "agent_runtime_cost": Decimal("0"),
                    "total_cost": Decimal("0"),
                    "invocations": 0,
                    "tokens": {"input": 0, "output": 0}
                }
            
            user_costs = cost_breakdown["users"][user_id]
            
            # Calculate costs based on metric type
            if metric_type == "bedrock_input_tokens":
                model_id = metric.get("model_id", "anthropic.claude-3-haiku-20240307-v1:0")
                token_cost = (value / 1000) * self.bedrock_pricing[model_id]["input_tokens"]
                cost_breakdown["bedrock_costs"] += token_cost
                user_costs["bedrock_cost"] += token_cost
                user_costs["tokens"]["input"] += int(value)
                cost_breakdown["total_tokens"]["input"] += int(value)
                
            elif metric_type == "bedrock_output_tokens":
                model_id = metric.get("model_id", "anthropic.claude-3-haiku-20240307-v1:0")
                token_cost = (value / 1000) * self.bedrock_pricing[model_id]["output_tokens"]
                cost_breakdown["bedrock_costs"] += token_cost
                user_costs["bedrock_cost"] += token_cost
                user_costs["tokens"]["output"] += int(value)
                cost_breakdown["total_tokens"]["output"] += int(value)
                
            elif metric_type == "weather_api_call":
                api_cost = self.weather_api_cost
                cost_breakdown["weather_api_costs"] += api_cost
                user_costs["weather_api_cost"] += api_cost
                
            elif metric_type == "agent_invocation":
                runtime_cost = self.agent_runtime_cost
                cost_breakdown["agent_runtime_costs"] += runtime_cost
                user_costs["agent_runtime_cost"] += runtime_cost
                user_costs["invocations"] += 1
                cost_breakdown["total_invocations"] += 1
            
            # Update user total cost
            user_costs["total_cost"] = (
                user_costs["bedrock_cost"] + 
                user_costs["weather_api_cost"] + 
                user_costs["agent_runtime_cost"]
            )
        
        # Calculate total cost
        total_cost = (
            cost_breakdown["bedrock_costs"] + 
            cost_breakdown["weather_api_costs"] + 
            cost_breakdown["agent_runtime_costs"]
        )
        
        return {
            "tenant_id": tenant_id,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "total_cost": float(total_cost),
            "cost_breakdown": {
                "bedrock_costs": float(cost_breakdown["bedrock_costs"]),
                "weather_api_costs": float(cost_breakdown["weather_api_costs"]),
                "agent_runtime_costs": float(cost_breakdown["agent_runtime_costs"]),
                "total_invocations": cost_breakdown["total_invocations"],
                "total_tokens": cost_breakdown["total_tokens"]
            },
            "users": {
                user_id: {
                    "bedrock_cost": float(user_data["bedrock_cost"]),
                    "weather_api_cost": float(user_data["weather_api_cost"]),
                    "agent_runtime_cost": float(user_data["agent_runtime_cost"]),
                    "total_cost": float(user_data["total_cost"]),
                    "invocations": user_data["invocations"],
                    "tokens": user_data["tokens"]
                }
                for user_id, user_data in cost_breakdown["users"].items()
            }
        }

    async def calculate_user_costs(self, tenant_id: str, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Calculate costs for a specific user"""
        
        tenant_costs = await self.calculate_tenant_costs(tenant_id, start_date, end_date)
        user_costs = tenant_costs["users"].get(user_id, {
            "bedrock_cost": 0.0,
            "weather_api_cost": 0.0,
            "agent_runtime_cost": 0.0,
            "total_cost": 0.0,
            "invocations": 0,
            "tokens": {"input": 0, "output": 0}
        })
        
        return {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            **user_costs
        }

    async def generate_cost_report(self, tenant_id: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive cost report"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        if tenant_id:
            # Single tenant report
            tenant_costs = await self.calculate_tenant_costs(tenant_id, start_date, end_date)
            return {
                "report_type": "single_tenant",
                "generated_at": datetime.now().isoformat(),
                "tenant_costs": tenant_costs
            }
        else:
            # Multi-tenant report
            all_tenants = await self.dynamodb_store.get_all_tenants()
            tenant_reports = []
            
            total_platform_cost = Decimal("0")
            
            for tenant in all_tenants:
                tenant_costs = await self.calculate_tenant_costs(tenant["tenant_id"], start_date, end_date)
                tenant_reports.append(tenant_costs)
                total_platform_cost += Decimal(str(tenant_costs["total_cost"]))
            
            return {
                "report_type": "multi_tenant",
                "generated_at": datetime.now().isoformat(),
                "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "total_platform_cost": float(total_platform_cost),
                "tenant_count": len(tenant_reports),
                "tenants": tenant_reports
            }

    async def track_usage_cost(self, tenant_id: str, user_id: str, session_id: str, 
                             metric_type: str, value: float, **metadata) -> None:
        """Track usage and calculate real-time cost"""
        
        # Store usage metric
        await self.dynamodb_store.store_usage_metric(
            tenant_id, user_id, session_id, metric_type, value, **metadata
        )
        
        # Calculate and store cost attribution
        cost = Decimal("0")
        
        if metric_type == "bedrock_input_tokens":
            model_id = metadata.get("model_id", "anthropic.claude-3-haiku-20240307-v1:0")
            cost = (Decimal(str(value)) / 1000) * self.bedrock_pricing[model_id]["input_tokens"]
            
        elif metric_type == "bedrock_output_tokens":
            model_id = metadata.get("model_id", "anthropic.claude-3-haiku-20240307-v1:0")
            cost = (Decimal(str(value)) / 1000) * self.bedrock_pricing[model_id]["output_tokens"]
            
        elif metric_type == "weather_api_call":
            cost = self.weather_api_cost
            
        elif metric_type == "agent_invocation":
            cost = self.agent_runtime_cost
        
        # Store cost attribution
        if cost > 0:
            await self.dynamodb_store.store_usage_metric(
                tenant_id, user_id, session_id, f"{metric_type}_cost", float(cost),
                original_metric=metric_type, **metadata
            )

    async def get_subscription_tier_costs(self, tier: SubscriptionTier, days: int = 30) -> Dict[str, Any]:
        """Get cost breakdown by subscription tier"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get all tenants with this tier
        tenants_by_tier = await self.dynamodb_store.get_tenants_by_tier(tier)
        
        total_cost = Decimal("0")
        tenant_count = 0
        
        tier_breakdown = {
            "bedrock_costs": Decimal("0"),
            "weather_api_costs": Decimal("0"),
            "agent_runtime_costs": Decimal("0"),
            "total_invocations": 0,
            "total_tokens": {"input": 0, "output": 0}
        }
        
        for tenant in tenants_by_tier:
            tenant_costs = await self.calculate_tenant_costs(tenant["tenant_id"], start_date, end_date)
            total_cost += Decimal(str(tenant_costs["total_cost"]))
            tenant_count += 1
            
            # Aggregate tier breakdown
            breakdown = tenant_costs["cost_breakdown"]
            tier_breakdown["bedrock_costs"] += Decimal(str(breakdown["bedrock_costs"]))
            tier_breakdown["weather_api_costs"] += Decimal(str(breakdown["weather_api_costs"]))
            tier_breakdown["agent_runtime_costs"] += Decimal(str(breakdown["agent_runtime_costs"]))
            tier_breakdown["total_invocations"] += breakdown["total_invocations"]
            tier_breakdown["total_tokens"]["input"] += breakdown["total_tokens"]["input"]
            tier_breakdown["total_tokens"]["output"] += breakdown["total_tokens"]["output"]
        
        avg_cost_per_tenant = total_cost / tenant_count if tenant_count > 0 else Decimal("0")
        
        return {
            "subscription_tier": tier.value,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "tenant_count": tenant_count,
            "total_cost": float(total_cost),
            "average_cost_per_tenant": float(avg_cost_per_tenant),
            "cost_breakdown": {
                "bedrock_costs": float(tier_breakdown["bedrock_costs"]),
                "weather_api_costs": float(tier_breakdown["weather_api_costs"]),
                "agent_runtime_costs": float(tier_breakdown["agent_runtime_costs"]),
                "total_invocations": tier_breakdown["total_invocations"],
                "total_tokens": tier_breakdown["total_tokens"]
            }
        }