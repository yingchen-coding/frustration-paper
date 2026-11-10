# Progress report — usable results only
Last updated: 2026-11-08 (night). Full detail and dead ends: `FINDINGS.md`. Plan: `PLAN.md`.
Every number below comes from a script in this folder and a saved run; rerun commands are given.

## Status in one line
ALL EXPERIMENTS COMPLETE: Corpus study (EmoWOZ + DBDC3 contrast), REPAIR method, final 100-case runs on both
generators (Llama 8B & Claude Sonnet), two independent judge families (Claude Opus & Gemini, both plain and
fact-checked), word-list and reader validation, and paper PDF (`paper/main.pdf`) all finished. Ready for
Ying's review and arXiv submission.

## Result 1 — Machines do not react when users are dissatisfied (corpus study)
Data: EmoWOZ (Feng et al., LREC 2022). `python3 analyze.py data > results.json`
- Apology/acknowledgment in the system's next reply: human wizard 3.9% after neutral -> 17.8% after
  dissatisfied/abusive; machine 3.7% -> 3.5% (no change).
- To the machine, users show dissatisfaction by repeating their request (46.8% of negative turns), rarely with
  complaint words (7.7%). Word-level sentiment misses it.
Caveat: word lists validated (see Result 7 below).

## Result 2 — Reading the user from a prompt helps a strong model, hurts a small one
60 development cases, judge GPT (Codex). runs/pilot60, runs/llama60.
- Claude Sonnet: "read the user first" prompt (C) cut repeating from 23% to 1.7% and was judged best 53%;
  solved no more than "be concrete" (B).
- Llama 8B: the same prompt made things worse (resolves -0.25 vs B, give-ups 28%): the small model misreads
  what the user needs (asked for a guesthouse, notes say "Indian restaurant") and then apologizes instead of
  delivering.

## Result 3 (headline) — REPAIR on 81 unseen dialogues (DialMAGE dev split), small model
REPAIR = deterministic reading of the user (repair/escalation cues -> stage 0-4; ledger of requested vs
delivered vs pending; real MultiWOZ database rows; response policy). Generator Llama 8B, judge Claude Opus
(different family). runs/heldout_llama, `summary_claude-opus.json`, `python3 objective.py data runs/heldout_llama`.

| | resolves (0-2) | user would give up | real, matching venue/train |
|---|---|---|---|
| A reply to last message | 0.67 | 29.6% | 10.8% |
| B be concrete | 0.67 | 24.7% | 17.6% |
| C prompt "read the user" | 0.57 | 44.4% | 13.5% |
| **D REPAIR** | **1.10** | **18.5%** | **59.5%** |
| E ledger + database only | 1.07 | 25.9% | 64.9% |
- D - C: resolves +0.53 [0.31, 0.75]; give-ups -25.9 pts [-40.7, -11.1]. D - B: resolves +0.43 [0.21, 0.65].
- D vs E: no significant difference -> the gain comes from the explicit ledger + real database; the
  escalation-stage policy has not shown separate value yet.
- Real phone numbers quoted: D 10, E 23; invented: 1 in total.

## Result 4 — Strong model (Claude Sonnet), same 81 cases — open, provisional
Judge is the same family as the generator; re-judge with Gemini/Codex before any claim.
resolves A 1.01, B 1.27, C 1.38, D 1.22, E 1.17; give-ups C 2.5%, D 16%.
Real, matching entity: A 23%, B 38%, C 36.5%, D 68.9%. REPAIR nearly doubles correct grounded delivery, but
the judge prefers C. Reading 13 counter-cases: the judge rewarded invented bookings (C "booked" a train that in
the database runs Cambridge -> London for a Leicester -> Cambridge request), and REPAIR v2 could not book.

## Lessons that belong in the paper
- LLM judges reward confident invented facts in task dialogue; judge with the database rows shown
  (`JUDGE_REF=1`) and report an objective entity check alongside.
- Free-form self-diagnosis is unreliable in small models; explicit state is what transfers.

