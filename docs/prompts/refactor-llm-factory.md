# Refactoring prompt: shared Ollama client construction

Status: illustrative prompt record; no external code-generation service was invoked.

## Goal

Create one configured local chat client per agent role and make client injection possible
for tests.

## Prompt

> Inspect the graph and agent calls. Extract only the repeated local Ollama construction
> into a typed helper, read model names/base URL/temperature/keep-alive from config,
> keep model calls injectable, and do not add a provider or inline runtime prompts.

## Result

Added `create_model_clients` in `src/tcgen/llm.py`; `create_graph` accepts clients for
offline tests.

## Review change

The helper uses a minimal `Invokable` protocol rather than a concrete chat-model type,
so deterministic fakes need implement only `invoke`.

## Before / after

```diff
- extractor = ChatOllama(model="...", base_url="...")
- generator = ChatOllama(model="...", base_url="...")
- critic = ChatOllama(model="...", base_url="...")
+ clients = create_model_clients(config)
+ graph = create_graph(config, clients=clients)
```
