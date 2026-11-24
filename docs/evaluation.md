# Evaluation and ablation

## Retrieval

Build/update the local index with `tcgen index .`, then run `tcgen eval-rag`. The
checked-in `tests/data/rag_eval.json` contains 15 questions with expected source paths.
The reported hit rate is the fraction of questions for which at least one expected
source file appears in the top-k retrieval results. No hit-rate result is claimed until
the command is run against the local index.

## Single-pass versus critic loop

Use the same PRD and the same role models for both runs. For the baseline, make a copy
of `config.yaml` with `max_iterations: 1`; run the normal configuration for the
critic-loop run:

```powershell
tcgen run --prd .\path\to\prd.md --out .\out\single --config .\config-one-pass.yaml
tcgen run --prd .\path\to\prd.md --out .\out\critic-loop --config .\config.yaml
tcgen compare --single-pass .\out\single\test-suite.json `
  --critic-loop .\out\critic-loop\test-suite.json --out .\out\ablation.json
```

The one-iteration run performs one generator pass and one critic evaluation; it is the
single-pass baseline, not a critic-free score. `tcgen compare` reports critic-loop
minus baseline quality, coverage, case-count, and elapsed-time deltas. Scores are
locally model-judged and should be reported with the PRD/model identifiers. No live
ablation has been run in this environment because Ollama models were not invoked.
