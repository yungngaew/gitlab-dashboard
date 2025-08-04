# tests/unit/services/test_history_service.py
import pytest
from pathlib import Path
from src.services.history_service import HistoryService

@pytest.fixture
def history_service(tmp_path):
    return HistoryService(str(tmp_path))

def test_save_report(history_service):
    report_data = {"test": "data"}
    filepath = history_service.save_report(report_data, "kickoff")
    assert Path(filepath).exists()
    
def test_cleanup_old_reports(history_service):
    # Create test reports
    report_data = {"test": "data"}
    history_service.save_report(report_data, "kickoff")
    
    # Test cleanup
    history_service.cleanup_old_reports(retention_days=0)
    assert len(list(Path(history_service.history_dir).glob("*.json"))) == 0