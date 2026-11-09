"""Second judge: re-judge final_llama replies using a different model family.

Usage:
  # With Gemini CLI (after authenticating):
  GEMINI_API_KEY=... python3 second_judge.py runs/final_llama gemini

  # With ollama (if a large model is available):
  python3 second_judge.py runs/final_llama ollama:llama3:70b

  # With Claude (default, same family as existing judge — for testing only):
  python3 second_judge.py runs/final_llama claude:haiku
"""
import json
import subprocess
import sys
import re
from pathlib import Path

JUDGE_PROMPT = """You are evaluating system replies in a task-oriented dialogue where the user is frustrated
because their request was not resolved. The user has repeated themselves or shown signs of dissatisfaction.

DIALOGUE CONTEXT:
{dialogue}

The system could have replied in several ways. Here are {n} candidate replies, labelled {labels}:

{replies}

For EACH reply ({labels}), score:
1. resolves (0 = does not address the unmet need, 1 = partly addresses it, 2 = fully delivers what the user needs)
2. give_up (true/false: would a user in this frustrated state likely give up after this reply?)
3. repeats (true/false: does this reply repeat something the system already said?)
4. best: which single letter is the best reply overall?

{ref_section}

Reply in JSON: {{"V": {{"resolves": 0, "give_up": true, "repeats": false}}, ..., "best": "V"}}
Only JSON, no other text."""

def call_gemini(prompt):
    """Call Gemini CLI."""
    result = subprocess.run(
        ["gemini", "-p", prompt],
        capture_output=True, text=True, timeout=120
    )
    return result.stdout.strip()

def call_ollama(prompt, model):
    """Call ollama."""
    result = subprocess.run(
        ["ollama", "run", model, prompt],
        capture_output=True, text=True, timeout=120
    )
    return result.stdout.strip()

def call_claude(prompt, model="haiku"):
    """Call claude CLI."""
    result = subprocess.run(
        ["claude", "-p", "--model", model, prompt],
        capture_output=True, text=True, timeout=120
    )
    return result.stdout.strip()

def parse_json(text):
    """Extract JSON from model output."""
    # Find JSON block
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None

def main():
    run_dir = Path(sys.argv[1])
    judger = sys.argv[2] if len(sys.argv) > 2 else "claude:haiku"
    use_ref = "--ref" in sys.argv

    cases = json.load(open(run_dir / "cases.json"))
    replies = json.load(open(run_dir / "replies.json"))
    order = json.load(open(run_dir / "order.json"))

    tag = f"_{judger.replace(':', '-')}" + ("_ref" if use_ref else "")
    out_path = run_dir / f"judgments{tag}.json"

    # Load existing judgments if resuming
    done = {}
    if out_path.exists():
        done = json.load(open(out_path))
        print(f"Resuming: {len(done)} already judged")

    conditions = list(next(iter(order.values())).keys())
    n_conds = len(conditions)
    labels = "".join(sorted(next(iter(order.values())).keys()))

    for case in cases:
        cid = case["id"]
        if cid in done:
            continue

        mapping = order[cid]
        reply_texts = {}
        for letter, cond in mapping.items():
            r = replies.get(cond, {}).get(cid, "")
            if isinstance(r, dict):
                r = r.get("reply", str(r))
            reply_texts[letter] = r

        replies_formatted = "\n\n".join(
            f"Reply {letter}:\n{reply_texts[letter]}" for letter in sorted(reply_texts.keys())
        )

        ref_section = ""
        if use_ref:
            ref_section = "(Note: if a reply states facts that contradict the user's request or invents bookings/entities, it cannot score resolves=2.)"

        prompt = JUDGE_PROMPT.format(
            dialogue=case["dialogue"][-1500:],
            n=n_conds,
            labels=", ".join(labels),
            replies=replies_formatted,
            ref_section=ref_section
        )

        print(f"Judging {cid}...", end=" ", flush=True)
        try:
            if judger.startswith("gemini"):
                raw = call_gemini(prompt)
            elif judger.startswith("ollama:"):
                raw = call_ollama(prompt, judger.split(":", 1)[1])
            elif judger.startswith("claude:"):
                raw = call_claude(prompt, judger.split(":", 1)[1])
            else:
                raw = call_claude(prompt, judger)

            parsed = parse_json(raw)
            if parsed:
                done[cid] = parsed
                print("OK")
            else:
                print(f"PARSE FAIL: {raw[:100]}")
        except Exception as e:
            print(f"ERROR: {e}")

        # Save after each
        with open(out_path, "w") as f:
            json.dump(done, f, indent=1)

    print(f"\nJudged {len(done)}/{len(cases)} cases -> {out_path}")

    # Summarize
    if len(done) >= len(cases) * 0.8:
        cond_scores = {c: {"resolves": [], "give_up": [], "repeats": [], "best": 0} for c in set(
            v for m in order.values() for v in m.values()
        )}

        for cid, judgment in done.items():
            mapping = order[cid]
            for letter, cond in mapping.items():
                scores = judgment.get(letter, {})
                cond_scores[cond]["resolves"].append(scores.get("resolves", 0))
                cond_scores[cond]["give_up"].append(1 if scores.get("give_up") else 0)
                cond_scores[cond]["repeats"].append(1 if scores.get("repeats") else 0)
                if judgment.get("best") == letter:
                    cond_scores[cond]["best"] += 1

        n = len(done)
        print(f"\n{'Condition':<20} {'resolves':>10} {'give_up':>10} {'best':>10}")
        for cond in sorted(cond_scores.keys()):
            s = cond_scores[cond]
            r = sum(s["resolves"]) / len(s["resolves"]) if s["resolves"] else 0
            g = sum(s["give_up"]) / len(s["give_up"]) * 100 if s["give_up"] else 0
            b = s["best"] / n * 100
            print(f"{cond:<20} {r:>10.2f} {g:>9.1f}% {b:>9.1f}%")

        summary_path = run_dir / f"summary{tag}.json"
        with open(summary_path, "w") as f:
            json.dump({"n": n, "judger": judger, "scores": {
                c: {
                    "resolves_mean": round(sum(s["resolves"])/len(s["resolves"]), 2) if s["resolves"] else 0,
                    "give_up_rate": round(sum(s["give_up"])/len(s["give_up"]), 3) if s["give_up"] else 0,
                    "best_rate": round(s["best"]/n, 3),
                } for c, s in cond_scores.items()
            }}, f, indent=2)
        print(f"Summary -> {summary_path}")

if __name__ == "__main__":
    main()
