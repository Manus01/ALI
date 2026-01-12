import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.campaign_agent import CampaignAgent

MOCK_BRAND_DNA = {
    "name": "TestBrand",
    "visual_styles": ["Minimalist"],
    "color_palette": {"primary": "#000000"},
    "target_countries": ["US"],
}


def test_campaign_agent_creative_intent():
    async def _test():
        with patch('app.agents.campaign_agent.get_model') as mock_get_model:
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = json.dumps({
                "objective": "Drive leads",
                "angle": "value-led",
                "hook_type": "authority",
                "hypothesis": "Authority framing will increase CTR"
            })
            mock_model.generate_content_async = AsyncMock(return_value=mock_response)
            mock_get_model.return_value = mock_model

            agent = CampaignAgent()
            intent = await agent.generate_creative_intent(
                "Drive leads",
                MOCK_BRAND_DNA,
                {"Q1": "A1"},
                selected_channels=["linkedin"]
            )

            assert intent["objective"] == "Drive leads"
            assert intent["angle"] == "value-led"
            assert intent["hook_type"] == "authority"
            assert intent["hypothesis"] == "Authority framing will increase CTR"
            assert mock_model.generate_content_async.called

    asyncio.run(_test())
