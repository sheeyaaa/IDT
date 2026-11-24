Review the generated test cases strictly against the requirement points. Score
correctness, clarity, atomicity, completeness of steps, traceability, and diversity on
0-10 scales. Provide an overall quality score from 0-10 and semantic coverage from 0-100:
mere ID references do not count if the scenario does not actually test the requirement.
Flag unsupported assertions as hallucination risks. Feedback must be specific and
actionable, reference test-case IDs where applicable, and list every missing
requirement ID. Do not invent requirements or claim a numeric threshold absent from
the PRD. The deterministic coverage mapping is included; preserve its uncovered items
in missing_req_ids.

Requirements:
{{requirements}}

Test cases:
{{test_cases}}

Deterministic coverage:
{{coverage}}
