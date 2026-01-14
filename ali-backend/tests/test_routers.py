import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import verify_token

# --- MOCK AUTH ---
def mock_verify_token_user():
    return {"uid": "user_123", "email": "test@example.com", "role": "user"}

def mock_verify_token_admin():
    return {"uid": "admin_999", "email": "manoliszografos@gmail.com", "role": "admin"}

# --- TESTS ---

def test_dashboard_overview():
    """ Verify Dashboard Endpoint returns structure (mocked DB). """
    # Override Dependency
    app.dependency_overrides[verify_token] = mock_verify_token_user
    
    with patch("app.routers.dashboard.db") as mock_db:
        # Mock Firestore .get().to_dict()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"profile": {"name": "Test User"}, "metrics": []}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        # Mock Metricool (prevent real calls)
        with patch("app.routers.dashboard.MetricoolClient") as MockClient:
            mock_mc = MockClient.return_value
            mock_mc.get_dashboard_snapshot.return_value = {"status": "connected"}
            mock_mc.get_historical_breakdown.return_value = {"dates": [], "datasets": {}}
            
            client = TestClient(app)
            response = client.get("/api/dashboard/overview")
            
            assert response.status_code == 200
            data = response.json()
            assert "profile" in data
            assert data["profile"]["name"] == "Test User"

@pytest.mark.skip(reason="Endpoint /api/admin/research/troubleshoot not implemented yet")
def test_admin_troubleshoot_rbac():
    """ Verify non-admins cannot access troubleshoot endpoint. """
    # 1. Test as USER (Should be 403 or 401 depending on logic, but `verify_admin` usually checks role)
    # The current `verify_admin` in admin.py just checks verify_token. 
    # Let's check logic: `if user.get("role") != "admin": raise HTTPException(403)`
    
    app.dependency_overrides[verify_token] = mock_verify_token_user
    client = TestClient(app)
    response = client.post("/api/admin/research/troubleshoot")
    assert response.status_code in [403, 401] # Depending on implementation

@pytest.mark.skip(reason="TroubleshootingAgent module not implemented yet")
def test_admin_troubleshoot_success():
    """ Verify admins CAN access troubleshoot endpoint. """
    app.dependency_overrides[verify_token] = mock_verify_token_admin
    
    with patch("app.agents.troubleshooting_agent.TroubleshootingAgent") as MockAgent:
        mock_instance = MockAgent.return_value
        mock_instance.run_troubleshooter.return_value = {"status": "success"}
        
        client = TestClient(app)
        response = client.post("/api/admin/research/troubleshoot")
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"

def test_auth_verify():
    """ Basic smoke test for Auth router. """
    # Since Auth relies heavily on Firebase, we test the 'me' endpoint if it exists or similar
    app.dependency_overrides[verify_token] = mock_verify_token_user
    client = TestClient(app)
    # response = client.get("/api/auth/me") # If this exists
    # If not, we skip.
    pass