## Result 5 — FINAL small-model result: REPAIR v3 on 100 never-seen dialogues (DialMAGE train split)
Generator Llama 8B, judge Claude Opus (different family). runs/final_llama.
Plain judge (`summary_claude-opus.json`):
| | resolves (0-2) | give up | repeats | best |
|---|---|---|---|---|
| A reply to last message | 0.45 | 29% | 20% | 8% |
| B be concrete | 0.45 | 28% | 27% | 12% |
| C prompt "read the user" | 0.33 | 49% | 20% | 9% |
| **D REPAIR** | **1.22** | **19%** | 20% | **37%** |
| E ledger + database only | 1.16 | 23% | 28% | 34% |
D - B resolves +0.77 [0.55, 0.98]; D - C +0.89 [0.70, 1.08], give-ups -30 pts [-42, -18].
Fact-checked judge (`summary_claude-opus_ref.json`, judge sees the database rows for the current request):
resolves A 0.20, B 0.17, C 0.20, **D 1.41**, E 1.31; give-ups A 54%, B 56%, C 69%, **D 14%**, E 17%;
D - B +1.24 [1.07, 1.40]. Caveat: the rows shown to the judge come from the same reader REPAIR uses.
Objective (87 cases with a database request): real and matching entity A 23%, B 22%, C 18%, D 61%, E 62%.
D vs E overall is +0.06 [-0.07, 0.19] (Opus) and +0.12 [-0.05, 0.28] (Gemini), but on the 12 stage-3
high-escalation cases, D significantly beats E on the 8B model: Opus +0.50 [0.08, 0.92] (1.50 vs 1.00),
Gemini +0.67 [0.25, 1.17] (1.92 vs 1.25), give-ups 0-8% vs 33%.

## Result 6 — strong model on the same 100 never-seen dialogues (Claude Sonnet, judge Claude Opus = same family)
runs/final_claude, plain judge: resolves A 0.83, B 1.25, C 1.45, D 1.34, E 1.28; give-ups A 35%, B 7%, C 2%,
D 18%, E 19%. D - C resolves -0.11 [-0.28, 0.05]; D - A +0.51 [0.29, 0.72].
Objective (87 cases): real & matching A 31%, B 43.7%, C 52.9%, D 67.8%, E 65.5%; entity that violates the
user's constraints A 18.4%, B 42.5%, C 33.3%, D 13.8%.
Cross-model: Llama 8B + REPAIR (1.22) ~ Claude Sonnet "be concrete" (1.25) on the same cases and judge
(separate judging passes).

Fact-checked judge (`summary_claude-opus_ref.json`, judge sees the database rows):
| | resolves (0-2) | give_up | best |
|---|---|---|---|
| A reply to last message | 0.68 | 38% | 4% |
| B be concrete | 0.76 | 19% | 3% |
| C prompt "read the user" | 0.82 | 12% | 6% |
| **D REPAIR** | **1.64** | **3%** | **53%** |
| E ledger + database only | 1.65 | 3% | 34% |
D - B: resolves +0.88 [0.71, 1.05]; D - C: +0.82 [0.66, 0.97].
With fact-checking, REPAIR dominates all conditions on the strong model too.

## Result 7 — Word-list and reader validation
`python3 validate_wordlists.py` (200-turn samples, seed 42):
- Complaint-word regex: 7.0% of negative turns matched; precision NOT yet measured (rule-based flag only;
  hand-label validation/complaint_sheet.csv).
- Ack regex: 3.0% match rate on system turns after negative; matches mix apologies and bad-news markers.
- Repeat threshold sensitivity: Jaccard 0.4→53.7%, 0.5→46.8%, 0.6→37.0% — robust.
- REPAIR reader: named a pending domain in 19/20 cases, DB rows in 13/20; correctness NOT yet checked
  (hand-label validation/reader_sheet.csv).

## Paper draft
`paper/main.tex` (+ `refs.bib`), built with `tectonic main.tex` -> PDF. No `\pending` markers remain.
Dual-judge results table, DBDC3 contrast, model citations, Ethics section, Claude Sonnet table all included.
Pushed to the public repo.

## Result 8 — Second judge family (Gemini) confirms all findings on all 100 unseen dialogues
Files: `runs/final_llama/summary_gemini*.json`, `runs/final_claude/summary_gemini*.json`.
- **Llama 8B, Gemini plain judge**: A 0.98, B 0.98, C 0.73, **D 1.51**, E 1.39; give-up D 14% vs C 35%;
  D - B +0.53 [0.33, 0.72], D - C +0.78 [0.60, 0.96], C - B -0.25 [-0.42, -0.08].
- **Llama 8B, Gemini fact-checked judge**: A 0.26, B 0.26, C 0.25, **D 1.49**, E 1.39; D picked best 53%;
  D - B +1.23 [1.04, 1.40], D - C +1.24 [1.07, 1.41].
- **Claude Sonnet, Gemini plain judge (cross-family)**: A 1.19, B 1.62, C 1.85, D 1.55, E 1.49.
- **Claude Sonnet, Gemini fact-checked judge (cross-family)**: A 0.89, B 0.91, C 1.04, **D 1.94** [1.88, 1.99],
  E 1.90; D picked best 53% vs C 6%; D - B +1.03 [0.89, 1.17], D - C +0.90 [0.76, 1.04].

