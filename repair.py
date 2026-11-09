"""REPAIR: Reading Escalation And Pending Items for Response.

Deterministic reading of a task-oriented dialogue at a user turn:
  - repair reader: linguistic cues of other-initiated repair and escalation -> stage 0-4
  - grounding ledger: what the user asked for per domain, whether it was delivered, what is pending
  - database lookup for the pending request (MultiWOZ db), relaxing one constraint at a time if nothing matches
The brief is given to any generator; the model does not have to infer the user's state itself.
"""
import json
import re
from pathlib import Path

from analyze import jaccard

DB_DIR = Path(__file__).resolve().parent / "data" / "db"
DOMAIN_WORDS = {
    "restaurant": r"restaurant|food|eat|dine|dinner|lunch|table|cuisine",
    "hotel": r"hotel|guest ?house|place to stay|stay|room|stars?|parking|wifi|internet",
    "attraction": r"attraction|museum|college|park|theatre|cinema|nightclub|pool|entertainment|architecture|boat|visit|things to do",
    "train": r"train|station|depart|arriv",
    "taxi": r"taxi|cab",
    "police": r"police",
    "hospital": r"hospital|department",
}
REQUIRED = {"train": [["departure"], ["destination"], ["day"]],
            "taxi": [["departure"], ["destination"], ["leaveAt", "arriveBy"]]}
RELAX_ORDER = ["type", "internet", "parking", "pricerange", "stars", "area", "food", "leaveAt", "arriveBy", "day"]
NOT_NEEDED = r"(does not|doesn't|do not|don't|no) need|not (required|necessary|important)|doesn't matter|don't care"
ASKED_INFO = {"phone": r"phone|number|contact", "address": r"address|where is|located", "postcode": r"post ?code",
              "price": r"price|cost|how much|fee", "reference": r"reference|booking number|confirm",
              "time": r"what time|when does|departure time|arrival time|leave at|arrive at", "travel time": r"how long|duration"}
OIR = re.compile(r"^\s*(what|huh|pardon|sorry)\s*\??\s*$|\?\?|\bwhat\?|i said|i told you|i already|already (said|told|asked)", re.I)
NEGATION = re.compile(r"\b(no|not|don't|didn't|doesn't|wrong|again|already|still|instead)\b", re.I)
META = re.compile(r"\b(can you help|help me|are you (there|listening)|you('re| are) not|understand( me)?\b|answer (me|my)|useless|stupid)\b", re.I)
GIVE_UP = re.compile(r"\b(forget it|never ?mind|bye|give up|waste of time|i'?ll go elsewhere|useless|stupid|idiot)\b", re.I)
DAYS = "monday|tuesday|wednesday|thursday|friday|saturday|sunday"
DAY_ABBR = {"mon": "monday", "tue": "tuesday", "tues": "tuesday", "wed": "wednesday", "thu": "thursday", "thur": "thursday",
            "thurs": "thursday", "fri": "friday", "sat": "saturday", "sun": "sunday"}


def load_db():
    db = {d: json.load(open(DB_DIR / f"{d}_db.json")) for d in ("restaurant", "hotel", "attraction", "train", "hospital")}
    db["police"] = json.load(open(DB_DIR / "police_db.json"))
    return db


DB = load_db()
NAMES = {d: sorted({r["name"].lower() for r in DB[d]}, key=len, reverse=True) for d in ("restaurant", "hotel", "attraction")}
FOODS = sorted({r["food"] for r in DB["restaurant"]}, key=len, reverse=True)
ATTR_TYPES = sorted({r["type"] for r in DB["attraction"]}, key=len, reverse=True)
STATIONS = sorted({r["departure"] for r in DB["train"]}, key=len, reverse=True)


def has(pattern, text):
    return re.search(r"(?<![a-z])(" + pattern + r")(?:s|es)?(?![a-z])", text, re.I) is not None


def find_name(text, domain):
    low = text.lower()
    return next((n for n in NAMES.get(domain, []) if len(n) > 3 and n in low), None)


def domains_in(text):
    found = [d for d, pat in DOMAIN_WORDS.items() if has(pat, text)]
    for d in ("restaurant", "hotel", "attraction"):
        if find_name(text, d) and d not in found:
            found.append(d)
    if any(f in text.lower() for f in FOODS) and "restaurant" not in found:
        found.append("restaurant")
    return found


