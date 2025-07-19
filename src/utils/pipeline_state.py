"""
Pipeline State Management
Tracks the state of each file through the pipeline stages
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set
from enum import Enum


class PipelineStage(Enum):
    """Enumeration of pipeline stages."""
    AUDIO_EXTRACTED = "audio_extracted"      # Video -> Audio extraction
    AUDIO_DOWNLOADED = "audio_downloaded"    # Downloaded from Google Drive
    TRANSCRIBED = "transcribed"              # Audio -> Raw transcript
    PARSED = "parsed"                        # Raw transcript -> Parsed transcript
    SUMMARIZED = "summarized"                # Parsed transcript -> Summary
    HACKMD_UPLOADED = "hackmd_uploaded"      # Summary -> HackMD
    DRIVE_UPLOADED = "drive_uploaded"        # All files -> Google Drive
    COMPLETED = "completed"                  # Fully processed


class FileState:
    """Tracks the state of a single file through the pipeline."""
    
    def __init__(self, filename: str, audio_path: Optional[Path] = None):
        self.filename = filename
        self.audio_path = audio_path
        self.stages_completed: Set[PipelineStage] = set()
        self.artifacts: Dict[str, Path] = {}
        self.metadata: Dict[str, any] = {}
        self.last_updated = datetime.now()
    
    def mark_stage_complete(self, stage: PipelineStage, artifact_path: Optional[Path] = None):
        """Mark a stage as complete for this file."""
        self.stages_completed.add(stage)
        if artifact_path:
            self.artifacts[stage.value] = artifact_path
        self.last_updated = datetime.now()
    
    def is_stage_complete(self, stage: PipelineStage) -> bool:
        """Check if a specific stage is complete."""
        return stage in self.stages_completed
    
    def get_artifact(self, stage: PipelineStage) -> Optional[Path]:
        """Get the artifact path for a specific stage."""
        return self.artifacts.get(stage.value)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "filename": self.filename,
            "audio_path": str(self.audio_path) if self.audio_path else None,
            "stages_completed": [s.value for s in self.stages_completed],
            "artifacts": {k: str(v) for k, v in self.artifacts.items()},
            "metadata": self.metadata,
            "last_updated": self.last_updated.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FileState':
        """Create from dictionary."""
        state = cls(
            filename=data["filename"],
            audio_path=Path(data["audio_path"]) if data["audio_path"] else None
        )
        state.stages_completed = {PipelineStage(s) for s in data["stages_completed"]}
        state.artifacts = {k: Path(v) for k, v in data["artifacts"].items()}
        state.metadata = data["metadata"]
        state.last_updated = datetime.fromisoformat(data["last_updated"])
        return state


class PipelineStateManager:
    """Manages the state of all files in the pipeline."""
    
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.file_states: Dict[str, FileState] = {}
        self.load_state()
    
    def load_state(self):
        """Load state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    for filename, state_data in data.items():
                        self.file_states[filename] = FileState.from_dict(state_data)
            except Exception as e:
                print(f"Warning: Could not load pipeline state: {e}")
    
    def save_state(self):
        """Save state to file."""
        try:
            data = {filename: state.to_dict() for filename, state in self.file_states.items()}
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save pipeline state: {e}")
    
    def get_or_create_file_state(self, filename: str, audio_path: Optional[Path] = None) -> FileState:
        """Get existing file state or create new one."""
        if filename not in self.file_states:
            self.file_states[filename] = FileState(filename, audio_path)
        return self.file_states[filename]
    
    def mark_stage_complete(self, filename: str, stage: PipelineStage, 
                          artifact_path: Optional[Path] = None):
        """Mark a stage complete for a file."""
        state = self.get_or_create_file_state(filename)
        state.mark_stage_complete(stage, artifact_path)
        self.save_state()
    
    def is_stage_complete(self, filename: str, stage: PipelineStage) -> bool:
        """Check if a stage is complete for a file."""
        if filename not in self.file_states:
            return False
        return self.file_states[filename].is_stage_complete(stage)
    
    def get_artifact_path(self, filename: str, stage: PipelineStage) -> Optional[Path]:
        """Get artifact path for a stage."""
        if filename not in self.file_states:
            return None
        return self.file_states[filename].get_artifact(stage)
    
    def check_artifacts_exist(self, filename: str, stages: List[PipelineStage]) -> bool:
        """Verify that artifacts for given stages actually exist on disk."""
        if filename not in self.file_states:
            return False
        
        state = self.file_states[filename]
        for stage in stages:
            if not state.is_stage_complete(stage):
                return False
            
            artifact = state.get_artifact(stage)
            if artifact and not artifact.exists():
                # Artifact is missing, mark stage as incomplete
                state.stages_completed.discard(stage)
                self.save_state()
                return False
        
        return True
    
    def get_files_needing_stage(self, stage: PipelineStage) -> List[str]:
        """Get list of files that need a specific stage."""
        return [
            filename for filename, state in self.file_states.items()
            if not state.is_stage_complete(stage)
        ]
    
    def get_pipeline_summary(self) -> Dict[str, Dict[str, any]]:
        """Get summary of pipeline state for all files."""
        summary = {}
        for filename, state in self.file_states.items():
            summary[filename] = {
                "stages_completed": [s.value for s in state.stages_completed],
                "last_updated": state.last_updated.isoformat(),
                "artifacts_exist": {
                    stage.value: bool(artifact and artifact.exists())
                    for stage, artifact in [
                        (PipelineStage(k), Path(v)) for k, v in state.artifacts.items()
                    ]
                }
            }
        return summary
    
    def clean_missing_artifacts(self):
        """Remove references to artifacts that no longer exist."""
        for filename, state in self.file_states.items():
            missing_stages = []
            for stage_str, artifact_path in state.artifacts.items():
                if not Path(artifact_path).exists():
                    stage = PipelineStage(stage_str)
                    missing_stages.append(stage)
            
            for stage in missing_stages:
                state.stages_completed.discard(stage)
                if stage.value in state.artifacts:
                    del state.artifacts[stage.value]
        
        self.save_state()