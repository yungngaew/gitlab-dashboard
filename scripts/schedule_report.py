#!/usr/bin/env python3
"""Schedule weekly team reports."""

import sys
from pathlib import Path
from datetime import datetime
import schedule
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.weekly_reports import send_scheduled_report
from src.utils import Config, setup_logging, get_logger

logger = get_logger(__name__)

def send_monday_report():
    """Send Monday kickoff report."""
    config = Config()
    group_ids = config.get_gitlab_config().get('group_ids', [])
    recipients = config.get_email_config().get('recipients', [])
    
    logger.info("Sending Monday kickoff report...")
    send_scheduled_report(group_ids, recipients, 'kickoff')

def send_friday_report():
    """Send Friday wrap-up report."""
    config = Config()
    group_ids = config.get_gitlab_config().get('group_ids', [])
    recipients = config.get_email_config().get('recipients', [])
    
    logger.info("Sending Friday wrap-up report...")
    send_scheduled_report(group_ids, recipients, 'wrapup')

def main():
    """Schedule and run reports."""
    setup_logging()
    
    # Schedule reports
    schedule.every().monday.at("08:30").do(send_monday_report)
    schedule.every().friday.at("08:30").do(send_friday_report)
    
    logger.info("Report scheduler started")
    logger.info("- Monday reports scheduled for 08:30")
    logger.info("- Friday reports scheduled for 08:30")
    
    # Run continuously
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()