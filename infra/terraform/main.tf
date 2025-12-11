terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

# KMS Key for DynamoDB Encryption
resource "aws_kms_key" "dynamodb_key" {
  description             = "KMS key for DynamoDB table encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  tags = {
    Name        = "DynamoDB-Encryption-Key"
    Environment = var.environment
  }
}

resource "aws_kms_alias" "dynamodb_key_alias" {
  name          = "alias/dynamodb-encryption"
  target_key_id = aws_kms_key.dynamodb_key.key_id
}

# DynamoDB Tables
resource "aws_dynamodb_table" "tenant_sessions" {
  name           = "tenant-sessions"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "session_key"

  attribute {
    name = "session_key"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.dynamodb_key.arn
  }

  tags = {
    Name = "TenantSessions"
    Environment = var.environment
  }
}

resource "aws_dynamodb_table" "tenant_usage" {
  name           = "tenant-usage"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "tenant_id"
  range_key      = "timestamp"

  attribute {
    name = "tenant_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.dynamodb_key.arn
  }

  tags = {
    Name = "TenantUsage"
    Environment = var.environment
  }
}

# Cognito User Pool
resource "aws_cognito_user_pool" "multi_tenant_pool" {
  name = "multi-tenant-chat-users"

  username_attributes = ["email"]
  auto_verified_attributes = ["email"]

  schema {
    attribute_data_type = "String"
    name               = "email"
    required           = true
    mutable           = true
  }

  schema {
    attribute_data_type = "String"
    name               = "tenant_id"
    required           = false
    mutable           = true
  }

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }
}

# Cognito User Pool Client
resource "aws_cognito_user_pool_client" "multi_tenant_client" {
  name         = "multi-tenant-chat-client"
  user_pool_id = aws_cognito_user_pool.multi_tenant_pool.id

  generate_secret = false
  
  explicit_auth_flows = [
    "ADMIN_NO_SRP_AUTH",
    "USER_PASSWORD_AUTH",
    "USER_SRP_AUTH"
  ]

  access_token_validity  = 60
  id_token_validity     = 60
  refresh_token_validity = 43200

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "minutes"
  }
}

# IAM Role for Application
resource "aws_iam_role" "app_role" {
  name = "multi-tenant-app-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for DynamoDB
resource "aws_iam_role_policy" "dynamodb_policy" {
  name = "dynamodb-access"
  role = aws_iam_role.app_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.tenant_sessions.arn,
          aws_dynamodb_table.tenant_usage.arn
        ]
      }
    ]
  })
}

# IAM Policy for Bedrock
resource "aws_iam_role_policy" "bedrock_policy" {
  name = "bedrock-access"
  role = aws_iam_role.app_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeAgent",
          "bedrock:InvokeModel"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/*",
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:agent/*",
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:agent-alias/*/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:GetAgent",
          "bedrock:ListAgents"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:agent/*"
        ]
      }
    ]
  })
}

# IAM Policy for Cognito
resource "aws_iam_role_policy" "cognito_policy" {
  name = "cognito-access"
  role = aws_iam_role.app_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cognito-idp:GetUser",
          "cognito-idp:AdminGetUser"
        ]
        Resource = aws_cognito_user_pool.multi_tenant_pool.arn
      }
    ]
  })
}