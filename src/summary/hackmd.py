"""HackMD integration for uploading summaries."""

import requests
from typing import Optional, Dict, List

from ..core.logger import logger
from ..core.exceptions import NetworkError


class HackMDUploader:
    """Handles uploading content to HackMD."""
    
    def __init__(self, api_token: str):
        """Initialize HackMD uploader.
        
        Args:
            api_token: HackMD API token
        """
        self.api_token = api_token
        self.base_url = "https://api.hackmd.io/v1"
    
    def upload_note(self, content: str, title: str) -> Optional[Dict]:
        """Upload a single note to HackMD.
        
        Args:
            content: Markdown content
            title: Note title
            
        Returns:
            Dictionary with upload result or None if error
        """
        # Clean up title
        if title.endswith('.md'):
            title = title[:-3]
        title = title.replace('_parsed', '').replace('_', ' ').strip()
        
        # Ensure proper title in content
        md_lines = content.lstrip().splitlines()
        if not md_lines or not md_lines[0].strip().startswith("# "):
            content = f"# {title}\n\n" + content.lstrip()
        else:
            md_lines[0] = f"# {title}"
            content = "\n".join(md_lines)
        
        # Append hashtag
        hashtag = "#gemini-stt-project"
        content_lines = content.rstrip().splitlines()
        if not any(line.strip() == hashtag for line in content_lines[-3:]):
            content = content.rstrip() + "\n\n" + hashtag + "\n"
        
        # Prepare request
        url = f"{self.base_url}/notes"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        data = {
            "title": title,
            "content": content,
            "readPermission": "guest",
            "writePermission": "signed_in"
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.ok:
                note_data = response.json()
                note_id = note_data.get("id")
                shared_url = f"https://hackmd.io/{note_id}"
                logger.success(f"Uploaded to HackMD: {shared_url}")
                return {"title": title, "url": shared_url, "id": note_id}
            else:
                logger.error(f"HackMD upload failed: {response.status_code} {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error uploading to HackMD: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading to HackMD: {e}")
            return None
    
    def batch_upload_notes(self, notes: Dict[str, str]) -> List[Dict]:
        """Upload multiple notes to HackMD.
        
        Args:
            notes: Dictionary mapping titles to content
            
        Returns:
            List of successful upload results
        """
        results = []
        
        for title, content in notes.items():
            logger.info(f"Uploading {title} to HackMD...")
            result = self.upload_note(content, title)
            
            if result:
                results.append(result)
            else:
                logger.warning(f"Failed to upload {title}")
        
        logger.info(f"Successfully uploaded {len(results)}/{len(notes)} notes to HackMD")
        return results
    
    def update_note(self, note_id: str, content: str) -> bool:
        """Update an existing note on HackMD.
        
        Args:
            note_id: HackMD note ID
            content: New content
            
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/notes/{note_id}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        data = {"content": content}
        
        try:
            response = requests.patch(url, headers=headers, json=data, timeout=30)
            
            if response.ok:
                logger.success(f"Updated HackMD note {note_id}")
                return True
            else:
                logger.error(f"Failed to update note: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating HackMD note: {e}")
            return False