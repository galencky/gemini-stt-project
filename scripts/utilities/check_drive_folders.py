#!/usr/bin/env python3
"""
Check if Google Drive folders are in My Drive or Shared Drive
"""

import sys
sys.path.insert(0, '.')

from src.utils import config
from src.integrations import GoogleDriveClient

def check_folders():
    print("Checking Google Drive folder locations...\n")
    
    client = GoogleDriveClient(config.GDRIVE_SERVICE_ACCOUNT_JSON)
    
    folders = {
        "TO_BE_TRANSCRIBED": config.TO_BE_TRANSCRIBED_FOLDER_ID,
        "TRANSCRIBED": config.TRANSCRIBED_FOLDER_ID,
        "PROCESSED": config.PROCESSED_FOLDER_ID
    }
    
    for name, folder_id in folders.items():
        try:
            # Get folder info
            folder_info = client.drive_service.files().get(
                fileId=folder_id,
                fields="id,name,driveId,owners,permissions",
                supportsAllDrives=True
            ).execute()
            
            print(f"{name} Folder:")
            print(f"  ID: {folder_id}")
            print(f"  Name: {folder_info.get('name', 'Unknown')}")
            
            if 'driveId' in folder_info:
                print(f"  Location: Shared Drive (ID: {folder_info['driveId']})")
            else:
                print(f"  Location: My Drive")
                if 'owners' in folder_info:
                    owner = folder_info['owners'][0]
                    print(f"  Owner: {owner.get('displayName', 'Unknown')} ({owner.get('emailAddress', 'Unknown')})")
            
            # Check service account permissions
            permissions = folder_info.get('permissions', [])
            sa_permission = None
            for perm in permissions:
                if perm.get('emailAddress') == client.creds.service_account_email:
                    sa_permission = perm
                    break
            
            if sa_permission:
                print(f"  Service Account Permission: {sa_permission.get('role', 'Unknown')}")
            else:
                print(f"  Service Account Permission: Not found")
            
            print()
            
        except Exception as e:
            print(f"{name} Folder: Error - {e}\n")

if __name__ == "__main__":
    check_folders()