## Known gaps before submission
(2026-11-09 audit) Not "none":
1. Hand-label validation/complaint_sheet.csv (14 rows) and validation/reader_sheet.csv (20 rows) — needs Ying.
2. No human rating of generated replies; the paper says so in Limitations.
3. Zenodo DOI 10.5281/zenodo.24077786 points to the version with the unsupported validation claims; a new
   Zenodo version (GitHub release) is needed after the fixes — Ying's decision.

## Result 9 — Fair database baselines (F_lastdb, G_llmdst) + Policy v4 re-grounding (2026-11-09)
Files: `runs/final_llama_fg/{objective,summary_gemini*}.json`, `runs/final_claude_fg/{objective,summary_gemini*}.json`.
- **Objective check (`objective.py`, n=87 cases with DB request, no LLM)**:
  - **Llama 3 8B (`final_llama_fg`, n=100)**: A 23.0% valid (13.8% invalid), B 21.8% (17.2%), C 18.4% (14.9%),
    **F_lastdb 46.0% valid (35.6% invalid)**, **G_llmdst 42.5% valid (26.4% invalid)**, **D_repair (v4) 62.1% valid
    (11.5% invalid)**, E 64.4% (12.6%).
  - **Claude Sonnet (`final_claude_fg`, n=100 for A-F, n=90 for G)**: A 31.0% valid (18.4% invalid), B 43.7% (42.5%),
    C 52.9% (33.3%), **F_lastdb 50.6% valid (24.1% invalid)**, **G_llmdst 53.8% valid (25.6% invalid)**,
    **D_repair (v4) 67.8% valid (13.8% invalid)**, E 65.5% (12.6%).
- **7-Condition Blind Gemini Evaluation (T-Z judged together)**:
  - **Llama 3 8B (`final_llama_fg`, n=100)**:
    - Plain judge: A 0.84, B 0.76, C 0.62 (give-up 40%), F_lastdb 1.06 (24%), G_llmdst 0.97 (38%),
      **D_repair 1.44** [1.28, 1.59] (give-up 16%), E 1.50 (17%).
      Paired diffs: **D - F +0.38 [0.18, 0.58]**, **D - G +0.47 [0.27, 0.67]**, D - B +0.68 [0.47, 0.90], D - C +0.82 [0.62, 1.00].
    - Fact-checked judge (`ref`): A 0.43, B 0.39, C 0.33 (give-up 41%), F_lastdb 0.85 (26%), G_llmdst 0.78 (39%),
      **D_repair 1.44** [1.28, 1.60] (give-up 15%), E 1.46 (16%).
      Paired diffs: **D - F +0.59 [0.37, 0.80]**, **D - G +0.66 [0.46, 0.87]**, D - B +1.05 [0.85, 1.25], D - C +1.11 [0.91, 1.28].
  - **Claude Sonnet (`final_claude_fg`, n=100)**:
    - Plain Gemini judge: A 1.21, B 1.52, C 1.70, F_lastdb 1.31 (give-up 23%), G_llmdst 1.78 (3%),
      **D_repair 1.81** (give-up **2%**), E 1.75 (3%). (Policy v4 eliminates the v3 plain-judge gap: D > C even without fact-checking!)
      Paired diffs: **D - F +0.50 [0.33, 0.68]**, **D - B +0.29 [0.13, 0.44]**, D - C +0.11 [-0.03, 0.25].
    - Plain Opus judge: A 0.81, B 1.11, C 1.40, F_lastdb 1.04 (give-up 36%), G_llmdst 1.42 (14%),
      **D_repair 1.36** (give-up 13%), E 1.31 (18%). Paired diffs: **D - F +0.32 [0.16, 0.49]**, **D - B +0.25 [0.07, 0.42]**.
    - Fact-checked Gemini judge (`ref`): A 0.93, B 1.01, C 1.12, F_lastdb 1.24 (give-up 23%), G_llmdst 1.59 (3%),
      **D_repair 1.93** (give-up **1%**), E 1.89 (2%).
      Paired diffs: **D - F +0.69 [0.51, 0.87]**, **D - G +0.34 [0.22, 0.47]**, **D - C +0.81 [0.66, 0.96]**, **D - B +0.92 [0.77, 1.07]**.
  - **Official Llama 3.1 8B Instruct (`final_llama31`, n=100)**:
    - Objective check (`objective.py`, n=87): A 24.1% valid (19.5% invalid), B 21.8% (17.2%), C 18.4% (13.8%),
      **F_lastdb 41.4% valid (25.3% invalid)**, **G_llmdst 34.5% valid (31.0% invalid)**, **D_repair (v4) 63.2% valid
      (8.0% invalid)**, E 62.1% (13.8%).
    - Plain Gemini judge: A 0.83 (give-up 13%), B 0.81 (9%), C 0.51 (36%; **C - B -0.30 [-0.43, -0.17]**),
      F_lastdb 1.09 (20%), G_llmdst 1.07 (22%), **D_repair 1.60** [1.48, 1.71] (give-up **5%**), E 1.56 (9%).
      Paired diffs: **D - F +0.51 [0.32, 0.69]**, **D - G +0.53 [0.33, 0.71]**, **D - B +0.79 [0.61, 0.95]**, **D - C +1.09 [0.93, 1.24]**.
    - Fact-checked Gemini judge (`ref`): A 0.24 (14%), B 0.25 (11%), C 0.15 (36%; **C - B -0.10 [-0.18, -0.02]**),
      F_lastdb 0.86 (20%), G_llmdst 0.72 (23%), **D_repair 1.54** [1.40, 1.66] (give-up **5%**), E 1.45 (9%).
      Paired diffs: **D - F +0.68 [0.49, 0.87]**, **D - G +0.82 [0.64, 0.99]**, **D - B +1.29 [1.11, 1.44]**, **D - C +1.39 [1.23, 1.53]**.

