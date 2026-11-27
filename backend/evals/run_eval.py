import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from typing import Any

import httpx

from app.schemas import UserProfile
from app.services import advice as advice_service
from app.services.advice import AdviceServiceError
from evals import checks


EVALS_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVALS_DIR.parents[1]
PROMPTS_DIR = REPO_ROOT / "backend" / "app" / "prompts"
RESULTS_DIR = EVALS_DIR / "results"
PROMPT_FILES = {version: PROMPTS_DIR / f"advice_{version}.txt" for version in ("v1", "v2", "v3")}
MAX_CASES = 148
DEFAULT_DELAY_SECONDS = 12.0
_REAL_ASYNC_CLIENT = httpx.AsyncClient


def _load_cases() -> tuple[list[dict[str, Any]], str]:
    with (EVALS_DIR / "cases.yaml").open(encoding="utf-8") as file:
        definition = json.load(file)
    notice = definition.get("input_data_notice", "")
    if "TEST INPUT" not in notice:
        raise ValueError("AQI fixture notice must clearly mark values as TEST INPUTS.")

    matrix = definition["matrix"]
    buckets = {bucket["name"]: bucket for bucket in matrix["aqi_buckets"]}
    cases = []
    for city_index, city in enumerate(matrix["cities"]):
        for bucket_index, bucket in enumerate(matrix["aqi_buckets"]):
            pair_group = f"{city}:{bucket['name']}"
            commute_mode = matrix["commute_modes"][
                (city_index + bucket_index) % len(matrix["commute_modes"])
            ]
            has_purifier = (city_index + bucket_index) % 2 == 0
            for persona in matrix["personas"]:
                cases.append(
                    _make_case(
                        case_id=f"{city.casefold()}-{bucket['name'].casefold().replace(' ', '-')}-{persona}",
                        city=city,
                        persona=persona,
                        commute_mode=commute_mode,
                        has_purifier=has_purifier,
                        bucket=bucket,
                        pair_group=pair_group,
                    )
                )

    for edge in definition["edge_cases"]:
        cases.append(
            _make_case(
                case_id=edge["id"],
                city=edge["city"],
                persona=edge["persona"],
                commute_mode=edge["commute_mode"],
                has_purifier=edge["has_purifier"],
                bucket=buckets[edge["aqi_bucket"]],
                pair_group=None,
            )
        )
    if len(cases) != MAX_CASES:
        raise ValueError(f"Expected {MAX_CASES} evaluation cases, found {len(cases)}.")
    return cases, notice


def _make_case(
    *,
    case_id: str,
    city: str,
    persona: str,
    commute_mode: str,
    has_purifier: bool,
    bucket: dict[str, Any],
    pair_group: str | None,
) -> dict[str, Any]:
    case = {
        "id": case_id,
        "input": {
            "city": city,
            "persona": persona,
            "commute_mode": commute_mode,
            "has_purifier": has_purifier,
            "aqi": bucket["aqi"],
            "category": bucket["name"],
            "pm25": bucket["pm25"],
            "pm10": bucket["pm10"],
            "observed_at": "2026-01-01T00:00:00+00:00",
            "is_stale": False,
            "source": "Evaluation fixture (TEST INPUT ONLY)",
            "station": "Test input; not a live monitoring station",
        },
        "pair_group": pair_group,
    }
    return case


class _ObservedAsyncClient:
    def __init__(self, attempts: list[dict[str, Any]], *args: Any, **kwargs: Any):
        self._attempts = attempts
        self._client = _REAL_ASYNC_CLIENT(*args, **kwargs)

    async def __aenter__(self):
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return await self._client.__aexit__(exc_type, exc_value, traceback)

    async def post(self, *args: Any, **kwargs: Any):
        attempt = {"http_status": None, "schema_valid": False}
        self._attempts.append(attempt)
        try:
            response = await self._client.post(*args, **kwargs)
        except httpx.HTTPError as error:
            attempt["error"] = type(error).__name__
            raise
        attempt["http_status"] = response.status_code
        return response


