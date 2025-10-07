#!/usr/bin/env python3
"""
Setup Cognito Groups for Admin Authentication
Creates tenant-specific admin groups and assigns users
"""

import boto3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_cognito_admin_groups():
    """Create Cognito Groups for tenant admins"""
    
    cognito_client = boto3.client('cognito-idp')
    user_pool_id = os.getenv('COGNITO_USER_POOL_ID')
    
    if not user_pool_id:
        print("❌ COGNITO_USER_POOL_ID not found in environment")
        return
    
    # Define tenant admin groups
    admin_groups = [
        {
            "GroupName": "acme-corp-admins",
            "Description": "Acme Corporation Administrators",
            "Precedence": 1
        },
        {
            "GroupName": "beta-inc-admins", 
            "Description": "Beta Industries Administrators",
            "Precedence": 1
        },
        {
            "GroupName": "gamma-llc-admins",
            "Description": "Gamma LLC Administrators", 
            "Precedence": 1
        }
    ]
    
    print("🔐 Setting up Cognito Admin Groups...")
    
    # Create groups
    for group in admin_groups:
        try:
            cognito_client.create_group(
                GroupName=group["GroupName"],
                UserPoolId=user_pool_id,
                Description=group["Description"],
                Precedence=group["Precedence"]
            )
            print(f"✅ Created group: {group['GroupName']}")
        except cognito_client.exceptions.GroupExistsException:
            print(f"ℹ️  Group already exists: {group['GroupName']}")
        except Exception as e:
            print(f"❌ Error creating group {group['GroupName']}: {e}")
    
    print("\n📋 Admin Groups Setup Complete!")
    print("\n🔧 To add users to admin groups, use:")
    print("python scripts/add_admin_user.py <email> <tenant-id>")
    
    return True

def add_user_to_admin_group(email: str, tenant_id: str):
    """Add user to tenant admin group"""
    
    cognito_client = boto3.client('cognito-idp')
    user_pool_id = os.getenv('COGNITO_USER_POOL_ID')
    
    group_name = f"{tenant_id}-admins"
    
    try:
        # Add user to group
        cognito_client.admin_add_user_to_group(
            UserPoolId=user_pool_id,
            Username=email,
            GroupName=group_name
        )
        print(f"✅ Added {email} to {group_name}")
        return True
        
    except Exception as e:
        print(f"❌ Error adding user to group: {e}")
        return False

def list_admin_groups():
    """List all admin groups and their members"""
    
    cognito_client = boto3.client('cognito-idp')
    user_pool_id = os.getenv('COGNITO_USER_POOL_ID')
    
    try:
        # List all groups
        response = cognito_client.list_groups(UserPoolId=user_pool_id)
        
        print("🔐 Admin Groups:")
        for group in response['Groups']:
            if group['GroupName'].endswith('-admins'):
                print(f"\n📋 {group['GroupName']}")
                print(f"   Description: {group['Description']}")
                
                # List users in group
                users_response = cognito_client.list_users_in_group(
                    UserPoolId=user_pool_id,
                    GroupName=group['GroupName']
                )
                
                if users_response['Users']:
                    print("   Members:")
                    for user in users_response['Users']:
                        email = next((attr['Value'] for attr in user['Attributes'] if attr['Name'] == 'email'), 'No email')
                        print(f"     - {email}")
                else:
                    print("   Members: None")
        
    except Exception as e:
        print(f"❌ Error listing groups: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            list_admin_groups()
        elif sys.argv[1] == "add" and len(sys.argv) == 4:
            email = sys.argv[2]
            tenant_id = sys.argv[3]
            add_user_to_admin_group(email, tenant_id)
        else:
            print("Usage:")
            print("  python setup_cognito_admin_groups.py          # Create groups")
            print("  python setup_cognito_admin_groups.py list     # List groups")
            print("  python setup_cognito_admin_groups.py add <email> <tenant-id>  # Add user to group")
    else:
        setup_cognito_admin_groups()