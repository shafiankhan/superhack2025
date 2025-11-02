import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration management for NinjaTriage AI."""
    
    # AWS Configuration
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    # AWS Secrets Manager
    NINJA_CREDENTIALS_SECRET_NAME = os.getenv("NINJA_CREDENTIALS_SECRET_NAME", "ninja-rmm-credentials")
    
    # AWS Bedrock
    BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
    
    # NinjaRMM Configuration
    NINJA_BASE_URL = os.getenv("NINJA_BASE_URL", "https://app.ninjarmm.com")
    ALERT_LIMIT = int(os.getenv("ALERT_LIMIT", "10"))
    
    # SuperOps Webhook
    SUPEROPS_WEBHOOK_URL = os.getenv("SUPEROPS_WEBHOOK_URL", "https://hooks.example.com/superops-ticket")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "agent_log.json")
    
    # Performance
    PROCESSING_TIMEOUT = int(os.getenv("PROCESSING_TIMEOUT", "300"))  # 5 minutes
    RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))
    
    @classmethod
    def validate(cls, demo_mode: bool = False) -> bool:
        """Validate required configuration."""
        if demo_mode:
            # In demo mode, we don't need real AWS credentials
            return True
            
        required_vars = [
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY"
        ]
        
        missing = [var for var in required_vars if not getattr(cls, var)]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return True
    
    @classmethod
    def get_aws_config(cls) -> dict:
        """Get AWS configuration dictionary."""
        return {
            "region_name": cls.AWS_REGION,
            "aws_access_key_id": cls.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": cls.AWS_SECRET_ACCESS_KEY
        }