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
  C resolves 2 and D (real Leicester trains, no booking) 1, with give_up. => judging must check facts against the database.
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


## 10. Word-list and reader validation (2026-11-08, script: validate_wordlists.py)

### Complaint-word regex
200 sampled negative DialMAGE user turns:
- Matched: 14/200 (7.0%) — consistent with the 7.7% reported in §2.
- True positives: 13; False positives: 1 (task language: "no. I need a train that arrives at 21:45").
- Precision: 92.9%. The list catches real complaints when they occur; its low recall confirms our claim
  that word-level sentiment misses most dissatisfaction.

### Ack regex
200 system turns after negative user turns:
- Matched: 6/200 (3.0%) — consistent with the 3.5% reported in §1.
- All 6 matches are genuine acknowledgments ("sorry", "unfortunately", "I am afraid"). Zero "I see" false matches.

### Repeat threshold sensitivity (all DialMAGE negative turns, n=4,264)
| Jaccard threshold | Negative turns that repeat | Share |
|---|---|---|
| >= 0.3 | 2,704 | 63.4% |
| >= 0.4 | 2,290 | 53.7% |
| >= 0.5 | 1,994 | 46.8% |
| >= 0.6 | 1,577 | 37.0% |
| >= 0.7 | 1,306 | 30.6% |
Findings are directionally robust across thresholds. The 0.5 threshold is a reasonable midpoint.

### REPAIR reader spot-check (20 random cases from runs/final_llama)
- Pending request identified: 19/20 (95%)
- Database rows provided: 13/20 (65% — 7 cases had missing required slots, so the reader correctly asked for them instead)
- Escalation stage distribution: stage 2 (18), stage 3 (2)
- Errors: 0/20

## 11. Fact-checked Claude results (final_claude, runs/final_claude/summary_claude-opus_ref.json)
n=100 unseen DialMAGE train-split cases, Claude Sonnet generator, Claude Opus judge with JUDGE_REF=1.
| | resolves (0-2) | give_up | repeats | best |
|---|---|---|---|---|
| A reply to last message | 0.68 [0.55, 0.81] | 38% | 17% | 4% |
| B be concrete | 0.76 [0.61, 0.91] | 19% | 19% | 3% |
| C prompt "read the user" | 0.82 [0.67, 0.97] | 12% | 6% | 6% |
| **D REPAIR** | **1.64** [1.52, 1.75] | **3%** | 2% | **53%** |
| E ledger + database only | 1.65 [1.55, 1.74] | 3% | 6% | 34% |
D - B: resolves +0.88 [0.71, 1.05]; D - C: +0.82 [0.66, 0.97].
The fact-checked judge reverses the plain-judge result where C > D. Without database verification, the
judge rewards invented bookings and phone numbers; with it, REPAIR dominates all conditions on both models.


## 12. Second corpus: DBDC3 (chat-oriented breakdown detection, 415 dialogues)
Script: `analyze_dbdc3.py`. Data: `data/dbdc3/` (github.com/dbd-challenge/dbdc3).
DBDC3 annotates system turns as breakdown (X), possible breakdown (T), or not (O) in chat-oriented
human-machine dialogues (no task goals).

After majority-vote breakdown (862/4,335 system turns = 19.9%):
- User repeats after breakdown: 62/742 = **8.4%** [6.5, 10.4]
- User repeats, no breakdown: 206/3,017 = **6.8%** [5.9, 7.8]
- Difference: **+1.5 pp** (barely significant)

Compare to DialMAGE (task-oriented): negative turns repeat 46.8% vs neutral 13.2% (+33.6 pp).

**Interpretation:** Repetition as a frustration signal is specific to task-oriented dialogue, where there is
an unmet task need the user can re-state. In chat, there is nothing specific to repeat, so breakdowns do
not trigger repetition. This is added to the paper as a contrast finding in Section 3.


## 13. Second judge family: Gemini on both final 100-case runs (2026-11-08)
Files: `runs/final_llama/judgments_gemini.json`, `summary_gemini.json`, `judgments_gemini_ref.json`,
`summary_gemini_ref.json`, and corresponding files in `runs/final_claude/`.
All 100 unseen DialMAGE train-split cases judged blind with the exact same `order.json` shuffling and `JUDGE`
prompt as Claude Opus.

### Llama 8B generator, Gemini judge (cross-family)
Plain judge (`summary_gemini.json`):
| | resolves (0-2) | give_up | repeats | best |
|---|---|---|---|---|
| A reply to last message | 0.98 [0.85, 1.11] | 19% | 18% | 8% |
| B be concrete | 0.98 [0.85, 1.11] | 18% | 19% | 15% |
| C prompt "read the user" | 0.73 [0.60, 0.86] | 35% | 17% | 7% |
| **D REPAIR** | **1.51** [1.37, 1.65] | **14%** | **10%** | **38%** |
| E ledger + database only | 1.39 [1.23, 1.55] | 22% | 17% | 32% |
- D - B: resolves +0.53 [0.33, 0.72]; D - C: +0.78 [0.60, 0.96], give_up -21 pts [-31, -11].
- C - B: resolves -0.25 [-0.42, -0.08], give_up +17 pts [5, 28] — confirms across a second judge family that
  prompt-only reading significantly hurts the 8B model.

