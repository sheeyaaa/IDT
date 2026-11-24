# Sourcegraph and semantic code navigation

## Set up Sourcegraph

Create or select a Sourcegraph account, add this repository as a repository to index,
and wait for indexing before running code searches. For a private repository, grant
the Sourcegraph integration only the repository access needed for indexing. A local
Sourcegraph Docker deployment is an alternative where supported by the current
Sourcegraph distribution. Availability and setup were not verified from this offline
workspace; do not treat this document as evidence that an instance is active.

In the Sourcegraph repository search box, scope queries to this repository (or select
the repository first). For references, use the symbol's references/code search
results; for definitions, select the symbol and use the language server's go-to-
definition or Sourcegraph symbol navigation when indexed language support provides it.

## Example navigation queries

1. `repo:^github\.com/<org>/<repo>$ "critique" file:src/tcgen/`
   — locate blackboard reads and writes for critic results.
2. `repo:^github\.com/<org>/<repo>$ "add_node" file:graph.py`
   — find graph node registrations.
3. `repo:^github\.com/<org>/<repo>$ "invoke_structured" lang:python`
   — follow validated model call sites.
4. `repo:^github\.com/<org>/<repo>$ "req_ids" lang:python`
   — trace test-case/requirement links.
5. `repo:^github\.com/<org>/<repo>$ "render_prompt" lang:python`
   — find runtime prompt template consumers.
6. `repo:^github\.com/<org>/<repo>$ "uncovered_requirement_ids" lang:python`
   — follow deterministic coverage results.

Replace `<org>/<repo>` with the actual GitHub owner and repository. Screenshots are
not included because no authenticated indexed Sourcegraph session was available; this
is a documented limitation rather than fabricated evidence.
