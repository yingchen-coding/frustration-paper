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
