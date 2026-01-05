"""
ROLEPLAY TUTORIAL GENERATION TESTS
===================================
This script tests the `generate_tutorial` function with 10 diverse scenarios.
Each scenario simulates a different topic complexity, user profile, and expected output.

USAGE: python -m pytest tests/roleplay_tutorial_tests.py -v
"""

import unittest
from unittest.mock import MagicMock, patch
import logging
import time
import json
from datetime import datetime
from app.agents.tutorial_agent import generate_tutorial

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("roleplay_tests")

# Test Scenarios - 10 Diverse Topics
TEST_SCENARIOS = [
    {
        "id": 1,
        "topic": "Instagram Reels Algorithm 2025",
        "category": "Social Media",
        "complexity": "HIGH",
        "expected_sections": ["Understanding Reels", "Algorithm Signals", "Content Strategy"]
    },
    {
        "id": 2,
        "topic": "Email Marketing Automation for Beginners",
        "category": "Email Marketing",
        "complexity": "LOW",
        "expected_sections": ["Introduction", "Tools Overview", "First Campaign"]
    },
    {
        "id": 3,
        "topic": "TikTok Shop Setup and Optimization",
        "category": "E-Commerce",
        "complexity": "MEDIUM",
        "expected_sections": ["Account Setup", "Product Listing", "Promotion"]
    },
    {
        "id": 4,
        "topic": "Google Ads Performance Max Campaigns",
        "category": "Paid Advertising",
        "complexity": "HIGH",
        "expected_sections": ["Campaign Types", "Asset Groups", "Optimization"]
    },
    {
        "id": 5,
        "topic": "Content Repurposing: Blog to Video Pipeline",
        "category": "Content Strategy",
        "complexity": "MEDIUM",
        "expected_sections": ["Content Selection", "Script Writing", "Video Production"]
    },
    {
        "id": 6,
        "topic": "LinkedIn Thought Leadership Strategy",
        "category": "B2B Marketing",
        "complexity": "MEDIUM",
        "expected_sections": ["Profile Optimization", "Post Cadence", "Engagement"]
    },
    {
        "id": 7,
        "topic": "Influencer Marketing ROI Measurement",
        "category": "Influencer Marketing",
        "complexity": "HIGH",
        "expected_sections": ["KPI Selection", "Tracking Methods", "Reporting"]
    },
    {
        "id": 8,
        "topic": "YouTube Shorts vs TikTok: Platform Comparison",
        "category": "Platform Strategy",
        "complexity": "LOW",
        "expected_sections": ["Audience Demographics", "Algorithm Differences", "Best Practices"]
    },
    {
        "id": 9,
        "topic": "Customer Journey Mapping with Analytics",
        "category": "Analytics",
        "complexity": "HIGH",
        "expected_sections": ["Touchpoint Identification", "Data Collection", "Visualization"]
    },
    {
        "id": 10,
        "topic": "AI Tools for Social Media Managers",
        "category": "Productivity",
        "complexity": "LOW",
        "expected_sections": ["Tool Categories", "Use Cases", "Workflow Integration"]
    }
]

class TestTutorialGenerationRoleplay(unittest.TestCase):
    """
    Role-Play Test Suite: Simulates real user tutorial requests.
    Each test mocks the LLM and Asset Agents to validate the pipeline.
    """

    @patch('app.agents.tutorial_agent.db')
    @patch('app.agents.tutorial_agent.VideoAgent')
    @patch('app.agents.tutorial_agent.ImageAgent')
    @patch('app.agents.tutorial_agent.AudioAgent')
    @patch('app.agents.tutorial_agent.generate_curriculum_blueprint')
    @patch('app.agents.tutorial_agent.write_section_narrative')
    @patch('app.agents.tutorial_agent.design_section_assets')
    @patch('app.agents.tutorial_agent.review_tutorial_quality')
    def test_all_scenarios(self, mock_review, mock_assets, mock_narrative, mock_blueprint,
                           mock_audio, mock_image, mock_video, mock_db):
        """
        Runs through all 10 scenarios and logs results.
        """
        results = []
        
        for scenario in TEST_SCENARIOS:
            logger.info(f"\n{'='*60}")
            logger.info(f"🎬 SCENARIO {scenario['id']}: {scenario['topic']}")
            logger.info(f"   Category: {scenario['category']} | Complexity: {scenario['complexity']}")
            logger.info(f"{'='*60}")
            
            # Configure Mocks for this scenario
            mock_blueprint.return_value = {
                "course_title": scenario['topic'],
                "pedagogical_metaphor": "Building a Foundation",
                "sections": [
                    {"title": sec, "type": "supportive", "goal": f"Explain {sec}"}
                    for sec in scenario['expected_sections']
                ],
                "estimated_duration": "15 mins",
                "difficulty": "Intermediate"
            }
            
            mock_narrative.return_value = f"This is the detailed educational content about {scenario['topic']}. " * 10
            
            mock_assets.return_value = {
                "assets": [
                    {"type": "video_clip", "visual_prompt": f"Cinematic {scenario['topic']}"},
                    {"type": "quiz_single", "question": "What did you learn?", "options": ["A", "B", "C", "D"], "correct_answer": 0}
                ]
            }
            
            mock_review.return_value = {"score": 85, "status": "PASSED", "feedback": "Well structured."}

            # Mock Agents
            mock_video.return_value.generate_video.return_value = "https://storage.googleapis.com/mock/video.mp4"
            mock_image.return_value.generate_image.return_value = "https://storage.googleapis.com/mock/image.png"
            mock_audio.return_value.generate_audio.return_value = "https://storage.googleapis.com/mock/audio.mp3"

            # Execute
            start_time = time.time()
            try:
                result = generate_tutorial(
                    user_id=f"test_user_{scenario['id']}",
                    topic=scenario['topic']
                )
                duration = time.time() - start_time
                
                # Validate Result Structure
                has_title = 'title' in result
                has_sections = 'sections' in result and len(result['sections']) > 0
                has_assets = all('blocks' in sec for sec in result.get('sections', []))
                
                status = "✅ PASSED" if (has_title and has_sections and has_assets) else "❌ FAILED"
                
                results.append({
                    "scenario": scenario['id'],
                    "topic": scenario['topic'],
                    "status": status,
                    "duration": f"{duration:.2f}s",
                    "sections_count": len(result.get('sections', [])),
                    "error": None
                })
                
                logger.info(f"   {status} | Duration: {duration:.2f}s | Sections: {len(result.get('sections', []))}")
                
            except Exception as e:
                duration = time.time() - start_time
                results.append({
                    "scenario": scenario['id'],
                    "topic": scenario['topic'],
                    "status": "❌ EXCEPTION",
                    "duration": f"{duration:.2f}s",
                    "sections_count": 0,
                    "error": str(e)
                })
                logger.error(f"   ❌ EXCEPTION: {e}")
        
        # Summary Report
        logger.info(f"\n{'='*60}")
        logger.info("📊 ROLEPLAY TEST SUMMARY")
        logger.info(f"{'='*60}")
        passed = sum(1 for r in results if "PASSED" in r['status'])
        failed = len(results) - passed
        logger.info(f"   Total: {len(results)} | Passed: {passed} | Failed: {failed}")
        
        for r in results:
            logger.info(f"   [{r['scenario']:02d}] {r['status']} - {r['topic'][:40]}...")
            if r['error']:
                logger.info(f"        Error: {r['error'][:80]}")
        
        # Assert all passed
        self.assertEqual(failed, 0, f"{failed} scenarios failed. See logs for details.")

if __name__ == '__main__':
    unittest.main()
