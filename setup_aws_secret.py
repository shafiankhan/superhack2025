#!/usr/bin/env python3
"""
Setup AWS Secrets Manager secret for NinjaRMM credentials
"""

import boto3
import json
from config import Config

def create_ninja_secret():
    """Create AWS Secrets Manager secret for NinjaRMM credentials."""
    try:
        print("🔐 Setting up NinjaRMM credentials in AWS Secrets Manager...")
        
        # Get user input for credentials
        print("\nPlease provide your NinjaRMM credentials:")
        username = input("NinjaRMM Username/Email: ")
        password = input("NinjaRMM Password: ")
        
        if not username or not password:
            print("❌ Username and password are required")
            return False
        
        # Create secrets manager client
        secrets_client = boto3.client('secretsmanager', **Config.get_aws_config())
        
        # Prepare secret data
        secret_data = {
            "username": username,
            "password": password
        }
        
        secret_name = Config.NINJA_CREDENTIALS_SECRET_NAME
        
        try:
            # Try to create the secret
            response = secrets_client.create_secret(
                Name=secret_name,
                Description="NinjaRMM login credentials for NinjaTriage AI",
                SecretString=json.dumps(secret_data)
            )
            
            print(f"✅ Secret created successfully!")
            print(f"   Secret ARN: {response['ARN']}")
            
        except secrets_client.exceptions.ResourceExistsException:
            # Secret already exists, update it
            print(f"⚠️  Secret already exists, updating...")
            
            response = secrets_client.update_secret(
                SecretId=secret_name,
                SecretString=json.dumps(secret_data)
            )
            
            print(f"✅ Secret updated successfully!")
            print(f"   Secret ARN: {response['ARN']}")
        
        print(f"\n🎯 Secret Name: {secret_name}")
        print("✅ NinjaTriage AI can now access NinjaRMM credentials securely!")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create secret: {e}")
        return False

def show_iam_policy():
    """Show required IAM policy for NinjaTriage AI."""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "secretsmanager:GetSecretValue"
                ],
                "Resource": f"arn:aws:secretsmanager:*:*:secret:{Config.NINJA_CREDENTIALS_SECRET_NAME}*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel"
                ],
                "Resource": f"arn:aws:bedrock:*::foundation-model/{Config.BEDROCK_MODEL_ID}"
            }
        ]
    }
    
    print("\n📋 Required IAM Policy for NinjaTriage AI:")
    print("=" * 50)
    print(json.dumps(policy, indent=2))
    print("=" * 50)

if __name__ == "__main__":
    print("🥷 NinjaTriage AI - AWS Setup")
    print("=" * 40)
    
    # Show IAM policy first
    show_iam_policy()
    
    print("\n" + "=" * 40)
    
    # Ask if user wants to create secret
    create_secret = input("\nDo you want to create the NinjaRMM credentials secret? (y/n): ")
    
    if create_secret.lower() in ['y', 'yes']:
        success = create_ninja_secret()
        
        if success:
            print("\n🚀 Setup Complete! You can now run:")
            print("   python ninja_triage.py  # Production mode")
        else:
            print("\n⚠️  Setup failed. You can still run:")
            print("   python ninja_triage.py --demo  # Demo mode")
    else:
        print("\n💡 You can run in demo mode without AWS setup:")
        print("   python ninja_triage.py --demo")