async def _generate_observed(
    profile: UserProfile, reading: dict[str, Any]
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], str | None]:
    attempts: list[dict[str, Any]] = []
    original_client = advice_service.httpx.AsyncClient
    original_parser = advice_service._parse_advice

    def observed_parser(text: str):
        parsed = original_parser(text)
        if attempts:
            attempts[-1]["schema_valid"] = True
        return parsed

    advice_service.httpx.AsyncClient = lambda *args, **kwargs: _ObservedAsyncClient(
        attempts, *args, **kwargs
    )
    advice_service._parse_advice = observed_parser
    try:
        response = await advice_service.generate_advice(profile, reading)
        return response.model_dump(mode="json"), attempts, None
    except AdviceServiceError as error:
        return None, attempts, str(error)
    finally:
        advice_service.httpx.AsyncClient = original_client
        advice_service._parse_advice = original_parser


async def _judge_response(
    profile: UserProfile,
    reading: dict[str, Any],
    advice: dict[str, Any],
) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_KEY is not configured for the optional judge.")
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    rubric = (
        "Evaluate this air-quality advice against its supplied profile and reading. "
        "Return JSON with integer scores 1-5 for actionability, clarity, correctness, "
        "and a short rationale. Correctness means conservative, internally consistent "
        "advice grounded in the supplied context; do not reward invented facts.\n"
        f"Profile: {profile.model_dump(mode='json')}\n"
        f"Reading (test input): {reading}\n"
        f"Advice: {json.dumps(advice, ensure_ascii=True)}"
    )
    body = {
        "contents": [{"parts": [{"text": rubric}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "object",
                "properties": {
                    key: {"type": "integer", "minimum": 1, "maximum": 5}
                    for key in ("actionability", "clarity", "correctness")
                },
                "required": ["actionability", "clarity", "correctness"],
            },
        },
    }
    async with _REAL_ASYNC_CLIENT(timeout=httpx.Timeout(30.0)) as client:
        response = await client.post(url, params={"key": api_key}, json=body)
    response.raise_for_status()
    payload = response.json()
    text = payload["candidates"][0]["content"]["parts"][0]["text"]
    result = json.loads(text)
    scores = {
        key: result[key]
        for key in ("actionability", "clarity", "correctness")
    }
    if any(type(score) is not int or not 1 <= score <= 5 for score in scores.values()):
        raise ValueError("Judge returned a score outside the expected 1-5 range.")
    return {**scores, "rationale": str(result.get("rationale", ""))}


def _metric_percentage(metric: dict[str, Any]) -> str:
    passed = metric.get("passed")
    total = metric.get("total")
    if not isinstance(passed, int) or not isinstance(total, int) or total == 0:
        return "n/a"
    percentage = (Decimal(passed * 100) / Decimal(total)).quantize(
        Decimal("0.01"), rounding=ROUND_DOWN
    )
    return f"{percentage}% ({passed}/{total})"


def _metric_table(version: str, metrics: dict[str, Any]) -> str:
    rows = [
        ("Schema validity, first try", metrics["schema_validity"]["first_try"]),
        (
            "Schema validity, after one retry",
            metrics["schema_validity"]["after_one_retry"],
        ),
        ("Explanation coverage", metrics["explanation_coverage"]),
        ("Safety rules", metrics["safety_rules"]),
        (
            "Persona differentiation",
            metrics["persona_differentiation"]["different_pairs"],
        ),
        ("Commute context use", metrics["context_use"]["commute"]),
        ("Purifier-status context use", metrics["context_use"]["purifier_status"]),
        (
            "Reading level (Flesch-Kincaid grade <= 8)",
            metrics["reading_level"]["grade_eight_or_below"],
        ),
    ]
    lines = [
        f"| Prompt | Metric | Result |",
        "|---|---|---:|",
    ]
    lines.extend(
        f"| {version} | {name} | {_metric_percentage(value)} |"
        for name, value in rows
    )
    return "\n".join(lines)


def _judge_summary(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    summary = {
        key: {"score_sum": 0, "count": 0}
        for key in ("actionability", "clarity", "correctness")
    }
    for record in records:
        result = record.get("judge")
        if not isinstance(result, dict):
            continue
        for key in summary:
            score = result.get(key)
            if isinstance(score, int):
                summary[key]["score_sum"] += score
                summary[key]["count"] += 1
    return summary


def _update_prompt_evolution() -> None:
    path = REPO_ROOT / "docs" / "prompt_evolution.md"
    contents = path.read_text(encoding="utf-8")
    start_marker = "<!-- EVAL RESULTS START -->"
    end_marker = "<!-- EVAL RESULTS END -->"
    if start_marker not in contents or end_marker not in contents:
        raise ValueError("Prompt evolution evaluation-results markers are missing.")

    latest: dict[str, tuple[str, dict[str, Any]]] = {}
    for result_path in RESULTS_DIR.glob("eval_v*.json"):
        result = json.loads(result_path.read_text(encoding="utf-8"))
        version = result.get("prompt_version")
        if version not in {"v1", "v2", "v3"}:
            continue
        timestamp = str(result.get("completed_at", ""))
        if version not in latest or timestamp > latest[version][0]:
            latest[version] = (timestamp, result["metrics"])

    table = [
        "| Prompt | First-try schema | After-retry schema | Explanation | Safety | Persona distinction | Commute context | Purifier context | Reading level |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for version in ("v1", "v2", "v3"):
        if version not in latest:
            continue
        metrics = latest[version][1]
        values = (
            metrics["schema_validity"]["first_try"],
            metrics["schema_validity"]["after_one_retry"],
            metrics["explanation_coverage"],
            metrics["safety_rules"],
            metrics["persona_differentiation"]["different_pairs"],
            metrics["context_use"]["commute"],
            metrics["context_use"]["purifier_status"],
            metrics["reading_level"]["grade_eight_or_below"],
        )
        rendered = " | ".join(_metric_percentage(value) for value in values)
        table.append(f"| {version} | {rendered} |")

    if latest:
        intro = (
            "Latest saved real evaluation per prompt version. Percentages are "
            "truncated to two decimal places (never rounded up); exact counts are "
            "shown as passed/total. The JSON run artifacts contain the full results."
        )
        body = f"{intro}\n\n" + "\n".join(table)
    else:
        body = (
            "No real Gemini evaluation runs are recorded yet. This comparison will "
            "contain only measured results after prompt versions are evaluated."
        )
    before = contents.split(start_marker, 1)[0]
    after = contents.split(end_marker, 1)[1]
    path.write_text(
        before + start_marker + "\n" + body + "\n" + end_marker + after,
        encoding="utf-8",
    )


async def _run(args: argparse.Namespace) -> Path:
    if not os.getenv("GEMINI_KEY"):
        raise RuntimeError("GEMINI_KEY is not configured; no Gemini calls were made.")
    cases, notice = _load_cases()
    selected = cases[: args.max_cases]
    original_prompt_path = advice_service.PROMPT_PATH
    advice_service.PROMPT_PATH = PROMPT_FILES[args.prompt]
    records = []
    judge_attempts = []
    try:
        for index, case in enumerate(selected):
            if index:
                await asyncio.sleep(args.delay_seconds)
            case_input = case["input"]
            profile = UserProfile.model_validate(
                {
                    "city": case_input["city"],
                    "persona": case_input["persona"],
                    "commute_mode": case_input["commute_mode"],
                    "has_purifier": case_input["has_purifier"],
                }
            )
            reading = {
                key: case_input[key]
                for key in (
                    "city",
                    "aqi",
                    "category",
                    "pm25",
                    "pm10",
                    "observed_at",
                    "source",
                    "is_stale",
                    "station",
                )
            }
            advice, attempts, error = await _generate_observed(profile, reading)
            record = {
                "id": case["id"],
                "pair_group": case["pair_group"],
                "input": case_input,
                "attempts": attempts,
                "advice": advice,
                "error": error,
            }
            if args.judge and advice is not None:
                await asyncio.sleep(args.delay_seconds)
                try:
                    record["judge"] = await _judge_response(profile, reading, advice)
                except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError) as judge_error:
                    record["judge"] = {"error": str(judge_error)}
                judge_attempts.append(record["judge"])
            records.append(record)
            print(
                f"[{index + 1}/{len(selected)}] {case['id']}: "
                f"{'ok' if advice is not None else 'service error'} "
                f"({len(attempts)} advice HTTP attempt(s))"
            )
    finally:
        advice_service.PROMPT_PATH = original_prompt_path

    metrics = {
        "schema_validity": checks.schema_validity(records),
        "explanation_coverage": checks.explanation_coverage(records),
        "safety_rules": checks.safety_rules(records),
        "persona_differentiation": checks.persona_differentiation(records),
        "context_use": checks.context_use(records),
        "reading_level": checks.reading_level(records),
    }
    judge_summary = _judge_summary(records) if args.judge else None
    completed_at = datetime.now(timezone.utc).isoformat()
    run = {
        "prompt_version": args.prompt,
        "completed_at": completed_at,
        "case_count": len(records),
        "advice_http_attempt_count": sum(len(record["attempts"]) for record in records),
        "judge_enabled": args.judge,
        "judge_call_count": len(judge_attempts),
        "input_data_notice": notice,
        "delay_seconds": args.delay_seconds,
        "metrics": metrics,
        "judge_summary": judge_summary,
        "cases": records,
    }
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"eval_{args.prompt}_{timestamp}"
    json_path = RESULTS_DIR / f"{stem}.json"
    markdown_path = RESULTS_DIR / f"{stem}.md"
    json_path.write_text(json.dumps(run, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    markdown = [
        f"# Advice evaluation: {args.prompt}",
        "",
        f"- Completed at (UTC): {completed_at}",
        f"- Cases: {len(records)}",
        f"- Advice Gemini HTTP attempts: {run['advice_http_attempt_count']}",
        f"- Optional judge enabled: {'yes' if args.judge else 'no'}",
        f"- AQI fixtures: {notice}",
        "- Reading level uses the heuristic Flesch-Kincaid grade; target is grade 8 or below.",
        "- Safety and context checks are deterministic text heuristics, not medical review.",
        "",
        _metric_table(args.prompt, metrics),
        "",
        "Persona differentiation also reports mean token Jaccard dissimilarity in the JSON.",
    ]
    if args.judge:
        markdown.extend(
            [
                "",
                "## Optional LLM judge",
                "Judge scores are subjective and potentially biased: Gemini is grading Gemini.",
                f"Judge requests attempted: {len(judge_attempts)}.",
                "",
                "| Rubric | Mean score (1-5, exact sum/count) |",
                "|---|---:|",
            ]
        )
        for name, result in judge_summary.items():
            markdown.append(
                f"| {name} | {result['score_sum']}/{result['count']} |"
                if result["count"]
                else f"| {name} | n/a (0 scores) |"
            )
    markdown_path.write_text("\n".join(markdown) + "\n", encoding="utf-8")
    _update_prompt_evolution()
    print(f"Results: {json_path}")
    print(f"Summary: {markdown_path}")
    return json_path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate an advice prompt version.")
    parser.add_argument("--prompt", required=True, choices=tuple(PROMPT_FILES))
    parser.add_argument(
        "--max-cases",
        type=int,
        default=MAX_CASES,
        help=f"Run at most this many cases (hard maximum {MAX_CASES}).",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help="Minimum delay between top-level Gemini calls; defaults to 12 seconds.",
    )
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Enable the optional Gemini-as-judge rubric (adds API calls).",
    )
    args = parser.parse_args(argv)
    if not 1 <= args.max_cases <= MAX_CASES:
        parser.error(f"--max-cases must be between 1 and {MAX_CASES}.")
    if args.delay_seconds < DEFAULT_DELAY_SECONDS:
        parser.error(f"--delay-seconds must be at least {DEFAULT_DELAY_SECONDS:g}.")
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        asyncio.run(_run(args))
    except (AdviceServiceError, OSError, RuntimeError, ValueError) as error:
        print(f"Evaluation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
