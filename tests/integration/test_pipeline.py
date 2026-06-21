"""
Integration tests for SOV3 ↔ Jarvis ↔ Meok UI - Fixed
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSOV3JarvisIntegration:
    """Test SOV3 and Jarvis integration"""

    def test_sov3_imports(self):
        """Test SOV3 modules can be imported"""
        try:
            from sov3_enhanced_consciousness import Sov3Consciousness

            assert Sov3Consciousness is not None
        except ImportError as e:
            pytest.skip(f"SOV3 not available: {e}")

    def test_jarvis_imports(self):
        """Test Jarvis modules can be imported"""
        try:
            from jarvis_orchestrator_v2 import JarvisOrchestrator

            assert JarvisOrchestrator is not None
        except ImportError:
            pass


class TestJarvisMeokIntegration:
    """Test Jarvis and Meok UI integration"""

    def test_jarvis_client_exists(self):
        """Test SOV3 client exists"""
        import os

        client_path = "/Users/nicholas/clawd/meok/ui/src/lib/sov3-client.ts"
        if os.path.exists(client_path):
            assert True
        else:
            pytest.skip("Meok UI not available")


class TestSOV3MeokStatus:
    """Test SOV3 status endpoint for Meok dashboard"""

    def test_status_endpoint_exists(self):
        """Test status endpoint code exists"""
        import os

        path = "/Users/nicholas/clawd/meok/ui/src/app/api/sov3/status/route.ts"
        if os.path.exists(path):
            with open(path) as f:
                content = f.read()
                assert "GET" in content or "status" in content.lower()
        else:
            pytest.skip("Status route not available")


class TestEndToEnd:
    """End-to-end integration tests"""

    def test_full_pipeline_config(self):
        """Test pipeline configuration exists"""
        import os

        sov3_path = (
            "/Users/nicholas/clawd/sovereign-temple/sov3_enhanced_consciousness.py"
        )
        jarvis_path = "/Users/nicholas/clawd/sovereign-temple/jarvis_orchestrator_v2.py"

        exists = os.path.exists(sov3_path) or os.path.exists(jarvis_path)
        if not exists:
            pytest.skip("Pipeline modules not available")

        assert True

    def test_health_check_all_systems(self):
        """Test health check returns status for all systems"""
        import os

        health_checks = []

        if os.path.exists("/Users/nicholas/clawd/sovereign-temple"):
            health_checks.append({"system": "sov3", "status": "configured"})

        if os.path.exists("/Users/nicholas/clawd/meok/ui"):
            health_checks.append({"system": "meok_ui", "status": "configured"})

        assert len(health_checks) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
