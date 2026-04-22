#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import lint_chapter_text as lint_module
import runner as runner_module


EXPORTED_DIRS = (
    "input",
    "premise",
    "outline",
    "chapters",
    "context",
    "reviews",
    "findings",
    "gate",
    "packets",
    "revisions",
    "snapshots",
    "reports",
    "status",
)

EXPORTED_TOP_LEVEL_FILES = (
    "FINAL_NOVEL.md",
    "FINAL_NOVEL.manual_rescue.md",
    "FINAL_NOVEL.posthoc_revision.md",
)

STAGE_PROFILE_EXPORT_KEYS = (
    "outline",
    "outline_revision",
    "spatial_layout",
    "draft",
    "review",
    "full_review",
    "cross_chapter_audit",
    "local_window_audit",
    "llm_aggregator",
    "revision",
)

STAGE_PROFILE_FALLBACKS = {
    "outline_revision": "outline",
    "spatial_layout": "outline",
    "local_window_audit": "cross_chapter_audit",
    "llm_aggregator": "revision",
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise runner_module.PipelineError(f"required file not found: {path}")
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise runner_module.PipelineError(f"failed to parse JSON: {path}") from exc
    if not isinstance(loaded, dict):
        raise runner_module.PipelineError(f"expected object JSON: {path}")
    return loaded


def _artifact_slug(text: str) -> str:
    return runner_module.slugify(text).replace("-", "_")


def _read_title(run_dir: Path) -> str:
    title_path = run_dir / "outline" / "title.txt"
    if title_path.is_file():
        title = title_path.read_text(encoding="utf-8").strip()
        if title:
            return title
    final_novel_path = run_dir / "FINAL_NOVEL.md"
    if final_novel_path.is_file():
        first_line = final_novel_path.read_text(encoding="utf-8").splitlines()[:1]
        if first_line:
            line = first_line[0].strip()
            if line.startswith("# "):
                return line[2:].strip()
    return run_dir.name


def _profile_from_global_config(run_config: dict[str, Any]) -> dict[str, Any]:
    profile: dict[str, Any] = {}
    provider = str(run_config.get("provider", "")).strip()
    model = str(run_config.get("model", "")).strip()
    reasoning_effort = str(run_config.get("reasoning_effort", "")).strip()
    if provider:
        profile["provider"] = provider
    if model:
        profile["model"] = model
    if reasoning_effort:
        profile["reasoning_effort"] = reasoning_effort
    return profile


def _clean_profile(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    cleaned: dict[str, Any] = {}
    for key in ("provider", "model", "reasoning_effort"):
        value = str(raw.get(key, "")).strip()
        if value:
            cleaned[key] = value
    return cleaned


def _resolve_stage_profile(run_config: dict[str, Any], stage_key: str) -> dict[str, Any]:
    stage_profiles = run_config.get("stage_profiles", {})
    if not isinstance(stage_profiles, dict):
        stage_profiles = {}
    profile = _clean_profile(stage_profiles.get(stage_key))
    if profile:
        return profile
    fallback_key = STAGE_PROFILE_FALLBACKS.get(stage_key)
    if fallback_key:
        profile = _clean_profile(stage_profiles.get(fallback_key))
        if profile:
            return profile
    return _profile_from_global_config(run_config)


def _build_generation_metadata(
    run_dir: Path,
    final_status: dict[str, Any],
    run_config: dict[str, Any],
) -> dict[str, Any]:
    title = _read_title(run_dir)
    stages: dict[str, Any] = {
        "premise": {
            "mode": str(run_config.get("premise_mode", "")).strip() or "user",
        }
    }
    for stage_key in STAGE_PROFILE_EXPORT_KEYS:
        profile = _resolve_stage_profile(run_config, stage_key)
        if profile:
            stages[stage_key] = profile
    revision_pass_profiles = run_config.get("revision_pass_profiles", {})
    if not isinstance(revision_pass_profiles, dict):
        revision_pass_profiles = {}
    return {
        "schema_version": 2,
        "title": title,
        "completed_at_utc": final_status.get("completed_at_utc"),
        "exported_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "execution_mode": "stage_profiles",
        "run_status": final_status.get("status"),
        "terminal_reason": final_status.get("terminal_reason"),
        "source_run": str(run_dir.resolve()),
        "final_artifact_source": final_status.get("final_novel_file", "FINAL_NOVEL.md"),
        "chapter_count": final_status.get("chapter_count"),
        "success_cycle": final_status.get("success_cycle"),
        "min_cycles": final_status.get("min_cycles"),
        "max_cycles": final_status.get("max_cycles"),
        "add_cycles": final_status.get("add_cycles", 0),
        "base_completed_cycles": final_status.get("base_completed_cycles", 0),
        "validation_mode": final_status.get("validation_mode"),
        "final_cycle_global_only": bool(run_config.get("final_cycle_global_only", False)),
        "local_window_size": run_config.get("local_window_size"),
        "local_window_overlap": run_config.get("local_window_overlap"),
        "stages": stages,
        "revision_passes": {
            key: _clean_profile(value)
            for key, value in sorted(revision_pass_profiles.items())
            if _clean_profile(value)
        },
        "exported_dirs": list(EXPORTED_DIRS),
    }


def _lint_cycle_number(final_status: dict[str, Any]) -> int:
    success_cycle = final_status.get("success_cycle")
    if isinstance(success_cycle, int) and success_cycle >= 1:
        return success_cycle
    return 1


def _lint_report_path(run_dir: Path, cycle: int) -> Path:
    return run_dir / "logs" / f"cycle_{cycle:02d}" / "lint_report.json"


def _run_export_lint(run_dir: Path, final_status: dict[str, Any]) -> dict[str, Any] | None:
    chapters_dir = run_dir / "chapters"
    if not chapters_dir.is_dir():
        return None
    payload = lint_module.build_report_payload(
        lint_module.lint_chapter_directory(chapters_dir, apply_fixes=False)
    )
    lint_module.write_report(
        _lint_report_path(run_dir, _lint_cycle_number(final_status)),
        payload,
    )
    return payload


def _raise_on_blocking_lint(payload: dict[str, Any]) -> None:
    blocked = lint_module.blocking_findings(payload)
    if not blocked:
        return
    preview = ", ".join(
        f"{row['chapter_id']}:{row['line']}" for row in blocked[:5]
    )
    raise runner_module.PipelineError(
        "export blocked by lint warnings: interrogative dialogue is missing question marks "
        f"at {preview}. Re-run with --allow-lint-warnings to override."
    )


def export_run_to_artifacts(
    run_dir: Path,
    artifacts_root: Path,
    *,
    book_slug: str = "",
    overwrite: bool = False,
    allow_lint_warnings: bool = False,
) -> Path:
    run_dir = run_dir.resolve()
    artifacts_root = artifacts_root.resolve()
    final_status = _load_json(run_dir / "reports" / "final_status.json")
    run_config = _load_json(run_dir / "config" / "run_config.json")
    lint_payload = _run_export_lint(run_dir, final_status)
    if lint_payload is not None and not allow_lint_warnings:
        _raise_on_blocking_lint(lint_payload)
    title = _read_title(run_dir)
    slug = _artifact_slug(book_slug or title)
    dest_dir = artifacts_root / "books" / slug
    if dest_dir.exists():
        if not overwrite:
            raise runner_module.PipelineError(
                f"destination already exists: {dest_dir} (use --overwrite to replace it)"
            )
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    for rel in EXPORTED_TOP_LEVEL_FILES:
        src = run_dir / rel
        if src.is_file():
            shutil.copy2(src, dest_dir / rel)

    for rel in EXPORTED_DIRS:
        src = run_dir / rel
        if not src.exists():
            continue
        shutil.copytree(src, dest_dir / rel)

    metadata = _build_generation_metadata(run_dir, final_status, run_config)
    (dest_dir / "generation_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return dest_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a completed run directory into the companion artifacts repository."
    )
    parser.add_argument("run_dir", help="Path to the completed run directory.")
    parser.add_argument(
        "--artifacts-root",
        default=str(Path(__file__).resolve().parents[2] / "artifacts"),
        help="Path to the artifacts repository root. Default: ../artifacts beside this repo.",
    )
    parser.add_argument(
        "--book-slug",
        default="",
        help="Optional destination slug under books/. Default: derived from outline/title.txt.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the destination book directory if it already exists.",
    )
    parser.add_argument(
        "--allow-lint-warnings",
        action="store_true",
        help="Allow export to proceed even if the deterministic lint report still has question-mark blockers.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir).expanduser()
    artifacts_root = Path(args.artifacts_root).expanduser()
    dest_dir = export_run_to_artifacts(
        run_dir,
        artifacts_root,
        book_slug=args.book_slug,
        overwrite=bool(args.overwrite),
        allow_lint_warnings=bool(args.allow_lint_warnings),
    )
    print(dest_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
