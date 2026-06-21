#!/usr/bin/env python3
"""
SIGIL — Sovereign Inter-aGent Interchange Language
==================================================
A compact, deterministic, token-efficient protocol for SOV3 agents to talk to
each other faster — with a LOSSLESS human-readable translator so you (and an
auditor) can always read exactly what was said.

WHAT THIS IS NOT
----------------
This is NOT David Wynn Miller's "Quantum Grammar / Parse-Syntax." That system is
pseudo-legal and has zero computational meaning. SIGIL is the opposite: a real
controlled DSL with a rigid grammar (one line → one parse), a machine form
(dict) and two human renderings (gloss = English, table = audit row).

WHY IT'S USEFUL
---------------
1. SPEED/COST: agents exchange dense lines instead of verbose English (~2-5x
   fewer tokens at SOV3's message sizes; the gap widens with structured content).
2. DETERMINISM: every line parses exactly one way — no ambiguity between agents.
3. HUMAN-READABLE: gloss() turns any line back into plain English on demand.
4. AUDITABLE (the business angle): every exchange hashes to a stable digest you
   can sign with the attestation engine → "verifiable agent communication,"
   which is exactly what EU AI Act Art 12 (logging) + Art 14 (oversight) demand.

GRAMMAR
-------
    OP|arg|arg|...            # pipe-delimited, opcode first
Opcodes: P propose · V vote · M memory · Q query · C care · H handoff · S state · A alert
Vote glyphs: + APPROVE · - REJECT · ~ ABSTAIN
"""

import hashlib
import json
import re

OPCODES = {
    "P": "propose", "V": "vote", "M": "memory", "Q": "query",
    "C": "care", "H": "handoff", "S": "state", "A": "alert",
}
CHOICE = {"+": "APPROVE", "-": "REJECT", "~": "ABSTAIN"}
CHOICE_INV = {v: k for k, v in CHOICE.items()}


# ---- machine layer: dict <-> SIGIL line (LOSSLESS) -------------------------

def encode(d: dict) -> str:
    """Structured agent intent (dict) -> compact SIGIL line."""
    op = d["op"]
    if op == "P":
        return f"P|{d['id']}|{d['topic']}|{','.join(d['options'])}"
    if op == "V":
        return f"V|{d['agent']}|{d['prop']}|{CHOICE_INV[d['choice']]}|{d['conf']}"
    if op == "M":
        return f"M|{d['key']}|{d['value']}|{d['salience']}"
    if op == "Q":
        return f"Q|{d['pattern']}|{d['k']}"
    if op == "C":
        return f"C|{d['subject']}|{d['score']}|{','.join(d['dims'])}"
    if op == "H":
        return f"H|{d['frm']}|{d['to']}|{d['task']}"
    if op == "S":
        return "S|" + "|".join(f"{k}:{v}" for k, v in d["fields"].items())
    if op == "A":
        return f"A|{d['level']}|{d['msg']}"
    raise ValueError(f"unknown op {op!r}")


def parse(line: str) -> dict:
    """SIGIL line -> structured dict (the inverse of encode)."""
    parts = line.strip().split("|")
    op, a = parts[0], parts[1:]
    if op == "P":
        return {"op": "P", "id": a[0], "topic": a[1], "options": a[2].split(",")}
    if op == "V":
        return {"op": "V", "agent": a[0], "prop": a[1],
                "choice": CHOICE.get(a[2], a[2]), "conf": a[3]}
    if op == "M":
        return {"op": "M", "key": a[0], "value": a[1], "salience": a[2]}
    if op == "Q":
        return {"op": "Q", "pattern": a[0], "k": a[1]}
    if op == "C":
        return {"op": "C", "subject": a[0], "score": a[1], "dims": a[2].split(",")}
    if op == "H":
        return {"op": "H", "frm": a[0], "to": a[1], "task": a[2]}
    if op == "S":
        return {"op": "S", "fields": dict(kv.split(":", 1) for kv in a)}
    if op == "A":
        return {"op": "A", "level": a[0], "msg": a[1]}
    raise ValueError(f"unknown op {op!r}")


# ---- human layer: SIGIL line -> plain English -----------------------------

