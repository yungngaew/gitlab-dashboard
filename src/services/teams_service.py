# src/services/teams_service.py
from typing import Dict, Any
import requests
from datetime import datetime
from ..utils.logger import get_logger
import time

logger = get_logger(__name__)

class TeamsWebhookService:
    """Service for sending messages to Microsoft Teams via webhook."""
    
    def send_message(self, webhook_url: str, message: Dict[str, Any]) -> bool:
        """Send message to Teams channel via webhook.
        
        Args:
            webhook_url: Teams webhook URL
            message: Message payload in Teams card format
            
        Returns:
            bool: True if successful
        """
        try:
            response = requests.post(webhook_url, json=message)
            response.raise_for_status()
            logger.info("Successfully sent message to Teams")
            return True
        except Exception as e:
            logger.error(f"Failed to send Teams message: {e}")
            return False
    
    def format_report_for_teams(self, report_data: Dict[str, Any], report_type: str = 'kickoff') -> Dict[str, Any]:
        """Format report data as Teams message card.
        
        Args:
            report_data: Report data dictionary
            report_type: Either 'kickoff' or 'wrapup'
            
        Returns:
            Teams message card payload
        """
        # Get summary data
        summary = report_data.get('executive_summary', {})
        key_metrics = summary.get('key_metrics', {})
        
        # Create Teams message card
        return {
            "type": "message",
            "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "version": "1.0",
                    "body": [
                        {
                            "type": "TextBlock",
                            "size": "Large",
                            "weight": "Bolder",
                            "text": f"{'Weekly Kickoff' if report_type == 'kickoff' else 'Weekly Wrap-up'} Report"
                        },
                        {
                            "type": "TextBlock",
                            "text": datetime.now().strftime("%Y-%m-%d"),
                            "spacing": "None"
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {
                                    "title": "Total Commits:",
                                    "value": str(key_metrics.get('total_commits', 0))
                                },
                                {
                                    "title": "Active Contributors:",
                                    "value": str(key_metrics.get('active_contributors', 0))
                                },
                                {
                                    "title": "Healthy Projects:",
                                    "value": str(key_metrics.get('healthy_projects', 0))
                                }
                            ]
                        },
                        {
                            "type": "TextBlock",
                            "text": "Projects Needing Attention:",
                            "weight": "Bolder",
                            "spacing": "Medium"
                        }
                    ]
                }
            }]
        }
    
    def send_message_with_retry(self, webhook_url: str, message: Dict[str, Any], max_retries: int = 3) -> bool:
          for attempt in range(max_retries):
              if self.send_message(webhook_url, message):
                  return True
              time.sleep(2 ** attempt)  # Exponential backoff
          return False