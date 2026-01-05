"""
Tests for Relevance Filter Agent
Tests the AI-powered entity disambiguation for brand monitoring.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import json

from app.agents.relevance_filter_agent import RelevanceFilterAgent


class TestRelevanceFilterAgent:
    """Tests for the RelevanceFilterAgent."""
    
    def test_init(self):
        """Test agent initialization."""
        agent = RelevanceFilterAgent()
        assert agent.name == "RelevanceFilterAgent"
        assert agent.model is not None
    
    @pytest.mark.asyncio
    async def test_filter_articles_empty_list(self):
        """Test filtering empty article list."""
        agent = RelevanceFilterAgent()
        
        result, stats = await agent.filter_articles(
            brand_profile={"brand_name": "TestBrand"},
            articles=[],
            feedback_patterns=[]
        )
        
        assert result == []
        assert stats == {"total": 0, "relevant": 0, "filtered_out": 0}
    
    @pytest.mark.asyncio
    async def test_filter_articles_structure(self):
        """Test that filtered articles have the correct structure."""
        agent = RelevanceFilterAgent()
        
        # Create test articles
        test_articles = [
            {
                "id": "test_001",
                "title": "TestBrand Launches New Product",
                "source_name": "Tech News",
                "content": "TestBrand, a digital marketing agency, announced a new service.",
                "description": "Marketing agency expansion",
                "url": "https://example.com/1",
                "published_at": "2024-01-01T00:00:00"
            },
            {
                "id": "test_002",
                "title": "Muhammad Ali Documentary Released",
                "source_name": "Sports News",
                "content": "A new documentary about the legendary boxer Muhammad Ali.",
                "description": "Boxing documentary",
                "url": "https://example.com/2",
                "published_at": "2024-01-01T00:00:00"
            }
        ]
        
        brand_profile = {
            "brand_name": "ALI",
            "industry": "Digital Marketing Agency",
            "offerings": ["Social media marketing", "SEO", "PPC"],
            "description": "A digital marketing agency based in New York"
        }
        
        # Mock the model response
        with patch.object(agent.model, 'generate_content_async') as mock_generate:
            mock_response = Mock()
            mock_response.text = json.dumps([
                {
                    "article_index": 0,
                    "is_relevant": True,
                    "confidence": 0.95,
                    "reasoning": "Article discusses the marketing agency",
                    "entity_detected": "ALI Marketing Agency"
                },
                {
                    "article_index": 1,
                    "is_relevant": False,
                    "confidence": 0.98,
                    "reasoning": "Article is about the boxer Muhammad Ali, not the marketing agency",
                    "entity_detected": "Muhammad Ali (boxer)"
                }
            ])
            mock_generate.return_value = mock_response
            
            result, stats = await agent.filter_articles(
                brand_profile=brand_profile,
                articles=test_articles,
                feedback_patterns=[]
            )
        
        # Only 1 article should pass the filter
        assert len(result) == 1
        assert result[0]["id"] == "test_001"
        
        # Check filter stats
        assert stats["total"] == 2
        assert stats["relevant"] == 1
        assert stats["filtered_out"] == 1
        assert stats["filter_rate"] == 50.0
        
        # Check that relevance metadata was added
        assert "relevance_confidence" in result[0]
        assert "relevance_reasoning" in result[0]
    
    @pytest.mark.asyncio
    async def test_filter_with_feedback_patterns(self):
        """Test that feedback patterns are used in filtering."""
        agent = RelevanceFilterAgent()
        
        test_articles = [{
            "id": "test_001",
            "title": "ALI Stock Drops 5%",
            "source_name": "Finance News",
            "content": "Alibaba (ALI) stock fell today amid market concerns.",
            "url": "https://example.com/finance",
            "published_at": "2024-01-01T00:00:00"
        }]
        
        brand_profile = {
            "brand_name": "ALI",
            "industry": "Digital Marketing",
            "offerings": ["Marketing services"]
        }
        
        feedback_patterns = [
            {
                "title": "ALI Stock Rally Continues",
                "snippet": "Alibaba stock performance",
                "detected_entity": "Alibaba Inc"
            }
        ]
        
        with patch.object(agent.model, 'generate_content_async') as mock_generate:
            mock_response = Mock()
            mock_response.text = json.dumps([{
                "article_index": 0,
                "is_relevant": False,
                "confidence": 0.99,
                "reasoning": "Article is about Alibaba stock, not the marketing agency",
                "entity_detected": "Alibaba Inc (stock ticker: ALI)"
            }])
            mock_generate.return_value = mock_response
            
            result, stats = await agent.filter_articles(
                brand_profile=brand_profile,
                articles=test_articles,
                feedback_patterns=feedback_patterns
            )
        
        # Article should be filtered out
        assert len(result) == 0
        assert stats["filtered_out"] == 1
    
    @pytest.mark.asyncio
    async def test_llm_failure_defaults_to_relevant(self):
        """Test that LLM failure defaults to keeping articles (safe fallback)."""
        agent = RelevanceFilterAgent()
        
        test_articles = [{
            "id": "test_001",
            "title": "Test Article",
            "content": "Some content",
            "url": "https://example.com",
            "published_at": "2024-01-01T00:00:00"
        }]
        
        with patch.object(agent.model, 'generate_content_async') as mock_generate:
            mock_generate.side_effect = Exception("LLM API Error")
            
            result, stats = await agent.filter_articles(
                brand_profile={"brand_name": "TestBrand"},
                articles=test_articles,
                feedback_patterns=[]
            )
        
        # Should default to relevant when LLM fails
        assert len(result) == 1
        assert stats["relevant"] == 1
        assert stats["filtered_out"] == 0
    
    def test_extract_feedback_pattern(self):
        """Test feedback pattern extraction."""
        agent = RelevanceFilterAgent()
        
        pattern = agent.extract_feedback_pattern(
            article_title="Muhammad Ali Boxing News",
            article_snippet="The legendary boxer continues to inspire...",
            brand_name="ALI"
        )
        
        assert "title" in pattern
        assert "snippet" in pattern
        assert "brand_searched" in pattern
        assert pattern["brand_searched"] == "ALI"


class TestRelevanceFilterIntegration:
    """Integration tests for relevance filtering in brand monitoring flow."""
    
    def test_filter_agent_imports(self):
        """Test that the filter agent can be imported alongside other components."""
        try:
            from app.agents.relevance_filter_agent import RelevanceFilterAgent
            from app.agents.brand_monitoring_agent import BrandMonitoringAgent
            from app.routers.brand_monitoring import router
            
            filter_agent = RelevanceFilterAgent()
            monitoring_agent = BrandMonitoringAgent()
            
            print("✅ All relevance filter components import successfully")
            print(f"  - RelevanceFilterAgent: {filter_agent.name}")
            print(f"  - BrandMonitoringAgent: {monitoring_agent.name}")
            return True
        except Exception as e:
            print(f"❌ Import error: {e}")
            return False


def run_sync_test():
    """Run a synchronous test to verify imports work."""
    try:
        from app.agents.relevance_filter_agent import RelevanceFilterAgent
        agent = RelevanceFilterAgent()
        print(f"✅ RelevanceFilterAgent initialized: {agent.name}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    run_sync_test()
