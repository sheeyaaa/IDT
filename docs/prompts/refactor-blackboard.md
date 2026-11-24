# Refactoring prompt: explicit blackboard state

Status: illustrative prompt record; no external code-generation service was invoked.

## Goal

Replace loose shared dictionaries with named LangGraph state keys and validated agent
payloads.

## Prompt

> Map each agent's reads and writes. Define explicit blackboard fields and Pydantic
> schemas for requirements, test cases, coverage and critic results. Keep routing
> deterministic and make every boundary reject malformed data.

## Result

Added `GraphState` plus strict Pydantic models in `src/tcgen/state.py` and
`src/tcgen/models.py`.

## Review change

Graph orchestration remains in `graph.py`; the schemas do not embed LLM calls or routing.

## Before / after

```diff
- state["critic_result"] = arbitrary_model_dict
- if state["critic_result"].get("done"): ...
+ state["critique"] = Critique.model_validate_json(response)
+ if score_and_coverage_pass or iteration >= configured_cap: ...
```
