import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Bedrock Agent Configuration
    BEDROCK_AGENT_ID = os.getenv("BEDROCK_AGENT_ID", "")
    BEDROCK_AGENT_ALIAS_ID = os.getenv("BEDROCK_AGENT_ALIAS_ID", "TSTALIASID")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    
    # Application Configuration
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", "8000"))
    
    # Cognito Configuration
    COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "")
    COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID", "")
    
    # DynamoDB Configuration
    SESSIONS_TABLE = os.getenv("SESSIONS_TABLE", "tenant-sessions")
    USAGE_TABLE = os.getenv("USAGE_TABLE", "tenant-usage")
    
    # JWT Configuration
    JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_HOURS = 24
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate required configuration"""
        errors = []
        
        if not cls.COGNITO_USER_POOL_ID:
            errors.append("COGNITO_USER_POOL_ID is required")
        
        if not cls.COGNITO_CLIENT_ID:
            errors.append("COGNITO_CLIENT_ID is required")
            
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "config": {
                "agent_id": cls.BEDROCK_AGENT_ID,
                "agent_alias_id": cls.BEDROCK_AGENT_ALIAS_ID,
                "aws_region": cls.AWS_REGION
            }
        }