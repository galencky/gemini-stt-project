"""Pipeline state management for resume capability."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .logger import logger


class PipelineState:
    """Manages pipeline state for resume capability."""
    
    def __init__(self, state_file: Path = Path("working/pipeline_state.json")):
        """Initialize state manager.
        
        Args:
            state_file: Path to state file
        """
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()
    
    def _load_state(self) -> Dict[str, Any]:
        """Load state from file or create new state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                logger.info(f"Loaded existing pipeline state from {self.state_file}")
                return state
            except Exception as e:
                logger.warning(f"Failed to load state file: {e}")
        
        # Create new state
        return {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "completed_steps": [],
            "files_processed": {},
            "transcriptions": {},
            "summaries": {},
            "uploads": {},
            "current_step": None,
            "errors": []
        }
    
    def save(self):
        """Save current state to file."""
        self.state["last_updated"] = datetime.now().isoformat()
        
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.debug(f"Saved pipeline state to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def mark_step_complete(self, step: str):
        """Mark a pipeline step as complete."""
        if step not in self.state["completed_steps"]:
            self.state["completed_steps"].append(step)
        self.state["current_step"] = None
        self.save()
    
    def set_current_step(self, step: str):
        """Set the current pipeline step."""
        self.state["current_step"] = step
        self.save()
    
    def is_step_complete(self, step: str) -> bool:
        """Check if a step is already complete."""
        return step in self.state["completed_steps"]
    
    def add_processed_file(self, category: str, filename: str, data: Dict):
        """Add a processed file to state.
        
        Args:
            category: Category (e.g., 'video', 'audio', 'transcript')
            filename: File name
            data: Associated data
        """
        if category not in self.state["files_processed"]:
            self.state["files_processed"][category] = {}
        
        self.state["files_processed"][category][filename] = {
            "processed_at": datetime.now().isoformat(),
            **data
        }
        self.save()
    
    def is_file_processed(self, category: str, filename: str) -> bool:
        """Check if a file has been processed."""
        return (category in self.state["files_processed"] and 
                filename in self.state["files_processed"][category])
    
    def get_processed_files(self, category: str) -> Dict:
        """Get all processed files in a category."""
        return self.state["files_processed"].get(category, {})
    
    def add_transcription(self, filename: str, transcript_path: str):
        """Add a completed transcription."""
        self.state["transcriptions"][filename] = {
            "path": transcript_path,
            "completed_at": datetime.now().isoformat()
        }
        self.save()
    
    def get_transcriptions(self) -> Dict:
        """Get all completed transcriptions."""
        return self.state["transcriptions"]
    
    def add_summary(self, filename: str, summary_path: str):
        """Add a generated summary."""
        self.state["summaries"][filename] = {
            "path": summary_path,
            "generated_at": datetime.now().isoformat()
        }
        self.save()
    
    def get_summaries(self) -> Dict:
        """Get all generated summaries."""
        return self.state["summaries"]
    
    def add_upload(self, filename: str, url: str, service: str = "hackmd"):
        """Add an upload record."""
        if service not in self.state["uploads"]:
            self.state["uploads"][service] = {}
        
        self.state["uploads"][service][filename] = {
            "url": url,
            "uploaded_at": datetime.now().isoformat()
        }
        self.save()
    
    def add_gdrive_sync(self, filename: str, folder_id: str):
        """Add a Google Drive sync record."""
        if "gdrive_synced" not in self.state:
            self.state["gdrive_synced"] = {}
        
        self.state["gdrive_synced"][filename] = {
            "folder_id": folder_id,
            "synced_at": datetime.now().isoformat()
        }
        self.save()
    
    def is_gdrive_synced(self, filename: str) -> bool:
        """Check if a file has been synced to Google Drive."""
        return filename in self.state.get("gdrive_synced", {})
    
    def add_folder_organized(self, stem: str, location: str = "gdrive"):
        """Track that a folder has been organized.
        
        Args:
            stem: File stem
            location: Where it was organized ("gdrive" or "local")
        """
        if "folders_organized" not in self.state:
            self.state["folders_organized"] = {}
        
        self.state["folders_organized"][stem] = {
            "location": location,
            "organized_at": datetime.now().isoformat()
        }
        self.save()
    
    def is_folder_organized(self, stem: str) -> bool:
        """Check if a folder has already been organized."""
        return stem in self.state.get("folders_organized", {})
    
    def get_failed_syncs(self) -> List[str]:
        """Get list of files that failed to sync."""
        failed = []
        for error in self.state.get("errors", []):
            if "sync" in error.get("context", "").lower() and "Failed to sync" in error.get("error", ""):
                # Extract filename from error message
                import re
                match = re.search(r"Failed to sync (\S+) to Google Drive", error["error"])
                if match:
                    failed.append(match.group(1))
        return list(set(failed))
    
    def get_uploads(self, service: str = "hackmd") -> Dict:
        """Get upload records for a service."""
        return self.state["uploads"].get(service, {})
    
    def add_error(self, error: str, context: str):
        """Add an error to the state."""
        self.state["errors"].append({
            "error": error,
            "context": context,
            "timestamp": datetime.now().isoformat()
        })
        self.save()
    
    def clear(self):
        """Clear all state and start fresh."""
        self.state = self._load_state()
        self.state["created_at"] = datetime.now().isoformat()
        self.state["completed_steps"] = []
        self.state["files_processed"] = {}
        self.state["transcriptions"] = {}
        self.state["summaries"] = {}
        self.state["uploads"] = {}
        self.state["gdrive_synced"] = {}
        self.state["folders_organized"] = {}
        self.state["current_step"] = None
        self.state["errors"] = []
        self.save()
        logger.info("Cleared pipeline state")
    
    def should_resume(self) -> bool:
        """Check if pipeline should resume from previous state."""
        return (self.state_file.exists() and 
                len(self.state["completed_steps"]) > 0 and
                self.state["current_step"] is not None)