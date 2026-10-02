"""Run the eval suite: real agent, real tools, real seeded data, scored.

For each case in evals/cases.yaml the runner asks the live agent the merchant
question, records which tools it actually called, and scores two assertions:
expected tools were used, and expected facts appear in the answer. Results go
to stdout and evals/report.md.

    .venv/Scripts/python evals/run_evals.py [--filter case_id]
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agent.runner import (
    DEFAULT_MODEL_ID,
    make_agent,
    start_mcp_client,
    used_tool_names,
)

CASES_PATH = Path(__file__).resolve().parent / "cases.yaml"
REPORT_PATH = Path(__file__).resolve().parent / "report.md"


def load_cases(filter_id: str | None) -> list[dict]:
    cases = yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))["cases"]
    if filter_id:
        cases = [case for case in cases if case["id"] == filter_id]
    if not cases:
        raise SystemExit(f"no eval cases matched filter {filter_id!r}")
    return cases


def score(case: dict, answer: str, used: set[str]) -> tuple[bool, list[str], list[str]]:
    missing_tools = [tool for tool in case.get("expected_tools", []) if tool not in used]
    missing_mentions = [
        mention for mention in case.get("must_mention", []) if mention.casefold() not in answer.casefold()
    ]
    return (not missing_tools and not missing_mentions), missing_tools, missing_mentions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--filter", default=None, help="run only the case with this id")
    args = parser.parse_args()

    logging.basicConfig(level=logging.ERROR)
    cases = load_cases(args.filter)

    client = start_mcp_client()
    rows: list[dict] = []
    try:
        tools = client.list_tools_sync()
        for case in cases:
            agent = make_agent(tools)
            started = time.perf_counter()
            # A crashing case is itself a failing case: capture and continue.
            try:
                result = agent(case["question"])
                answer = str(result).strip()
                used = used_tool_names(result)
                error = None
            except Exception as exc:  # noqa: BLE001
                answer, used, error = "", set(), f"{type(exc).__name__}: {str(exc)[:120]}"
            passed, missing_tools, missing_mentions = score(case, answer, used)
            rows.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "passed": passed and error is None,
                    "used": sorted(used),
                    "missing_tools": missing_tools,
                    "missing_mentions": missing_mentions,
                    "answer": answer,
                    "error": error,
                    "seconds": round(time.perf_counter() - started, 1),
                }
            )
            status = "PASS" if rows[-1]["passed"] else "FAIL"
            print(f"{status}  {case['id']}  ({rows[-1]['seconds']}s)")
    finally:
        client.stop(None, None, None)

    passed_count = sum(1 for row in rows if row["passed"])
    total = len(rows)
    print(f"\n{passed_count}/{total} cases passed ({round(100 * passed_count / total)}%)")

    write_report(rows, passed_count, total)
    print(f"report written to {REPORT_PATH.relative_to(REPO_ROOT)}")
    return 1 if passed_count < total else 0


def write_report(rows: list[dict], passed_count: int, total: int) -> None:
    lines = [
        "# Eval report",
        "",
        (
            f"Run: {datetime.now(UTC).isoformat(timespec='seconds')} | "
            f"model: {DEFAULT_MODEL_ID} | result: {passed_count}/{total} passed"
        ),
        "",
        "| Case | Result | Tools used | Notes |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        result = "PASS" if row["passed"] else "FAIL"
        notes = []
        if row["error"]:
            notes.append(f"error: {row['error']}")
        if row["missing_tools"]:
            notes.append(f"missing tools: {', '.join(row['missing_tools'])}")
        if row["missing_mentions"]:
            notes.append(f"missing mentions: {', '.join(row['missing_mentions'])}")
        lines.append(
            f"| {row['id']} | {result} | {', '.join(row['used']) or '-'} | {'; '.join(notes) or '-'} |"
        )
    lines += ["", "## Answers", ""]
    for row in rows:
        lines += [f"### {row['id']} ({'PASS' if row['passed'] else 'FAIL'})", "", f"> {row['question']}", "", row["answer"] or "(no answer)", ""]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
