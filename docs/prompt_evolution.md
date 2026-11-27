# Prompt Evolution Log

## v1 - Baseline

Source: `backend/app/prompts/advice_v1.txt`

The original prompt established the core role, supplied live AQI context, and enforced persona-specific safety rules. It was a useful baseline, but the output guidance was broad and could be too repetitive or generic.

What the human changed:
- Defined the exact profile fields, AQI context, and structured JSON output.
- Required stale readings to be disclosed.

What the AI produced:
- Initial versioned prompt and persona rules.

## v2 - Action-oriented structure

Source: `backend/app/prompts/advice_v2.txt`

Changes from v1:
- Grouped context into a clearly labeled block.
- Added explicit priority order for immediate exposure reduction.
- Requested 3 to 5 routine actions and explained the purpose of each section.
- Added clearer persona and sustainable-swap constraints.
- Expanded practical alternatives when a purifier is unavailable.

Why:
- Reduce generic advice and make the model focus on actions the user can take today.

## v3 - Current production prompt

Source: `backend/app/prompts/advice_v3.txt`

Changes from v2:
- Added a decision-first format: risk-reduction actions come before supporting detail.
- Added explicit persona output behavior, including a child-family go/limited/no-go decision.
- Added commute-specific rules for walking, cycling, public transport, and cars.
- Added severe-winter-smog guidance for outdoor exposure, cautious ventilation, and indoor pollution sources.
- Added concise output counts and guardrails against unsupported thresholds or medical certainty.
- Added stale-reading wording and city-specific feasibility constraints.

Why:
- Improve consistency across personas and keep answers concise, evidence-bounded, and easier to compare side by side.

## Iteration test matrix

Run advice requests against these representative combinations:

| Case | AQI/category | Persona | Commute | Purifier | Result to check |
|---|---|---|---|---|---|
| Delhi high-pollution commute | 243 / Poor | working_professional | public_transport | no | Shorter waits and lower roadside exposure |
| Child outdoor play | 301 / Very Poor | child_family | none | yes | Explicit go/limited/no-go decision |
| Senior walk | 143 / Moderate | senior | walk | no | Lower-exertion, quieter-route options |
| Stale data | 180 / Moderate, stale | student | cycle | no | Summary identifies stale data and gives caution only |

The service currently loads v3 at `PROMPT_PATH`. v1 and v2 remain available for comparison and prompt-evolution review.
