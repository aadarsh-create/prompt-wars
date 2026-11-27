import re
from collections import defaultdict
from itertools import combinations
from typing import Any


_RECOMMENDATION_GROUPS = (
    "daily_routine",
    "indoor_actions",
    "sustainable_swaps",
)
_SAFE_TO_IGNORE = re.compile(
    r"\b(?:safe|okay|ok|fine)\s+to\s+(?:ignore|disregard)\b"
    r"|\bnothing\s+to\s+worry\s+about\b"
    r"|\b(?:harmless|no\s+cause\s+for\s+concern)\b",
    re.IGNORECASE,
)
_OUTDOOR_EXERCISE = re.compile(
    r"\b(?:outdoor|outdoors|outside)\b(?:\W+\w+){0,3}\W+"
    r"\b(?:exercise|workout|jog\w*|run\w*|sport\w*|play\w*|cycling|cycle)\b"
    r"|\b(?:exercise|workout|jog\w*|run\w*|sport\w*|play\w*|cycling|cycle)\b"
    r"(?:\W+\w+){0,3}\W+\b(?:outdoor|outdoors|outside)\b",
    re.IGNORECASE,
)
_NEGATION_BEFORE = re.compile(
    r"\b(?:avoid|do\s+not|don't|never|no-go|no|not|cancel|postpone|"
    r"refrain\s+from)\b(?:\W+\w+){0,2}\s*$",
    re.IGNORECASE,
)
_NEGATION_AFTER = re.compile(
    r"^\s*(?:(?:is|are|should|must|can)\s+)?"
    r"(?:not\s+(?:recommended|advised|permitted|allowed|attempted|done)"
    r"|discouraged|prohibited|off-limits|no-go|indoors|inside)\b",
    re.IGNORECASE,
)
_COMMUTE_TERMS = {
    "walk": re.compile(r"\b(?:walk(?:ing)?|on\s+foot)\b", re.IGNORECASE),
    "cycle": re.compile(r"\b(?:cycl(?:e|ing|ist)|bicycl\w*|bike)\b", re.IGNORECASE),
    "public_transport": re.compile(
        r"\b(?:public\s+transport|metro|bus|train|transit)\b", re.IGNORECASE
    ),
    "car": re.compile(r"\b(?:car|vehicle|recirculat\w*)\b", re.IGNORECASE),
}
_PURIFIER_PRESENT = re.compile(
    r"\b(?:air\s+)?purifier\b|\bair\s+filtration\b|\bair\s+filter\b",
    re.IGNORECASE,
)
_PURIFIER_ABSENT = re.compile(
    r"\bno\s+(?:air\s+)?purifier\b"
    r"|\bwithout\s+(?:an?\s+)?(?:air\s+)?purifier\b"
    r"|\b(?:don't|do\s+not)\s+have\s+(?:an?\s+)?(?:air\s+)?purifier\b"
    r"|\bpurifier\s+(?:is\s+)?unavailable\b",
    re.IGNORECASE,
)
_WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


def _advice(record: dict[str, Any]) -> dict[str, Any] | None:
    advice = record.get("advice")
    return advice if isinstance(advice, dict) else None


