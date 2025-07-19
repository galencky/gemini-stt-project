import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from typing import List, Dict, Optional

class EmailSender:
    def __init__(self, smtp_user: str, smtp_pass: str, smtp_server: str = "smtp.gmail.com", smtp_port: int = 465):
        """Initialize email sender with SMTP credentials."""
        self.smtp_user = smtp_user
        self.smtp_pass = smtp_pass
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
    
    def send_hackmd_links(self, recipient: str, shared_links: List[Dict]) -> bool:
        """Send an email with HackMD links to the recipient."""
        if not shared_links:
            print("⚠️  No shared links to send")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.smtp_user
            msg["To"] = recipient
            msg["Subject"] = Header("📝 Your Uploaded HackMD Speech Summaries (Gemini STT)", "utf-8")
            
            # Build email body
            body = self._create_email_body(shared_links)
            
            # Attach body to message
            msg.attach(MIMEText(body, "plain", "utf-8"))
            
            # Send email
            print(f"\n📧 Sending email to {recipient}...")
            
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            
            print(f"✅ Email sent successfully to {recipient}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            print("❌ Email authentication failed. Please check your email credentials.")
            return False
        except smtplib.SMTPException as e:
            print(f"❌ SMTP error occurred: {e}")
            return False
        except Exception as e:
            print(f"❌ Error sending email: {e}")
            return False
    
    def _create_email_body(self, shared_links: List[Dict]) -> str:
        """Create the email body with HackMD links."""
        body_lines = [
            "Hello,",
            "",
            "Your audio files were transcribed using Gemini STT with chunking",
            "and summarized using Gemini 2.5 Pro. The summaries are now",
            "available on HackMD:",
            "",
        ]
        
        # Add links
        for link in shared_links:
            body_lines.append(f"• {link['title']}: {link['url']}")
        
        body_lines.extend([
            "",
            f"Total documents processed: {len(shared_links)}",
            "",
            "The transcriptions were processed in 5-minute chunks to ensure accuracy,",
            "and the summaries were generated based on the complete transcripts.",
            "",
            "If you have any questions, please feel free to reply to this email.",
            "",
            "Best regards,",
            "Gemini-STT Bot"
        ])
        
        return "\n".join(body_lines)
    
    def send_error_report(self, recipient: str, errors: List[Dict]) -> bool:
        """Send an error report email."""
        if not errors:
            return True  # No errors to report
        
        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_user
            msg["To"] = recipient
            msg["Subject"] = Header("⚠️ Gemini STT Processing Errors", "utf-8")
            
            # Build error report
            body_lines = [
                "Hello,",
                "",
                "Some errors occurred during the Gemini STT processing:",
                "",
            ]
            
            for error in errors:
                if "audio_file" in error:
                    body_lines.append(f"• {error['audio_file'].name}: {error.get('error', 'Unknown error')}")
                else:
                    body_lines.append(f"• {error.get('error', 'Unknown error')}")
            
            body_lines.extend([
                "",
                "Please check the logs for more details.",
                "",
                "Best regards,",
                "Gemini-STT Bot"
            ])
            
            body = "\n".join(body_lines)
            msg.attach(MIMEText(body, "plain", "utf-8"))
            
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            
            print("✅ Error report sent")
            return True
            
        except Exception as e:
            print(f"❌ Error sending error report: {e}")
            return False
    
    def send_processing_summary(self, recipient: str, stats: Dict) -> bool:
        """Send a processing summary email with statistics."""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_user
            msg["To"] = recipient
            msg["Subject"] = Header("📊 Gemini STT Processing Summary", "utf-8")
            
            # Build summary
            body_lines = [
                "Hello,",
                "",
                "Here's a summary of the Gemini STT processing session:",
                "",
                "📊 Processing Statistics:",
                f"• Audio files processed: {stats.get('audio_files', 0)}",
                f"• Successful transcriptions: {stats.get('successful_transcriptions', 0)}",
                f"• Failed transcriptions: {stats.get('failed_transcriptions', 0)}",
                f"• Summaries generated: {stats.get('summaries_generated', 0)}",
                f"• Files uploaded to HackMD: {stats.get('hackmd_uploads', 0)}",
                "",
            ]
            
            if stats.get('total_duration'):
                body_lines.append(f"• Total audio duration: {stats['total_duration']}")
            
            if stats.get('processing_time'):
                body_lines.append(f"• Processing time: {stats['processing_time']}")
            
            body_lines.extend([
                "",
                "Best regards,",
                "Gemini-STT Bot"
            ])
            
            body = "\n".join(body_lines)
            msg.attach(MIMEText(body, "plain", "utf-8"))
            
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            
            print("✅ Processing summary sent")
            return True
            
        except Exception as e:
            print(f"❌ Error sending processing summary: {e}")
            return False