"""
gepa_compliance.py — GEPA-optimise a compliance-answer prompt against the Article-50 eval.

The agent-stack research's highest-ROI move, now unblocked by article50_eval. Runs in the
ISOLATED venv (~/clawd/.venv_agentstack) — never touches the live SOV3 venv. Uses local Ollama
(gemma4:e4b) as both task + reflection model. Measures baseline (raw prompt) vs GEPA-optimised
mean score on the eval, and saves the evolved instruction so SOV3 can use it.

Run: ~/clawd/.venv_agentstack/bin/python multi_agent/gepa_compliance.py
"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dspy
import article50_eval as ev

OLLAMA = "http://localhost:11434"
MODEL = "ollama_chat/gemma4:e4b"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "evals", "gepa_compliance_prompt.txt")


class ComplianceQA(dspy.Signature):
    """Answer the EU AI Act question precisely, citing the exact Article (e.g. Article 50(2)) and key terms."""
    question: str = dspy.InputField()
    answer: str = dspy.OutputField(desc="concise, cites the right Article number(s) and key compliance terms")


def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
    s = ev.score(getattr(pred, "answer", "") or "", gold.entry)
    fb = (f"Scored {s:.2f}. To improve, the answer MUST contain these citations {gold.entry['citations']} "
          f"and these terms {gold.entry['keywords']} verbatim.")
    try:
        return dspy.Prediction(score=s, feedback=fb)
    except Exception:
        return s


def mean_score(program, items):
    tot = 0.0
    for e in items:
        try:
            ans = program(question=e["question"]).answer
        except Exception:
            ans = ""
        tot += ev.score(ans, e)
    return round(tot / len(items), 4)


def main():
    lm = dspy.LM(MODEL, api_base=OLLAMA, api_key="", max_tokens=600, temperature=0.0)
    dspy.configure(lm=lm)
    prog = dspy.ChainOfThought(ComplianceQA)

    EVAL = ev.EVAL
    sample = EVAL[:8]                      # bounded eval for speed
    trainset = [dspy.Example(question=e["question"], entry=e).with_inputs("question") for e in EVAL[:6]]
    valset = [dspy.Example(question=e["question"], entry=e).with_inputs("question") for e in EVAL[6:10]]

    t0 = time.time()
    base = mean_score(prog, sample)
    print(f"  baseline mean (n={len(sample)}): {base}  [{time.time()-t0:.0f}s]")

    # bounded GEPA budget so it finishes in one run
    try:
        gepa = dspy.GEPA(metric=metric, max_metric_calls=40, reflection_lm=lm, track_stats=False)
    except TypeError:
        gepa = dspy.GEPA(metric=metric, auto="light", reflection_lm=lm)
    compiled = gepa.compile(prog, trainset=trainset, valset=valset)

    opt = mean_score(compiled, sample)
    print(f"  optimised mean (n={len(sample)}): {opt}  [{time.time()-t0:.0f}s total]")
    print(f"  LIFT: {base} → {opt}  ({'+' if opt>=base else ''}{round(opt-base,4)})")

    # save the evolved instruction
    try:
        instr = ""
        for name, p in compiled.named_predictors():
            instr = getattr(p.signature, "instructions", "") or ""
            break
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w") as f:
            f.write(instr)
        print(f"  saved evolved instruction → {OUT} ({len(instr)} chars)")
    except Exception as e:
        print(f"  (instruction save skipped: {e})")


if __name__ == "__main__":
    main()
