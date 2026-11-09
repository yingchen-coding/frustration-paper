# Findings so far (2026-11-08)

Data: EmoWOZ (Feng et al., LREC 2022, CC BY-NC 4.0), downloaded from Zenodo record 6506504.
- MultiWOZ part: 10,438 dialogues, human "wizard" plays the system.
- DialMAGE part: 995 dialogues, a real machine system talks to people.
Negative user turn = label dissatisfied (2) or abusive (4). Script: `analyze.py`; output: `results.json`.
95% CIs: bootstrap over dialogues, 2,000 resamples.

## 1. Humans change how they talk when the user is unhappy; the machine does not
Share of system replies with an apology/acknowledgment word (`sorry`, `apolog*`, `I understand`, `my mistake`, ...):

| | after neutral user turn | after dissatisfied/abusive turn |
|---|---|---|
| Human wizard (MultiWOZ) | 3.9% | 17.8% |
| Machine (DialMAGE) | 3.7% | 3.5% |

With `unfortunately` / `I'm afraid` included: human 5.4% → 20.3% [17.7, 22.7]; machine 5.6% [5.0, 6.3] → 5.0% [4.2, 5.8].

## 2. Dissatisfaction is mostly not in the words
Share of negative user turns that contain a negation/complaint word, repeat an earlier request of the same user (token Jaccard >= 0.5), or neither:

| | complaint word | repeats own request | neither |
|---|---|---|---|
| MultiWOZ negative turns (n=958) | 53.0% | 3.0% | 44.6% |
| DialMAGE negative turns (n=4,264) | 7.7% | 46.8% | 47.6% |
| DialMAGE neutral turns (n=7,230) | 3.0% | 13.2% | 84.2% |

With the machine, users show dissatisfaction by asking again, not by complaining. A word-level sentiment detector misses it.

## 3. Repeating itself goes with the user staying unhappy
Machine reply nearly identical to its own previous reply (Jaccard >= 0.8) after a negative turn: 1.8% (n=71).
Next user turn still negative: 88.3% [80.0, 95.7] after a repeat vs 54.6% [52.7, 56.6] otherwise. Small n.

## 4. Intervention smoke test (runs/smoke, n=10, generator Claude Sonnet, judge Codex) — pipeline check only
85 eligible test-split cases (dissatisfied/abusive turn that repeats an earlier request).
resolves (0-2): A_baseline 1.3, B_direct 1.5, C_diagnose 1.5. Judged best: A 10%, B 40%, C 50%.
give_up: A 10%, B 0%, C 0%. repeats: 10% each. All CIs overlap at n=10; no claim.
Observation: a strong LLM baseline already fixes much of what the original system got wrong (ceiling effect).
The gap C vs B may only show on weaker generators or harder cases.

## 5. Intervention pilot (runs/pilot60, n=60, generator Claude Sonnet, judge Codex high effort, blind)
| | resolves (0-2) | give_up | repeats itself | judged best |
|---|---|---|---|---|
| A_baseline | 1.18 [1.03, 1.33] | 13.3% | 23.3% | 13.3% |
| B_direct | 1.63 [1.50, 1.77] | 8.3% | 10.0% | 33.3% |
| C_diagnose | 1.68 [1.53, 1.82] | 5.0% | 1.7% [0.0, 5.0] | 53.3% [41.7, 65.0] |
Paired differences (bootstrap 95% CI):
- C - A: resolves +0.50 [0.30, 0.68]; repeats -21.7 pts [-33.3, -10.0].
- C - B: resolves +0.05 [-0.12, 0.20] (no difference); repeats -8.3 pts [-16.7, -1.7] (C repeats less).
- B - A: resolves +0.45 [0.27, 0.63].
Reading: most of the gain in solving comes from "be concrete" (B); reading the user's unmet need (C) adds a
clear drop in repeating itself and is picked best most often, but does not yet solve more than B.
One judge only, no human check yet.

## 6. Same pilot with a small model (runs/llama60, n=60, generator dolphin-llama3:8b via ollama, same judge)
C runs as two calls (read the user -> reply) because the 8B model does not follow a combined format.
| | resolves (0-2) | give_up | repeats | best |
|---|---|---|---|---|
| A_baseline | 1.45 | 15.0% | 11.7% | 38.3% |
| B_direct | 1.43 | 20.0% | 13.3% | 30.0% |
| C_diagnose | 1.18 | 28.3% | 21.7% | 31.7% |
C - B: resolves -0.25 [-0.48, -0.02]. Prompt-only "read the user first" HURTS the small model.
Why (18 cases where C < B, read by hand): the 8B model's free-text reading is often wrong — it names needs from
earlier in the dialogue or invents them (asked for a guesthouse; notes say "Indian restaurant") — and then the
reply apologizes and promises instead of delivering ("Please bear with me").
Implication for the method: the reading must be explicit, checkable state (repair cues + ledger of
requested/delivered/pending), not the model's own free-form reflection. This motivates REPAIR (PLAN.md).

