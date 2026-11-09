# Understand the User, Don't Repeat: Linguistic Cues of Unmet Needs and Explicit Repair in Task-Oriented Dialogue

[![Version](https://img.shields.io/github/v/tag/yingchen-coding/frustration-paper?sort=semver&label=version)](https://github.com/yingchen-coding/frustration-paper/releases)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24077786.svg)](https://doi.org/10.5281/zenodo.24077786)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

When a dialogue system fails, users rarely say so with complaint words. They repeat or rephrase the request,
write "what?" or "??", or get shorter. This repository studies those linguistic and emotional cues of an
unmet need and tests a method, **REPAIR**, that reads them explicitly so a model solves what the user is
still waiting for instead of answering only the last message.

## Paper

The preprint source is in [`paper/main.tex`](paper/main.tex); rendered artifacts are
[`paper/frustration-paper.pdf`](paper/frustration-paper.pdf) ([`paper/main.pdf`](paper/main.pdf)),
[`paper/frustration-paper.html`](paper/frustration-paper.html) ([live GitHub Pages](https://yingchen-coding.github.io/frustration-paper/)),
[`paper/frustration-paper.docx`](paper/frustration-paper.docx), and the arXiv source bundle
[`paper/arxiv-upload.zip`](paper/arxiv-upload.zip).

Citable artifact DOI: [10.5281/zenodo.24077786](https://doi.org/10.5281/zenodo.24077786).

The resulting brief is given to any generator. Paper PDF: [`paper/main.pdf`](paper/main.pdf) (`paper/main.tex`).

## Key Findings
1. **Machines do not react to dissatisfaction.** In EmoWOZ, human wizards acknowledge or apologize after a
   dissatisfied user turn 17.8% of the time (3.9% after neutral turns); the machine system: 3.5% vs 3.7%.
2. **Dissatisfaction follows a repair escalation ladder, not complaint words.** Toward the machine, 46.8% of
   dissatisfied turns repeat an earlier request while only 7.7% contain a complaint word (precision 92.9%).
   Across all 12,093 DialMAGE user turns (`analyze_ladder.py`), dissatisfaction rises monotonically with
   repair stage: **16.3%** (stage 0) → **34.3%** (stage 1) → **60.3%** (stage 2) → **79.3%** (stage 3+),
   capturing **81.7%** of all negative turns at stage ≥ 1. In chat-oriented dialogue without task goals
   (DBDC3, `analyze_dbdc3.py`), repetition barely rises after breakdowns (+1.5 pp vs +33.6 pp in task dialogue).
3. **Telling a model to "read the user first" helps a strong model and hurts a small one.** On 100 unseen
   cases, prompt-only self-diagnosis hurts an 8B model under both judge families (Gemini: −0.25 [−0.42, −0.08]
   vs "be concrete", give-ups 35%–49%): the 8B model misreads the need and apologizes instead of delivering.
4. **REPAIR on 100 unseen dialogues (two generators × two independent judge families):**
   - **Llama 3 8B generator:** REPAIR raises `resolves` (0–2) from 0.45 to **1.22** (Opus judge) and from 0.98
     to **1.51** (Gemini judge), cuts give-ups from 49%/35% (prompt-only) to **19%/14%**, and raises real,
     matching database entities from 18.4%–23.0% to **60.9%** (vs 10.3% for the original DialMAGE system).
     On stage-3 high-escalation cases, REPAIR's escalation policy significantly beats ledger+database alone
     (Opus +0.50 [0.08, 0.92], Gemini +0.67 [0.25, 1.17]).
   - **Strong model (Sonnet) & judge hallucination bias:** Plain LLM judges award full marks to 38%–65% of
     replies that name an entity violating the user's constraints (e.g., invented train bookings). With
     database fact-checking (`JUDGE_REF=1`), inter-judge correlation rises to $r = 0.81\text{--}0.90$ and
     REPAIR dominates all baselines on both models (Sonnet: **1.64** Opus, **1.94** Gemini).

## Reproduce
```bash
mkdir -p data/db
for f in emowoz-multiwoz emowoz-dialmage data-split; do
  curl -L -o data/$f.json https://zenodo.org/record/6506504/files/$f.json; done
for d in attraction hospital hotel police restaurant taxi train; do
  curl -L -o data/db/${d}_db.json https://raw.githubusercontent.com/budzianowski/multiwoz/master/db/${d}_db.json; done

python3 analyze.py data > results.json                      # corpus study (Table 1)
python3 analyze_ladder.py data                              # repair ladder across 12,093 turns (Table 2)
python3 analyze_dbdc3.py                                    # DBDC3 chat contrast corpus
python3 validate_wordlists.py                               # word-list precision & reader spot-check
SPLIT=train JUDGER=claude:opus GEN=ollama:dolphin-llama3:8b \
  python3 intervene.py data runs/final_llama 100            # generate A-E replies and judge them
python3 second_judge.py data runs/final_llama gemini        # second judge family (plain + JUDGE_REF=1)
python3 objective.py data runs/final_llama                  # database entity check, no LLM
```
Generation uses the `claude` CLI or a local `ollama` model; judging uses the `claude` or `codex` CLI.
`JUDGE_REF=1` shows the judge the database rows so invented facts cannot score full marks.

## Data and licence
EmoWOZ (Feng et al., LREC 2022) is CC BY-NC 4.0; MultiWOZ database files are from
github.com/budzianowski/multiwoz. Neither is redistributed here except dialogue excerpts inside `runs/`,
used for non-commercial research with attribution. Code: MIT (see `LICENSE`).

## Author
Ying Chen
