"""Tests for validate_hand_toml.py — SOV3 HAND.toml structural validation."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
VALIDATOR = HERE / "validate_hand_toml.py"
SPEC = HERE / "sov3-hand-manifest.spec.toml"
EXAMPLE = HERE / "examples" / "eu-ai-act-compliance-hand" / "HAND.toml"


def test_spec_file_passes():
    """The spec file (with [schema] block) should validate."""
    r = subprocess.run([sys.executable, str(VALIDATOR), str(SPEC)],
                       capture_output=True, text=True)
    assert r.returncode == 0, f"expected 0, got {r.returncode}\nSTDOUT: {r.stdout}\nSTDERR: {r.stderr}"
    assert "Schema block is valid" in r.stdout
    assert "sov3-hand-manifest" in r.stdout
    assert "openfang-hand-manifest" in r.stdout


def test_example_hand_passes():
    """The real-world example (eu-ai-act-compliance-hand) should validate."""
    assert EXAMPLE.exists(), f"example file missing: {EXAMPLE}"
    r = subprocess.run([sys.executable, str(VALIDATOR), str(EXAMPLE)],
                       capture_output=True, text=True)
    assert r.returncode == 0, f"expected 0, got {r.returncode}\nSTDOUT: {r.stdout}\nSTDERR: {r.stderr}"
    assert "All structural checks pass" in r.stdout
    assert "eu-ai-act-compliance-hand" in r.stdout
    assert "11 listed" in r.stdout  # 11 tools in the example
    assert "builtin:sov3" in r.stdout


def test_example_has_sovereign_extensions():
    """The example must include the 3 SOV3 sovereign extensions."""
    import tomllib
    with EXAMPLE.open("rb") as f:
        d = tomllib.load(f)
    assert "sovereign" in d, "example must have [sovereign] block"
    sov = d["sovereign"]
    assert "compliance_frameworks" in sov
    assert "oscal_components" in sov
    assert "sigil_chain" in sov
    assert "data_residency" in sov
    assert "access_control" in sov
    # Must include EU AI Act (the whole point)
    assert any("EU AI Act" in fw for fw in sov["compliance_frameworks"])
    # Must reference the hive
    assert "meok-backend" in sov["sigil_chain"]
    # Must defer to council
    assert sov["access_control"] == "council_oversight"


def test_example_agent_uses_sov3_module():
    """SOV3 Hands default to the SOV3 neural core, not raw LLM."""
    import tomllib
    with EXAMPLE.open("rb") as f:
        d = tomllib.load(f)
    assert d["agent"]["module"] == "builtin:sov3"
    assert d["agent"]["model"] == "sov3-base-7b"
    # Must reference SIGIL in the system prompt (sovereign extension)
    assert "SIGIL" in d["agent"]["system_prompt"]
    # Must reference the queens in the system prompt
    assert "queen-care" in d["agent"]["system_prompt"]
    assert "queen-watch" in d["agent"]["system_prompt"]


def test_example_has_critical_finding_action():
    """The example should have a 'critical_finding_action' setting (the key safety knob)."""
    import tomllib
    with EXAMPLE.open("rb") as f:
        d = tomllib.load(f)
    settings_keys = {s["key"] for s in d.get("settings", [])}
    assert "critical_finding_action" in settings_keys


def test_validator_detects_missing_id():
    """A Hand missing 'id' should fail validation."""
    import tempfile
    broken = HERE / "_test_broken.toml"
    broken.write_text("""
name = "broken"
description = "no id"
category = "other"
tools = ["mcp__x"]
[agent]
name = "x"
module = "builtin:sov3"
model = "x"
max_iterations = 1
system_prompt = "x"
""")
    try:
        r = subprocess.run([sys.executable, str(VALIDATOR), str(broken)],
                           capture_output=True, text=True)
        assert r.returncode == 1, f"expected 1, got {r.returncode}\nSTDOUT: {r.stdout}"
        assert "Missing required" in r.stdout or "id" in r.stdout
    finally:
        broken.unlink()


def test_validator_detects_invalid_category():
    """A Hand with an invalid category should fail validation."""
    import tempfile
    broken = HERE / "_test_broken.toml"
    broken.write_text("""
id = "broken"
name = "broken"
description = "bad category"
category = "underwater_basket_weaving"
tools = ["mcp__x"]
[agent]
name = "x"
module = "builtin:sov3"
model = "x"
max_iterations = 1
system_prompt = "x"
""")
    try:
        r = subprocess.run([sys.executable, str(VALIDATOR), str(broken)],
                           capture_output=True, text=True)
        assert r.returncode == 1
        assert "category" in r.stdout
    finally:
        broken.unlink()


def test_validator_detects_empty_tools():
    """A Hand with no tools should fail validation."""
    broken = HERE / "_test_broken.toml"
    broken.write_text("""
id = "broken"
name = "broken"
description = "no tools"
category = "other"
tools = []
[agent]
name = "x"
module = "builtin:sov3"
model = "x"
max_iterations = 1
system_prompt = "x"
""")
    try:
        r = subprocess.run([sys.executable, str(VALIDATOR), str(broken)],
                           capture_output=True, text=True)
        assert r.returncode == 1
        assert "tools" in r.stdout
    finally:
        broken.unlink()


if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-v"]))