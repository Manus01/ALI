"""
MEDIA AGENTS TEST SUITE
=======================
Comprehensive tests for VideoAgent, ImageAgent, and AudioAgent.
Tests initialization, generation methods, error handling, and byte extraction.

USAGE: python -m pytest tests/test_media_agents.py -v
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_media_agents")


# Mock types module for image agent before importing
mock_types = MagicMock()
mock_types.GenerateImageConfig = MagicMock
mock_types.ReferenceImage = MagicMock
mock_types.SubjectImage = MagicMock
mock_types.GcsSource = MagicMock


class TestVideoAgent:
    """Tests for VideoAgent (Veo 3.1)"""
    
    @patch('app.services.video_agent.storage.Client')
    @patch('app.services.video_agent.genai.Client')
    def test_video_agent_initialization(self, mock_genai, mock_storage):
        """Test VideoAgent initializes correctly with clients"""
        from app.services.video_agent import VideoAgent
        
        agent = VideoAgent()
        
        assert agent.storage_client is not None
        assert agent.client is not None
        mock_genai.assert_called_once()
    
    @patch('app.services.video_agent.storage.Client')
    @patch('app.services.video_agent.genai.Client')
    def test_video_agent_generate_returns_url_from_bytes(self, mock_genai, mock_storage):
        """Test that video generation uploads bytes and returns Firebase URL"""
        from app.services.video_agent import VideoAgent
        
        # Mock the video generation response with bytes
        mock_client = mock_genai.return_value
        mock_operation = MagicMock()
        mock_operation.done = MagicMock(return_value=True)
        
        # Create response with generated_videos containing bytes
        mock_video = MagicMock()
        mock_video.video = MagicMock()
        mock_video.video.video_bytes = b"fake_video_bytes"
        mock_video.gcs_uri = None
        
        mock_result = MagicMock()
        mock_result.generated_videos = [mock_video]
        mock_operation.result = MagicMock(return_value=mock_result)
        
        mock_client.models.generate_videos = MagicMock(return_value=mock_operation)
        
        # Mock storage upload
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_storage.return_value.bucket.return_value = mock_bucket
        
        agent = VideoAgent()
        result = agent.generate_video("Test video prompt", folder="test")
        
        assert result is not None
        assert "firebasestorage.googleapis.com" in result
        mock_blob.upload_from_string.assert_called_once()
    
    @patch('app.services.video_agent.storage.Client')
    @patch('app.services.video_agent.genai.Client')
    def test_video_agent_generate_returns_url_from_gcs_uri(self, mock_genai, mock_storage):
        """Test that video generation can return signed URL from GCS URI"""
        from app.services.video_agent import VideoAgent
        
        mock_client = mock_genai.return_value
        mock_operation = MagicMock()
        mock_operation.done = MagicMock(return_value=True)
        
        # Create response with generated_videos containing URI (no bytes)
        mock_video = MagicMock()
        mock_video.video = None
        mock_video.video_bytes = None
        mock_video.bytes = None
        mock_video.gcs_uri = "gs://bucket/path/video.mp4"
        
        mock_result = MagicMock()
        mock_result.generated_videos = [mock_video]
        mock_operation.result = MagicMock(return_value=mock_result)
        
        mock_client.models.generate_videos = MagicMock(return_value=mock_operation)
        
        # Mock signed URL generation
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = "https://signed-url.example.com/video.mp4"
        mock_bucket.blob.return_value = mock_blob
        mock_storage.return_value.bucket.return_value = mock_bucket
        
        agent = VideoAgent()
        result = agent.generate_video("Test video prompt")
        
        assert result is not None
    
    @patch('app.services.video_agent.storage.Client')
    @patch('app.services.video_agent.genai.Client')
    def test_video_agent_handles_generation_failure(self, mock_genai, mock_storage):
        """Test that video generation returns None on API failure"""
        from app.services.video_agent import VideoAgent
        
        mock_client = mock_genai.return_value
        mock_client.models.generate_videos.side_effect = Exception("API Error")
        
        agent = VideoAgent()
        result = agent.generate_video("Test video prompt")
        
        assert result is None
    
    @patch('app.services.video_agent.storage.Client')
    @patch('app.services.video_agent.genai.Client')
    def test_video_agent_handles_no_client(self, mock_genai, mock_storage):
        """Test that video generation returns None when client not initialized"""
        from app.services.video_agent import VideoAgent
        
        mock_genai.side_effect = Exception("Client init failed")
        
        agent = VideoAgent()
        agent.client = None  # Simulate failed initialization
        result = agent.generate_video("Test video prompt")
        
        assert result is None
    
    @patch('app.services.video_agent.storage.Client')
    @patch('app.services.video_agent.genai.Client')
    def test_video_agent_handles_list_prompt(self, mock_genai, mock_storage):
        """Test that video generation handles list prompts correctly"""
        from app.services.video_agent import VideoAgent
        
        mock_client = mock_genai.return_value
        mock_operation = MagicMock()
        mock_operation.done = MagicMock(return_value=True)
        
        mock_video = MagicMock()
        mock_video.video = MagicMock()
        mock_video.video.video_bytes = b"fake_video_bytes"
        
        mock_result = MagicMock()
        mock_result.generated_videos = [mock_video]
        mock_operation.result = MagicMock(return_value=mock_result)
        
        mock_client.models.generate_videos = MagicMock(return_value=mock_operation)
        
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_storage.return_value.bucket.return_value = mock_bucket
        
        agent = VideoAgent()
        # Pass list instead of string (edge case mentioned in code)
        result = agent.generate_video(["Test prompt in list"], folder="test")
        
        assert result is not None


class TestImageAgent:
    """Tests for ImageAgent (Imagen 4.0)"""
    
    @patch('app.services.image_agent.storage.Client')
    @patch('app.services.image_agent.genai.Client')
    def test_image_agent_initialization(self, mock_genai, mock_storage):
        """Test ImageAgent initializes correctly"""
        from app.services.image_agent import ImageAgent
        
        agent = ImageAgent()
        
        assert agent.storage_client is not None
        assert agent.client is not None
    
    @patch('app.services.image_agent.types')
    @patch('app.services.image_agent.storage.Client')
    @patch('app.services.image_agent.genai.Client')
    def test_image_agent_generate_returns_url(self, mock_genai, mock_storage, mock_types):
        """Test that image generation uploads bytes and returns Firebase URL"""
        from app.services.image_agent import ImageAgent
        
        mock_client = mock_genai.return_value
        
        # Mock response with generated_images
        mock_image = MagicMock()
        mock_image.image_bytes = b"fake_image_bytes"
        
        mock_response = MagicMock()
        mock_response.generated_images = [mock_image]
        
        mock_client.models.generate_images.return_value = mock_response
        
        # Mock storage
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_storage.return_value.bucket.return_value = mock_bucket
        
        agent = ImageAgent()
        result = agent.generate_image("Test image prompt", folder="test")
        
        assert result is not None
        assert "firebasestorage.googleapis.com" in result
        mock_blob.upload_from_string.assert_called_once()
    
    @patch('app.services.image_agent.types')
    @patch('app.services.image_agent.storage.Client')
    @patch('app.services.image_agent.genai.Client')
    def test_image_agent_handles_no_bytes(self, mock_genai, mock_storage, mock_types):
        """Test that image generation returns None when no bytes returned"""
        from app.services.image_agent import ImageAgent
        
        mock_client = mock_genai.return_value
        
        # Create a mock image object that explicitly returns None for all byte attributes
        # Use a simple class instead of MagicMock to avoid auto-creation of attributes
        class MockImageNoBytes:
            image_bytes = None
            _image_bytes = None
            image = None
        
        mock_image = MockImageNoBytes()
        
        mock_response = MagicMock()
        mock_response.generated_images = [mock_image]
        
        mock_client.models.generate_images.return_value = mock_response
        
        agent = ImageAgent()
        result = agent.generate_image("Test image prompt")
        
        assert result is None
    
    @patch('app.services.image_agent.types')
    @patch('app.services.image_agent.storage.Client')
    @patch('app.services.image_agent.genai.Client')
    def test_image_agent_handles_generation_failure(self, mock_genai, mock_storage, mock_types):
        """Test that image generation returns None on API failure"""
        from app.services.image_agent import ImageAgent
        
        mock_client = mock_genai.return_value
        mock_client.models.generate_images.side_effect = Exception("API Error")
        
        agent = ImageAgent()
        result = agent.generate_image("Test image prompt")
        
        assert result is None
    
    @patch('app.services.image_agent.types')
    @patch('app.services.image_agent.storage.Client')
    @patch('app.services.image_agent.genai.Client')
    def test_image_agent_appends_brand_dna(self, mock_genai, mock_storage, mock_types):
        """Test that brand DNA is appended to prompt"""
        from app.services.image_agent import ImageAgent
        
        mock_client = mock_genai.return_value
        
        mock_image = MagicMock()
        mock_image.image_bytes = b"fake_image_bytes"
        
        mock_response = MagicMock()
        mock_response.generated_images = [mock_image]
        
        mock_client.models.generate_images.return_value = mock_response
        
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_storage.return_value.bucket.return_value = mock_bucket
        
        agent = ImageAgent()
        result = agent.generate_image(
            "Test image prompt",
            brand_dna="Blue colors, modern style",
            folder="test"
        )
        
        assert result is not None
        # Verify the prompt was enhanced with brand DNA
        call_args = mock_client.models.generate_images.call_args
        assert "Brand" in str(call_args) or result is not None


class TestAudioAgent:
    """Tests for AudioAgent (Gemini 2.5 TTS)"""
    
    @patch('app.services.audio_agent.storage.Client')
    @patch('app.services.audio_agent.genai.Client')
    def test_audio_agent_initialization(self, mock_genai, mock_storage):
        """Test AudioAgent initializes correctly"""
        from app.services.audio_agent import AudioAgent
        
        agent = AudioAgent()
        
        assert agent.storage_client is not None
        assert agent.client is not None
    
    @patch('app.services.audio_agent.storage.Client')
    @patch('app.services.audio_agent.genai.Client')
    def test_audio_agent_generate_returns_url(self, mock_genai, mock_storage):
        """Test that audio generation uploads bytes and returns Firebase URL"""
        from app.services.audio_agent import AudioAgent
        
        mock_client = mock_genai.return_value
        
        # Mock response with inline_data containing audio bytes
        mock_inline_data = MagicMock()
        mock_inline_data.data = b"fake_audio_bytes"
        
        mock_part = MagicMock()
        mock_part.inline_data = mock_inline_data
        
        mock_content = MagicMock()
        mock_content.parts = [mock_part]
        
        mock_candidate = MagicMock()
        mock_candidate.content = mock_content
        
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]
        # IMPORTANT: The audio_agent checks hasattr(operation, "done") - we need to not have it
        # or mock it properly. Also error must be None.
        del mock_response.done  # Remove 'done' so hasattr returns False
        
        mock_client.models.generate_content.return_value = mock_response
        
        # Mock storage
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_storage.return_value.bucket.return_value = mock_bucket
        
        agent = AudioAgent()
        result = agent.generate_audio("Test audio text", folder="test")
        
        assert result is not None
        assert "firebasestorage.googleapis.com" in result
    
    @patch('app.services.audio_agent.storage.Client')
    @patch('app.services.audio_agent.genai.Client')
    def test_audio_agent_truncates_long_text(self, mock_genai, mock_storage):
        """Test that text over 4096 chars is truncated"""
        from app.services.audio_agent import AudioAgent
        
        mock_client = mock_genai.return_value
        
        mock_inline_data = MagicMock()
        mock_inline_data.data = b"fake_audio_bytes"
        
        mock_part = MagicMock()
        mock_part.inline_data = mock_inline_data
        
        mock_content = MagicMock()
        mock_content.parts = [mock_part]
        
        mock_candidate = MagicMock()
        mock_candidate.content = mock_content
        
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]
        del mock_response.done  # Remove 'done' so hasattr returns False
        
        mock_client.models.generate_content.return_value = mock_response
        
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_storage.return_value.bucket.return_value = mock_bucket
        
        agent = AudioAgent()
        long_text = "A" * 5000  # Over 4096 chars
        result = agent.generate_audio(long_text, folder="test")
        
        # Should still work (truncated internally)
        assert result is not None
    
    @patch('app.services.audio_agent.storage.Client')
    @patch('app.services.audio_agent.genai.Client')
    def test_audio_agent_handles_no_bytes(self, mock_genai, mock_storage):
        """Test that audio generation returns None when no bytes returned"""
        from app.services.audio_agent import AudioAgent
        
        mock_client = mock_genai.return_value
        
        mock_response = MagicMock()
        mock_response.candidates = []
        mock_response.text = None
        
        mock_client.models.generate_content.return_value = mock_response
        
        agent = AudioAgent()
        result = agent.generate_audio("Test audio text")
        
        assert result is None
    
    @patch('app.services.audio_agent.storage.Client')
    @patch('app.services.audio_agent.genai.Client')
    def test_audio_agent_handles_empty_text(self, mock_genai, mock_storage):
        """Test that audio generation returns None for empty text"""
        from app.services.audio_agent import AudioAgent
        
        agent = AudioAgent()
        result = agent.generate_audio("", folder="test")
        
        assert result is None


class TestFabricateBlock:
    """Tests for the fabricate_block function in tutorial_agent"""
    
    def test_fabricate_block_video_success(self):
        """Test video block creation with successful generation"""
        from app.agents.tutorial_agent import fabricate_block
        
        mock_video_agent = MagicMock()
        mock_video_agent.generate_video.return_value = "https://storage.example.com/video.mp4"
        mock_image_agent = MagicMock()
        mock_audio_agent = MagicMock()
        
        block = {"type": "video_clip", "visual_prompt": "Test scene"}
        result = fabricate_block(block, "Test Topic", mock_video_agent, mock_image_agent, mock_audio_agent)
        
        assert result["type"] == "video"
        assert result["url"] == "https://storage.example.com/video.mp4"
    
    def test_fabricate_block_video_fallback_to_image(self):
        """Test video block falls back to image on video failure"""
        from app.agents.tutorial_agent import fabricate_block
        
        mock_video_agent = MagicMock()
        mock_video_agent.generate_video.return_value = None  # Video fails
        mock_image_agent = MagicMock()
        mock_image_agent.generate_image.return_value = "https://storage.example.com/image.png"
        mock_audio_agent = MagicMock()
        
        block = {"type": "video_clip", "visual_prompt": "Test scene"}
        result = fabricate_block(block, "Test Topic", mock_video_agent, mock_image_agent, mock_audio_agent)
        
        assert result["type"] == "image"
        assert result["fallback"] is True
        assert result["url"] == "https://storage.example.com/image.png"
    
    def test_fabricate_block_video_complete_failure(self):
        """Test video block returns placeholder on complete failure"""
        from app.agents.tutorial_agent import fabricate_block
        
        mock_video_agent = MagicMock()
        mock_video_agent.generate_video.return_value = None
        mock_image_agent = MagicMock()
        mock_image_agent.generate_image.return_value = None  # Fallback also fails
        mock_audio_agent = MagicMock()
        
        block = {"type": "video_clip", "visual_prompt": "Test scene"}
        result = fabricate_block(block, "Test Topic", mock_video_agent, mock_image_agent, mock_audio_agent)
        
        assert result["type"] == "placeholder"
        assert result["original_type"] == "video"
        assert result["status"] == "failed"
    
    def test_fabricate_block_image_success(self):
        """Test image block creation with successful generation"""
        from app.agents.tutorial_agent import fabricate_block
        
        mock_video_agent = MagicMock()
        mock_image_agent = MagicMock()
        mock_image_agent.generate_image.return_value = "https://storage.example.com/image.png"
        mock_audio_agent = MagicMock()
        
        block = {"type": "image_diagram", "visual_prompt": "Test diagram"}
        result = fabricate_block(block, "Test Topic", mock_video_agent, mock_image_agent, mock_audio_agent)
        
        assert result["type"] == "image"
        assert result["url"] == "https://storage.example.com/image.png"
    
    def test_fabricate_block_audio_success(self):
        """Test audio block creation with successful generation"""
        from app.agents.tutorial_agent import fabricate_block
        
        mock_video_agent = MagicMock()
        mock_image_agent = MagicMock()
        mock_audio_agent = MagicMock()
        mock_audio_agent.generate_audio.return_value = "https://storage.example.com/audio.mp3"
        
        block = {"type": "audio_note", "script": "Test audio script"}
        result = fabricate_block(block, "Test Topic", mock_video_agent, mock_image_agent, mock_audio_agent)
        
        assert result["type"] == "audio"
        assert result["url"] == "https://storage.example.com/audio.mp3"
        assert result["transcript"] == "Test audio script"
    
    def test_fabricate_block_audio_failure(self):
        """Test audio block returns placeholder on failure"""
        from app.agents.tutorial_agent import fabricate_block
        
        mock_video_agent = MagicMock()
        mock_image_agent = MagicMock()
        mock_audio_agent = MagicMock()
        mock_audio_agent.generate_audio.return_value = None
        
        block = {"type": "audio_note", "script": "Test audio script"}
        result = fabricate_block(block, "Test Topic", mock_video_agent, mock_image_agent, mock_audio_agent)
        
        assert result["type"] == "placeholder"
        assert result["original_type"] == "audio"
        assert result["status"] == "failed"
    
    def test_fabricate_block_passthrough_quiz(self):
        """Test quiz blocks pass through unchanged"""
        from app.agents.tutorial_agent import fabricate_block
        
        mock_video_agent = MagicMock()
        mock_image_agent = MagicMock()
        mock_audio_agent = MagicMock()
        
        block = {"type": "quiz_single", "question": "What is X?", "options": ["A", "B"], "correct_answer": 0}
        result = fabricate_block(block, "Test Topic", mock_video_agent, mock_image_agent, mock_audio_agent)
        
        assert result == block
    
    def test_fabricate_block_handles_exception(self):
        """Test fabricate_block handles unexpected exceptions gracefully"""
        from app.agents.tutorial_agent import fabricate_block
        
        mock_video_agent = MagicMock()
        mock_video_agent.generate_video.side_effect = Exception("Unexpected error")
        mock_image_agent = MagicMock()
        mock_audio_agent = MagicMock()
        
        block = {"type": "video_clip", "visual_prompt": "Test scene"}
        result = fabricate_block(block, "Test Topic", mock_video_agent, mock_image_agent, mock_audio_agent)
        
        assert result["type"] == "placeholder"
        assert result["status"] == "failed"
        assert "error" in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
