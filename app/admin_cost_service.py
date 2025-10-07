"""
Admin-Only Granular Cost Attribution Service
Provides detailed cost breakdown by tenant, user, and service for admin users only
"""

from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from app.dynamodb_store import DynamoDBStore
from app.models import SubscriptionTier

class AdminCostService:
    """Admin-only granular cost attribution with service-wise breakdown"""
    
    def __init__(self):
        self.dynamodb_store = DynamoDBStore()
        
        # Service-wise pricing
        self.service_pricing = {
            "bedrock_agent": {
                "input_tokens": Decimal("0.00025"),
                "output_tokens": Decimal("0.00125"),
                "invocation": Decimal("0.001")
            },
            "weather_api": {
                "api_call": Decimal("0.0001")
            },
            "mcp_runtime": {
                "tool_execution": Decimal("0.0005")
            },
            "session_management": {
                "session_creation": Decimal("0.0001"),
                "session_maintenance": Decimal("0.00005")
            },
            "authentication": {
                "jwt_validation": Decimal("0.00001"),
                "cognito_operation": Decimal("0.00002")
            }
        }
    
    def is_admin_user(self, user_context: Dict[str, Any]) -> bool:
        """Check if user has admin privileges for their tenant"""
        # Admin users have custom:role = 'admin' in JWT
        return user_context.get("role") == "admin"
    
    async def get_tenant_overall_cost(self, tenant_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """1. Overall Tenant Cost - Admin Only"""
        
        usage_metrics = await self.dynamodb_store.get_tenant_usage_metrics(tenant_id, start_date, end_date)
        
        total_cost = Decimal("0")
        service_costs = {
            "bedrock_agent": Decimal("0"),
            "weather_api": Decimal("0"),
            "mcp_runtime": Decimal("0"),
            "session_management": Decimal("0"),
            "authentication": Decimal("0")
        }
        
        for metric in usage_metrics:
            service_cost = self._calculate_service_cost(metric)
            total_cost += service_cost["amount"]
            service_costs[service_cost["service"]] += service_cost["amount"]
        
        return {
            "tenant_id": tenant_id,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "total_cost": float(total_cost),
            "service_breakdown": {k: float(v) for k, v in service_costs.items()},
            "cost_per_service_percentage": {
                k: float((v / total_cost * 100) if total_cost > 0 else 0) 
                for k, v in service_costs.items()
            }
        }
    
    async def get_tenant_per_user_cost(self, tenant_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """2. Per User Cost - Admin Only"""
        
        usage_metrics = await self.dynamodb_store.get_tenant_usage_metrics(tenant_id, start_date, end_date)
        
        user_costs = {}
        
        for metric in usage_metrics:
            user_id = metric.get("user_id", "unknown")
            if user_id not in user_costs:
                user_costs[user_id] = {
                    "total_cost": Decimal("0"),
                    "service_costs": {
                        "bedrock_agent": Decimal("0"),
                        "weather_api": Decimal("0"),
                        "mcp_runtime": Decimal("0"),
                        "session_management": Decimal("0"),
                        "authentication": Decimal("0")
                    },
                    "usage_stats": {
                        "invocations": 0,
                        "tokens": {"input": 0, "output": 0},
                        "sessions": 0
                    }
                }
            
            service_cost = self._calculate_service_cost(metric)
            user_costs[user_id]["total_cost"] += service_cost["amount"]
            user_costs[user_id]["service_costs"][service_cost["service"]] += service_cost["amount"]
            
            # Update usage stats
            if metric["metric_type"] == "agent_invocation":
                user_costs[user_id]["usage_stats"]["invocations"] += 1
            elif metric["metric_type"] == "bedrock_input_tokens":
                user_costs[user_id]["usage_stats"]["tokens"]["input"] += int(metric["value"])
            elif metric["metric_type"] == "bedrock_output_tokens":
                user_costs[user_id]["usage_stats"]["tokens"]["output"] += int(metric["value"])
        
        return {
            "tenant_id": tenant_id,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "users": {
                user_id: {
                    "total_cost": float(user_data["total_cost"]),
                    "service_costs": {k: float(v) for k, v in user_data["service_costs"].items()},
                    "usage_stats": user_data["usage_stats"]
                }
                for user_id, user_data in user_costs.items()
            }
        }
    
    async def get_tenant_service_wise_cost(self, tenant_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """3. Overall Tenant Service-wise Consumption Cost - Admin Only"""
        
        usage_metrics = await self.dynamodb_store.get_tenant_usage_metrics(tenant_id, start_date, end_date)
        
        service_breakdown = {}
        
        for service in self.service_pricing.keys():
            service_breakdown[service] = {
                "total_cost": Decimal("0"),
                "usage_count": 0,
                "cost_per_unit": {},
                "peak_usage_day": {"date": "", "cost": Decimal("0")},
                "daily_costs": {}
            }
        
        for metric in usage_metrics:
            service_cost = self._calculate_service_cost(metric)
            service = service_cost["service"]
            amount = service_cost["amount"]
            
            service_breakdown[service]["total_cost"] += amount
            service_breakdown[service]["usage_count"] += 1
            
            # Track daily costs
            date_key = metric["timestamp"][:10]
            if date_key not in service_breakdown[service]["daily_costs"]:
                service_breakdown[service]["daily_costs"][date_key] = Decimal("0")
            service_breakdown[service]["daily_costs"][date_key] += amount
            
            # Update peak usage day
            if service_breakdown[service]["daily_costs"][date_key] > service_breakdown[service]["peak_usage_day"]["cost"]:
                service_breakdown[service]["peak_usage_day"] = {
                    "date": date_key,
                    "cost": service_breakdown[service]["daily_costs"][date_key]
                }
        
        return {
            "tenant_id": tenant_id,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "service_breakdown": {
                service: {
                    "total_cost": float(data["total_cost"]),
                    "usage_count": data["usage_count"],
                    "average_cost_per_use": float(data["total_cost"] / data["usage_count"]) if data["usage_count"] > 0 else 0,
                    "peak_usage_day": {
                        "date": data["peak_usage_day"]["date"],
                        "cost": float(data["peak_usage_day"]["cost"])
                    },
                    "daily_trend": {k: float(v) for k, v in data["daily_costs"].items()}
                }
                for service, data in service_breakdown.items()
            }
        }
    
    async def get_user_service_wise_cost(self, tenant_id: str, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """4. User Service-wise Consumption Cost - Admin Only"""
        
        usage_metrics = await self.dynamodb_store.get_tenant_usage_metrics(tenant_id, start_date, end_date)
        user_metrics = [m for m in usage_metrics if m.get("user_id") == user_id]
        
        user_service_breakdown = {}
        
        for service in self.service_pricing.keys():
            user_service_breakdown[service] = {
                "total_cost": Decimal("0"),
                "usage_count": 0,
                "hourly_usage": {},
                "session_costs": {}
            }
        
        for metric in user_metrics:
            service_cost = self._calculate_service_cost(metric)
            service = service_cost["service"]
            amount = service_cost["amount"]
            
            user_service_breakdown[service]["total_cost"] += amount
            user_service_breakdown[service]["usage_count"] += 1
            
            # Track hourly usage
            hour_key = metric["timestamp"][:13]  # YYYY-MM-DDTHH
            if hour_key not in user_service_breakdown[service]["hourly_usage"]:
                user_service_breakdown[service]["hourly_usage"][hour_key] = Decimal("0")
            user_service_breakdown[service]["hourly_usage"][hour_key] += amount
            
            # Track session costs
            session_id = metric.get("session_id", "unknown")
            if session_id not in user_service_breakdown[service]["session_costs"]:
                user_service_breakdown[service]["session_costs"][session_id] = Decimal("0")
            user_service_breakdown[service]["session_costs"][session_id] += amount
        
        return {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "user_service_breakdown": {
                service: {
                    "total_cost": float(data["total_cost"]),
                    "usage_count": data["usage_count"],
                    "cost_per_hour": {k: float(v) for k, v in data["hourly_usage"].items()},
                    "cost_per_session": {k: float(v) for k, v in data["session_costs"].items()},
                    "average_cost_per_use": float(data["total_cost"] / data["usage_count"]) if data["usage_count"] > 0 else 0
                }
                for service, data in user_service_breakdown.items()
            }
        }
    
    def _calculate_service_cost(self, metric: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate cost for a specific metric and determine service"""
        
        metric_type = metric["metric_type"]
        value = Decimal(str(metric["value"]))
        
        if metric_type == "bedrock_input_tokens":
            return {
                "service": "bedrock_agent",
                "amount": (value / 1000) * self.service_pricing["bedrock_agent"]["input_tokens"]
            }
        elif metric_type == "bedrock_output_tokens":
            return {
                "service": "bedrock_agent", 
                "amount": (value / 1000) * self.service_pricing["bedrock_agent"]["output_tokens"]
            }
        elif metric_type == "agent_invocation":
            return {
                "service": "bedrock_agent",
                "amount": self.service_pricing["bedrock_agent"]["invocation"]
            }
        elif metric_type == "weather_api_call":
            return {
                "service": "weather_api",
                "amount": self.service_pricing["weather_api"]["api_call"]
            }
        elif metric_type == "mcp_tool_execution":
            return {
                "service": "mcp_runtime",
                "amount": self.service_pricing["mcp_runtime"]["tool_execution"]
            }
        elif metric_type == "session_creation":
            return {
                "service": "session_management",
                "amount": self.service_pricing["session_management"]["session_creation"]
            }
        elif metric_type == "jwt_validation":
            return {
                "service": "authentication",
                "amount": self.service_pricing["authentication"]["jwt_validation"]
            }
        else:
            return {
                "service": "session_management",
                "amount": self.service_pricing["session_management"]["session_maintenance"]
            }
    
    async def generate_comprehensive_admin_report(self, tenant_id: str, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive admin cost report with all 4 breakdowns"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get all 4 cost breakdowns
        overall_cost = await self.get_tenant_overall_cost(tenant_id, start_date, end_date)
        per_user_cost = await self.get_tenant_per_user_cost(tenant_id, start_date, end_date)
        service_wise_cost = await self.get_tenant_service_wise_cost(tenant_id, start_date, end_date)
        
        # Get top users by cost
        top_users = sorted(
            per_user_cost["users"].items(),
            key=lambda x: x[1]["total_cost"],
            reverse=True
        )[:5]
        
        return {
            "report_type": "comprehensive_admin_cost_report",
            "tenant_id": tenant_id,
            "generated_at": datetime.now().isoformat(),
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat(), "days": days},
            "summary": {
                "total_tenant_cost": overall_cost["total_cost"],
                "total_users": len(per_user_cost["users"]),
                "highest_cost_service": max(overall_cost["service_breakdown"].items(), key=lambda x: x[1])[0],
                "most_expensive_user": top_users[0][0] if top_users else "none"
            },
            "1_overall_tenant_cost": overall_cost,
            "2_per_user_costs": per_user_cost,
            "3_service_wise_costs": service_wise_cost,
            "4_top_users_by_cost": {user_id: user_data for user_id, user_data in top_users}
        }