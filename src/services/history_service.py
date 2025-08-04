# src/services/history_service.py
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timedelta
from ..utils.logger import get_logger

logger = get_logger(__name__)

class HistoryService:
    """Service for managing report history."""
    
    def __init__(self, history_dir: str = "reports/history"):
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
    
    def save_report(self, report_data: Dict[str, Any], report_type: str) -> str:
        """Save report to history.
        
        Args:
            report_data: Report data dictionary
            report_type: Either 'kickoff' or 'wrapup'
            
        Returns:
            str: Path to saved report file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"{report_type}_{timestamp}.json"
        filepath = self.history_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"Saved report to history: {filepath}")
        return str(filepath)
    
    def cleanup_old_reports(self, retention_days: int = 90) -> None:
        """Delete reports older than retention period.
        
        Args:
            retention_days: Number of days to keep reports
        """
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        for file in self.history_dir.glob("*.json"):
            try:
                # Parse date from filename (e.g., kickoff_20240315_0900.json)
                file_date = datetime.strptime(file.stem.split('_')[1], '%Y%m%d')
                if file_date < cutoff_date:
                    file.unlink()
                    logger.info(f"Deleted old report: {file}")
            except (ValueError, IndexError):
                logger.warning(f"Could not parse date from filename: {file}")
    
    def get_recent_reports(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get reports from the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of report data dictionaries
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        reports = []
        
        for file in sorted(self.history_dir.glob("*.json"), reverse=True):
            try:
                file_date = datetime.strptime(file.stem.split('_')[1], '%Y%m%d')
                if file_date >= cutoff_date:
                    with open(file, 'r', encoding='utf-8') as f:
                        reports.append(json.load(f))
            except (ValueError, IndexError, json.JSONDecodeError) as e:
                logger.warning(f"Error reading report {file}: {e}")
        
        return reports