"""Summary generation using Gemini API."""

from typing import Optional

import google.generativeai as genai

from ..core.logger import logger
from ..core.exceptions import TranscriptionError


class SummaryGenerator:
    """Generates summaries from transcripts using Gemini API."""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        """Initialize summary generator.
        
        Args:
            api_key: Gemini API key
            model: Model to use for generation
        """
        self.api_key = api_key
        self.model_name = model
        
        # Configure Gemini API
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
    
    def generate_summary(self, transcript: str, system_prompt: str) -> Optional[str]:
        """Generate summary from transcript.
        
        Args:
            transcript: Speech transcript text
            system_prompt: System prompt for summary generation
            
        Returns:
            Generated summary or None if error
        """
        if not transcript.strip():
            logger.warning("Empty transcript provided for summary")
            return None
        
        full_prompt = system_prompt.strip() + "\n\n" + transcript.strip()
        
        try:
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(temperature=0.5),
                stream=False,
            )
            
            logger.success("Generated summary successfully")
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini API error during summary generation: {e}")
            return None
    
    def batch_generate_summaries(self, transcripts: dict, system_prompt: str) -> dict:
        """Generate summaries for multiple transcripts.
        
        Args:
            transcripts: Dictionary mapping file names to transcript text
            system_prompt: System prompt for summary generation
            
        Returns:
            Dictionary mapping file names to summaries
        """
        summaries = {}
        
        for filename, transcript in transcripts.items():
            logger.info(f"Generating summary for {filename}")
            summary = self.generate_summary(transcript, system_prompt)
            
            if summary:
                summaries[filename] = summary
            else:
                logger.warning(f"Failed to generate summary for {filename}")
        
        logger.info(f"Generated {len(summaries)} summaries out of {len(transcripts)} transcripts")
        return summaries