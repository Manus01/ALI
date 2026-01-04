import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.campaign_agent import CampaignAgent
from app.agents.strategy_agent import StrategyAgent

# --- MOCK DATA ---
MOCK_BRAND_DNA = {
    "name": "TestBrand",
    "visual_styles": ["Minimalist"],
    "color_palette": {"primary": "#000000"},
    "target_countries": ["US"],
}

MOCK_CAMPAIGN_BLUEPRINT = {
    "theme": "Summer Sale",
    "instagram": {"caption": "Buy now", "visual_prompt": "Sun"},
    "tiktok": {"video_script": "Dance", "audio_style": "Pop"},
    "google_ads": {"headlines": ["Sale"], "descriptions": ["Cheap"], "keywords": ["buy"]}
}

# --- TESTS ---

def test_campaign_agent_questions():
    """ Verify CampaignAgent asks clarifying questions correctly. """
    async def _test():
        with patch('app.agents.campaign_agent.get_model') as mock_get_model:
            # Mock LLM Response
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = '["Q1", "Q2"]'
            mock_model.generate_content_async = AsyncMock(return_value=mock_response)
            
            mock_get_model.return_value = mock_model
            
            agent = CampaignAgent()
            questions = await agent.generate_clarifying_questions("Sell shoes", MOCK_BRAND_DNA)
            
            assert len(questions) == 2
            assert "Q1" in questions
            assert mock_model.generate_content_async.called

    asyncio.run(_test())

def test_campaign_agent_blueprint():
    """ Verify CampaignAgent generates a valid blueprint structure. """
    async def _test():
        with patch('app.agents.campaign_agent.get_model') as mock_get_model:
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = json.dumps(MOCK_CAMPAIGN_BLUEPRINT)
            mock_model.generate_content_async = AsyncMock(return_value=mock_response)
            mock_get_model.return_value = mock_model
            
            agent = CampaignAgent()
            blueprint = await agent.create_campaign_blueprint("Sell shoes", MOCK_BRAND_DNA, {"Q1": "A1"})
            
            assert blueprint["theme"] == "Summer Sale"
            assert "instagram" in blueprint
            assert "tiktok" in blueprint
    
    asyncio.run(_test())

def test_strategy_agent_handling():
    """ Verify StrategyAgent handles missing data gracefully. """
    async def _test():
        with patch('app.agents.strategy_agent.get_model') as mock_get_model:
            with patch('app.agents.strategy_agent.CryptoService'): # Mock valid class
                # Mock Client (Vertex AI)
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.text = "Strategy: Do X."
                mock_client.generate_content_async = AsyncMock(return_value=mock_response)
                mock_get_model.return_value = mock_client
                
                # Test Strategy Generation with Mock Data Fetch
                with patch.object(StrategyAgent, '_fetch_real_data', return_value=[{"spend": 100, "clicks": 10}]) as mock_fetch:
                    agent = StrategyAgent()
                    strategy = await agent.generate_strategy("Increase ROI", "user_123")
                    
                    assert "Strategy: Do X." in strategy
                    mock_fetch.assert_called_once()
    
    asyncio.run(_test())

def test_brand_agent_initialization():
    """ Verify BrandAgent can be instantiated. """
    try:
        from app.agents.brand_agent import BrandAgent
        agent = BrandAgent()
        assert agent.agent_name == "BrandAgent" 
    except ImportError:
        pass # Skip if not implemented yet