Fact-checked judge (`summary_gemini_ref.json`):
| | resolves (0-2) | give_up | repeats | best |
|---|---|---|---|---|
| A reply to last message | 0.26 [0.16, 0.38] | 41% | 26% | 3% |
| B be concrete | 0.26 [0.16, 0.37] | 39% | 29% | 3% |
| C prompt "read the user" | 0.25 [0.16, 0.36] | 51% | 24% | 4% |
| **D REPAIR** | **1.49** [1.35, 1.63] | **12%** | **12%** | **53%** |
| E ledger + database only | 1.39 [1.24, 1.53] | 16% | 16% | 37% |
- D - B: resolves +1.23 [1.04, 1.40]; D - C: +1.24 [1.07, 1.41].

### Claude Sonnet generator, Gemini judge (cross-family — resolves same-family bias concern)
Plain judge (`summary_gemini.json`):
- resolves: A 1.19 [1.03, 1.34], B 1.62 [1.51, 1.73], C 1.85 [1.78, 1.92], D 1.55 [1.41, 1.68], E 1.49 [1.35, 1.62].
- Without database rows, Gemini also rewards C's confident invented bookings.

Fact-checked judge (`summary_gemini_ref.json`):
| | resolves (0-2) | give_up | repeats | best |
|---|---|---|---|---|
| A reply to last message | 0.89 [0.75, 1.05] | 24% | 9% | 4% |
| B be concrete | 0.91 [0.77, 1.05] | 8% | 2% | 2% |
| C prompt "read the user" | 1.04 [0.90, 1.19] | 0% | 1% | 6% |
| **D REPAIR** | **1.94** [1.88, 1.99] | **1%** | **0%** | **53%** |
| E ledger + database only | 1.90 [1.83, 1.96] | 1% | 1% | 35% |
- D - B: resolves +1.03 [0.89, 1.17]; D - C: +0.90 [0.76, 1.04].
- Cross-family judge confirms: once hallucinated facts are checked against the database, REPAIR dominates on
  the strong model too.

## 14. Stage-stratified ablation: where the escalation policy helps (2026-11-08)
Across all 100 unseen cases on the 8B model, D_repair and E_ledger_db do not differ significantly overall
(D - E resolves: Opus +0.06 [-0.07, 0.19], Gemini +0.12 [-0.05, 0.28]). Stratifying by the repair reader's
escalation stage (88 cases at stage 2, 12 cases at stage 3):
- **Stage 2 (n=88)**: Opus D 1.18 vs E 1.18 (+0.00); Gemini D 1.45 vs E 1.41 (+0.05). The ledger and database
  carry the entire gain.
- **Stage 3 (n=12, stronger repair escalation)**:
  - Opus plain: D 1.50 vs E 1.00, **D - E +0.50 [0.08, 0.92]**; give-up D 8% vs E 33%.
  - Gemini plain: D 1.92 vs E 1.25, **D - E +0.67 [0.25, 1.17]**; give-up D 0% vs E 33% (-33 pts [-58, -8]).
  - Fact-checked judges: Opus D 1.50 vs E 1.25 (+0.25); Gemini D 1.67 vs E 1.33 (+0.33); give-up D 0% vs E 25%.
The repair reader and escalation policy show a clear, significant gain specifically on higher-escalation turns.

## 15. Repair escalation ladder & grounding ledger across all 12,093 DialMAGE user turns (`analyze_ladder.py`)
Evaluating REPAIR's deterministic stage reader and grounding ledger across the full DialMAGE corpus (995 dialogues,
12,093 annotated user turns; 95% bootstrap CIs over dialogues):
| Repair stage | n | Current turn negative | Next user turn negative |
|---|---|---|---|
| Stage 0 (no repair cues) | 4,767 | 16.3% [15.0, 17.7] | 32.7% [31.1, 34.2] |
| Stage 1 (rephrase, negation, shorter) | 4,242 | 34.3% [32.5, 36.1] | 37.9% [36.0, 39.7] |
| Stage 2 (repeat 1x, OIR, meta) | 2,177 | 60.3% [58.0, 62.5] | 45.3% [42.8, 47.8] |
| Stage 3+ (repeat >=2x or repeat + OIR/meta) | 907 | **79.3%** [75.7, 82.7] | **57.1%** [52.8, 61.4] |
- Stage >= 1 captures 3,485 / 4,264 = **81.7%** of all negative turns (vs 7.7% for complaint words).
- Turns where the grounding ledger shows an undelivered pending request from an earlier turn are negative **40.5%**
  [38.9, 42.1] (n=7,919) vs **25.3%** [23.3, 27.3] otherwise (n=4,174).
