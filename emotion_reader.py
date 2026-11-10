"""Can dissatisfaction be read from linguistic repair behaviour, without emotion words?

Compares detectors of a negative user turn (EmoWOZ dissatisfied/abusive) on a random sample of DialMAGE user turns:
  - complaint words (lexicon)
  - REPAIR repair stage >= 1 and >= 2 (linguistic cues only, no model)
  - LLM reading only the single utterance (word-level emotion)
  - LLM reading the dialogue up to that turn (context)
Usage: python3 emotion_reader.py data runs/emotion_reader [N]
"""
import json
import random
import re
import subprocess
import sys
from pathlib import Path

from analyze import final_label
from repair import stage_of

NEG = {2, 4}
COMPLAINT = re.compile(r"\b(no|not|don't|didn't|wrong|already|again|said|told|useless|stupid|bad|never|can't|cannot|why)\b", re.I)
BATCH = 20
SINGLE = ("For each numbered user message from a travel-booking chat, say whether the user is dissatisfied with the "
          "assistant (true/false). You see only the message itself. Return only JSON: {\"1\": true, ...}.")
CONTEXT = ("For each numbered case you see a travel-booking chat up to the user's latest message. Say whether the user "
           "is dissatisfied with the assistant at that latest message (true/false). Return only JSON: {\"1\": true, ...}.")


def sample_turns(root, n, seed=7):
    data = json.load(open(root / "emowoz-dialmage.json"))
    items = []
    for did, d in data.items():
        log = d["log"]
        for i in range(0, len(log), 2):
            lab = final_label(log[i])
            if lab is None or lab < 0 or not log[i]["text"].strip():
                continue
            items.append((did, i))
    rng = random.Random(seed)
    rng.shuffle(items)
    out = []
    for did, i in items[:n]:
        log = data[did]["log"]
        users = [log[k]["text"] for k in range(0, i + 1, 2)]
        ctx = "\n".join(("User: " if k % 2 == 0 else "Assistant: ") + log[k]["text"].strip()
                        for k in range(i + 1) if log[k]["text"].strip())
        out.append({"id": f"{did}#{i}", "text": log[i]["text"], "context": ctx[-2500:],
                    "neg": final_label(log[i]) in NEG, "stage": stage_of(users)[0]})
    return out


def llm(prompt):
    for _ in range(3):
        res = subprocess.run(["claude", "-p", "--model", "haiku", prompt], capture_output=True, text=True, timeout=600)
        if res.returncode == 0:
            s, e = res.stdout.find("{"), res.stdout.rfind("}")
            if s >= 0 and e > s:
                try:
                    return json.loads(res.stdout[s:e + 1])
                except json.JSONDecodeError:
                    pass
    raise RuntimeError("LLM call failed three times")


def llm_labels(turns, key, instruction, run_dir):
    path = run_dir / f"llm_{key}.json"
    done = json.loads(path.read_text()) if path.exists() else {}
    todo = [t for t in turns if t["id"] not in done]
    for b in range(0, len(todo), BATCH):
        batch = todo[b:b + BATCH]
        body = "\n\n".join(f"{n + 1}. {t['text'] if key == 'single' else t['context']}" for n, t in enumerate(batch))
        got = llm(f"{instruction}\n\n{body}")
        for n, t in enumerate(batch):
            v = got.get(str(n + 1))
            if isinstance(v, bool):
                done[t["id"]] = v
        path.write_text(json.dumps(done, indent=1))
    return done


def prf(pred, gold):
    tp = sum(p and g for p, g in zip(pred, gold))
    fp = sum(p and not g for p, g in zip(pred, gold))
    fn = sum(g and not p for p, g in zip(pred, gold))
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return prec, rec, (2 * prec * rec / (prec + rec) if prec + rec else 0.0)


def boot(rows, fn, n=2000, seed=0):
    rng = random.Random(seed)
    vals = sorted(fn([rows[rng.randrange(len(rows))] for _ in rows]) for _ in range(n))
    return [round(vals[int(0.025 * n)], 3), round(vals[int(0.975 * n) - 1], 3)]


def main():
    root, run_dir = Path(sys.argv[1]), Path(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 400
    run_dir.mkdir(parents=True, exist_ok=True)
    turns = sample_turns(root, n)
    single = llm_labels(turns, "single", SINGLE, run_dir)
    context = llm_labels(turns, "context", CONTEXT, run_dir)
    rows = [t for t in turns if t["id"] in single and t["id"] in context]
    detectors = {
        "complaint_words": lambda t: bool(COMPLAINT.search(t["text"])),
        "repair_stage>=1": lambda t: t["stage"] >= 1,
        "repair_stage>=2": lambda t: t["stage"] >= 2,
        "llm_single_utterance": lambda t: single[t["id"]],
        "llm_with_context": lambda t: context[t["id"]],
        "stage>=2_or_llm_single": lambda t: t["stage"] >= 2 or single[t["id"]],
    }
    out = {"n": len(rows), "negative_rate": round(sum(t["neg"] for t in rows) / len(rows), 3)}
    for name, det in detectors.items():
        p, r, f = prf([det(t) for t in rows], [t["neg"] for t in rows])
        out[name] = {"precision": round(p, 3), "recall": round(r, 3), "f1": round(f, 3),
                     "f1_ci95": boot(rows, lambda s, d=det: prf([d(t) for t in s], [t["neg"] for t in s])[2])}
    (run_dir / "summary.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
