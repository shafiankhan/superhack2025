import json
import boto3
from typing import Dict, Optional
from strand_agents import Agent, AgentConfig
from config import Config


class CredentialAgent(Agent):
    """Strand Agent for managing AWS Secrets Manager credentials."""
    
    def __init__(self):
        config = AgentConfig(
            name="credential_agent",
            description="Manages secure credential retrieval from AWS Secrets Manager"
        )
        super().__init__(config)
        self.secrets_client = None
        self.cached_credentials = None
    
    async def initialize(self):
        """Initialize AWS Secrets Manager client."""
        try:
            # Check if we have AWS credentials
            if Config.AWS_ACCESS_KEY_ID and Config.AWS_SECRET_ACCESS_KEY:
                self.secrets_client = boto3.client(
                    'secretsmanager',
                    **Config.get_aws_config()
                )
                self.log_info("Credential agent initialized with AWS Secrets Manager")
            else:
                self.log_info("Credential agent initialized in demo mode (no AWS credentials)")
        except Exception as e:
            self.log_error(f"Failed to initialize credential agent: {e}")
            raise
    
    async def get_ninja_credentials(self) -> Dict[str, str]:
        """Retrieve NinjaRMM credentials from AWS Secrets Manager."""
        if self.cached_credentials:
            return self.cached_credentials
        
        try:
            if self.secrets_client:
                self.log_info(f"Retrieving credentials from secret: {Config.NINJA_CREDENTIALS_SECRET_NAME}")
                
                response = self.secrets_client.get_secret_value(
                    SecretId=Config.NINJA_CREDENTIALS_SECRET_NAME
                )
                
                secret_data = json.loads(response['SecretString'])
                
                # Validate required fields
                required_fields = ['username', 'password']
                for field in required_fields:
                    if field not in secret_data:
                        raise ValueError(f"Missing required field in secret: {field}")
                
                self.cached_credentials = {
                    'username': secret_data['username'],
                    'password': secret_data['password']
                }
                
                self.log_info("Credentials retrieved successfully")
            else:
                # Demo mode - return mock credentials
                self.log_info("Using demo credentials (not real)")
                self.cached_credentials = {
                    'username': 'demo_user@company.com',
                    'password': 'demo_password_123'
                }
            
            return self.cached_credentials
            
        except Exception as e:
            self.log_error(f"Failed to retrieve credentials: {e}")
            raise
    
    async def clear_credentials(self):
        """Securely clear credentials from memory."""
        if self.cached_credentials:
            # Overwrite sensitive data
            for key in self.cached_credentials:
                self.cached_credentials[key] = "CLEARED"
            self.cached_credentials = None
            self.log_info("Credentials cleared from memory")
    
    async def cleanup(self):
        """Cleanup resources when agent shuts down."""
        await self.clear_credentials()
        self.log_info("Credential agent cleanup completed")