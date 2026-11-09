"""Evaluate repair cues vs explicit emotion words across external task-oriented dialogue corpora (USS: SGD and ReDial)."""
import ast
import json
import random
import re
import sys
from pathlib import Path

import repair

EMO_WORDS = re.compile(
    r"\b(frustrat|annoy|useless|terrible|horrible|ridiculous|stupid|angry|mad|upset|disappoint|hate|awful|pathetic|incompetent|worst)\w*\b",
    re.I,
)


def analyse_uss(root, corpus):
    dialogues = []
    cur_dlg = []
    for split in ("train", "valid", "test"):
        path = root / corpus / f"{split}_{corpus}.txt"
        for line in open(path):
            parts = line.strip().split("\t")
            if len(parts) < 3:
                continue
            turns = ast.literal_eval(parts[0])
            label = int(parts[2])  # 0=dissatisfied, 1=neutral, 2=satisfied
            if turns[-1].startswith("OVERALL|||"):
                if cur_dlg:
                    dialogues.append(cur_dlg)
                    cur_dlg = []
                continue
            user_turns = [t.split("|||")[0].strip() for t in turns if t.split("|||")[0].strip()]
            if not user_turns:
                continue
            st, _ = repair.stage_of(user_turns)
            cur_dlg.append({
                "neg": label == 0,
                "stage": st,
                "emo_word": bool(EMO_WORDS.search(user_turns[-1])),
            })
        if cur_dlg:
            dialogues.append(cur_dlg)
            cur_dlg = []

    def boot(fn, seed=0, B=2000):
        rng = random.Random(seed)
        n = len(dialogues)
        vals = [fn([dialogues[rng.randrange(n)] for _ in range(n)]) for _ in range(B)]
        vals.sort()
        return {"value": round(fn(dialogues), 4), "ci95": [round(vals[int(0.025 * B)], 4), round(vals[int(0.975 * B) - 1], 4)]}

    n_turns = sum(len(d) for d in dialogues)
    n_neg = sum(1 for d in dialogues for r in d if r["neg"])
    fn_emo_in_neg = lambda s: sum(1 for d in s for r in d if r["neg"] and r["emo_word"]) / max(1, sum(1 for d in s for r in d if r["neg"]))
    fn_cues_in_neg = lambda s: sum(1 for d in s for r in d if r["neg"] and r["stage"] >= 1) / max(1, sum(1 for d in s for r in d if r["neg"]))
    fn_neg_stg0 = lambda s: sum(1 for d in s for r in d if r["stage"] == 0 and r["neg"]) / max(1, sum(1 for d in s for r in d if r["stage"] == 0))
    fn_neg_stg1p = lambda s: sum(1 for d in s for r in d if r["stage"] >= 1 and r["neg"]) / max(1, sum(1 for d in s for r in d if r["stage"] >= 1))

    return {
        "corpus": f"USS-{corpus.upper()}",
        "dialogues": len(dialogues),
        "user_turns": n_turns,
        "negative_turns": n_neg,
        "emotion_word_share_of_negative": boot(fn_emo_in_neg),
        "repair_cue_share_of_negative": boot(fn_cues_in_neg),
        "negative_rate_stage_0": boot(fn_neg_stg0),
        "negative_rate_stage_1_plus": boot(fn_neg_stg1p),
    }


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/usda/dataset")
    out = [analyse_uss(root, c) for c in ("sgd", "redial")]
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
