Generate concise, executable manual test cases using only the supplied requirement
points. Link each case to one or more supplied requirement IDs. Cover a positive path
for each requirement and add negative, boundary, edge, security, or performance cases
when supported by the requirement. Never assert unstated product behaviour or invent
numeric thresholds. Include preconditions, numbered steps, test data, and observable
expected results. Use only supplied requirement IDs. On revision, change only the
flagged existing cases and add cases for missing requirements; do not rewrite
unflagged cases. Keep each batch focused on its supplied requirements.

Requirements:
{{requirements}}

Flagged existing cases:
{{existing_cases}}

Critic feedback (null on the first pass):
{{critique}}

Every supplied requirement ID must have at least one positive test case. Required
positive requirement IDs for this batch:
{{positive_requirement_ids}}
