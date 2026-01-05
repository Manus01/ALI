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
        assert agent.agent_name == "BrandMonitoringAgent"
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
        with patch.object(agent.model, 'generate_content_async') as mock_generate:
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
        with patch.object(agent.model, 'generate_content_async') as mock_generate:
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