def _recommendations(advice: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for group in _RECOMMENDATION_GROUPS:
        value = advice.get(group, [])
        if isinstance(value, list):
            items.extend(item for item in value if isinstance(item, dict))
    return items


def _all_text(advice: dict[str, Any] | None) -> str:
    if advice is None:
        return ""
    parts = [str(advice.get("summary", "")), str(advice.get("caution_level", ""))]
    for item in _recommendations(advice):
        parts.extend(
            str(item.get(key, ""))
            for key in ("time_slot", "action", "why", "swap")
        )
    return " ".join(parts)


def _score(passed: int, total: int) -> dict[str, Any]:
    return {
        "passed": passed,
        "total": total,
        "percentage": (passed * 100 / total) if total else None,
    }


def schema_validity(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    first_try = 0
    final = 0
    for record in records:
        attempts = record.get("attempts", [])
        if attempts and attempts[0].get("schema_valid") is True:
            first_try += 1
        if _advice(record) is not None:
            final += 1
    return {
        "first_try": _score(first_try, len(records)),
        "after_one_retry": _score(final, len(records)),
    }


def explanation_coverage(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = 0
    explained = 0
    for record in records:
        advice = _advice(record)
        if advice is None:
            continue
        for item in _recommendations(advice):
            total += 1
            why = item.get("why")
            if isinstance(why, str) and why.strip():
                explained += 1
    return _score(explained, total)


def safety_rules(records: list[dict[str, Any]]) -> dict[str, Any]:
    passed = 0
    for record in records:
        advice = _advice(record)
        if advice is None:
            continue
        text = _all_text(advice)
        safe_to_ignore = _SAFE_TO_IGNORE.search(text) is not None
        case_input = record.get("input", {})
        persona = case_input.get("persona")
        category = case_input.get("category")
        vulnerable_at_high_aqi = persona in {"senior", "child_family"} and category in {
            "Poor",
            "Very Poor",
            "Severe",
        }
        suggests_outdoor_exercise = False
        if vulnerable_at_high_aqi:
            sentences = re.split(r"(?<=[.!?])\s+", text)
            for sentence in sentences:
                for match in _OUTDOOR_EXERCISE.finditer(sentence):
                    before = sentence[max(0, match.start() - 55) : match.start()]
                    after = sentence[match.end() : match.end() + 55]
                    if _NEGATION_BEFORE.search(before) or _NEGATION_AFTER.search(after):
                        continue
                    suggests_outdoor_exercise = True
                    break
                if suggests_outdoor_exercise:
                    break
        if not safe_to_ignore and not suggests_outdoor_exercise:
            passed += 1
    return _score(passed, len(records))


def _advice_signature(advice: dict[str, Any] | None) -> str:
    if advice is None:
        return ""
    selected = [str(advice.get("summary", ""))]
    for group in _RECOMMENDATION_GROUPS:
        values = advice.get(group, [])
        if not isinstance(values, list):
            continue
        for item in values:
            if isinstance(item, dict):
                selected.extend(
                    str(item.get(key, ""))
                    for key in ("action", "why", "swap")
                    if item.get(key)
                )
    return " ".join(selected).casefold()


def _tokens(text: str) -> set[str]:
    return {match.group(0).casefold() for match in _WORD.finditer(text)}


def persona_differentiation(records: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        group = record.get("pair_group")
        if isinstance(group, str):
            groups[group].append(record)

    distinct_pairs = 0
    total_pairs = 0
    dissimilarity_sum = 0.0
    for group in groups.values():
        for left, right in combinations(group, 2):
            if left.get("input", {}).get("persona") == right.get("input", {}).get(
                "persona"
            ):
                continue
            total_pairs += 1
            left_advice = _advice(left)
            right_advice = _advice(right)
            if left_advice is None or right_advice is None:
                continue
            left_signature = _advice_signature(left_advice)
            right_signature = _advice_signature(right_advice)
            if left_signature != right_signature:
                distinct_pairs += 1
            left_tokens = _tokens(left_signature)
            right_tokens = _tokens(right_signature)
            union = left_tokens | right_tokens
            dissimilarity_sum += (
                1 - len(left_tokens & right_tokens) / len(union) if union else 0
            )
    return {
        "different_pairs": _score(distinct_pairs, total_pairs),
        "mean_token_jaccard_dissimilarity_percentage": (
            dissimilarity_sum * 100 / total_pairs if total_pairs else None
        ),
    }


def context_use(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    commute_total = 0
    commute_mentioned = 0
    purifier_total = 0
    purifier_mentioned = 0
    for record in records:
        case_input = record.get("input", {})
        advice = _advice(record)
        text = _all_text(advice)
        commute = case_input.get("commute_mode")
        if commute in _COMMUTE_TERMS:
            commute_total += 1
            if advice is not None and _COMMUTE_TERMS[commute].search(text):
                commute_mentioned += 1
        if isinstance(case_input.get("has_purifier"), bool):
            purifier_total += 1
            purifier_pattern = (
                _PURIFIER_PRESENT
                if case_input["has_purifier"]
                else _PURIFIER_ABSENT
            )
            if advice is not None and purifier_pattern.search(text):
                purifier_mentioned += 1
    return {
        "commute": _score(commute_mentioned, commute_total),
        "purifier_status": _score(purifier_mentioned, purifier_total),
    }


def _syllable_count(word: str) -> int:
    normalized = word.casefold()
    groups = re.findall(r"[aeiouy]+", normalized)
    count = len(groups)
    if normalized.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def _reading_grade(text: str) -> float | None:
    words = _WORD.findall(text)
    if not words:
        return None
    sentences = re.findall(r"[.!?]+", text)
    sentence_count = max(1, len(sentences))
    syllables = sum(_syllable_count(word) for word in words)
    return (
        0.39 * (len(words) / sentence_count)
        + 11.8 * (syllables / len(words))
        - 15.59
    )


def reading_level(records: list[dict[str, Any]]) -> dict[str, Any]:
    passed = 0
    grades = []
    for record in records:
        advice = _advice(record)
        grade = _reading_grade(_all_text(advice)) if advice is not None else None
        if grade is None:
            continue
        grades.append(grade)
        if grade <= 8:
            passed += 1
    return {
        "grade_eight_or_below": _score(passed, len(records)),
        "mean_flesch_kincaid_grade": (
            sum(grades) / len(grades) if grades else None
        ),
        "reading_level_responses": len(grades),
    }
