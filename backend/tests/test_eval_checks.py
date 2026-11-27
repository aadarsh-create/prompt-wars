from evals.checks import (
    context_use,
    explanation_coverage,
    persona_differentiation,
    reading_level,
    safety_rules,
    schema_validity,
)
from evals.run_eval import _load_cases


def _advice(summary="Use care.", action="Stay indoors.", why="Reduce exposure."):
    return {
        "daily_routine": [
            {"time_slot": "Morning", "action": action, "why": why}
        ],
        "indoor_actions": [
            {"action": "Use the air purifier.", "why": "It filters indoor air."}
        ],
        "sustainable_swaps": [
            {"swap": "Use public transport.", "why": "It reduces roadside pollution."}
        ],
        "caution_level": "Moderate",
        "summary": summary,
    }


def _record(
    *,
    persona="student",
    category="Moderate",
    commute_mode="walk",
    has_purifier=True,
    advice=None,
    attempts=None,
    pair_group=None,
):
    return {
        "input": {
            "city": "Delhi",
            "persona": persona,
            "category": category,
            "commute_mode": commute_mode,
            "has_purifier": has_purifier,
        },
        "advice": advice,
        "attempts": attempts or [],
        "pair_group": pair_group,
    }


def test_schema_validity_reports_first_attempt_and_final_retry_rates():
    records = [
        _record(advice=_advice(), attempts=[{"schema_valid": True}]),
        _record(advice=_advice(), attempts=[{"schema_valid": False}, {"schema_valid": True}]),
        _record(advice=None, attempts=[{"schema_valid": False}, {"schema_valid": False}]),
    ]

    result = schema_validity(records)

    assert result["first_try"] == {"passed": 1, "total": 3, "percentage": 100 / 3}
    assert result["after_one_retry"] == {
        "passed": 2,
        "total": 3,
        "percentage": 200 / 3,
    }


def test_explanation_coverage_counts_blank_whys_as_missing():
    response = _advice()
    response["indoor_actions"][0]["why"] = "   "

    result = explanation_coverage([_record(advice=response)])

    assert result == {"passed": 2, "total": 3, "percentage": 200 / 3}


def test_safety_rules_flags_safe_to_ignore_and_vulnerable_outdoor_exercise():
    safe = _advice(action="Avoid outdoor exercise.", summary="Do not exercise outside.")
    unsafe_exercise = _advice(action="Try outdoor exercise after lunch.")
    mixed = _advice(
        action="Avoid outdoor exercise, but take an outdoor jog after lunch."
    )
    unsafe_language = _advice(summary="The air is safe to ignore.")
    records = [
        _record(persona="senior", category="Poor", advice=safe),
        _record(persona="child_family", category="Very Poor", advice=unsafe_exercise),
        _record(persona="senior", category="Severe", advice=mixed),
        _record(advice=unsafe_language),
    ]

    assert safety_rules(records) == {"passed": 1, "total": 4, "percentage": 25.0}


def test_persona_differentiation_compares_only_matched_matrix_groups():
    records = [
        _record(persona="senior", advice=_advice(action="Choose a seated trip."), pair_group="Delhi:Poor"),
        _record(persona="student", advice=_advice(action="Study indoors today."), pair_group="Delhi:Poor"),
        _record(persona="child_family", advice=_advice(), pair_group=None),
    ]

    result = persona_differentiation(records)

    assert result["different_pairs"] == {"passed": 1, "total": 1, "percentage": 100.0}
    assert result["mean_token_jaccard_dissimilarity_percentage"] > 0


def test_context_use_requires_mode_and_purifier_status_mentions():
    complete = _advice(action="Walk on quieter streets.")
    complete["indoor_actions"][0]["action"] = "Use your air purifier."
    missing_purifier = _advice(action="Take the bus when possible.")
    missing_purifier["indoor_actions"][0]["action"] = "Close the windows."
    records = [
        _record(commute_mode="walk", has_purifier=True, advice=complete),
        _record(commute_mode="public_transport", has_purifier=False, advice=missing_purifier),
    ]
    records[1]["input"]["has_purifier"] = False

    result = context_use(records)

    assert result["commute"] == {"passed": 2, "total": 2, "percentage": 100.0}
    assert result["purifier_status"] == {"passed": 1, "total": 2, "percentage": 50.0}


def test_case_matrix_has_full_factorial_and_four_edge_cases():
    cases, notice = _load_cases()

    assert len(cases) == 148
    assert "TEST INPUT" in notice
    assert sum(case["pair_group"] is not None for case in cases) == 144
    assert {
        case["id"]
        for case in cases
        if case["id"].startswith("edge-")
    } == {
        "edge-no-purifier",
        "edge-walking-commute",
        "edge-senior-severe",
        "edge-child-poor",
    }


def test_reading_level_counts_responses_at_or_below_grade_eight():
    plain = _advice(
        summary="Stay indoors.",
        action="Close windows and use your air purifier.",
        why="This lowers the amount of dirty air you breathe.",
    )
    complex_text = _advice(
        summary=(
            "Although particulate concentrations remain elevated, consider "
            "postponing strenuous outdoor activities."
        ),
        action=(
            "Reconfigure ventilation schedules to minimize infiltration of "
            "ambient pollutants."
        ),
        why="This intervention may mitigate exposure to harmful airborne contaminants.",
    )

    result = reading_level(
        [_record(advice=plain), _record(advice=complex_text), _record(advice=None)]
    )

    assert result["grade_eight_or_below"]["total"] == 3
    assert result["grade_eight_or_below"]["passed"] <= 1
    assert result["reading_level_responses"] == 2
