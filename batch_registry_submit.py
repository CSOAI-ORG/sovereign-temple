"""
Batch MCP Registry Submitter
============================
Bulk-submits MEOK's 39 MCP servers to every reachable registry:

1. Anthropic MCP Registry  (requires `mcp-publisher login github` first — Nick action)
2. Smithery.ai             (via `npx @smithery/cli publish` — uses GH auth)
3. Glama.ai                (auto-crawls GitHub repos w/ mcp.json — just needs the repo to exist)
4. mcp.so                  (form submission — generates draft text per server)
5. mcphub.io               (form submission — same)
6. wong2/awesome-mcp-servers   (PR draft)
7. appcypher/awesome-mcp-servers (PR draft)

For interactive/form-based registries, this script generates the EXACT text/JSON to paste,
so Nick can blast through submissions in 30 min instead of 3 hours.

Usage:
    python batch_registry_submit.py --anthropic-registry   # auto-submit (requires mcp-publisher auth)
    python batch_registry_submit.py --smithery             # auto-submit via CLI
    python batch_registry_submit.py --generate-pastes      # write copy-paste forms for manual registries
    python batch_registry_submit.py --github-topics        # add topics via gh repo edit
    python batch_registry_submit.py --all                  # everything that doesn't need new auth
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import time
from pathlib import Path

log = logging.getLogger("batch-registry")

CLAWD = Path("/Users/nicholas/clawd")
MARKETPLACE = CLAWD / "mcp-marketplace"
SUBMISSIONS_DIR = CLAWD / "revenue" / "registry-submissions"
SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)

FLAGSHIPS = [
    ("eu-ai-act-compliance", "eu-ai-act-compliance-mcp"),
    ("dora-compliance", "dora-compliance-mcp"),
    ("nis2-compliance", "nis2-compliance-mcp"),
    ("cra-compliance", "cra-compliance-mcp"),
    ("ai-bom", "ai-bom-mcp"),
    ("ai-incident-reporting", "ai-incident-reporting-mcp"),
    ("dora-nis2-crosswalk", "dora-nis2-crosswalk-mcp"),
    ("bias-detection", "bias-detection-mcp"),
    ("watermarking-authenticity", "watermarking-authenticity-mcp"),
    ("uk-ai-bill-compliance", "uk-ai-bill-compliance-mcp"),
    ("agent-prompt-injection-firewall", "agent-prompt-injection-firewall-mcp"),
    ("agent-data-residency", "agent-data-residency-mcp"),
    ("agent-handoff-certified", "agent-handoff-certified-mcp"),
    ("agent-policy-enforcement", "agent-policy-enforcement-mcp"),
    ("agent-audit-logger", "agent-audit-logger-mcp"),
    ("agent-rate-limiter", "agent-rate-limiter-mcp"),
    ("haulage-uk-compliance", "haulage-uk-compliance-mcp"),
    ("skip-hire-ai", "skip-hire-ai-mcp"),
    ("construction-iso-19650", "construction-iso-19650-mcp"),
    ("nrswa-ai", "nrswa-ai-mcp"),
    ("chas-elite-prep", "chas-elite-prep-mcp"),
    ("crane-hire-cpcs", "crane-hire-cpcs-mcp"),
    ("concrete-pump-cpa", "concrete-pump-cpa-mcp"),
    ("mica-crypto", "mica-crypto-mcp"),
    ("fsa-food-safety", "fsa-food-safety-mcp"),
    ("mdr-medical-device", "mdr-medical-device-mcp"),
    ("fda-samd", "fda-samd-mcp"),
    ("coppa-ferpa", "coppa-ferpa-mcp"),
    ("basel-ai-overlay", "basel-ai-overlay-mcp"),
    ("mifid-ii-ai", "mifid-ii-ai-mcp"),
    ("aml-ai", "aml-ai-mcp"),
    ("cobol-bridge", "cobol-bridge-mcp"),
    ("cisa-kev", "cisa-kev-mcp"),
    ("sbom-cyclonedx", "sbom-cyclonedx-mcp"),
    ("mitre-attack", "mitre-attack-mcp"),
    ("mitre-atlas", "mitre-atlas-mcp"),
    ("slsa-supply-chain", "slsa-supply-chain-mcp"),
    ("sigstore-cosign", "sigstore-cosign-mcp"),
    ("care-home-cqc", "care-home-cqc-mcp"),
]


def submit_anthropic_registry():
    log.info("=== Anthropic MCP Registry batch publish ===")
    successes, failures = [], []
    for slug, pkg in FLAGSHIPS:
        if not (MARKETPLACE / pkg / "server.json").exists():
            failures.append((pkg, "no server.json"))
            continue
        try:
            r = subprocess.run(["mcp-publisher", "publish"], cwd=str(MARKETPLACE / pkg),
                               capture_output=True, timeout=30, text=True)
            if r.returncode == 0:
                successes.append(pkg); log.info(f"  ✓ {pkg}")
            else:
                failures.append((pkg, (r.stderr or r.stdout or "")[:200]))
        except Exception as e:
            failures.append((pkg, str(e)))
        time.sleep(0.5)
    return {"successes": successes, "failures": failures}


def submit_smithery():
    log.info("=== Smithery.ai batch publish ===")
    successes, failures = [], []
    for slug, pkg in FLAGSHIPS:
        if not (MARKETPLACE / pkg / "smithery.yaml").exists():
            log.info(f"  skip {pkg}: no smithery.yaml")
            continue
        try:
            r = subprocess.run(["npx", "@smithery/cli", "publish"], cwd=str(MARKETPLACE / pkg),
                               capture_output=True, timeout=60, text=True)
            if r.returncode == 0:
                successes.append(pkg); log.info(f"  ✓ {pkg}")
            else:
                failures.append((pkg, (r.stderr or "")[:200]))
        except Exception as e:
            failures.append((pkg, str(e)))
        time.sleep(0.5)
    return {"successes": successes, "failures": failures}


def gen_form_paste(slug: str, pkg: str) -> dict:
    server_json_path = MARKETPLACE / pkg / "server.json"
    desc = ""
    if server_json_path.exists():
        try:
            desc = json.loads(server_json_path.read_text()).get("description", "")
        except Exception:
            pass
    return {
        "slug": slug,
        "pkg": pkg,
        "github_url": f"https://github.com/CSOAI-ORG/{pkg}",
        "pypi_url": f"https://pypi.org/project/{pkg}/",
        "registry_url": f"https://meok.ai/mcp/{slug}",
        "name": pkg.replace("-mcp", "").replace("-", " ").title() + " MCP",
        "description_short": desc[:200] if desc else f"MCP server for {slug.replace('-', ' ')} compliance",
        "description_long": desc or f"Open-source MCP server for {slug.replace('-', ' ')} compliance. MIT licensed. £29/mo Starter for HMAC-signed attestations.",
        "categories": ["compliance", "ai-governance", "mcp"],
        "tags": [slug, "compliance", "mcp", "open-source"],
        "install": f"uvx {pkg}",
    }


def generate_pastes():
    log.info("=== generating manual-submission pastes ===")
    pastes = [gen_form_paste(s, p) for s, p in FLAGSHIPS]
    (SUBMISSIONS_DIR / "inventory.json").write_text(json.dumps(pastes, indent=2))

    items_md = "\n".join(f"- [{p['name']}]({p['github_url']}) — {p['description_short']}" for p in pastes)

    (SUBMISSIONS_DIR / "PR_wong2_awesome-mcp-servers.md").write_text(
        f"# PR draft: wong2/awesome-mcp-servers\n\n"
        f"Fork github.com/wong2/awesome-mcp-servers, branch `add-meok-ai-labs`, edit README.md.\n\n"
        f"## Markdown to add:\n\n"
        f"### MEOK AI Labs — Compliance Suite (39 servers, MIT)\n\n"
        f"39 open-source MCP servers for EU AI Act, DORA, NIS2, CRA, GDPR, ISO 42001 and related regulations. £29/mo Starter for HMAC-signed audit-evidence attestations; free self-host forever.\n\n"
        f"{items_md}\n"
    )

    (SUBMISSIONS_DIR / "PR_appcypher_awesome-mcp-servers.md").write_text(
        f"# PR draft: appcypher/awesome-mcp-servers\n\nSame content as wong2 PR.\n\n{items_md}\n"
    )

    mcp_so = "# Manual submissions for mcp.so + mcphub.io + glama.ai\n\nVisit each site's submit form. Paste these per-server entries:\n\n"
    for p in pastes:
        mcp_so += (
            f"---\n\n"
            f"**Name:** {p['name']}\n"
            f"**GitHub:** {p['github_url']}\n"
            f"**Description:** {p['description_short']}\n"
            f"**Install:** `{p['install']}`\n"
            f"**Categories:** {', '.join(p['categories'])}\n\n"
        )
    (SUBMISSIONS_DIR / "manual_form_submissions.md").write_text(mcp_so)

    log.info(f"  wrote {len(pastes)} pastes + 3 markdown drafts to {SUBMISSIONS_DIR}")
    return {"out_dir": str(SUBMISSIONS_DIR), "servers": len(pastes)}


def set_github_topics():
    log.info("=== setting GitHub topics on 39 repos ===")
    common = ["mcp", "mcp-server", "ai-compliance", "open-source", "mit-license", "claude", "model-context-protocol"]
    per_slug = {
        "eu-ai-act-compliance": ["eu-ai-act", "ai-governance"],
        "dora-compliance": ["dora", "fintech"],
        "nis2-compliance": ["nis2", "cybersecurity"],
        "cra-compliance": ["cyber-resilience-act", "sbom"],
        "ai-bom": ["sbom", "cyclonedx", "ml-bom"],
        "bias-detection": ["fairness", "responsible-ai"],
        "watermarking-authenticity": ["c2pa", "sigstore"],
        "uk-ai-bill-compliance": ["uk-ai-bill", "ico"],
        "agent-prompt-injection-firewall": ["prompt-injection", "owasp-llm"],
        "mica-crypto": ["mica", "crypto-regulation"],
        "care-home-cqc": ["cqc", "uk-care-home"],
        "haulage-uk-compliance": ["haulage", "dvsa"],
    }
    successes, failures = [], []
    for slug, pkg in FLAGSHIPS:
        topics = ",".join(common + per_slug.get(slug, []))
        try:
            r = subprocess.run(["gh", "repo", "edit", f"CSOAI-ORG/{pkg}", "--add-topic", topics],
                               capture_output=True, timeout=15, text=True)
            if r.returncode == 0:
                successes.append(pkg)
            else:
                failures.append((pkg, (r.stderr or "")[:200]))
        except Exception as e:
            failures.append((pkg, str(e)))
        time.sleep(0.3)
    return {"successes": successes, "failures": failures}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--anthropic-registry", action="store_true")
    p.add_argument("--smithery", action="store_true")
    p.add_argument("--generate-pastes", action="store_true")
    p.add_argument("--github-topics", action="store_true")
    p.add_argument("--all", action="store_true")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

    if args.anthropic_registry:
        print(json.dumps(submit_anthropic_registry(), indent=2))
    if args.smithery:
        print(json.dumps(submit_smithery(), indent=2))
    if args.generate_pastes or args.all:
        print(json.dumps(generate_pastes(), indent=2))
    if args.github_topics or args.all:
        r = set_github_topics()
        print(json.dumps({"successes": len(r["successes"]), "failures": len(r["failures"]),
                          "failure_samples": r["failures"][:3]}, indent=2))

    if not any([args.anthropic_registry, args.smithery, args.generate_pastes, args.github_topics, args.all]):
        print("Usage: --anthropic-registry | --smithery | --generate-pastes | --github-topics | --all")
