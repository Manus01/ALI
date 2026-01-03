import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestTroubleshootingAgent(unittest.TestCase):

    @patch('app.agents.troubleshooting_agent.cloud_logging')
    @patch('app.agents.troubleshooting_agent.get_model')
    @patch('app.agents.troubleshooting_agent.db')
    def test_end_to_end_flow(self, mock_db, mock_get_model, mock_logging):
        """ Verify logic: Fetch Logs -> Analyze -> Report """
        
        # 1. Mock Cloud Logging
        mock_client = MagicMock()
        mock_logging.Client.return_value = mock_client
        
        # Create a mock Log Entry
        mock_entry = MagicMock()
        mock_entry.payload = "Error: ConnectionRefusedError at /api/users"
        mock_entry.timestamp = "2026-01-01T12:00:00Z"
        mock_entry.resource.labels = {"service": "api"}
        
        mock_client.list_entries.return_value = [mock_entry]
        
        # 2. Mock LLM
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        
        mock_response = MagicMock()
        # Return valid JSON for the analysis
        mock_response.text = '{"root_cause": "Cloud SQL Connection Limit Reached", "sre_assessment": "Critical unavailability of persistence layer.", "suggested_fix": "Increase max_connections flag or upgrade tier.", "is_transient": false, "severity": "HIGH", "relevant_gcp_doc": "https://cloud.google.com/sql/docs/mysql/flags"}'
        mock_model.generate_content.return_value = mock_response
        
        # 3. Mock Firestore (Check for duplicate check and add)
        # Mocking the duplicate check query chain: db.collection...where...stream()
        mock_stream = MagicMock()
        mock_stream.__iter__.return_value = [] # No existing tasks found
        mock_db.collection().where().where().where().limit().stream.return_value = mock_stream
        
        # Import and Run
        from app.agents.troubleshooting_agent import TroubleshootingAgent
        agent = TroubleshootingAgent()
        result = agent.run_troubleshooter()
        
        # Assertions
        print("\n[TEST IMPLEMENTATION] Verifying Logic...")
        
        # Checked Logs?
        mock_client.list_entries.assert_called_once()
        print("   [OK] Fetched Logs")
        
        # Called AI?
        mock_model.generate_content.assert_called_once()
        args, kwargs = mock_model.generate_content.call_args
        self.assertIn("ConnectionRefusedError", args[0])
        print("   [OK] Prompted AI with Error")
        
        # Saved Task?
        mock_db.collection('admin_tasks').add.assert_called_once()
        print("   [OK] Created Admin Task")
        
        self.assertEqual(result['reports_filed'], 1)
        print("[SUCCESS] End-to-End Flow Verified")

if __name__ == '__main__':
    unittest.main()
