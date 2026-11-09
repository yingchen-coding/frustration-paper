"""Validate the word lists and thresholds used in analyze.py.
Outputs a validation report for FINDINGS.md / paper Limitations.
"""
import json, re, random
from collections import Counter
from pathlib import Path

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

no_match = 200 - tp - fp
print(f"\n=== COMPLAINT WORD VALIDATION (200 negative turns) ===")
print(f"Matched: {tp + fp} / 200 ({(tp + fp) / 200 * 100:.1f}%)")
print(f"  True positives: {tp}")
print(f"  False positives (task language): {fp}")
print(f"  Not matched: {no_match}")
if tp + fp > 0:
    print(f"  Precision: {tp / (tp + fp) * 100:.1f}%")
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
print(f"\n=== ACK REGEX VALIDATION (200 system turns after negative user turns) ===")
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
print(f"\n=== REPEAT THRESHOLD SENSITIVITY (all DialMAGE negative turns) ===")
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

# --- 4. Reader accuracy: check repair.py on 20 sampled cases from final_llama ---
print(f"\n=== REPAIR READER SPOT-CHECK (20 cases from final_llama) ===")
try:
    import repair
    with open("runs/final_llama/cases.json") as f:
        cases = json.load(f)
    random.shuffle(cases)
    check_cases = cases[:20]

    stage_dist = Counter()
    has_pending = 0
    has_db_rows = 0
    for c in check_cases:
        brief = repair.brief(c["dialogue"])
        # Count stages
        if "ESCALATION STAGE" in brief:
            for line in brief.split("\n"):
                if "ESCALATION STAGE" in line:
                    try:
                        stage = int(line.strip()[-1])
                        stage_dist[stage] += 1
                    except:
                        pass
        if "PENDING" in brief.upper() or "NOT YET" in brief.upper():
            has_pending += 1
        if "DATABASE" in brief.upper() or "ROWS" in brief.upper():
            has_db_rows += 1

    print(f"  Stage distribution: {dict(sorted(stage_dist.items()))}")
    print(f"  Cases with pending items identified: {has_pending}/20")
    print(f"  Cases with database rows: {has_db_rows}/20")
except Exception as e:
    print(f"  Could not run reader check: {e}")

print("\n=== DONE ===")
