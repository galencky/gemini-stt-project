"""Email notification system."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from typing import List, Dict, Optional

from ..core.logger import logger
from ..core.exceptions import NetworkError


class EmailNotifier:
    """Handles email notifications."""
    
    def __init__(self, smtp_user: str, smtp_pass: str, smtp_server: str = "smtp.gmail.com", 
                 smtp_port: int = 465):
        """Initialize email notifier.
        
        Args:
            smtp_user: SMTP username (email address)
            smtp_pass: SMTP password or app password
            smtp_server: SMTP server address
            smtp_port: SMTP server port
        """
        self.smtp_user = smtp_user
        self.smtp_pass = smtp_pass
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
    
    def send_summary_notification(self, recipient: str, shared_links: List[Dict], 
                                subject: Optional[str] = None) -> bool:
        """Send email notification with HackMD links.
        
        Args:
            recipient: Email recipient
            shared_links: List of dictionaries with 'title' and 'url' keys
            subject: Optional custom subject
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not shared_links:
            logger.warning("No links to send in email notification")
            return False
        
        # Default subject if not provided
        if not subject:
            subject = "📝 Your Uploaded HackMD Speech Summaries (Gemini STT)"
        
        # Build email body
        body_lines = [
            "Hello,",
            "",
            "Your audio files were transcribed using Gemini STT with chunking",
            "and summarized using Gemini 2.0 Flash. The summaries are now",
            "available on HackMD:",
            ""
        ]
        
        # Add links
        for link in shared_links:
            body_lines.append(f"- {link['title']}: {link['url']}")
        
        body_lines.extend([
            "",
            "If you have questions just reply to this email.",
            "",
            "Best regards,",
            "Gemini-STT Bot"
        ])
        
        body = "\n".join(body_lines)
        
        return self.send_email(recipient, subject, body)
    
    def send_email(self, recipient: str, subject: str, body: str, 
                   html_body: Optional[str] = None) -> bool:
        """Send a generic email.
        
        Args:
            recipient: Email recipient
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative' if html_body else 'mixed')
            msg["From"] = self.smtp_user
            msg["To"] = recipient
            msg["Subject"] = Header(subject, "utf-8")
            
            # Add text part
            msg.attach(MIMEText(body, "plain", "utf-8"))
            
            # Add HTML part if provided
            if html_body:
                msg.attach(MIMEText(html_body, "html", "utf-8"))
            
            # Send email
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            
            logger.success(f"Email sent successfully to {recipient}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("Email authentication failed. Check username and password.")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def send_error_notification(self, recipient: str, error_message: str, 
                              context: Optional[str] = None) -> bool:
        """Send error notification email.
        
        Args:
            recipient: Email recipient
            error_message: Error message to send
            context: Optional context about when/where error occurred
            
        Returns:
            True if sent successfully, False otherwise
        """
        subject = "❌ Gemini STT Processing Error"
        
        body_lines = [
            "Hello,",
            "",
            "An error occurred during Gemini STT processing:",
            "",
            f"Error: {error_message}",
        ]
        
        if context:
            body_lines.extend([
                "",
                f"Context: {context}"
            ])
        
        body_lines.extend([
            "",
            "Please check the logs for more details.",
            "",
            "Best regards,",
            "Gemini-STT Bot"
        ])
        
        body = "\n".join(body_lines)
        
        return self.send_email(recipient, subject, body)
    
    def test_connection(self) -> bool:
        """Test SMTP connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.smtp_user, self.smtp_pass)
            logger.success("Email connection test successful")
            return True
        except Exception as e:
            logger.error(f"Email connection test failed: {e}")
            return False