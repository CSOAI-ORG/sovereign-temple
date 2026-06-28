"""validate_hand_toml.py — structural validator for SOV3 HAND.toml manifests.

Mirrors validate_council_toml.py (in team-templates/) but for capability
manifests rather than council templates.

Catches:
- Toml parse errors
- Missing required top-level fields (id, name, description, category, tools, agent)
- Invalid category (must be in HandCategory enum)
- Tools list must be non-empty
- [sovereign] block validation (when present):
  - compliance_frameworks, oscal_components, sigil_chain, data_residency required
  - data_residency must be one of: uk, eu, us, apac
- [agent] block validation:
  - module, model, max_iterations, system_prompt required
  - temperature, max_tokens optional (have defaults)
  - max_iterations > 0
- [[settings]] validation:
  - key, label, description, setting_type required
  - setting_type must be in (text, number, select, multiselect, toggle, secret)
  - if type is select/multiselect, must have at least 1 [[settings.options]]
- [dashboard] validation:
  - must have at least 1 [[dashboard.metrics]]
"""
import sys
import tomllib
from pathlib import Path

REQUIRED_TOP_FIELDS = {"id", "name", "description", "category", "tools", "agent"}
VALID_CATEGORIES = {"content", "security", "productivity", "development",
                    "communication", "data", "finance", "other"}
VALID_SETTING_TYPES = {"text", "number", "select", "multiselect", "toggle", "secret"}
VALID_RESIDENCIES = {"uk", "eu", "us", "apac"}
REQUIRED_AGENT_FIELDS = {"name", "module", "model", "max_iterations", "system_prompt"}
REQUIRED_SOVEREIGN_FIELDS = {"compliance_frameworks", "oscal_components",
                             "sigil_chain", "data_residency", "access_control"}


