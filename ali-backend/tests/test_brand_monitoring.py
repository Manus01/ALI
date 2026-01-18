"""
Tests for Brand Monitoring Feature
Tests the news client, brand monitoring agent, and API endpoints.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
import asyncio

# Import the modules to test
from app.services.news_client import NewsClient
from app.agents.brand_monitoring_agent import BrandMonitoringAgent


class TestNewsClient:
    """Tests for the NewsClient service."""
    
    def test_init(self):
        """Test NewsClient initialization."""
        client = NewsClient()
        assert client.base_url == "https://newsdata.io/api/1/latest"
    
    def test_mock_data_structure(self):
        """Test that mock data has the correct structure."""
        client = NewsClient()
        mock_data = client._get_mock_data("TestBrand")
        
        assert isinstance(mock_data, list)
        assert len(mock_data) > 0
        
        # Verify structure of mock articles
        for article in mock_data:
            assert "id" in article
            assert "title" in article
            assert "source" in article
            assert "content" in article
            assert "url" in article
            assert "published_at" in article
    
    def test_mock_data_includes_negative(self):
        """Test that mock data includes negative sentiments for testing."""
        client = NewsClient()
        mock_data = client._get_mock_data("TestBrand")
        
        # Check that there's at least one article with keywords suggesting negative content
        negative_keywords = ["complaint", "scrutiny", "scandal", "investigation"]
        has_negative = any(
            any(keyword.lower() in article.get("title", "").lower() or 
                keyword.lower() in article.get("content", "").lower()
                for keyword in negative_keywords)
            for article in mock_data
        )
        assert has_negative, "Mock data should include negative sentiment articles for testing"
    
    @pytest.mark.asyncio
    async def test_search_brand_mentions_no_api_key(self):
        """Test that search returns mock data when API key is not set."""
        client = NewsClient()
        client.api_key = ""  # Ensure no API key
        
        articles = await client.search_brand_mentions("TestBrand")
        
        assert isinstance(articles, list)
        assert len(articles) > 0


class TestBrandMonitoringAgent:
    """Tests for the BrandMonitoringAgent."""
    
    def test_init(self):
        """Test agent initialization."""
        agent = BrandMonitoringAgent()
        assert agent.name == "BrandMonitoringAgent"
        assert agent.model is not None
    
    @pytest.mark.asyncio
    async def test_analyze_mentions_empty_list(self):
        """Test analyzing empty article list."""
        agent = BrandMonitoringAgent()
        
        result = await agent.analyze_mentions("TestBrand", [])
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_analyze_mentions_structure(self):
        """Test that analyzed mentions have the correct structure."""
        agent = BrandMonitoringAgent()
        
        # Create a mock article
        test_articles = [{
            "id": "test_001",
            "title": "Test Article",
            "source": "test_source",
            "source_name": "Test Source",
            "content": "This is a test article content.",
            "description": "Test description",
            "url": "https://example.com",
            "published_at": "2024-01-01T00:00:00"
        }]
        
        # Mock the model response
        with patch.object(agent.model, 'generate_content_async', new_callable=AsyncMock) as mock_generate:
            mock_response = Mock()
            mock_response.text = '''[
                {
                    "article_index": 0,
                    "sentiment": "neutral",
                    "sentiment_score": 0.0,
                    "severity": null,
                    "key_concerns": [],
                    "summary": "Test article summary"
                }
            ]'''
            mock_generate.return_value = mock_response
            
            result = await agent.analyze_mentions("TestBrand", test_articles)
        
        assert len(result) == 1
        assert "sentiment" in result[0]
        assert "sentiment_score" in result[0]
        assert result[0]["sentiment"] in ["positive", "neutral", "negative"]
    
    @pytest.mark.asyncio
    async def test_get_crisis_response_structure(self):
        """Test that crisis response has the expected structure."""
        agent = BrandMonitoringAgent()
        
        negative_mention = {
            "id": "test_negative",
            "title": "Company Faces Criticism",
            "source_name": "News Source",
            "content": "Customers are unhappy with the service.",
            "severity": 7,
            "key_concerns": ["service issues"],
            "ai_summary": "Negative press coverage"
        }
        
        # Mock the model response
        with patch.object(agent.model, 'generate_content_async', new_callable=AsyncMock) as mock_generate:
            mock_response = Mock()
            mock_response.text = '''{
                "executive_summary": "The company is facing criticism.",
                "escalation_level": "medium",
                "recommended_actions": [
                    {
                        "priority": 1,
                        "action": "Issue statement",
                        "rationale": "Address concerns",
                        "owner": "PR Team"
                    }
                ],
                "response_templates": {
                    "press_statement": "We are addressing this.",
                    "social_media": "We hear you.",
                    "internal_memo": "Team, we are working on this."
                },
                "timeline": {
                    "immediate": "Issue statement",
                    "short_term": "Follow up",
                    "long_term": "Implement changes"
                },
                "do_not_say": ["We are not responsible"],
                "key_messages": ["We care about our customers"]
            }'''
            mock_generate.return_value = mock_response
            
            result = await agent.get_crisis_response(negative_mention)
        
        assert result["status"] == "success"
        assert "executive_summary" in result
        assert "escalation_level" in result
        assert "recommended_actions" in result
        assert isinstance(result["recommended_actions"], list)


class TestBrandMonitoringEndpoints:
    """Integration tests for the brand monitoring API endpoints."""
    
    def test_mentions_endpoint_exists(self):
        """Test that the mentions endpoint is registered."""
        from app.main import app
        
        # Check if the route exists
        routes = [route.path for route in app.routes]
        assert any("/brand-monitoring/mentions" in route or "mentions" in route for route in routes), \
            "Brand monitoring mentions endpoint should be registered"
    
    def test_crisis_response_endpoint_exists(self):
        """Test that the crisis-response endpoint is registered."""
        from app.main import app
        
        routes = [route.path for route in app.routes]
        assert any("/brand-monitoring/crisis-response" in route or "crisis-response" in route for route in routes), \
            "Brand monitoring crisis-response endpoint should be registered"
    
    def test_evidence_export_endpoint_exists(self):
        """Test that the evidence export endpoint is registered."""
        from app.main import app
        
        routes = [route.path for route in app.routes]
        assert any("evidence-report" in route and "export" in route for route in routes), \
            "Evidence export endpoint should be registered"


class TestEvidencePackageExport:
    """Tests for Evidence Package ZIP export functionality."""
    
    def test_zip_builder_utility_import(self):
        """Test that zip_builder utility can be imported."""
        from app.utils.zip_builder import (
            build_evidence_package_zip,
            serialize_deterministic,
            compute_file_hash,
            flatten_sources,
            get_export_filename
        )
        assert callable(build_evidence_package_zip)
        assert callable(serialize_deterministic)
    
    def test_serialize_deterministic_sorts_keys(self):
        """Test that JSON serialization is deterministic."""
        from app.utils.zip_builder import serialize_deterministic
        
        # Keys in different order should produce same output
        data1 = {"b": 1, "a": 2, "c": 3}
        data2 = {"c": 3, "a": 2, "b": 1}
        
        result1 = serialize_deterministic(data1)
        result2 = serialize_deterministic(data2)
        
        assert result1 == result2, "Serialization should be deterministic"
        assert '"a": 2' in result1, "Keys should be sorted"
    
    def test_compute_file_hash_sha256(self):
        """Test SHA-256 hash computation."""
        from app.utils.zip_builder import compute_file_hash
        
        content = b"test content"
        hash_result = compute_file_hash(content)
        
        assert len(hash_result) == 64, "SHA-256 produces 64-char hex"
        # Verify against known hash
        import hashlib
        expected = hashlib.sha256(content).hexdigest()
        assert hash_result == expected
    
    def test_flatten_sources_sorting(self):
        """Test that sources are sorted by collected_at then url."""
        from app.utils.zip_builder import flatten_sources
        
        report = {
            "items": [
                {
                    "id": "item-1",
                    "sources": [
                        {"id": "src-3", "collected_at": "2026-01-18T03:00:00Z", "url": "https://b.com"},
                        {"id": "src-1", "collected_at": "2026-01-18T01:00:00Z", "url": "https://a.com"},
                        {"id": "src-2", "collected_at": "2026-01-18T02:00:00Z", "url": "https://a.com"},
                    ]
                }
            ]
        }
        
        flattened = flatten_sources(report)
        
        assert len(flattened) == 3
        assert flattened[0]["id"] == "src-1"  # Earliest time
        assert flattened[1]["id"] == "src-2"  # Next time
        assert flattened[2]["id"] == "src-3"  # Latest time
    
    def test_build_evidence_package_zip_structure(self):
        """Test that ZIP package contains required files."""
        from app.utils.zip_builder import build_evidence_package_zip
        import zipfile
        import io
        
        mock_report = {
            "id": "RPT-TEST123",
            "chain_valid": True,
            "report_hash": "abc123def456",
            "hash_algorithm": "SHA-256",
            "items": []
        }
        
        zip_bytes = build_evidence_package_zip(
            report=mock_report,
            user_id="test-user",
            request_id="req-123"
        )
        
        # Verify it's a valid ZIP
        zip_buffer = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            names = zf.namelist()
            
            assert "report.json" in names
            assert "sources.json" in names
            assert "integrity.json" in names
            assert "manifest.json" in names
            
            # Verify integrity.json content
            import json
            integrity_content = json.loads(zf.read("integrity.json"))
            assert integrity_content["verified"] == True
            assert integrity_content["algorithm"] == "SHA-256"
            assert integrity_content["requestId"] == "req-123"
    
    def test_get_export_filename_sanitizes_id(self):
        """Test filename generation with sanitization."""
        from app.utils.zip_builder import get_export_filename
        
        report = {"id": "RPT-ABC123DEF4"}
        filename = get_export_filename(report)
        
        assert filename == "evidence-RPT-ABC123DEF4.zip"
        assert "/" not in filename
        assert "\\" not in filename
    
    def test_provenance_json_in_zip(self):
        """Test that ZIP contains provenance.json with required fields."""
        from app.utils.zip_builder import build_evidence_package_zip
        import zipfile
        import io
        import json
        
        mock_report = {
            "id": "RPT-PROV123",
            "chain_valid": True,
            "report_hash": "abc123",
            "hash_algorithm": "SHA-256",
            "items": []
        }
        
        zip_bytes = build_evidence_package_zip(
            report=mock_report,
            user_id="test-user@example.com",
            request_id="req-provenance-test",
            environment="testing",
            app_version="1.0.0-test"
        )
        
        zip_buffer = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            assert "provenance.json" in zf.namelist()
            
            provenance = json.loads(zf.read("provenance.json"))
            
            # Verify required fields
            assert "exported_at" in provenance
            assert provenance["exported_by"] == "test-user@example.com"
            assert provenance["request_id"] == "req-provenance-test"
            assert provenance["environment"] == "testing"
            assert provenance["app_version"] == "1.0.0-test"
            
            # Verify exported_at is ISO format with Z suffix
            assert provenance["exported_at"].endswith("Z")
    
    def test_integrity_json_contains_package_hash(self):
        """Test that integrity.json contains non-empty packageHash."""
        from app.utils.zip_builder import build_evidence_package_zip
        import zipfile
        import io
        import json
        
        mock_report = {
            "id": "RPT-HASH123",
            "chain_valid": True,
            "report_hash": "def456",
            "hash_algorithm": "SHA-256",
            "items": []
        }
        
        zip_bytes = build_evidence_package_zip(
            report=mock_report,
            user_id="test-user",
            request_id="req-hash-test"
        )
        
        zip_buffer = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            integrity = json.loads(zf.read("integrity.json"))
            
            assert "packageHash" in integrity
            assert len(integrity["packageHash"]) == 64  # SHA-256 = 64 hex chars
            assert integrity["packageHash"] != ""
    
    def test_package_hash_matches_manifest_sha256(self):
        """Test that packageHash equals SHA256(manifest.json bytes)."""
        from app.utils.zip_builder import build_evidence_package_zip, compute_file_hash
        import zipfile
        import io
        import json
        
        mock_report = {
            "id": "RPT-VERIFY123",
            "chain_valid": True,
            "report_hash": "ghi789",
            "hash_algorithm": "SHA-256",
            "items": []
        }
        
        zip_bytes = build_evidence_package_zip(
            report=mock_report,
            user_id="verifier",
            request_id="req-verify-test"
        )
        
        zip_buffer = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            # Read manifest.json raw bytes
            manifest_bytes = zf.read("manifest.json")
            
            # Compute expected hash
            expected_hash = compute_file_hash(manifest_bytes)
            
            # Read packageHash from integrity.json
            integrity = json.loads(zf.read("integrity.json"))
            actual_hash = integrity["packageHash"]
            
            assert actual_hash == expected_hash, \
                f"packageHash mismatch: {actual_hash} != {expected_hash}"


def run_sync_test():
    """Run a synchronous test to verify imports work."""
    try:
        from app.services.news_client import NewsClient
        from app.agents.brand_monitoring_agent import BrandMonitoringAgent
        from app.routers.brand_monitoring import router
        
        client = NewsClient()
        agent = BrandMonitoringAgent()
        
        print("✅ All brand monitoring modules import successfully")
        print(f"  - NewsClient: {client.base_url}")
        print(f"  - BrandMonitoringAgent: {agent.agent_name}")
        print(f"  - Router endpoints: {len(router.routes)}")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False


if __name__ == "__main__":
    # Run a quick import check
    run_sync_test()

