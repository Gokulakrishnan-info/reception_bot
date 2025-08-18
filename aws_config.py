#!/usr/bin/env python3
"""
AWS Bedrock Configuration for AI Reception Bot
"""

import os
import boto3
from botocore.exceptions import ClientError

def setup_aws_credentials():
    """
    Setup AWS credentials for Bedrock access.
    You can set credentials in several ways:
    1. AWS CLI: aws configure
    2. Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
    3. IAM roles (if running on EC2)
    4. AWS credentials file: ~/.aws/credentials
    """
    
    # Check if credentials are available
    try:
        # Test Bedrock access by creating the client
        bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        print("✅ AWS Bedrock access configured successfully!")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'UnauthorizedOperation':
            print("❌ AWS credentials not configured or insufficient permissions")
            print("\n📋 To fix this:")
            print("1. Install AWS CLI: pip install awscli")
            print("2. Configure credentials: aws configure")
            print("3. Or set environment variables:")
            print("   export AWS_ACCESS_KEY_ID='your_access_key'")
            print("   export AWS_SECRET_ACCESS_KEY='your_secret_key'")
            print("   export AWS_DEFAULT_REGION='us-east-1'")
            print("\n🔑 You need Bedrock access permissions in your AWS account")
            return False
        else:
            print(f"❌ AWS Error: {e}")
            return False

def get_bedrock_client(region_name='us-east-1'):
    """
    Get a configured Bedrock client
    """
    try:
        return boto3.client('bedrock-runtime', region_name=region_name)
    except Exception as e:
        print(f"❌ Failed to create Bedrock client: {e}")
        return None

if __name__ == "__main__":
    setup_aws_credentials()
