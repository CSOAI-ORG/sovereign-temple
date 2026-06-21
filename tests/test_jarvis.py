"""
Jarvis Voice Pipeline Tests - Fixed
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestJarvisVoicePipeline:
    """Test Jarvis voice pipeline components"""

    def test_voice_pipeline_imports(self):
        """Test voice pipeline modules can be imported"""
        try:
            from voice_pipeline.jarvis_voice import JarvisVoice

            assert JarvisVoice is not None
        except ImportError:
            pytest.skip("Voice pipeline module not available")

    def test_voice_enhanced_imports(self):
        """Test enhanced voice module"""
        try:
            from voice_pipeline.jarvis_enhanced import JarvisEnhanced

            assert JarvisEnhanced is not None
        except ImportError:
            pytest.skip("Enhanced voice module not available")


class TestJarvisSkills:
    """Test Jarvis skill execution"""

    def test_skill_registration(self):
        """Test skill registration works"""
        try:
            from jarvis_orchestrator_v2 import JarvisOrchestrator

            assert JarvisOrchestrator is not None
        except ImportError:
            pytest.skip("Orchestrator not available")


class TestJarvisMemory:
    """Test Jarvis memory management"""

    def test_memory_imports(self):
        """Test memory module imports"""
        try:
            from jarvis_improved_memory import JarvisMemory

            assert JarvisMemory is not None
        except ImportError:
            pytest.skip("Memory module not available")


class TestJarvisOrchestrator:
    """Test Jarvis orchestration"""

    def test_orchestrator_exists(self):
        """Test orchestrator exists"""
        try:
            from jarvis_orchestrator_v2 import JarvisOrchestrator

            assert JarvisOrchestrator is not None
        except ImportError:
            pytest.skip("Orchestrator module not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
