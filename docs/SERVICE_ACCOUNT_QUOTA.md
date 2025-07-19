# Service Account Storage Quota Error

If you're seeing this error:
```
Service Accounts do not have storage quota. Leverage shared drives
```

This means your Google Drive folders are in "My Drive" which has storage limits for service accounts.

## Solutions

### Option 1: Use Shared Drives (Recommended)

1. Create a Shared Drive in Google Drive
2. Move your folders to the Shared Drive
3. Update your `.env` with the new folder IDs from the Shared Drive
4. Grant your service account access to the Shared Drive

### Option 2: Use Existing My Drive Folders

If you must use My Drive folders:

1. Share each folder with a regular Google account
2. Have that account create the folders
3. Grant your service account "Editor" access to those folders
4. The files will count against the regular account's quota, not the service account

### Option 3: Use Local Fallback (Automatic)

The pipeline automatically creates local organized folders when uploads fail:

1. Files are organized in `working/organized_for_upload/`
2. Same folder structure as Google Drive
3. You can manually upload these folders later
4. No configuration needed - happens automatically on quota errors

### Option 4: Disable File Upload

If you only need local processing:

1. Set `ORGANIZE_TO_FOLDERS=false` in your `.env`
2. Files will be processed locally but not uploaded
3. Use HackMD for sharing summaries online

## Why This Happens

Service accounts are designed for server-to-server interactions and don't have personal storage quotas. They can only create files in:
- Shared Drives (unlimited storage)
- Folders owned by other users (counts against that user's quota)

## Checking Your Setup

Run this to see if your folders are in a Shared Drive:
```cmd
python tools\check_drive_type.py
```