# Understand the user, don't repeat: unmet needs in task-oriented dialogue

When a dialogue system fails, users rarely say so with complaint words. They repeat or rephrase the request,
write "what?" or "??", or get shorter. This repository studies those linguistic and emotional cues of an
unmet need and tests a method, **REPAIR**, that reads them explicitly so a model solves what the user is
still waiting for instead of answering only the last message.

Work in progress. Numbers below are reproducible from this repository; see `PROGRESS.md` for the current
results and `FINDINGS.md` for the full log, including dead ends.

## Findings so far
1. **Machines do not react to dissatisfaction.** In EmoWOZ, human wizards acknowledge or apologize after a
   dissatisfied user turn 17.8% of the time (3.9% after neutral turns); the machine system: 3.5% vs 3.7%.
2. **Dissatisfaction is mostly not in the words.** Toward the machine, 46.8% of dissatisfied turns repeat an
   earlier request; only 7.7% contain a complaint or negation word.
3. **Telling a model to "read the user first" helps a strong model and hurts a small one.** The small model
   misreads the need and apologizes instead of delivering.
4. **REPAIR on 100 unseen dialogues (Llama 3 8B generator, Claude Opus judge):** resolves the user's need
   1.22 / 2 vs 0.45 for the baseline (+0.77 [0.55, 0.98] vs "be concrete"); the user would give up 19% vs 49%
   for the prompt-only version; a real, matching venue or train in 61% of replies vs 18-23%.

## REPAIR
`repair.py` — deterministic, no model calls:
- **Repair reader:** other-initiated repair and escalation cues (repeat/rephrase of an earlier request,
  "what?/??", no/not/again/already, meta-complaints, shorter turns) -> escalation stage 0-4.
- **Grounding ledger:** what the user asked for per domain, what was delivered, what is pending, and which
  required details are still missing.
- **Database grounding:** MultiWOZ database rows for the pending request, relaxing one constraint at a time.
- **Response policy** by stage (deliver first, ask only for missing details, book when asked).
The resulting brief is given to any generator.

## Reproduce
```bash
mkdir -p data/db
for f in emowoz-multiwoz emowoz-dialmage data-split; do
  curl -L -o data/$f.json https://zenodo.org/record/6506504/files/$f.json; done
for d in attraction hospital hotel police restaurant taxi train; do
  curl -L -o data/db/${d}_db.json https://raw.githubusercontent.com/budzianowski/multiwoz/master/db/${d}_db.json; done

python3 analyze.py data > results.json                      # corpus study
SPLIT=train JUDGER=claude:opus GEN=ollama:dolphin-llama3:8b \
  python3 intervene.py data runs/final_llama 100             # generate A-E replies and judge them
python3 objective.py data runs/final_llama                  # database check, no LLM
```
Generation uses the `claude` CLI or a local `ollama` model; judging uses the `claude` or `codex` CLI.
`JUDGE_REF=1` shows the judge the database rows so invented facts cannot score full marks.

## Data and licence
EmoWOZ (Feng et al., LREC 2022) is CC BY-NC 4.0; MultiWOZ database files are from
github.com/budzianowski/multiwoz. Neither is redistributed here except dialogue excerpts inside `runs/`,
used for non-commercial research with attribution. Code: MIT (see `LICENSE`).

## Author
Ying Chen