def constraints(text, domain):
    low = text.lower()
    c = {}
    area = re.search(r"\b(centre|center|north|south|east|west)\b", low)
    if area and domain in ("restaurant", "hotel", "attraction"):
        c["area"] = "centre" if area.group(1) == "center" else area.group(1)
    price = re.search(r"\b(cheap|moderate(?:ly)?|expensive)\b", low)
    if price and domain in ("restaurant", "hotel"):
        c["pricerange"] = price.group(1).replace("ly", "")
    if domain == "restaurant":
        food = next((f for f in FOODS if re.search(r"\b" + re.escape(f) + r"\b", low)), None)
        if food:
            c["food"] = food
    if domain == "hotel":
        stars = re.search(r"\b([0-5])[ -]?stars?\b", low)
        if stars:
            c["stars"] = stars.group(1)
        if re.search(r"guest ?house", low):
            c["type"] = "guesthouse"
        elif re.search(r"\bhotel\b", low) and "guest" not in low:
            c["type"] = "hotel"
        negated = re.search(NOT_NEEDED, low)
        if re.search(r"parking", low):
            c["parking"] = None if negated or "no parking" in low else "yes"
        if re.search(r"wifi|internet", low):
            c["internet"] = None if negated else "yes"
    if domain == "attraction":
        typ = next((t for t in ATTR_TYPES if t in low), None)
        if typ:
            c["type"] = typ
    if domain == "train":
        for key, pat in (("departure", r"\bfrom ([a-z ]+?)(?= to\b| on\b| at\b| after\b| by\b|[,.?!]|$)"),
                         ("destination", r"\b(?:to|into|for) ([a-z ]+?)(?= from\b| on\b| at\b| after\b| by\b|[,.?!]|$)")):
            for m in re.finditer(pat, low):
                st = next((s for s in STATIONS if s in m.group(1)), None)
                if st:
                    c[key] = st
                    break
        if "departure" not in c and "destination" not in c:
            bare = [s for s in STATIONS if re.search(r"\b" + re.escape(s) + r"\b", low)]
            if len(bare) == 1:
                c["_station"] = bare[0]
        day = re.search(r"\b(" + DAYS + r")\b", low) or re.search(r"\b(" + "|".join(DAY_ABBR) + r")\b", low)
        if day:
            c["day"] = DAY_ABBR.get(day.group(1), day.group(1))
        t = re.search(r"\b(after|leave at|leaves at|leaving at|depart at|by|arrive by|arrives by|before)\s+(\d{1,2}:\d{2})", low)
        if t:
            c["arriveBy" if t.group(1) in ("by", "arrive by", "arrives by", "before") else "leaveAt"] = t.group(2).zfill(5)
    if domain == "taxi":
        frm = re.search(r"\b(?:from|leave from|leaving from|pick me up at|pick up at|departing from) (?:the )?([a-z0-9' ]+?)(?= to\b| and\b| at\b| after\b| by\b|[,.?!]|$)", low)
        verbs = ("book", "go", "get", "be", "leave", "commute", "take", "travel", "pick", "make", "find", "know", "catch")
        to = next((m for m in re.finditer(r"\b(?:to|going to|towards) (?:the )?([a-z0-9' ]+?)(?= from\b| at\b| after\b| by\b| and\b|[,.?!]|$)", low)
                   if m.group(1).split()[0] not in verbs), None)
        if frm and frm.group(1).strip() not in ("there", "here"):
            c["departure"] = frm.group(1).strip()
        if to:
            c["destination"] = to.group(1).strip()
        t = re.search(r"\b(after|leave at|leaves at|leaving at|at|by|arrive by|arrives by|before)\s+(\d{1,2}:\d{2})", low)
        if t:
            c["arriveBy" if t.group(1) in ("by", "arrive by", "arrives by", "before") else "leaveAt"] = t.group(2).zfill(5)
    name = find_name(text, domain) if domain in NAMES else None
    if name:
        c["name"] = name
    return c


def matches(row, cons, domain):
    for k, v in cons.items():
        if domain == "train" and k == "leaveAt":
            if row["leaveAt"] < v:
                return False
        elif domain == "train" and k == "arriveBy":
            if row["arriveBy"] > v:
                return False
        elif str(row.get(k, "")).lower() != str(v).lower():
            return False
    return True


def query(domain, cons):
    """Rows matching all constraints; if none, drop one constraint at a time in RELAX_ORDER."""
    if domain not in ("restaurant", "hotel", "attraction", "train"):
        return [], []
    rows = [r for r in DB[domain] if matches(r, cons, domain)]
    if rows or "name" in cons:
        return rows, []
    for k in RELAX_ORDER:
        if k in cons:
            relaxed = {kk: vv for kk, vv in cons.items() if kk != k}
            rows = [r for r in DB[domain] if matches(r, relaxed, domain)]
            if rows:
                return rows, [k]
    return [], list(cons)


