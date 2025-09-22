#!/usr/bin/env python3
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (
    Stack,
    aws_dynamodb as dynamodb,
    aws_cognito as cognito,
    aws_iam as iam,
    aws_lambda as lambda_,
    CfnOutput,
    RemovalPolicy
)

class MultiTenantBedrockStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # DynamoDB Tables for Session Storage
        self.sessions_table = dynamodb.Table(
            self, "TenantSessions",
            table_name="tenant-sessions",
            partition_key=dynamodb.Attribute(name="session_key", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=True
        )

        self.usage_table = dynamodb.Table(
            self, "TenantUsage",
            table_name="tenant-usage",
            partition_key=dynamodb.Attribute(name="tenant_id", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="timestamp", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Cognito User Pool for Authentication
        self.user_pool = cognito.UserPool(
            self, "MultiTenantUserPool",
            user_pool_name="multi-tenant-chat-users",
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
                given_name=cognito.StandardAttribute(required=True, mutable=True),
                family_name=cognito.StandardAttribute(required=True, mutable=True)
            ),
            custom_attributes={
                "tenant_id": cognito.StringAttribute(min_len=1, max_len=50, mutable=True)
            },
            removal_policy=RemovalPolicy.DESTROY
        )

        # Cognito User Pool Client
        self.user_pool_client = cognito.UserPoolClient(
            self, "MultiTenantUserPoolClient",
            user_pool=self.user_pool,
            user_pool_client_name="multi-tenant-chat-client",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
                admin_user_password=True
            ),
            generate_secret=False,
            access_token_validity=cdk.Duration.hours(1),
            id_token_validity=cdk.Duration.hours(1),
            refresh_token_validity=cdk.Duration.days(30)
        )

        # IAM Role for Bedrock Agent
        self.bedrock_role = iam.Role(
            self, "BedrockAgentRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess")
            ]
        )

        # IAM Role for Application
        self.app_role = iam.Role(
            self, "AppExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Grant DynamoDB permissions
        self.sessions_table.grant_read_write_data(self.app_role)
        self.usage_table.grant_read_write_data(self.app_role)

        # Grant Bedrock permissions
        self.app_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeAgent",
                    "bedrock:InvokeModel",
                    "bedrock:GetAgent",
                    "bedrock:ListAgents"
                ],
                resources=["*"]
            )
        )

        # Grant Cognito permissions
        self.app_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cognito-idp:GetUser",
                    "cognito-idp:AdminGetUser"
                ],
                resources=[self.user_pool.user_pool_arn]
            )
        )

        # Note: Bedrock Agents will be created manually or via AWS CLI
        # CDK doesn't have native Bedrock Agent support yet
        
        # Outputs
        # Outputs
        CfnOutput(self, "UserPoolId", value=self.user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=self.user_pool_client.user_pool_client_id)
        CfnOutput(self, "SessionsTableName", value=self.sessions_table.table_name)
        CfnOutput(self, "UsageTableName", value=self.usage_table.table_name)
        CfnOutput(self, "AppRoleArn", value=self.app_role.role_arn)
        CfnOutput(self, "AgentId", value="manual-agent-setup-required")

app = cdk.App()
MultiTenantBedrockStack(app, "MultiTenantBedrockStack")
app.synth()