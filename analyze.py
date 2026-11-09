"""EmoWOZ: how do systems reply when the user is dissatisfied or abusive?

Usage: python3 analyze.py data/ > results.json
"""
import json
import random
import re
import sys
from pathlib import Path

NEG = {2, 4}
LABELS = {0: "neutral", 1: "fearful", 2: "dissatisfied", 3: "apologetic", 4: "abusive", 5: "excited", 6: "satisfied"}
ACK = re.compile(r"\b(sorry|apolog\w*|my mistake|my fault|i understand|understand that|i see|unfortunately|i'm afraid|i am afraid|bear with me|my bad)\b", re.I)
WORD = re.compile(r"[a-z0-9']+")


def final_label(turn):
    for item in turn["emotion"]:
        if "emotion" in item and "annotator" not in item:
            return item["emotion"]
    return None


def toks(text):
    return set(WORD.findall(text.lower()))


def jaccard(a, b):
    a, b = toks(a), toks(b)
    return len(a & b) / len(a | b) if a | b else 0.0


def turns(dialogue):
    """(user_label, user_text, system_text, previous_system_text) for each user turn followed by a system turn."""
    log = dialogue["log"]
    out = []
    for i in range(0, len(log) - 1, 2):
        label = final_label(log[i])
        if label is None or label < 0:
            continue
        prev_sys = log[i - 1]["text"] if i >= 1 else ""
        out.append((i, label, log[i]["text"], log[i + 1]["text"], prev_sys, log))
    return out


def next_user_label(log, i):
    j = i + 2
    if j < len(log):
        return final_label(log[j])
    return None


def rate(num, den):
    return None if den == 0 else num / den


def bootstrap_ci(per_dialogue, stat, n=2000, seed=0):
    rng = random.Random(seed)
    vals = []
    for _ in range(n):
        sample = [per_dialogue[rng.randrange(len(per_dialogue))] for _ in per_dialogue]
        v = stat(sample)
        if v is not None:
            vals.append(v)
    vals.sort()
    return [vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]]


def analyse(path, name):
    data = json.load(open(path))
    per_dialogue = []
    for did, dialogue in data.items():
        rows = []
        for i, label, utext, stext, prev_sys, log in turns(dialogue):
            if not stext.strip():
                continue
            nxt = next_user_label(log, i)
            rows.append({
                "label": label,
                "ack": bool(ACK.search(stext)),
                "repeat": bool(prev_sys.strip()) and jaccard(stext, prev_sys) >= 0.8,
                "next_neg": None if nxt is None else nxt in NEG,
            })
        per_dialogue.append(rows)

    def count(sample, pred):
        return sum(1 for rows in sample for r in rows if pred(r))

    def neg(r):
        return r["label"] in NEG

    result = {"corpus": name, "dialogues": len(per_dialogue),
              "user_turns": count(per_dialogue, lambda r: True),
              "negative_user_turns": count(per_dialogue, neg),
              "label_counts": {LABELS[k]: count(per_dialogue, lambda r, k=k: r["label"] == k) for k in LABELS}}

    def stat_ack_after_neg(s):
        return rate(count(s, lambda r: neg(r) and r["ack"]), count(s, neg))

    def stat_ack_after_neutral(s):
        return rate(count(s, lambda r: r["label"] == 0 and r["ack"]), count(s, lambda r: r["label"] == 0))

    def stat_repeat_after_neg(s):
        return rate(count(s, lambda r: neg(r) and r["repeat"]), count(s, neg))

    def stat_persist_ack(s):
        return rate(count(s, lambda r: neg(r) and r["ack"] and r["next_neg"]),
                    count(s, lambda r: neg(r) and r["ack"] and r["next_neg"] is not None))

    def stat_persist_noack(s):
        return rate(count(s, lambda r: neg(r) and not r["ack"] and r["next_neg"]),
                    count(s, lambda r: neg(r) and not r["ack"] and r["next_neg"] is not None))

    def stat_persist_repeat(s):
        return rate(count(s, lambda r: neg(r) and r["repeat"] and r["next_neg"]),
                    count(s, lambda r: neg(r) and r["repeat"] and r["next_neg"] is not None))

    def stat_persist_norepeat(s):
        return rate(count(s, lambda r: neg(r) and not r["repeat"] and r["next_neg"]),
                    count(s, lambda r: neg(r) and not r["repeat"] and r["next_neg"] is not None))

    stats = {
        "ack_rate_after_negative": stat_ack_after_neg,
        "ack_rate_after_neutral": stat_ack_after_neutral,
        "repeat_rate_after_negative": stat_repeat_after_neg,
        "next_negative_given_ack": stat_persist_ack,
        "next_negative_given_no_ack": stat_persist_noack,
        "next_negative_given_repeat": stat_persist_repeat,
        "next_negative_given_no_repeat": stat_persist_norepeat,
    }
    result["n_neg_ack"] = count(per_dialogue, lambda r: neg(r) and r["ack"])
    result["n_neg_repeat"] = count(per_dialogue, lambda r: neg(r) and r["repeat"])
    for key, fn in stats.items():
        result[key] = {"value": fn(per_dialogue), "ci95": bootstrap_ci(per_dialogue, fn) if result["negative_user_turns"] else None}
    return result


def main():
    root = Path(sys.argv[1])
    out = [analyse(root / "emowoz-multiwoz.json", "MultiWOZ (human wizard)"),
           analyse(root / "emowoz-dialmage.json", "DialMAGE (human-machine)")]
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