## 7. REPAIR v1 on the 60 development cases (runs/pilot60_r, Claude, 5 conditions judged together)
Judge (resolves 0-2): A 1.18, B 1.45, C 1.57, D_repair 1.22, E_ledger_db 1.20. give_up: C 3.3%, D 20%.
Objective (`objective.py`, reply names a real db entity matching the pending constraints, 53 cases):
A 34%, B 43%, C 47%, D 92.5%, E 88.7%; real db phone numbers quoted: D 5, others 0-1.
Llama 8B objective (runs/llama60_r): A 19%, B 21%, C 19%, D 79%, E 81%; real phones D 15, E 12, fake 0.
The two measures disagree. The objective score is partly circular (it uses the same reader that built the
brief), and reading 19 cases where D < C showed real reader errors:
- missed a train destination stated earlier ("need to catch a train ... to go to Stansted Airport");
- when required details were missing (train with only a day), the policy pushed "deliver", so D listed
  arbitrary trains (Cambridge -> London) instead of asking — the judge scored these 0;
- an older open topic (attraction) was shown next to the current one (taxi) and the reply mixed them.
Reader v2 fixes: required slots per domain (train: from/to/day; taxi: from/to/time) -> ask only for those;
only the current topic is shown; constraints carry over to turns without domain words; bare station answers
fill the missing slot; taxi "from the attraction to the restaurant" resolves to the named venues.
Because v2 was fixed by looking at these 60 cases, they are now the development set. v2 is evaluated on the
81 eligible DialMAGE **dev-split** cases, never looked at (runs/heldout_claude, runs/heldout_llama).

## 8. HELD-OUT result: REPAIR v2 on 81 unseen DialMAGE dev-split cases (judge Claude Opus; Codex out of quota)
Llama 8B generator (judge is a different model family):
| | resolves (0-2) | give_up | repeats | best | objective: real+matching entity (74) |
|---|---|---|---|---|---|
| A_baseline | 0.67 | 29.6% | 24.7% | 11% | 10.8% |
| B_direct | 0.67 | 24.7% | 22.2% | 11% | 17.6% |
| C_diagnose (prompt) | 0.57 | 44.4% | 18.5% | 4% | 13.5% |
| D_repair | **1.10** | **18.5%** | 16.0% | 37% | 59.5% |
| E_ledger_db | 1.07 | 25.9% | 16.0% | 37% | 64.9% |
D - B resolves +0.43 [0.21, 0.65]; D - C +0.53 [0.31, 0.75], give_up -25.9 pts [-40.7, -11.1].
E - D resolves -0.03 [-0.16, 0.12] -> on the small model the gain comes from the ledger + database; the
escalation stage/policy shows no separate effect yet (give_up -7.4 pts, CI crosses 0).
Real phone numbers quoted: D 10, E 23; invented: E 1, others 0.

Claude Sonnet generator (judge is SAME family — treat as provisional until re-judged by Gemini/Codex):
resolves A 1.01, B 1.27, C 1.38, D 1.22, E 1.17; give_up A 27%, B 6%, C 2.5%, D 16%, E 21%.
Objective: A 23%, B 38%, C 36.5%, D 68.9%, E 66.2%; real phones D 30, others 0-9; invented 0.
On the strong model the prompt-only reading (C) is judged best and has the fewest give-ups; REPAIR nearly
doubles grounded, correct delivery but the judge does not reward it, and D has more give-ups than C.

Summary so far: (1) a strong LLM can read the user from a prompt; a small one cannot, and free-form
self-diagnosis hurts it. (2) Making the reading explicit (ledger of pending needs + real database) lifts a
small model from 0.67 to 1.10 resolves and cuts give-ups from 44% to 19% vs the prompt version, on unseen
dialogues. (3) The escalation-stage policy has not yet shown value beyond the ledger. (4) Open: why REPAIR
raises give-ups on the strong model — next step is to read those cases.

## 9. Why REPAIR lost to the prompt on the strong model (13 held-out cases where D gave up and C did not)
- The judge rewards confident invented bookings. Example DMAGE3464: user wants 8 tickets Leicester -> Cambridge
  on Saturday; C "booked" TR0899 05:00-05:51, which in the database is Cambridge -> London Kings Cross. Judge gave
  C resolves 2 and D (real Leicester trains, no booking) 0. => judging must check facts against the database.
- REPAIR could not book: the brief had no booking step, so D listed options when the user said "book".
- Reader errors: "tourist attractions" (plural) not matched -> wrong topic; "does not need wifi" became wifi=yes;
  a generic "hotel" type blocked 3-star guesthouses in the north.
Reader v3 fixes: plural domain words, negated amenities removed, type/amenities relaxed first, booking intent
(people/stay/day/time) -> "you can book, give a reference".
Judge fix: `JUDGE_REF=1` shows the judge the database rows for the current request (same for all candidates)
and says contradicting facts cannot score 2. Both plain and fact-checked judging are reported.
The dev split has now been looked at, so v3 is evaluated on 100 cases from the DialMAGE **train** split
(never looked at): runs/final_claude, runs/final_llama.

## Not yet supported / caveats
- Both LLM conditions invent phone numbers and booking references (no database). The judge is told to rate
  whether the reply would get the user what they need; a factuality check is not part of the score.
- Acknowledgment is matched by a word list. Needs a hand-checked sample (precision/recall) before any claim.
- Ack is followed by MORE negative next turns (MultiWOZ 16.3% vs 8.4%; DialMAGE 62.8% vs 54.8%). Correlational: systems apologize when the task already failed. Do not claim apology hurts.
- "Repeats own request" uses a single Jaccard threshold; check 0.4/0.6 sensitivity.
- Only one corpus with a machine system (DialMAGE). A second corpus is needed before generalizing.
