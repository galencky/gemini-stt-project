import requests
import shutil
from pathlib import Path
from typing import List, Dict, Optional

class HackMDUploader:
    def __init__(self, api_token: str):
        """Initialize HackMD uploader with API token."""
        self.api_token = api_token
        self.base_url = "https://api.hackmd.io/v1"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
    
    def upload_markdown(self, md_content: str, filename: str) -> Optional[Dict]:
        """Upload a single markdown string to HackMD."""
        # Derive a clean title from the filename
        if filename.endswith('.md'):
            filename = filename[:-3]
        
        raw_title = filename.replace('_parsed', '').strip()
        title = raw_title.replace('_', ' ').strip()
        
        # Ensure there's a top-level heading
        md_lines = md_content.lstrip().splitlines()
        if not md_lines or not md_lines[0].strip().startswith("# "):
            md_content = f"# {title}\n\n" + md_content.lstrip()
        else:
            # Replace the first line with our title
            md_lines[0] = f"# {title}"
            md_content = "\n".join(md_lines)
        
        # Append hashtag
        hashtag = "#gemini-stt-project"
        content_lines = md_content.rstrip().splitlines()
        
        # Check if hashtag already exists in last 3 lines
        if not any(line.strip() == hashtag for line in content_lines[-3:]):
            md_content = md_content.rstrip() + "\n\n" + hashtag + "\n"
        
        # Prepare request data
        data = {
            "title": title,
            "content": md_content,
            "readPermission": "guest",
            "writePermission": "signed_in"
        }
        
        try:
            # Make API request
            response = requests.post(
                f"{self.base_url}/notes",
                headers=self.headers,
                json=data
            )
            
            if response.ok:
                result = response.json()
                note_id = result.get("id")
                shared_url = f"https://hackmd.io/{note_id}"
                
                print(f"✅ Uploaded to HackMD: {shared_url}")
                
                return {
                    "title": title,
                    "url": shared_url,
                    "note_id": note_id
                }
            else:
                print(f"❌ HackMD upload failed for {filename}: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error uploading to HackMD: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error uploading to HackMD: {e}")
            return None
    
    def upload_file(self, file_path: Path) -> Optional[Dict]:
        """Upload a markdown file to HackMD."""
        try:
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Upload it
            return self.upload_markdown(content, file_path.name)
            
        except Exception as e:
            print(f"❌ Error reading file {file_path}: {e}")
            return None
    
    def batch_upload_and_move(self, markdown_dir: Path, uploaded_dir: Path) -> List[Dict]:
        """Upload all markdown files from a directory and move them after successful upload."""
        shared_links = []
        
        # Find all markdown files
        md_files = list(markdown_dir.glob("*.md"))
        
        if not md_files:
            print(f"⚠️  No markdown files found in {markdown_dir}")
            return shared_links
        
        print(f"\n📤 Found {len(md_files)} markdown files to upload to HackMD")
        
        for md_file in md_files:
            print(f"\n📝 Processing: {md_file.name}")
            
            # Upload the file
            result = self.upload_file(md_file)
            
            if result:
                shared_links.append(result)
                
                # Move the file to uploaded directory
                try:
                    dest_file = uploaded_dir / md_file.name
                    shutil.move(str(md_file), str(dest_file))
                    print(f"✅ Moved {md_file.name} → {dest_file}")
                except Exception as e:
                    print(f"⚠️  Failed to move {md_file.name}: {e}")
            else:
                print(f"⚠️  Failed to upload {md_file.name}, file not moved")
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"HackMD upload complete!")
        print(f"✅ Successfully uploaded: {len(shared_links)} files")
        print(f"{'='*60}")
        
        return shared_links
    
    def update_note(self, note_id: str, content: str, title: Optional[str] = None) -> bool:
        """Update an existing HackMD note."""
        data = {"content": content}
        if title:
            data["title"] = title
        
        try:
            response = requests.patch(
                f"{self.base_url}/notes/{note_id}",
                headers=self.headers,
                json=data
            )
            
            if response.ok:
                print(f"✅ Updated HackMD note: {note_id}")
                return True
            else:
                print(f"❌ Failed to update note: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating HackMD note: {e}")
            return False
    
    def get_note_info(self, note_id: str) -> Optional[Dict]:
        """Get information about a HackMD note."""
        try:
            response = requests.get(
                f"{self.base_url}/notes/{note_id}",
                headers=self.headers
            )
            
            if response.ok:
                return response.json()
            else:
                print(f"❌ Failed to get note info: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting HackMD note info: {e}")
            return None
    
    def create_index_page(self, shared_links: List[Dict], title: str = "Gemini STT Transcription Index") -> Optional[Dict]:
        """Create an index page on HackMD with links to all uploaded documents."""
        # Create index content
        content = f"# {title}\n\n"
        content += "This page contains links to all transcribed and summarized medical audio files.\n\n"
        content += "## Uploaded Documents\n\n"
        
        # Add links
        for idx, link in enumerate(shared_links, 1):
            content += f"{idx}. [{link['title']}]({link['url']})\n"
        
        content += f"\n\n---\n\n*Total documents: {len(shared_links)}*\n"
        content += "\n#gemini-stt-project\n"
        
        # Upload index page
        return self.upload_markdown(content, "index.md")