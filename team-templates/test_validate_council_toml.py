"""Tests for validate_council_toml.py — council Toml structural validation."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
VALIDATOR = HERE / "validate_council_toml.py"
TOML = HERE / "sovereign-council.toml"


def test_validator_exits_0_on_valid():
    """The shipped Toml should pass validation."""
    r = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        capture_output=True, text=True
    )
    assert r.returncode == 0, f"expected 0, got {r.returncode}\nSTDOUT: {r.stdout}\nSTDERR: {r.stderr}"
    assert "All structural checks pass" in r.stdout
    assert "13 nodes" in r.stdout
    assert "f=4" in r.stdout
    assert "quorum=9" in r.stdout


def test_validator_output_mentions_count():
    """Validator should report agent + task counts."""
    r = subprocess.run([sys.executable, str(VALIDATOR)], capture_output=True, text=True)
    assert "Queens: 12 of 12" in r.stdout
    assert "Tasks: 13" in r.stdout
    assert "Leader: queen-king" in r.stdout
    assert "BFT math: n=13" in r.stdout


def test_validator_detects_broken_toml():
    """A malformed Toml should make the validator fail to load."""
    import tempfile
    import tomllib
    # Write a deliberately broken Toml that has the right structure
    # but with one agent missing the 'mandate' field (a structural error)
    broken = HERE / "_test_broken.toml"
    broken.write_text("""
[template]
name = "broken"
description = "test"
command = ["x"]
backend = "x"

[template.leader]
name = "queen-king"
type = "x"
task = "x"
arcana = "x"
domain = "x"
color = "#000000"
first_words = "x"
personality = "x"
# missing 'mandate' field — should fail validation

[[template.agents]]
name = "queen-strategy"
type = "x"
task = "x"
arcana = "x"
domain = "x"
color = "#000000"
mandate = "x"
first_words = "x"
personality = "x"
""")
    try:
        # The validator is a script that takes a hard-coded path
        # (Path(__file__).parent / "sovereign-council.toml") so we can't
        # directly point it at a broken file. But we can test the
        # structural logic by importing the module-level functions.
        # Quick hack: copy the broken file, run validator, restore.
        from shutil import copyfile
        backup = HERE / "_backup.toml"
        copyfile(TOML, backup)
        copyfile(broken, TOML)
        try:
            r = subprocess.run([sys.executable, str(VALIDATOR)], capture_output=True, text=True)
            assert r.returncode == 1, f"broken Toml should exit 1, got {r.returncode}"
            assert "missing" in r.stdout.lower() or "error" in r.stdout.lower()
        finally:
            copyfile(backup, TOML)
            backup.unlink()
    finally:
        broken.unlink()


def test_toml_file_is_parseable():
    """The Toml itself must be parseable as valid Toml."""
    import tomllib
    with TOML.open("rb") as f:
        d = tomllib.load(f)
    assert d["template"]["name"] == "sovereign-council"
    assert d["template"]["leader"]["name"] == "queen-king"
    assert len(d["template"]["agents"]) == 12
    assert len(d["template"]["tasks"]) == 13


def test_every_queen_has_first_words():
    """Per the persona schema, every queen should have a 'first_words' field."""
    import tomllib
    with TOML.open("rb") as f:
        d = tomllib.load(f)
    for a in d["template"]["agents"]:
        assert "first_words" in a, f"{a['name']} missing first_words"
        assert len(a["first_words"]) > 10, f"{a['name']} first_words too short"


def test_veto_queens_have_explicit_veto_marker():
    """Care + Watch should have a clear veto annotation in the task field."""
    import tomllib
    with TOML.open("rb") as f:
        d = tomllib.load(f)
    veto_names = {"queen-care", "queen-watch"}
    for a in d["template"]["agents"]:
        if a["name"] in veto_names:
            # Either in mandate or in task
            has_veto = "VETO" in a["task"] or "VETO" in a.get("mandate", "")
            assert has_veto, f"{a['name']} should mention VETO in task or mandate"


def test_king_task_says_wait_for_all_12():
    """Per the ClawTeam pattern, the King MUST wait for all 12 verdicts."""
    import tomllib
    with TOML.open("rb") as f:
        d = tomllib.load(f)
    king_task = d["template"]["leader"]["task"]
    assert "WAIT" in king_task.upper() or "wait" in king_task
    assert "12" in king_task or "ALL" in king_task
    assert "Ed25519" in king_task or "SIGIL" in king_task


if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-v"]))