def main():
    if len(sys.argv) < 2:
        # Default: validate the spec file in this folder
        p = Path(__file__).parent / "sov3-hand-manifest.spec.toml"
    else:
        p = Path(sys.argv[1])
    if not p.exists():
        print(f"❌ File not found: {p}")
        return 1
    try:
        with p.open("rb") as f:
            tpl = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        print(f"❌ Toml parse error: {e}")
        return 1

    errors = []
    warnings = []

    # Special case: if the file has a [schema] block, it's a spec/documentation
    # file, not a real Hand. Validate the schema block but don't require
    # the standard Hand fields.
    if "schema" in tpl and not tpl.get("id"):
        schema = tpl["schema"]
        if "version" not in schema:
            errors.append("[schema] block missing 'version' field")
        if "spec" not in schema:
            errors.append("[schema] block missing 'spec' field")
        if not errors:
            print(f"\n=== SOV3 HAND.toml Schema Block Validation ===")
            print(f"File: {p}")
            print(f"spec: {schema.get('spec', '?')}")
            print(f"version: {schema.get('version', '?')}")
            print(f"adapted_from: {schema.get('adapted_from', '?')}")
            print(f"adapted_date: {schema.get('adapted_date', '?')}")
            print(f"\n✅ Schema block is valid.")
            return 0

    # 1. Required top-level fields
    missing = REQUIRED_TOP_FIELDS - set(tpl.keys())
    if missing:
        errors.append(f"Missing required top-level fields: {missing}")

    # 2. id format
    if "id" in tpl and not tpl["id"].replace("-", "").replace("_", "").isalnum():
        errors.append(f"id must be lowercase-alphanumeric-with-hyphens, got {tpl['id']!r}")

    # 3. category
    if "category" in tpl and tpl["category"] not in VALID_CATEGORIES:
        errors.append(f"category must be one of {VALID_CATEGORIES}, got {tpl['category']!r}")

    # 4. tools
    if "tools" in tpl:
        if not isinstance(tpl["tools"], list):
            errors.append("tools must be a list")
        elif len(tpl["tools"]) == 0:
            errors.append("tools must be non-empty (a Hand with no tools is useless)")
        else:
            for tool in tpl["tools"]:
                if not isinstance(tool, str):
                    errors.append(f"tools must be strings, got {type(tool).__name__}: {tool!r}")

    # 5. requires
    if "requires" in tpl:
        for i, req in enumerate(tpl["requires"]):
            for field in ("key", "label", "requirement_type"):
                if field not in req:
                    errors.append(f"requires[{i}] missing field: {field}")

    # 6. settings
    if "settings" in tpl:
        for i, s in enumerate(tpl["settings"]):
            for field in ("key", "label", "description", "setting_type"):
                if field not in s:
                    errors.append(f"settings[{i}] missing field: {field}")
            if "setting_type" in s:
                st = s["setting_type"]
                if st not in VALID_SETTING_TYPES:
                    errors.append(f"settings[{i}].setting_type {st!r} not in {VALID_SETTING_TYPES}")
                if st in ("select", "multiselect"):
                    if not s.get("options"):
                        errors.append(f"settings[{i}] with type={st} must have [[settings.options]]")

    # 7. agent
    if "agent" in tpl:
        agent = tpl["agent"]
        missing_agent = REQUIRED_AGENT_FIELDS - set(agent.keys())
        if missing_agent:
            errors.append(f"agent missing fields: {missing_agent}")
        if "max_iterations" in agent and agent["max_iterations"] <= 0:
            errors.append(f"agent.max_iterations must be > 0, got {agent['max_iterations']}")
        if "temperature" in agent:
            temp = agent["temperature"]
            if not (0.0 <= temp <= 2.0):
                warnings.append(f"agent.temperature {temp} outside typical range [0.0, 2.0]")
        # module check
        if "module" in agent:
            valid_modules = ("builtin:chat", "builtin:sov3", "builtin:claude",
                             "builtin:openai", "builtin:ollama")
            if not any(agent["module"].startswith(m) for m in valid_modules):
                warnings.append(f"agent.module {agent['module']!r} not in {valid_modules}")

    # 8. sovereign
    if "sovereign" in tpl:
        sov = tpl["sovereign"]
        missing_sov = REQUIRED_SOVEREIGN_FIELDS - set(sov.keys())
        if missing_sov:
            errors.append(f"sovereign missing fields: {missing_sov}")
        if "data_residency" in sov and sov["data_residency"] not in VALID_RESIDENCIES:
            errors.append(f"sovereign.data_residency must be one of {VALID_RESIDENCIES}, got {sov['data_residency']!r}")
        if "compliance_frameworks" in sov and not sov["compliance_frameworks"]:
            errors.append("sovereign.compliance_frameworks must be non-empty")
        if "oscal_components" in sov and not sov["oscal_components"]:
            errors.append("sovereign.oscal_components must be non-empty")

    # 9. dashboard
    if "dashboard" in tpl:
        dash = tpl["dashboard"]
        if "metrics" in dash and not dash["metrics"]:
            errors.append("dashboard must have at least 1 [[dashboard.metrics]]")
        for i, m in enumerate(dash.get("metrics", [])):
            for field in ("label", "memory_key", "format"):
                if field not in m:
                    errors.append(f"dashboard.metrics[{i}] missing field: {field}")
            if "format" in m and m["format"] not in ("number", "percentage", "duration", "bytes", "text"):
                warnings.append(f"dashboard.metrics[{i}].format {m['format']!r} is non-standard")

    # Report
    print(f"\n=== SOV3 HAND.toml Validation ===")
    print(f"File: {p}")
    if tpl.get("id"):
        print(f"id: {tpl['id']}")
    if tpl.get("name"):
        print(f"name: {tpl['name']}")
    if tpl.get("category"):
        print(f"category: {tpl['category']}")
    if tpl.get("tools"):
        print(f"tools: {len(tpl['tools'])} listed")
    if tpl.get("agent"):
        print(f"agent: module={tpl['agent'].get('module')}, model={tpl['agent'].get('model')}")
    if tpl.get("sovereign"):
        print(f"sovereign: {tpl['sovereign'].get('data_residency', '?')} + "
              f"{len(tpl['sovereign'].get('compliance_frameworks', []))} frameworks")
    if warnings:
        print(f"\n⚠️  Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")
    if errors:
        print(f"\n❌ Errors ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"\n✅ All structural checks pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())