"""Email delivery service for weekly productivity reports."""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
import logging
from pathlib import Path

from ..utils.config import Config

logger = logging.getLogger(__name__)


class EmailService:
    """Handle email delivery for weekly reports."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize email service.
        
        Args:
            config: Configuration object with email settings
        """
        self.config = config or Config()
        self.smtp_config = self._get_smtp_config()
    
    def _get_smtp_config(self) -> Dict[str, Any]:
        """Get SMTP configuration from config and environment."""
        # Default values
        defaults = {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'use_tls': True,
            'username': '',
            'password': '',
            'from_email': '',
            'from_name': 'GitLab Analytics'
        }
        
        # Get from config file
        email_config = self.config._config.get('email', {})
        
        # Update with environment variables
        import os
        smtp_config = {
            'smtp_server': os.getenv('SMTP_SERVER', email_config.get('smtp_server', defaults['smtp_server'])),
            'smtp_port': int(os.getenv('SMTP_PORT', email_config.get('smtp_port', defaults['smtp_port']))),
            'use_tls': os.getenv('SMTP_USE_TLS', str(email_config.get('use_tls', defaults['use_tls']))).lower() == 'true',
            'username': os.getenv('SMTP_USERNAME', email_config.get('username', defaults['username'])),
            'password': os.getenv('SMTP_PASSWORD', email_config.get('password', defaults['password'])),
            'from_email': os.getenv('SMTP_FROM_EMAIL', email_config.get('from_email', defaults['from_email'])),
            'from_name': os.getenv('SMTP_FROM_NAME', email_config.get('from_name', defaults['from_name']))
        }
        
        return smtp_config
    
    def send_weekly_report(
        self,
        html_content: str,
        recipients: List[str],
        subject: str = "Weekly Productivity Report",
        attachments: Optional[List[str]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """Send weekly productivity report via email.
        
        Args:
            html_content: HTML content of the email
            recipients: List of recipient email addresses
            subject: Email subject line
            attachments: Optional list of file paths to attach
            cc: Optional list of CC recipients
            bcc: Optional list of BCC recipients
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Validate configuration
            if not self._validate_config():
                return False
            
            # Create message
            message = self._create_message(
                html_content=html_content,
                recipients=recipients,
                subject=subject,
                cc=cc,
                bcc=bcc
            )
            
            # Add attachments
            if attachments:
                for attachment_path in attachments:
                    self._add_attachment(message, attachment_path)
            
            # Send email
            return self._send_email(message, recipients, cc, bcc)
            
        except Exception as e:
            logger.error(f"Failed to send weekly report email: {e}", exc_info=True)
            return False
    
    def send_test_email(
        self,
        recipient: str,
        test_message: str = "This is a test email from GitLab Analytics."
    ) -> bool:
        """Send a test email to verify configuration.
        
        Args:
            recipient: Test recipient email address
            test_message: Test message content
            
        Returns:
            True if test email sent successfully, False otherwise
        """
        try:
            html_content = f"""
            <html>
            <body>
                <h2>GitLab Analytics - Email Test</h2>
                <p>{test_message}</p>
                <p>If you received this email, your email configuration is working correctly.</p>
                <hr>
                <small>Sent from GitLab Analytics Email Service</small>
            </body>
            </html>
            """
            
            return self.send_weekly_report(
                html_content=html_content,
                recipients=[recipient],
                subject="GitLab Analytics - Email Test"
            )
            
        except Exception as e:
            logger.error(f"Failed to send test email: {e}", exc_info=True)
            return False
    
    def _validate_config(self) -> bool:
        """Validate email configuration."""
        required_fields = ['smtp_server', 'smtp_port', 'username', 'password', 'from_email']
        
        for field in required_fields:
            if not self.smtp_config.get(field):
                logger.error(f"Missing required email configuration: {field}")
                return False
        
        return True
    
    def _create_message(
        self,
        html_content: str,
        recipients: List[str],
        subject: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> MIMEMultipart:
        """Create email message."""
        message = MIMEMultipart('alternative')
        
        # Headers
        message['Subject'] = subject
        message['From'] = f"{self.smtp_config['from_name']} <{self.smtp_config['from_email']}>"
        message['To'] = ', '.join(recipients)
        
        if cc:
            message['Cc'] = ', '.join(cc)
        
        # Add HTML content
        html_part = MIMEText(html_content, 'html', 'utf-8')
        message.attach(html_part)
        
        # Add plain text version (simplified)
        plain_text = self._html_to_plain_text(html_content)
        text_part = MIMEText(plain_text, 'plain', 'utf-8')
        message.attach(text_part)
        
        return message
    
    def _add_attachment(self, message: MIMEMultipart, file_path: str) -> None:
        """Add file attachment to email message."""
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"Attachment file not found: {file_path}")
                return
            
            with open(path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {path.name}'
            )
            
            message.attach(part)
            logger.info(f"Added attachment: {path.name}")
            
        except Exception as e:
            logger.error(f"Failed to add attachment {file_path}: {e}")
    
    def _send_email(
        self,
        message: MIMEMultipart,
        recipients: List[str],
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """Send email via SMTP."""
        try:
            # Combine all recipients
            all_recipients = recipients.copy()
            if cc:
                all_recipients.extend(cc)
            if bcc:
                all_recipients.extend(bcc)
            
            # Connect to SMTP server
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_config['smtp_server'], self.smtp_config['smtp_port']) as server:
                if self.smtp_config['use_tls']:
                    server.starttls(context=context)
                
                server.login(self.smtp_config['username'], self.smtp_config['password'])
                
                # Send email
                text = message.as_string()
                server.sendmail(self.smtp_config['from_email'], all_recipients, text)
                
                logger.info(f"Email sent successfully to {len(all_recipients)} recipients")
                return True
                
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed - check username/password")
            return False
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"Recipients refused: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}", exc_info=True)
            return False
    
    def _html_to_plain_text(self, html_content: str) -> str:
        """Convert HTML content to plain text for email compatibility."""
        # Simple HTML to text conversion
        import re
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Add some basic formatting
        text = text.replace('Weekly Productivity Report', 'WEEKLY PRODUCTIVITY REPORT\n' + '='*50)
        text = text.replace('Executive Summary', '\n\nEXECUTIVE SUMMARY\n' + '-'*20)
        text = text.replace('Team Activity', '\n\nTEAM ACTIVITY\n' + '-'*15)
        text = text.replace('Project Health', '\n\nPROJECT HEALTH\n' + '-'*15)
        text = text.replace('Team Performance', '\n\nTEAM PERFORMANCE\n' + '-'*18)
        text = text.replace('Insights & Next Steps', '\n\nINSIGHTS & NEXT STEPS\n' + '-'*22)
        
        return text


class WeeklyReportEmailSender:
    """High-level service for sending weekly productivity report emails."""
    
    def __init__(self, email_service: Optional[EmailService] = None):
        """Initialize weekly report email sender.
        
        Args:
            email_service: Email service instance
        """
        self.email_service = email_service or EmailService()
    
    def send_team_report(
        self,
        report_data: Dict[str, Any],
        recipients: List[str],
        team_name: str = "Development Team",
        include_charts: bool = True,
        attachments: Optional[List[str]] = None
    ) -> bool:
        """Send complete weekly team report via email.
        
        Args:
            report_data: Report data from WeeklyProductivityReporter
            recipients: List of recipient email addresses
            team_name: Name of the team for the report
            include_charts: Whether to include embedded charts
            attachments: Optional list of file paths to attach
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            from ..templates.weekly_report_email import WeeklyReportEmailTemplate
            
            # Generate HTML content
            template = WeeklyReportEmailTemplate()
            html_content = template.generate_html_email(
                report_data=report_data,
                team_name=team_name,
                include_charts=include_charts
            )
            
            # Generate subject line
            metadata = report_data.get('metadata', {})
            week_ending = metadata.get('period_end', '')
            if week_ending:
                from datetime import datetime
                end_date = datetime.fromisoformat(week_ending)
                subject = f"Weekly Productivity Report - {team_name} - Week Ending {end_date.strftime('%B %d, %Y')}"
            else:
                subject = f"Weekly Productivity Report - {team_name}"
            
            # Send email
            return self.email_service.send_weekly_report(
                html_content=html_content,
                recipients=recipients,
                subject=subject,
                attachments=attachments
            )
            
        except Exception as e:
            logger.error(f"Failed to send team report email: {e}", exc_info=True)
            return False
    
    def send_test_email(self, recipient: str) -> bool:
        """Send test email to verify configuration.
        
        Args:
            recipient: Test recipient email address
            
        Returns:
            True if test email sent successfully, False otherwise
        """
        return self.email_service.send_test_email(recipient)