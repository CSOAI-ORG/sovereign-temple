"""Test that the 3 SOV3small3 master tools are wired into sovereign-mcp-server.

Covers:
- The import block (handle_sov3small3_master_status/benchmark/speculative_demo)
- The SOV3SMALL3_TOOL_DEFS inclusion in the tool list
- The handler dispatch (3 elifs in the route handler)
"""
import re
import sys
from pathlib import Path

SERVER_PATH = Path("/Users/nicholas/clawd/sovereign-temple/sovereign-mcp-server.py")


def test_import_block_present():
    """The SOV3small3 import block must be present."""
    text = SERVER_PATH.read_text()
    # The import block (right after the sov3small block)
    assert "from sov3small3 import (" in text
    assert "handle_sov3small3_master_status as _handle_sov3small3_master_status" in text
    assert "handle_sov3small3_master_benchmark as _handle_sov3small3_master_benchmark" in text
    assert "handle_sov3small3_speculative_demo as _handle_sov3small3_speculative_demo" in text
    assert "SOV3SMALL3_TOOL_DEFINITIONS as _SOV3SMALL3_TOOL_DEFS" in text
    assert "SOV3SMALL3_AVAILABLE = True" in text
    assert "[startup] SOV3small3 MASTER loaded" in text


def test_tool_defs_inclusion():
    """The SOV3SMALL3_TOOL_DEFS must be included in the all-tools concatenation."""
    text = SERVER_PATH.read_text()
    # Should appear after SOV3SMALL_TOOL_DEFS and before BIG_BRAIM_TOOL_DEFS
    pattern = r"_SOV3SMALL3_TOOL_DEFS if SOV3SMALL3_AVAILABLE else \[\]"
    assert re.search(pattern, text), "SOV3SMALL3 tool defs not found in tool list"
    # Order check: SOV3SMALL3 should come after SOV3SMALL
    sm_pos = text.find("_SOV3SMALL_TOOL_DEFS")
    sm3_pos = text.find("_SOV3SMALL3_TOOL_DEFS")
    bb_pos = text.find("_BIG_BRAIM_TOOL_DEFS")
    assert sm_pos < sm3_pos < bb_pos, f"tool order: SOV3SMALL={sm_pos} SOV3SMALL3={sm3_pos} BIG_BRAIM={bb_pos}"


def test_handler_dispatch():
    """The 3 elifs must be in the handler dispatch."""
    text = SERVER_PATH.read_text()
    # Find the SOV3small3 section
    assert 'name == "sov3small3_master_status" and SOV3SMALL3_AVAILABLE' in text
    assert 'name == "sov3small3_master_benchmark" and SOV3SMALL3_AVAILABLE' in text
    assert 'name == "sov3small3_speculative_demo" and SOV3SMALL3_AVAILABLE' in text
    # Each must return the correct handler
    assert "return _handle_sov3small3_master_status(arguments)" in text
    assert "return _handle_sov3small3_master_benchmark(arguments)" in text
    assert "return _handle_sov3small3_speculative_demo(arguments)" in text


def test_sov3small3_module_imports_cleanly():
    """The sov3small3 module should import without errors."""
    sys.path.insert(0, str(SERVER_PATH.parent))
    from sov3small3 import (
        handle_sov3small3_master_status,
        handle_sov3small3_master_benchmark,
        handle_sov3small3_speculative_demo,
        SOV3SMALL3_TOOL_DEFINITIONS,
    )
    assert callable(handle_sov3small3_master_status)
    assert callable(handle_sov3small3_master_benchmark)
    assert callable(handle_sov3small3_speculative_demo)
    assert len(SOV3SMALL3_TOOL_DEFINITIONS) == 3


def test_tool_defs_match_handlers():
    """Each tool definition's name must have a corresponding handler dispatch."""
    sys.path.insert(0, str(SERVER_PATH.parent))
    from sov3small3 import SOV3SMALL3_TOOL_DEFINITIONS
    text = SERVER_PATH.read_text()
    for td in SOV3SMALL3_TOOL_DEFINITIONS:
        assert f'name == "{td["name"]}"' in text, f"missing handler for {td['name']}"


def test_sov3small3_handler_smoke():
    """Each handler should be callable with empty args and return a dict."""
    import asyncio
    sys.path.insert(0, str(SERVER_PATH.parent))
    from sov3small3 import (
        handle_sov3small3_master_status,
        handle_sov3small3_master_benchmark,
        handle_sov3small3_speculative_demo,
    )
    # status
    s = handle_sov3small3_master_status({})
    assert "tiers" in s
    assert "configs" in s
    # benchmark (async)
    r = asyncio.run(handle_sov3small3_master_benchmark({}))
    assert "results" in r
    assert len(r["results"]) == 3
    # speculative (async)
    sp = asyncio.run(handle_sov3small3_speculative_demo({}))
    assert "demos" in sp
    assert len(sp["demos"]) == 10


if __name__ == "__main__":
    import subprocess
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-v"]))