def row_text(domain, r):
    if domain == "train":
        return f"train {r['trainID']}: {r['departure']} -> {r['destination']}, {r['day']}, leaves {r['leaveAt']}, arrives {r['arriveBy']}, {r['price']}, {r['duration']}"
    keep = ["name", "type", "area", "food", "pricerange", "stars", "parking", "internet", "address", "postcode", "phone", "entrance fee"]
    return "; ".join(f"{k}: {r[k]}" for k in keep if k in r and r[k] not in ("", "?"))


def stage_of(user_turns):
    last = user_turns[-1]
    earlier = user_turns[:-1]
    repeats = sum(1 for e in earlier if jaccard(last, e) >= 0.5)
    rephrase = any(0.3 <= jaccard(last, e) < 0.5 for e in earlier)
    cues = []
    if repeats:
        cues.append(f"repeats an earlier request ({repeats}x)")
    elif rephrase:
        cues.append("rephrases an earlier request")
    if OIR.search(last):
        cues.append("other-initiated repair (what?/??/I said)")
    if NEGATION.search(last):
        cues.append("no/not/again/already")
    if META.search(last):
        cues.append("talks about the conversation itself (can you help / understand)")
    lengths = sorted(len(u.split()) for u in earlier)
    if lengths and len(last.split()) < 0.5 * lengths[len(lengths) // 2]:
        cues.append("much shorter than before")
    if GIVE_UP.search(last):
        stage = 4
    elif (repeats and (OIR.search(last) or META.search(last))) or repeats >= 2:
        stage = 3
    elif repeats or OIR.search(last) or META.search(last):
        stage = 2
    elif cues:
        stage = 1
    else:
        stage = 0
    return stage, cues


def read(log, upto):
    """Ledger and stage for the dialogue log (EmoWOZ format) at user turn index `upto`."""
    users = [log[i]["text"] for i in range(0, upto + 1, 2)]
    systems = [(i, log[i]["text"]) for i in range(1, upto, 2) if log[i]["text"].strip()]
    ledger = {}
    order = []
    for idx, i in enumerate(range(0, upto + 1, 2)):
        text = log[i]["text"]
        # A turn without domain words still refines the domain the user was last talking about.
        doms = domains_in(text)
        keyword_doms = [d for d, pat in DOMAIN_WORDS.items() if has(pat, text)]
        prev_sys = log[i - 1]["text"].lower() if i >= 1 else ""
        if order and order[-1] in ("taxi", "train") and not keyword_doms:
            # A bare answer ("the oak bistro") to a taxi/train question fills that domain's slot.
            d0 = order[-1]
            if d0 == "taxi":
                name = next((find_name(text, dd) for dd in ("restaurant", "hotel", "attraction") if find_name(text, dd)), None)
                if name:
                    slot = "departure" if re.search(r"from|leaving|depart|pick", prev_sys) else "destination"
                    ledger[d0]["constraints"][slot] = name
                    ledger[d0]["since"] = i
            doms = [d0]
        for d in (doms or order[-1:]):
            ledger.setdefault(d, {"constraints": {}, "asked": set(), "since": i})
            new = constraints(text, d)
            station = new.pop("_station", None)
            if station:
                cons = ledger[d]["constraints"]
                new["destination" if "departure" in cons and "destination" not in cons else
                    "departure" if "departure" not in cons else "destination"] = station
            for key in ("departure", "destination"):
                ref = re.sub(r"^the ", "", new.get(key, ""))
                if d == "taxi" and ref in ("restaurant", "hotel", "attraction", "guesthouse", "museum", "college"):
                    src = "hotel" if ref == "guesthouse" else "attraction" if ref in ("museum", "college") else ref
                    named = ledger.get(src, {}).get("constraints", {}).get("name") or next(
                        (find_name(log[k]["text"], src) for k in range(i, -1, -1) if find_name(log[k]["text"], src)), None)
                    if named:
                        new[key] = named
            if new:
                for k, v in new.items():
                    if v is None:
                        ledger[d]["constraints"].pop(k, None)
                    else:
                        ledger[d]["constraints"][k] = v
                ledger[d]["since"] = i
            ledger[d]["asked"] |= {k for k, p in ASKED_INFO.items() if has(p, text)}
            if d in order:
                order.remove(d)
            order.append(d)
    for d, entry in ledger.items():
        later = " ".join(t for i, t in systems if i > entry["since"]).lower()
        if d == "train":
            entry["delivered"] = bool(re.search(r"\btr\d{4}\b", later))
        elif d in NAMES:
            entry["delivered"] = any(n in later for n in NAMES[d] if len(n) > 3)
        else:
            entry["delivered"] = bool(re.search(r"\d{5,}", later))
    # Focus on what the user is talking about now: the most recent domain, even if an older one is also open.
    pending = order[-1:]
    for d, entry in ledger.items():
        entry["missing"] = [alts[0] for alts in REQUIRED.get(d, []) if not any(a in entry["constraints"] for a in alts)]
    stage, cues = stage_of(users)
    booking = {}
    recent = " ".join(users[-3:]).lower()
    if re.search(r"\b(book|reserve|reservation|tickets?)\b", users[-1].lower()) or (
            re.search(r"\b(book|reserve|reservation)\b", recent) and re.search(r"\b\d+\b", users[-1])):
        people = re.search(r"\b(\d+) (?:people|persons?|peoples|guests|tickets|of us)\b|\bfor (\d+)\b", recent)
        stay = re.search(r"\b(\d+) (?:nights?|days?)\b", recent)
        day = re.search(r"\b(" + DAYS + r")\b", recent)
        time = re.search(r"\b(\d{1,2}:\d{2})\b", recent)
        booking = {k: v for k, v in (("people", people and (people.group(1) or people.group(2))),
                                     ("stay", stay and stay.group(1)), ("day", day and day.group(1)),
                                     ("time", time and time.group(1))) if v}
        booking["requested"] = True
    said = [t for _, t in systems[-4:]]
    return {"stage": stage, "cues": cues, "ledger": ledger, "pending": pending, "said": said, "booking": booking}


def brief(log, upto, max_rows=3):
    r = read(log, upto)
    lines = [f"Escalation stage: {r['stage']} of 4" + (f" (cues: {', '.join(r['cues'])})" if r["cues"] else "")]
    if not r["pending"]:
        lines.append("No domain request found; answer the last message directly.")
    for d in r["pending"]:
        e = r["ledger"][d]
        cons = e["constraints"]
        lines.append(f"Pending request: {d}" + (f" with {json.dumps(cons)}" if cons else " (no constraints given yet)")
                     + (f"; user also asked for: {', '.join(sorted(e['asked']))}" if e["asked"] else ""))
        if e["missing"]:
            lines.append(f"  Missing before anything can be delivered: {', '.join(e['missing'])}. Ask for exactly these "
                         "in one short question, say why you need them, and do not guess or list unrelated options.")
            continue
        rows, relaxed = query(d, cons)
        if d == "police":
            p = DB["police"][0]
            lines.append(f"  Database: {p['name']}, {p['address']}, phone {p['phone']}")
        elif d == "taxi":
            lines.append("  Taxi: can be booked; give car colour/type and a 10-digit contact number.")
        elif rows:
            if relaxed:
                lines.append(f"  No exact match. Closest options after dropping {relaxed[0]}:")
            for row in rows[:max_rows]:
                lines.append("  Database: " + row_text(d, row))
            if len(rows) > max_rows:
                lines.append(f"  ({len(rows)} matches in total)")
        elif d in ("restaurant", "hotel", "attraction", "train"):
            lines.append("  Database: nothing matches even after relaxing; say so in one sentence and ask for the one change that would help.")
    if r["booking"]:
        b = {k: v for k, v in r["booking"].items() if k != "requested"}
        lines.append("Booking requested" + (f" ({json.dumps(b)})" if b else "") + ": you can book. Book the best matching "
                     "database option (or the one the user chose) and give a reference number of 8 characters. Ask only "
                     "for booking details that are truly missing.")
    if r["said"]:
        lines.append("Already said by the assistant (do not repeat): " + " | ".join(s.strip() for s in r["said"]))
    policy = {
        0: "Answer normally.",
        1: "Answer the request directly.",
        2: "Deliver the pending item first, using the database rows. Ask a question back only for the details listed as missing.",
        3: "Deliver the pending item completely in this reply, with the details the user asked for. If it cannot be done, say why in one sentence and give the closest option. One short acknowledgment is fine; no long apology.",
        4: "The user is close to giving up. Say in two short sentences what you can give them right now (from the database) and what you cannot, and offer a human agent.",
    }[r["stage"]]
    lines.append("Policy: " + policy)
    return "\n".join(lines), r


def log_for(case_id, data):
    did, idx = case_id.split("#")
    return data[did]["log"], int(idx)


if __name__ == "__main__":
    import sys
    data = json.load(open(Path(sys.argv[1]) / "emowoz-dialmage.json"))
    for case in json.load(open(sys.argv[2]))[: int(sys.argv[3]) if len(sys.argv) > 3 else 5]:
        log, i = log_for(case["id"], data)
        print("=====", case["id"])
        print(case["dialogue"][-400:])
        print("--- brief")
        print(brief(log, i)[0])