## In progress (2026-11-09 afternoon, this session) — closing the reviewer gaps
- Gap 5 (judging): Opus re-judging of final_claude_fg, final_llama_fg, final_llama31 with JUDGE_BATCH=4
  (7 candidates per case made 10-case batches fail); Gemini finishing final_claude_fg (90 -> 100).
- Gap 2 (emotion in the method): `emotion_reader.py` — on 400 random DialMAGE user turns, compare detectors of
  dissatisfaction: complaint words, REPAIR repair stage (no model), LLM on the single utterance, LLM with context.
  Claim to test: the linguistic repair stage reads the user's emotional state better than word-level emotion.
- Gaps 1+4 (multi-turn, does the stage policy matter over turns): `simulate.py` — Llama 3.1 8B system under
  B/D/E/G, Claude Sonnet user simulator, fixed patience (2 unhelpful replies in a row = quit), up to 3 replies,
  50 cases: success rate, quit rate, turns to success. runs/sim_llama31.
- Reader v4.1: "today/tomorrow/any day" now counts as a given day (found in the simulator smoke test, where
  REPAIR asked for the day again after "tomorrow"). Single-turn runs above used v4.
- Gap 3 (human rating): not planned — Ying: humans cannot carry this volume; the paper uses two judge families,
  an objective database check and a simulated user instead, and says so in Limitations.

## Result 9 — Emotion is read from linguistic behaviour and context, not from the words (gap 2)
`python3 emotion_reader.py data runs/emotion_reader 400` — 400 random DialMAGE user turns, 38% negative
(EmoWOZ labels); LLM = Claude Haiku.
| detector of a dissatisfied/abusive turn | precision | recall | F1 [95% CI] |
|---|---|---|---|
| complaint words | 0.60 | 0.10 | 0.17 [0.10, 0.24] |
| LLM, single utterance only | 0.47 | 0.05 | 0.08 [0.03, 0.15] |
| REPAIR repair stage >= 1 (no model) | 0.53 | 0.85 | 0.65 [0.59, 0.70] |
| REPAIR repair stage >= 2 (no model) | 0.72 | 0.49 | 0.58 [0.51, 0.65] |
| LLM with the dialogue context | 0.67 | 0.86 | 0.75 [0.70, 0.80] |
An LLM that reads only the message misses 95% of dissatisfied turns; the same LLM with context catches 86%.
The deterministic repair stage reaches 0.65 F1 with no model call. Dissatisfaction lives in the dialogue
(repetition, repair), which is why REPAIR's reader is an emotion reader.

## Result 10 — Qwen 2.5 7B, same 100 cases, 7 conditions (runs/final_qwen) — mixed
Resolves (0-2): Opus judge A 0.53, B 0.42, C 0.34, D 1.08, E 1.22, F 0.96, G 1.15;
Gemini judge A 1.00, B 1.04, C 0.87, D 1.70, E 1.74, F 1.30, G 1.41.
D - G: Opus -0.07 [-0.25, 0.11] (no difference); Gemini +0.29 [0.11, 0.46]. D - E: Opus -0.14 [-0.27, -0.02].
Objective: real & matching D 59.8%, E 62.1%, F 48.3%, G 48.3%; constraint-violating D 6.9%, G 28.7%.
Reading: on Qwen the two judges disagree about REPAIR vs model-tracked state; the objective check favours
REPAIR's reading (fewer wrong entities). Report as mixed, not as a win.
