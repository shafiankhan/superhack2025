#!/usr/bin/env python3
"""
Test AWS connection and available services
"""

import boto3
from config import Config

def test_aws_connection():
    """Test AWS connection and list available services."""
    try:
        print("🔍 Testing AWS Connection...")
        
        # Test basic AWS connection
        sts = boto3.client('sts', **Config.get_aws_config())
        identity = sts.get_caller_identity()
        
        print(f"✅ AWS Connection Successful!")
        print(f"   Account: {identity.get('Account')}")
        print(f"   User: {identity.get('Arn')}")
        
        # Test Bedrock availability
        print("\n🤖 Testing AWS Bedrock...")
        try:
            bedrock = boto3.client('bedrock', **Config.get_aws_config())
            models = bedrock.list_foundation_models()
            
            print(f"✅ Bedrock Available - {len(models['modelSummaries'])} models found")
            
            # Check if our target model is available
            target_model = Config.BEDROCK_MODEL_ID
            available_models = [m['modelId'] for m in models['modelSummaries']]
            
            if target_model in available_models:
                print(f"✅ Target model available: {target_model}")
            else:
                print(f"⚠️  Target model not found: {target_model}")
                print("Available models:")
                for model in available_models[:5]:  # Show first 5
                    print(f"   - {model}")
                
        except Exception as e:
            print(f"❌ Bedrock Error: {e}")
        
        # Test Secrets Manager
        print("\n🔐 Testing AWS Secrets Manager...")
        try:
            secrets = boto3.client('secretsmanager', **Config.get_aws_config())
            
            # Try to list secrets (just to test permissions)
            response = secrets.list_secrets(MaxResults=1)
            print(f"✅ Secrets Manager Available")
            
            # Try to access our specific secret
            try:
                secret_response = secrets.get_secret_value(
                    SecretId=Config.NINJA_CREDENTIALS_SECRET_NAME
                )
                print(f"✅ NinjaRMM credentials secret found: {Config.NINJA_CREDENTIALS_SECRET_NAME}")
            except secrets.exceptions.ResourceNotFoundException:
                print(f"⚠️  NinjaRMM credentials secret not found: {Config.NINJA_CREDENTIALS_SECRET_NAME}")
                print("   You'll need to create this secret for production mode")
            except Exception as e:
                print(f"❌ Secret access error: {e}")
                
        except Exception as e:
            print(f"❌ Secrets Manager Error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ AWS Connection Failed: {e}")
        return False

if __name__ == "__main__":
    success = test_aws_connection()
    
    if success:
        print("\n🚀 AWS Setup Complete - Ready for Production Deployment!")
    else:
        print("\n⚠️  AWS Setup Issues - Use Demo Mode for Testing")
        print("   Run: python ninja_triage.py --demo")