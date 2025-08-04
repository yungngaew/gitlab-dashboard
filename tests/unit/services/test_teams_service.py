# tests/unit/services/test_teams_service.py
import pytest
from unittest.mock import Mock, patch
from src.services.teams_service import TeamsWebhookService

def test_send_message_success():
    service = TeamsWebhookService()
    with patch('requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        assert service.send_message("fake_url", {"text": "test"}) == True
        mock_post.assert_called_once()

def test_send_message_failure():
    service = TeamsWebhookService()
    with patch('requests.post') as mock_post:
        mock_post.side_effect = Exception("Network error")
        assert service.send_message("fake_url", {"text": "test"}) == False

