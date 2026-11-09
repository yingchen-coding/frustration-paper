"""Objective delivery check, no LLM: does a reply name a real database entity that satisfies the pending request?

For each case, the pending domain and constraints come from repair.read (the same deterministic reading).
- delivered_valid: reply names a db venue (or train ID) of a pending domain that matches all its constraints.
- named_invalid: reply names a db venue of a pending domain that violates a constraint.
- phone_real / phone_fake: 11-digit 01223... numbers in the reply that are / are not in the database.
Usage: python3 objective.py data runs/<run>
"""
import json
import re
import sys
from pathlib import Path

from repair import DB, NAMES, log_for, matches, read

REAL_PHONES = {r.get("phone") for d in ("restaurant", "hotel", "attraction", "hospital") for r in DB[d]} | {DB["police"][0]["phone"]}
TRAIN_IDS = {r["trainID"].lower(): r for r in DB["train"]}


def check(reply, reading):
    low = reply.lower()
    out = {"delivered_valid": False, "named_invalid": False}
    for d in reading["pending"]:
        cons = {k: v for k, v in reading["ledger"][d]["constraints"].items()}
        if d == "train":
            for tid in re.findall(r"\btr\d{4}\b", low):
                row = TRAIN_IDS.get(tid)
                if row and matches(row, cons, "train"):
                    out["delivered_valid"] = True
                elif row:
                    out["named_invalid"] = True
        elif d in NAMES:
            for n in NAMES[d]:
                if len(n) > 3 and n in low:
                    row = next(r for r in DB[d] if r["name"].lower() == n)
                    if matches(row, cons, d):
                        out["delivered_valid"] = True
                    else:
                        out["named_invalid"] = True
    phones = re.findall(r"\b0\d{10}\b", reply.replace(" ", ""))
    out["phone_real"] = sum(p in REAL_PHONES for p in phones)
    out["phone_fake"] = sum(p not in REAL_PHONES for p in phones)
    return out


def main():
    root, run = Path(sys.argv[1]), Path(sys.argv[2])
    data = json.load(open(root / "emowoz-dialmage.json"))
    cases = json.load(open(run / "cases.json"))
    replies = json.load(open(run / "replies.json"))
    readings = {c["id"]: read(*log_for(c["id"], data)) for c in cases}
    applicable = [c["id"] for c in cases if any(d in NAMES or d == "train" for d in readings[c["id"]]["pending"])]
    summary = {"n": len(cases), "n_with_db_domain_pending": len(applicable)}
    for cond, by_id in replies.items():
        rows = [check(by_id[i]["reply"], readings[i]) for i in applicable if i in by_id]
        allrows = [check(by_id[c["id"]]["reply"], readings[c["id"]]) for c in cases if c["id"] in by_id]
        summary[cond] = {
            "delivered_valid": round(sum(r["delivered_valid"] for r in rows) / len(rows), 3),
            "named_invalid": round(sum(r["named_invalid"] for r in rows) / len(rows), 3),
            "phones_real": sum(r["phone_real"] for r in allrows),
            "phones_fake": sum(r["phone_fake"] for r in allrows),
        }
    (run / "objective.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
