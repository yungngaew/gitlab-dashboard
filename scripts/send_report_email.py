#!/usr/bin/env python3
"""Simple email sender for weekly reports."""

import os
import sys
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

def send_html_email(html_file_path: str, recipient: str, subject: str) -> bool:
    """Send HTML file via email."""
    try:
        # Read HTML content
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Get email configuration from environment
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        from_email = os.getenv('SMTP_FROM_EMAIL', smtp_username)
        from_name = os.getenv('SMTP_FROM_NAME', 'GitLab Analytics')
        
        if not smtp_username or not smtp_password:
            print("❌ Missing SMTP_USERNAME or SMTP_PASSWORD environment variables")
            return False
        
        # Create message
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = f"{from_name} <{from_email}>"
        message['To'] = recipient
        
        # Add HTML content
        html_part = MIMEText(html_content, 'html', 'utf-8')
        message.attach(html_part)
        
        # Send email
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(smtp_username, smtp_password)
            server.sendmail(from_email, [recipient], message.as_string())
        
        print(f"✅ Email sent successfully to: {recipient}")
        return True
        
    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        return False

def main():
    """Main function."""
    if len(sys.argv) < 4:
        print("Usage: python3 send_report_email.py <html_file> <recipient> <subject>")
        return 1
    
    html_file = sys.argv[1]
    recipient = sys.argv[2]
    subject = sys.argv[3]
    
    if not Path(html_file).exists():
        print(f"❌ HTML file not found: {html_file}")
        return 1
    
    success = send_html_email(html_file, recipient, subject)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())