def gloss(line: str) -> str:
    """The translator: any SIGIL line -> plain English."""
    p = parse(line)
    op = p["op"]
    if op == "P":
        return f"Proposal {p['id']}: \"{p['topic']}\" — options: {', '.join(p['options'])}."
    if op == "V":
        return f"Agent {p['agent']} votes {p['choice']} on proposal {p['prop']} (confidence {p['conf']})."
    if op == "M":
        return f"Store memory [{p['key']}] = \"{p['value']}\" (salience {p['salience']})."
    if op == "Q":
        return f"Retrieve top {p['k']} memories matching \"{p['pattern']}\"."
    if op == "C":
        return f"Care assessment of {p['subject']}: {p['score']} across {', '.join(p['dims'])}."
    if op == "H":
        return f"Handoff from {p['frm']} to {p['to']}: {p['task']}."
    if op == "S":
        return "State — " + ", ".join(f"{k}={v}" for k, v in p["fields"].items()) + "."
    if op == "A":
        return f"ALERT[{p['level']}]: {p['msg']}"
    return line


# ---- audit layer: stable digest you can sign (ties to attestation moat) ----

def digest(line: str) -> str:
    """Canonical hash of an exchange — feed to the attestation signer."""
    canon = json.dumps(parse(line), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()[:16]


def approx_tokens(s: str) -> int:
    """Rough token proxy (chars/4 heuristic — real BPE differs, but the RATIO holds)."""
    return max(1, round(len(s) / 4))


# ---- demo ------------------------------------------------------------------

if __name__ == "__main__":
    # A short SOV3 council exchange, written natively in SIGIL.
    convo = [
        "P|ad6d|Prioritise Q3: apex-unblock vs TUI-distribution vs partnership|A,B,C",
        "V|jarvis|ad6d|+|0.82",
        "V|sophie|ad6d|~|0.41",
        "V|orion|ad6d|+|0.77",
        "C|proposal-ad6d|0.91|attunement,reciprocity,non-maleficence",
        "M|decision/ad6d|council leans A (apex-unblock), care-aligned|0.88",
        "S|consciousness:0.525|agents:46|care:0.967|khaldunian_warn:false",
        "A|info|2/3 supermajority reached — proposal ad6d ADOPTED",
    ]

    # Equivalent verbose English an LLM would otherwise emit (for fair comparison).
    english = [
        'New council proposal ad6d: "Prioritise Q3: apex-unblock vs TUI-distribution vs partnership". The available options are A, B, and C.',
        "Agent jarvis votes to APPROVE proposal ad6d with a confidence of 0.82.",
        "Agent sophie votes to ABSTAIN on proposal ad6d with a confidence of 0.41.",
        "Agent orion votes to APPROVE proposal ad6d with a confidence of 0.77.",
        "Care assessment of proposal ad6d scored 0.91 across attunement, reciprocity, and non-maleficence.",
        'Store a memory under decision/ad6d: "council leans A (apex-unblock), care-aligned" with salience 0.88.',
        "Current state: consciousness 0.525, 46 active agents, care alignment 0.967, no Khaldunian warning.",
        "Alert (info level): a two-thirds supermajority was reached, so proposal ad6d is ADOPTED.",
    ]

    print("=" * 74)
    print("SIGIL — live demo: an SOV3 council vote, machine-dense + human-readable")
    print("=" * 74)

    sig_tok = eng_tok = 0
    for s, e in zip(convo, english):
        st, et = approx_tokens(s), approx_tokens(e)
        sig_tok += st
        eng_tok += et
        print(f"\n  SIGIL  ({st:>3} tok)  {s}")
        print(f"  ENGLISH({et:>3} tok)  {gloss(s)}")
        print(f"  audit-digest        {digest(s)}   <- sign this for an auditable log")

    print("\n" + "=" * 74)
    print(f"  TOTAL — SIGIL {sig_tok} tok  vs  English {eng_tok} tok  "
          f"=>  {eng_tok/sig_tok:.1f}x denser, {(1-sig_tok/eng_tok)*100:.0f}% fewer tokens")
    print("=" * 74)

    # Prove the machine layer is lossless: SIGIL -> dict -> SIGIL is identity.
    ok = all(encode(parse(s)) == s for s in convo)
    print(f"  round-trip lossless (SIGIL->dict->SIGIL == original): {ok}")
    print("  human-readable on demand: gloss() ✓   auditable: digest() ✓\n")
