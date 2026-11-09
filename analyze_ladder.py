"""Evaluate the repair escalation ladder and grounding ledger across all DialMAGE user turns."""
import json
import random
import sys
from pathlib import Path

import analyze
import repair


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")
    dialmage = json.load(open(root / "emowoz-dialmage.json"))

    per_dlg = []
    for did, dlg in dialmage.items():
        log = dlg if isinstance(dlg, list) else dlg.get("log", [])
        rows = []
        for i in range(0, len(log), 2):
            turn = log[i]
            emo = analyze.final_label(turn)
            if emo is None:
                continue
            is_neg = emo in {2, 4}
            r = repair.read(log, i)
            stg = min(r["stage"], 3)
            unmet = any(not r["ledger"][d]["delivered"] and i >= 2 for d in r["pending"])
            nxt_neg = None
            if i + 2 < len(log):
                nxt_emo = analyze.final_label(log[i + 2])
                if nxt_emo is not None:
                    nxt_neg = nxt_emo in {2, 4}
            rows.append({"stg": stg, "neg": is_neg, "nxt_neg": nxt_neg, "unmet": unmet})
        per_dlg.append(rows)

    def boot(fn, seed=0, B=2000):
        rng = random.Random(seed)
        n = len(per_dlg)
        vals = [fn([per_dlg[rng.randrange(n)] for _ in range(n)]) for _ in range(B)]
        vals.sort()
        return {"value": round(fn(per_dlg), 4), "ci95": [round(vals[int(0.025 * B)], 4), round(vals[int(0.975 * B) - 1], 4)]}

    out = {"total_turns": sum(len(d) for d in per_dlg), "stages": {}, "ledger_unmet": {}}
    for s in range(4):
        key = f"stage_{s}" if s < 3 else "stage_3_plus"
        cnt = sum(1 for d in per_dlg for r in d if r["stg"] == s)
        fn_cur = lambda sample, s=s: sum(1 for d in sample for r in d if r["stg"] == s and r["neg"]) / max(1, sum(1 for d in sample for r in d if r["stg"] == s))
        fn_nxt = lambda sample, s=s: sum(1 for d in sample for r in d if r["stg"] == s and r["nxt_neg"] is True) / max(1, sum(1 for d in sample for r in d if r["stg"] == s and r["nxt_neg"] is not None))
        out["stages"][key] = {"n": cnt, "current_negative": boot(fn_cur), "next_negative": boot(fn_nxt)}

    for flag, label in [(False, "delivered_or_first_turn"), (True, "pending_unmet")]:
        cnt = sum(1 for d in per_dlg for r in d if r["unmet"] == flag)
        fn_cur = lambda sample, f=flag: sum(1 for d in sample for r in d if r["unmet"] == f and r["neg"]) / max(1, sum(1 for d in sample for r in d if r["unmet"] == f))
        out["ledger_unmet"][label] = {"n": cnt, "current_negative": boot(fn_cur)}

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
