#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


CHAPTER_FILE_RE = re.compile(r"chapter_(\d{2})\.md$")
LIST_MARKER_RE = re.compile(r"^(\s*)(?:[-*]|\d+\.)\s+(.*\S.*)$")
QUOTE_SEGMENT_RE = re.compile(r'["\u201c](.+?)["\u201d]')
WORD_RE = re.compile(r"[A-Za-z']+")

WH_STARTERS = {"what", "where", "when", "why", "who", "how"}
AUXILIARY_STARTERS = {
    "can",
    "do",
    "does",
    "did",
    "is",
    "are",
    "was",
    "were",
    "will",
    "would",
    "should",
    "could",
    "may",
    "have",
    "has",
    "had",
}
EXCLAMATIVE_WH_ARTICLES = {"a", "an", "the"}


def _chapter_sort_key(path: Path) -> tuple[int, str]:
    match = CHAPTER_FILE_RE.search(path.name)
    if match:
        return int(match.group(1)), path.name
    return 10_000, path.name


def _chapter_id_from_path(path: Path) -> str:
    match = CHAPTER_FILE_RE.search(path.name)
    if match:
        return f"chapter_{match.group(1)}"
    return path.stem


def _line_excerpt(line: str) -> str:
    return line.strip()[:160]


def _is_list_context(lines: list[str], index: int, prev_marker_line: bool) -> bool:
    previous_nonblank = ""
    for prev_index in range(index - 1, -1, -1):
        if lines[prev_index].strip():
            previous_nonblank = lines[prev_index].rstrip()
            break
    if previous_nonblank.endswith(":"):
        return True
    if prev_marker_line:
        return True
    next_is_marker = False
    for next_index in range(index + 1, len(lines)):
        if not lines[next_index].strip():
            continue
        next_is_marker = bool(LIST_MARKER_RE.match(lines[next_index]))
        break
    return next_is_marker


def _is_interrogative_dialogue(segment: str) -> bool:
    stripped = segment.strip().lstrip("\u2014-").strip()
    tokens = WORD_RE.findall(stripped)
    if not tokens:
        return False
    first = tokens[0].lower()
    if first in AUXILIARY_STARTERS:
        return True
    if first not in WH_STARTERS:
        return False
    if first == "what" and len(tokens) >= 2 and tokens[1].lower() in EXCLAMATIVE_WH_ARTICLES:
        return False
    if len(tokens) < 3:
        return False
    if first == "what" and len(tokens) >= 3 and tokens[1].lower() in {
        "i",
        "you",
        "he",
        "she",
        "we",
        "they",
    }:
        return False
    if first == "how" and len(tokens) == 3 and tokens[1].lower() in {
        "strange",
        "awful",
        "funny",
        "wild",
    }:
        return False
    return True


def lint_chapter_file(
    chapter_path: Path,
    *,
    apply_fixes: bool = True,
) -> dict[str, Any]:
    original = chapter_path.read_text(encoding="utf-8")
    has_trailing_newline = original.endswith("\n")
    lines = original.splitlines()
    updated_lines = list(lines)
    findings: list[dict[str, Any]] = []

    in_code_block = False
    previous_marker_line = False
    file_modified = False

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            previous_marker_line = False
            continue
        if in_code_block:
            previous_marker_line = False
            continue

        line_number = index + 1
        list_match = LIST_MARKER_RE.match(line)
        if list_match and not stripped.startswith("#"):
            is_contextual_list = _is_list_context(lines, index, previous_marker_line)
            if not is_contextual_list:
                findings.append(
                    {
                        "type": "stray_list_marker",
                        "line": line_number,
                        "excerpt": _line_excerpt(line),
                        "auto_fixed": apply_fixes,
                    }
                )
                if apply_fixes:
                    updated_lines[index] = f"{list_match.group(1)}{list_match.group(2)}"
                    file_modified = True
            previous_marker_line = True
            continue

        previous_marker_line = False

        if '"' not in line and "\u201c" not in line:
            continue
        for segment_match in QUOTE_SEGMENT_RE.finditer(line):
            segment = segment_match.group(1).strip()
            if not segment or segment.endswith("?"):
                continue
            if _is_interrogative_dialogue(segment):
                findings.append(
                    {
                        "type": "interrogative_missing_qmark",
                        "line": line_number,
                        "excerpt": _line_excerpt(segment),
                        "auto_fixed": False,
                    }
                )

    if file_modified:
        rendered = "\n".join(updated_lines)
        if has_trailing_newline:
            rendered += "\n"
        chapter_path.write_text(rendered, encoding="utf-8")

    return {
        "chapter_id": _chapter_id_from_path(chapter_path),
        "findings": findings,
    }


def lint_chapter_directory(
    chapters_dir: Path,
    *,
    apply_fixes: bool = True,
) -> list[dict[str, Any]]:
    chapter_files = sorted(chapters_dir.glob("*.md"), key=_chapter_sort_key)
    return [
        lint_chapter_file(chapter_file, apply_fixes=apply_fixes)
        for chapter_file in chapter_files
    ]


def build_report_payload(chapter_reports: list[dict[str, Any]]) -> dict[str, Any]:
    finding_count = 0
    blocking_finding_count = 0
    auto_fix_count = 0
    for report in chapter_reports:
        for finding in report.get("findings", []):
            finding_count += 1
            if finding.get("auto_fixed"):
                auto_fix_count += 1
            if (
                finding.get("type") == "interrogative_missing_qmark"
                and not finding.get("auto_fixed", False)
            ):
                blocking_finding_count += 1
    return {
        "chapter_reports": chapter_reports,
        "summary": {
            "chapter_count": len(chapter_reports),
            "finding_count": finding_count,
            "blocking_finding_count": blocking_finding_count,
            "auto_fix_count": auto_fix_count,
        },
    }


def blocking_findings(payload: dict[str, Any]) -> list[dict[str, Any]]:
    reports = payload.get("chapter_reports")
    if not isinstance(reports, list) and "chapter_id" in payload:
        reports = [payload]
    if not isinstance(reports, list):
        return []
    blocked: list[dict[str, Any]] = []
    for report in reports:
        if not isinstance(report, dict):
            continue
        chapter_id = str(report.get("chapter_id", "")).strip()
        findings = report.get("findings", [])
        if not isinstance(findings, list):
            continue
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            if (
                finding.get("type") == "interrogative_missing_qmark"
                and not finding.get("auto_fixed", False)
            ):
                blocked.append(
                    {
                        "chapter_id": chapter_id,
                        "line": finding.get("line"),
                        "excerpt": finding.get("excerpt", ""),
                    }
                )
    return blocked


def write_report(output_path: Path, payload: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lint chapter markdown for deterministic punctuation and formatting issues."
    )
    parser.add_argument(
        "input_path",
        help="Path to a chapter markdown file or a directory of chapter markdown files.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional JSON report path. Defaults to stdout.",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Do not auto-fix stray list markers; only report findings.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input_path).expanduser().resolve()
    apply_fixes = not bool(args.report_only)
    if input_path.is_dir():
        payload = build_report_payload(
            lint_chapter_directory(input_path, apply_fixes=apply_fixes)
        )
    elif input_path.is_file():
        payload = lint_chapter_file(input_path, apply_fixes=apply_fixes)
    else:
        raise SystemExit(f"input path not found: {input_path}")

    if args.output:
        write_report(Path(args.output).expanduser(), payload)
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
