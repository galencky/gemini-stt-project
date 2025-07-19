from pathlib import Path
from typing import List, Optional, Dict
import google.generativeai as genai

class Summarizer:
    def __init__(self, api_key: str, system_prompt: str):
        """Initialize summarizer with Gemini API key and system prompt."""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-pro")
        self.system_prompt = system_prompt
    
    def generate_summary(self, speech_text: str) -> Optional[str]:
        """Generate a summary of the speech text using Gemini."""
        try:
            # Combine system prompt with speech text
            full_prompt = self.system_prompt.strip() + "\n\n" + speech_text.strip()
            
            print("🤖 Generating summary with Gemini...")
            
            # Generate summary
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(temperature=0.5),
                stream=False,
            )
            
            if response.text:
                print("✅ Summary generated successfully")
                return response.text
            else:
                print("❌ No summary generated")
                return None
                
        except Exception as e:
            print(f"❌ Error generating summary: {e}")
            return None
    
    def summarize_transcript_file(self, transcript_path: Path) -> Optional[str]:
        """Read a transcript file and generate its summary."""
        try:
            # Read the transcript
            with open(transcript_path, 'r', encoding='utf-8') as f:
                speech_text = f.read().strip()
            
            if not speech_text:
                print(f"⚠️  Transcript file is empty: {transcript_path}")
                return None
            
            print(f"\n📄 Processing: {transcript_path.name}")
            print(f"   Size: {len(speech_text)} characters")
            
            # Generate summary
            return self.generate_summary(speech_text)
            
        except Exception as e:
            print(f"❌ Error reading transcript file: {e}")
            return None
    
    def batch_summarize(self, input_dir: Path, output_dir: Path, 
                       file_pattern: str = "*_parsed.txt") -> Dict:
        """Summarize all matching transcript files in a directory."""
        results = {
            "successful": [],
            "failed": [],
            "skipped": []
        }
        
        # Find all matching transcript files
        transcript_files = list(input_dir.glob(file_pattern))
        
        if not transcript_files:
            print(f"⚠️  No files matching '{file_pattern}' found in {input_dir}")
            return results
        
        print(f"\n📚 Found {len(transcript_files)} transcript files to summarize")
        
        for transcript_file in transcript_files:
            print(f"\n{'='*60}")
            print(f"Processing: {transcript_file.name}")
            
            # Generate summary
            summary = self.summarize_transcript_file(transcript_file)
            
            if summary:
                # Create output filename
                output_filename = transcript_file.stem.replace('_parsed', '') + '.md'
                output_path = output_dir / output_filename
                
                try:
                    # Save summary
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(summary)
                    
                    print(f"✅ Saved summary to: {output_path}")
                    results["successful"].append({
                        "transcript": transcript_file,
                        "summary": output_path
                    })
                    
                except Exception as e:
                    print(f"❌ Error saving summary: {e}")
                    results["failed"].append({
                        "transcript": transcript_file,
                        "error": str(e)
                    })
            else:
                results["failed"].append({
                    "transcript": transcript_file,
                    "error": "Summary generation failed"
                })
        
        # Print summary report
        print(f"\n{'='*60}")
        print(f"Summarization complete!")
        print(f"✅ Successful: {len(results['successful'])}")
        print(f"❌ Failed: {len(results['failed'])}")
        print(f"⏭️  Skipped: {len(results['skipped'])}")
        print(f"{'='*60}")
        
        return results
    
    def create_combined_summary(self, summaries: List[Path], output_path: Path) -> bool:
        """Create a combined summary document from multiple summaries."""
        try:
            combined_content = []
            combined_content.append("# Combined Medical Transcription Summaries\n")
            
            for summary_path in summaries:
                with open(summary_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                # Add file name as section header
                combined_content.append(f"\n## {summary_path.stem}\n")
                combined_content.append(content)
                combined_content.append("\n---\n")
            
            # Write combined summary
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(combined_content))
            
            print(f"✅ Created combined summary: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating combined summary: {e}")
            return False
    
    @staticmethod
    def format_summary_for_display(summary: str) -> str:
        """Format summary for better display (e.g., add line breaks, headers)."""
        lines = summary.strip().split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append('')
                continue
            
            # Enhance formatting based on content patterns
            if line.startswith('#'):
                # Ensure proper spacing around headers
                formatted_lines.append('')
                formatted_lines.append(line)
                formatted_lines.append('')
            elif line.startswith(('-', '*', '•')):
                # List items
                formatted_lines.append(line)
            else:
                # Regular paragraphs
                formatted_lines.append(line)
        
        # Clean up multiple empty lines
        result = '\n'.join(formatted_lines)
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result.strip()

import re  # Add this import at the top of the file