import pytest
from unittest.mock import MagicMock, patch
from app.services.metricool_client import MetricoolClient

def test_metricool_timeout_handling():
    """ Verify MetricoolClient handles timeouts effectively. """
    with patch('requests.get') as mock_get:
        # Simulate Timeout
        mock_get.side_effect = Exception("ReadTimeout")
        
        client = MetricoolClient()
        # Should catch exception and return fallback/zero state or re-raise logged error
        # Logic in get_yesterday_stats catches Exception and logs it.
        stats = client.get_yesterday_stats("123")
        
        assert stats["total_spend"] == 0
        assert stats["ctr"] == 0

# NOTE: test_video_agent_fallback_chain removed - VideoAgent deprecated and deleted
