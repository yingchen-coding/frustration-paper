"""Validate the word lists and thresholds used in analyze.py.
Outputs a validation report for FINDINGS.md / paper Limitations.
"""
import csv
import json
import random
import re
from pathlib import Path

import repair

NEG = {2, 4}

# Same regexes as analyze.py
ACK = re.compile(r"\b(sorry|apolog\w*|my mistake|my fault|i understand|understand that|i see|unfortunately|i'm afraid|i am afraid|bear with me|my bad)\b", re.I)
COMPLAINT = re.compile(r"\b(no|not|wrong|incorrect|already|again|still|frustrat|annoy|useless|terrible|horrible|ridiculous|stupid|help me)\b", re.I)
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

with open("data/emowoz-dialmage.json") as f:
    data = json.load(f)

random.seed(42)

# Collect all negative user turns and system turns after them
neg_user_turns = []
sys_after_neg = []
all_user_texts_by_dlg = {}  # for repeat analysis

for dlg_id, dlg in data.items():
    turns = dlg["log"]
    user_texts = []
    for i, turn in enumerate(turns):
        if i % 2 == 0:  # user turn
            lab = final_label(turn)
            if lab is None:
                continue
            if lab in NEG:
                neg_user_turns.append({
                    "dlg": dlg_id, "idx": i, "text": turn["text"],
                    "prev_user_texts": list(user_texts),
                })
                if i + 1 < len(turns):
                    sys_after_neg.append(turns[i + 1]["text"])
            user_texts.append(turn["text"])

print(f"Total negative user turns in DialMAGE: {len(neg_user_turns)}")
print(f"System turns after negative: {len(sys_after_neg)}")

# --- 1. Complaint word validation on 200 sampled negative turns ---
random.shuffle(neg_user_turns)
s200 = neg_user_turns[:200]

tp, fp, fn = 0, 0, 0
fp_examples = []
tp_examples = []
fn_examples = []

for s in s200:
    m = COMPLAINT.search(s["text"])
    if m:
        word = m.group(0).lower()
        text_l = s["text"].lower()
        idx = text_l.index(word)
        after = text_l[idx + len(word):].strip()[:40]
        # Heuristic: "no/not" followed by task words = false positive
        task_words = ["parking", "internet", "wifi", "expensive", "matter", "need",
                      "preference", "particular", "specific", "care", "price range"]
        is_fp = word in ("no", "not") and any(p in after for p in task_words)
        if is_fp:
            fp += 1
            fp_examples.append(f"  [{word}] {s['text'][:130]}")
        else:
            tp += 1
            tp_examples.append(f"  [{word}] {s['text'][:130]}")

Path("validation").mkdir(exist_ok=True)
with open(Path("validation") / "complaint_sheet.csv", "w") as f:
    f.write("matched_word,heuristic_flag,text,LABEL_real_complaint(y/n)\n")
    for flag, rows in (("task_language", fp_examples), ("complaint", tp_examples)):
        for line in rows:
            word, text = line.strip()[1:].split("] ", 1)
            f.write(f'"{word}",{flag},"{text.replace(chr(34), chr(39))}",\n')
no_match = 200 - tp - fp
print("\n=== COMPLAINT WORD VALIDATION (200 negative turns) ===")
print(f"Matched: {tp + fp} / 200 ({(tp + fp) / 200 * 100:.1f}%)")
print(f"  Not flagged: {tp}")
print(f"  Flagged by heuristic as task language: {fp}")
print(f"  Not matched: {no_match}")
if tp + fp > 0:
    print(f"  Heuristic precision (NOT hand-labelled; see validation/complaint_sheet.csv): {tp / (tp + fp) * 100:.1f}%")
print(f"  Recall (of complaint-word turns): {(tp + fp) / 200 * 100:.1f}% of negative turns matched")

if fp_examples:
    print("\nFalse positive examples:")
    for e in fp_examples[:5]:
        print(e)

print("\nTrue positive examples:")
for e in tp_examples[:8]:
    print(e)

# --- 2. Ack regex validation on 200 system turns after negative ---
random.shuffle(sys_after_neg)
sys200 = sys_after_neg[:200]

ack_matched = sum(1 for t in sys200 if ACK.search(t))
print("\n=== ACK REGEX VALIDATION (200 system turns after negative user turns) ===")
print(f"Ack matched: {ack_matched} / 200 ({ack_matched / 200 * 100:.1f}%)")

ack_examples = [(t[:130], ACK.search(t).group(0)) for t in sys200 if ACK.search(t)][:8]
print("\nMatched examples:")
for text, word in ack_examples:
    print(f"  [{word}] {text}")

# Check for false matches (system saying "I see" as task language)
false_ack = sum(1 for t in sys200 if ACK.search(t) and ACK.search(t).group(0).lower() == "i see"
               and "i see that" not in t.lower())
print(f"\n'I see' matches (potential false acks): {false_ack}")

# --- 3. Repeat threshold sensitivity ---
print("\n=== REPEAT THRESHOLD SENSITIVITY (all DialMAGE negative turns) ===")
for threshold in [0.3, 0.4, 0.5, 0.6, 0.7]:
    repeat_count = 0
    total_neg = 0
    for dlg_id, dlg in data.items():
        turns = dlg["log"]
        user_texts = []
        for i, turn in enumerate(turns):
            if i % 2 == 0:
                lab = final_label(turn)
                if lab is None:
                    continue
                if lab in NEG:
                    total_neg += 1
                    for prev in user_texts:
                        if jaccard(turn["text"], prev) >= threshold:
                            repeat_count += 1
                            break
                user_texts.append(turn["text"])
    print(f"  Jaccard >= {threshold}: {repeat_count}/{total_neg} ({repeat_count / total_neg * 100:.1f}%)")

# --- 4. Reader output sheet for hand labelling (20 cases from final_llama) ---
print("\n=== REPAIR READER SHEET (20 cases from final_llama) ===")
dm = json.load(open(Path("data") / "emowoz-dialmage.json"))
with open("runs/final_llama/cases.json") as f:
    reader_cases = json.load(f)
rng = random.Random(42)
rng.shuffle(reader_cases)
out_dir = Path("validation")
out_dir.mkdir(exist_ok=True)
found = with_rows = 0
with open(out_dir / "reader_sheet.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["case_id", "last_user_turns", "stage", "pending", "constraints", "missing", "has_db_rows",
                "LABEL_pending_domain_correct(y/n)", "LABEL_constraints_correct(y/n)", "notes"])
    for c in reader_cases[:20]:
        log, i = repair.log_for(c["id"], dm)
        text, r = repair.brief(log, i)
        dom = r["pending"][0] if r["pending"] else ""
        e2 = r["ledger"].get(dom, {})
        rows = "Database:" in text
        found += bool(dom)
        with_rows += rows
        users = [log[k]["text"] for k in range(0, i + 1, 2)][-3:]
        w.writerow([c["id"], " || ".join(users), r["stage"], dom, json.dumps(e2.get("constraints", {})),
                    ",".join(e2.get("missing", [])), rows, "", "", ""])
print(f"  Reader named a pending domain: {found}/20; gave database rows: {with_rows}/20")
print("  Correctness is NOT checked here; label validation/reader_sheet.csv by hand.")

print("\n=== DONE ===")
