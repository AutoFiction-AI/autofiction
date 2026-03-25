#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import runner as runner_mod


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _load_text_if_exists(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _profile_from_source(
    source_run_config: dict[str, Any],
    stage_keys: tuple[str, ...],
) -> dict[str, Any]:
    stage_profiles = source_run_config.get("stage_profiles")
    if not isinstance(stage_profiles, dict):
        return {}
    for stage_key in stage_keys:
        profile = stage_profiles.get(stage_key)
        if isinstance(profile, dict):
            return profile
    return {}


def _resolve_profile(
    *,
    source_run_config: dict[str, Any],
    stage_keys: tuple[str, ...],
    provider_override: str | None,
    agent_bin_override: str | None,
    model_override: str | None,
    effort_override: str | None,
    fallback_provider: str,
    fallback_profile: runner_mod.ExecutionProfile | None = None,
) -> runner_mod.ExecutionProfile:
    source_profile = _profile_from_source(source_run_config, stage_keys)
    source_provider_raw = str(source_profile.get("provider", "")).strip()
    source_provider = (
        runner_mod._resolve_provider(source_provider_raw) if source_provider_raw else ""
    )
    provider_raw = (
        str(provider_override or "").strip()
        or source_provider
        or (fallback_profile.provider if fallback_profile else "")
        or fallback_provider
    )
    provider = runner_mod._resolve_provider(provider_raw)

    same_as_source = bool(source_provider) and source_provider == provider
    same_as_fallback = fallback_profile is not None and fallback_profile.provider == provider

    source_agent_bin = str(source_profile.get("agent_bin", "")).strip() if same_as_source else ""
    source_model = str(source_profile.get("model", "")).strip() if same_as_source else ""
    source_effort = (
        str(source_profile.get("reasoning_effort", "")).strip() if same_as_source else ""
    )

    fallback_agent_bin = fallback_profile.agent_bin if same_as_fallback else ""
    fallback_model = fallback_profile.model if same_as_fallback else ""
    fallback_effort = fallback_profile.reasoning_effort if same_as_fallback else ""

    agent_bin = runner_mod._resolve_agent_bin(
        provider,
        str(agent_bin_override or source_agent_bin or fallback_agent_bin or ""),
    )
    model = runner_mod._resolve_default_model(
        provider,
        str(model_override or source_model or fallback_model or ""),
    )
    effort = runner_mod._resolve_reasoning_effort(
        provider,
        str(effort_override or source_effort or fallback_effort or ""),
    )
    return runner_mod.ExecutionProfile(
        provider=provider,
        agent_bin=agent_bin,
        model=model,
        reasoning_effort=effort,
    )


def _resolve_revision_pass_profiles(
    *,
    source_run_config: dict[str, Any],
    revision_profile: runner_mod.ExecutionProfile,
    preserve_source_profiles: bool,
) -> dict[str, runner_mod.ExecutionProfile]:
    if not preserve_source_profiles:
        return {}
    raw_profiles = source_run_config.get("revision_pass_profiles")
    if not isinstance(raw_profiles, dict):
        return {}

    resolved: dict[str, runner_mod.ExecutionProfile] = {}
    for pass_key, raw_profile in raw_profiles.items():
        if not isinstance(pass_key, str) or not isinstance(raw_profile, dict):
            continue
        provider_raw = str(raw_profile.get("provider", "")).strip() or revision_profile.provider
        provider = runner_mod._resolve_provider(provider_raw)
        same_as_base = provider == revision_profile.provider
        agent_bin = runner_mod._resolve_agent_bin(
            provider,
            str(
                raw_profile.get("agent_bin")
                or (revision_profile.agent_bin if same_as_base else "")
                or ""
            ),
        )
        model = runner_mod._resolve_default_model(
            provider,
            str(
                raw_profile.get("model")
                or (revision_profile.model if same_as_base else "")
                or ""
            ),
        )
        effort = runner_mod._resolve_reasoning_effort(
            provider,
            str(
                raw_profile.get("reasoning_effort")
                or (revision_profile.reasoning_effort if same_as_base else "")
                or ""
            ),
        )
        resolved[pass_key] = runner_mod.ExecutionProfile(
            provider=provider,
            agent_bin=agent_bin,
            model=model,
            reasoning_effort=effort,
        )
    return resolved


def _copy_if_missing(src: Path, dst: Path) -> None:
    if dst.exists():
        return
    if not src.exists():
        raise runner_mod.PipelineError(f"missing required source artifact: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _copy_tree_if_missing(src_root: Path, dst_root: Path) -> None:
    if not src_root.is_dir():
        raise runner_mod.PipelineError(f"missing required source directory: {src_root}")
    for src_path in sorted(src_root.rglob("*")):
        rel = src_path.relative_to(src_root)
        dst_path = dst_root / rel
        if src_path.is_dir():
            dst_path.mkdir(parents=True, exist_ok=True)
            continue
        if dst_path.exists():
            continue
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)


def _resolve_source_run_dir(
    novel_dir: Path,
    explicit_source_run_dir: str,
) -> Path | None:
    raw = explicit_source_run_dir.strip()
    if not raw:
        raw = _load_text_if_exists(novel_dir / "source_run.txt")
    if not raw:
        metadata = _load_json_if_exists(novel_dir / "generation_metadata.json")
        raw = str(metadata.get("source_run", "")).strip()
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def _resolve_baseline_file(novel_dir: Path, explicit_baseline: str) -> Path:
    if explicit_baseline.strip():
        candidate = Path(explicit_baseline).expanduser()
        if not candidate.is_absolute():
            candidate = (novel_dir / candidate).resolve()
        else:
            candidate = candidate.resolve()
        if not candidate.is_file():
            raise runner_mod.PipelineError(f"--baseline-file does not exist: {candidate}")
        return candidate

    candidates = (
        novel_dir / "FINAL_NOVEL.md",
        novel_dir / "FINAL_NOVEL.manual_rescue.md",
        novel_dir / "manual_rescue" / "FINAL_NOVEL.manual_rescue.md",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise runner_mod.PipelineError(
        "could not find a baseline novel file under the generated novel directory"
    )


def _resolve_seed_dir(
    *,
    label: str,
    primary_dir: Path,
    fallback_dir: Path | None,
) -> Path:
    if primary_dir.is_dir():
        return primary_dir
    if fallback_dir and fallback_dir.is_dir():
        return fallback_dir
    raise runner_mod.PipelineError(
        f"missing {label} directory; checked {primary_dir}"
        + (f" and {fallback_dir}" if fallback_dir else "")
    )


def _resolve_seed_file(
    *,
    primary_file: Path,
    fallback_file: Path | None,
) -> Path | None:
    if primary_file.is_file():
        return primary_file
    if fallback_file and fallback_file.is_file():
        return fallback_file
    return None


def _seed_posthoc_inputs(
    *,
    novel_dir: Path,
    source_run_dir: Path | None,
    workspace_dir: Path,
) -> dict[str, Path | None]:
    source_chapters_dir = _resolve_seed_dir(
        label="chapters",
        primary_dir=novel_dir / "chapters",
        fallback_dir=(source_run_dir / "chapters") if source_run_dir else None,
    )
    source_outline_dir = _resolve_seed_dir(
        label="outline",
        primary_dir=novel_dir / "outline",
        fallback_dir=(source_run_dir / "outline") if source_run_dir else None,
    )
    premise_path = _resolve_seed_file(
        primary_file=novel_dir / "input" / "premise.txt",
        fallback_file=(source_run_dir / "input" / "premise.txt") if source_run_dir else None,
    )

    _copy_tree_if_missing(source_chapters_dir, workspace_dir / "chapters")
    _copy_tree_if_missing(source_outline_dir, workspace_dir / "outline")
    if premise_path is not None:
        _copy_if_missing(premise_path, workspace_dir / "input" / "premise.txt")

    return {
        "chapters_dir": source_chapters_dir,
        "outline_dir": source_outline_dir,
        "premise_file": premise_path,
    }


def _render_compiled_novel_text(
    *,
    title: str,
    chapter_specs: list[runner_mod.ChapterSpec],
    chapters_dir: Path,
) -> str:
    parts = [f"# {title}\n\n"]
    for idx, spec in enumerate(chapter_specs):
        chapter_file = chapters_dir / f"{spec.chapter_id}.md"
        if not chapter_file.is_file():
            raise runner_mod.PipelineError(f"missing chapter file for baseline verification: {chapter_file}")
        parts.append(chapter_file.read_text(encoding="utf-8").strip() + "\n")
        if idx != len(chapter_specs) - 1:
            parts.append("\n\n")
    return "".join(parts)


def _verify_baseline_matches_chapters(
    *,
    baseline_file: Path,
    title: str,
    chapter_specs: list[runner_mod.ChapterSpec],
    chapters_dir: Path,
    allow_mismatch: bool,
) -> bool:
    baseline_text = baseline_file.read_text(encoding="utf-8")
    compiled_text = _render_compiled_novel_text(
        title=title,
        chapter_specs=chapter_specs,
        chapters_dir=chapters_dir,
    )
    if baseline_text == compiled_text:
        return True
    if allow_mismatch:
        return False
    raise runner_mod.PipelineError(
        "baseline novel file does not match the seeded chapter files; "
        "use --allow-final-mismatch to proceed anyway"
    )


def _placeholder_chapter_review(chapter_id: str) -> dict[str, Any]:
    return {
        "chapter_id": chapter_id,
        "verdicts": {
            runner_mod.PRIMARY_REVIEW_LENS: "PASS",
            "craft": "PASS",
            "dialogue": "PASS",
            "prose": "PASS",
        },
        "findings": [],
        "summary": "Synthetic PASS chapter review for posthoc review-only baseline seeding.",
    }


def _write_placeholder_chapter_reviews(
    runner: runner_mod.NovelPipelineRunner,
    *,
    cycle: int,
) -> None:
    cpad = runner._cpad(cycle)
    for spec in runner.chapter_specs:
        runner._write_json(
            f"reviews/cycle_{cpad}/{spec.chapter_id}.review.json",
            _placeholder_chapter_review(spec.chapter_id),
        )


def _is_fallback_full_award_review(data: dict[str, Any]) -> bool:
    findings = data.get("findings")
    if not isinstance(findings, list) or len(findings) != 1:
        return False
    finding = findings[0]
    if not isinstance(finding, dict):
        return False
    return str(finding.get("finding_id", "")).strip() == "fallback_full_award_contract"


def _load_validated_full_award(
    runner: runner_mod.NovelPipelineRunner,
    *,
    cycle: int,
) -> dict[str, Any]:
    cpad = runner._cpad(cycle)
    rel = f"reviews/cycle_{cpad}/full_award.review.json"
    full_novel_file = f"snapshots/cycle_{cpad}/FINAL_NOVEL.md"
    chapter_ids = {spec.chapter_id for spec in runner.chapter_specs}
    data = runner._load_repaired_full_award_review(rel, cycle, chapter_ids, full_novel_file)
    runner._validate_full_award_review_json(data, cycle, chapter_ids, rel, full_novel_file)
    return data


def _load_validated_cross_chapter_audit(
    runner: runner_mod.NovelPipelineRunner,
    *,
    cycle: int,
) -> dict[str, Any]:
    cpad = runner._cpad(cycle)
    rel = runner._cross_chapter_audit_rel(cycle)
    full_novel_file = f"snapshots/cycle_{cpad}/FINAL_NOVEL.md"
    chapter_ids = {spec.chapter_id for spec in runner.chapter_specs}
    data = runner._load_repaired_cross_chapter_audit(rel, cycle, chapter_ids, full_novel_file)
    runner._validate_cross_chapter_audit_json(data, cycle, chapter_ids, rel, full_novel_file)
    return data


def _build_posthoc_runner(
    *,
    repo_root: Path,
    workspace_dir: Path,
    source_run_config: dict[str, Any],
    premise: str,
    max_parallel_revisions: int,
    validation_mode: str,
    job_timeout_seconds: int,
    job_idle_timeout_seconds: int,
    dry_run: bool,
    skip_cross_chapter_audit: bool,
    review_provider: str | None,
    review_agent_bin: str | None,
    review_model: str | None,
    review_effort: str | None,
    audit_provider: str | None,
    audit_agent_bin: str | None,
    audit_model: str | None,
    audit_effort: str | None,
    revision_provider: str | None,
    revision_agent_bin: str | None,
    revision_model: str | None,
    revision_effort: str | None,
) -> runner_mod.NovelPipelineRunner:
    revision_override_present = any(
        bool(str(value or "").strip())
        for value in (
            revision_provider,
            revision_agent_bin,
            revision_model,
            revision_effort,
        )
    )
    revision_profile = _resolve_profile(
        source_run_config=source_run_config,
        stage_keys=("revision",),
        provider_override=revision_provider,
        agent_bin_override=revision_agent_bin,
        model_override=revision_model,
        effort_override=revision_effort,
        fallback_provider="codex",
    )
    full_review_profile = _resolve_profile(
        source_run_config=source_run_config,
        stage_keys=("full_review",),
        provider_override=review_provider,
        agent_bin_override=review_agent_bin,
        model_override=review_model,
        effort_override=review_effort,
        fallback_provider="claude",
    )
    audit_profile = _resolve_profile(
        source_run_config=source_run_config,
        stage_keys=("cross_chapter_audit", "full_review"),
        provider_override=audit_provider,
        agent_bin_override=audit_agent_bin,
        model_override=audit_model,
        effort_override=audit_effort,
        fallback_provider=full_review_profile.provider,
        fallback_profile=full_review_profile,
    )

    revision_pass_profiles = _resolve_revision_pass_profiles(
        source_run_config=source_run_config,
        revision_profile=revision_profile,
        preserve_source_profiles=not revision_override_present,
    )

    stage_profiles = {
        stage_group: revision_profile for stage_group in runner_mod.STAGE_GROUP_VALUES
    }
    stage_profiles["full_review"] = full_review_profile
    stage_profiles["cross_chapter_audit"] = audit_profile
    stage_profiles["revision"] = revision_profile

    source_award_profile = str(source_run_config.get("award_profile", "")).strip()
    max_parallel_reviews = int(source_run_config.get("max_parallel_reviews", 0) or 0) or 2
    cfg = runner_mod.RunnerConfig(
        premise=premise or None,
        premise_mode="user",
        premise_brief=None,
        award_profile=source_award_profile or "major-award",
        premise_seed=None,
        premise_reroll_max=0,
        premise_candidate_count=1,
        premise_generation_batch_size=1,
        premise_min_unique_clusters=1,
        premise_shortlist_size=1,
        run_dir=workspace_dir,
        max_cycles=1,
        min_cycles=1,
        max_parallel_drafts=1,
        max_parallel_reviews=max_parallel_reviews,
        max_parallel_revisions=max_parallel_revisions,
        provider=revision_profile.provider,
        agent_bin=revision_profile.agent_bin,
        model=revision_profile.model,
        reasoning_effort=revision_profile.reasoning_effort,
        stage_profiles=stage_profiles,
        revision_pass_profiles=revision_pass_profiles,
        dry_run=dry_run,
        dry_run_chapter_count=0,
        job_timeout_seconds=job_timeout_seconds,
        job_idle_timeout_seconds=job_idle_timeout_seconds,
        validation_mode=validation_mode,
        skip_cross_chapter_audit=skip_cross_chapter_audit,
    )
    return runner_mod.NovelPipelineRunner(repo_root=repo_root, cfg=cfg)


def _write_posthoc_summary(
    *,
    workspace_dir: Path,
    novel_dir: Path,
    baseline_file: Path,
    source_run_dir: Path | None,
    runner: runner_mod.NovelPipelineRunner,
    aggregate: dict[str, Any],
    review_only: bool,
    baseline_match_verified: bool,
) -> None:
    cpad = runner._cpad(1)
    audit_rel = runner._cross_chapter_audit_rel(1)
    summary = {
        "generated_novel_dir": str(novel_dir),
        "baseline_file": str(baseline_file),
        "source_run_dir": str(source_run_dir) if source_run_dir else None,
        "workspace_dir": str(workspace_dir),
        "cycle": 1,
        "review_only": review_only,
        "skip_cross_chapter_audit": runner.cfg.skip_cross_chapter_audit,
        "baseline_match_verified": baseline_match_verified,
        "compiled_novel_file": "FINAL_NOVEL.posthoc_revision.md",
        "full_review_file": f"reviews/cycle_{cpad}/full_award.review.json",
        "cross_chapter_audit_file": None if runner.cfg.skip_cross_chapter_audit else audit_rel,
        "chapters_touched": aggregate["summary"]["chapters_touched"],
        "finding_counts": {
            "total_unresolved_medium_plus": aggregate["summary"]["total_unresolved_medium_plus"],
            "by_severity": aggregate["summary"]["by_severity"],
            "by_source": aggregate["summary"]["by_source"],
        },
        "full_award_verdict": aggregate["full_award_verdict"],
        "cross_chapter_audit_failed": bool(
            aggregate.get("cross_chapter_audit_failed", False)
        ),
        "stage_profiles": {
            key: {
                "provider": profile.provider,
                "agent_bin": profile.agent_bin,
                "model": profile.model,
                "reasoning_effort": profile.reasoning_effort,
            }
            for key, profile in sorted(runner.cfg.stage_profiles.items())
            if key in {"full_review", "cross_chapter_audit", "revision"}
        },
        "revision_pass_profiles": {
            key: {
                "provider": profile.provider,
                "agent_bin": profile.agent_bin,
                "model": profile.model,
                "reasoning_effort": profile.reasoning_effort,
            }
            for key, profile in sorted(runner.cfg.revision_pass_profiles.items())
        },
    }
    report_dir = workspace_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "posthoc_revision_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a fresh full-book review, cross-chapter audit, and rescue-style revision "
            "pass against an exported novel directory under generated_novels."
        )
    )
    parser.add_argument(
        "novel_dir",
        help="Path to an exported novel directory (for example a book directory from the companion artifacts repo).",
    )
    parser.add_argument(
        "--workspace-name",
        default="posthoc_revision",
        help="Subdirectory to create inside the generated novel directory. Default: posthoc_revision",
    )
    parser.add_argument(
        "--source-run-dir",
        default="",
        help="Optional source run dir override. Default: infer from source_run.txt or generation_metadata.json.",
    )
    parser.add_argument(
        "--baseline-file",
        default="",
        help="Optional baseline novel file override. Default: FINAL_NOVEL.md, then FINAL_NOVEL.manual_rescue.md.",
    )
    parser.add_argument(
        "--allow-final-mismatch",
        action="store_true",
        help="Proceed even if the selected baseline novel does not exactly match the seeded chapter files.",
    )
    parser.add_argument(
        "--review-only",
        action="store_true",
        help="Run the review stages and aggregation only; skip revision.",
    )
    parser.add_argument(
        "--skip-cross-chapter-audit",
        action="store_true",
        help="Skip the new cross-chapter audit stage.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use runner mock outputs instead of calling providers.",
    )
    parser.add_argument(
        "--max-parallel-revisions",
        type=int,
        default=0,
        help="Parallel revisions. Default: reuse source run setting, else 4.",
    )
    parser.add_argument(
        "--validation-mode",
        default="",
        help="Validation mode. Default: reuse source run setting, else balanced.",
    )
    parser.add_argument(
        "--job-timeout-seconds",
        type=int,
        default=3600,
        help="Wall-clock timeout per job. Default: 3600.",
    )
    parser.add_argument(
        "--job-idle-timeout-seconds",
        type=int,
        default=1800,
        help="Idle timeout per job. Default: 1800.",
    )
    parser.add_argument("--review-provider", default="")
    parser.add_argument("--review-agent-bin", default="")
    parser.add_argument("--review-model", default="")
    parser.add_argument("--review-effort", default="")
    parser.add_argument("--audit-provider", default="")
    parser.add_argument("--audit-agent-bin", default="")
    parser.add_argument("--audit-model", default="")
    parser.add_argument("--audit-effort", default="")
    parser.add_argument("--revision-provider", default="")
    parser.add_argument("--revision-agent-bin", default="")
    parser.add_argument("--revision-model", default="")
    parser.add_argument("--revision-effort", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    novel_dir = Path(args.novel_dir).expanduser().resolve()
    if not novel_dir.is_dir():
        raise runner_mod.PipelineError(f"generated novel directory does not exist: {novel_dir}")

    source_run_dir = _resolve_source_run_dir(novel_dir, str(args.source_run_dir))
    source_run_config: dict[str, Any] = {}
    if source_run_dir and (source_run_dir / "config" / "run_config.json").is_file():
        source_run_config = _load_json_if_exists(source_run_dir / "config" / "run_config.json")

    source_parallel = int(source_run_config.get("max_parallel_revisions", 0) or 0)
    max_parallel_revisions = args.max_parallel_revisions or source_parallel or 4
    validation_mode = (
        str(args.validation_mode).strip().lower()
        or str(source_run_config.get("validation_mode", "")).strip().lower()
        or "balanced"
    )
    if validation_mode not in runner_mod.VALIDATION_MODES:
        allowed = ", ".join(sorted(runner_mod.VALIDATION_MODES))
        raise runner_mod.PipelineError(f"--validation-mode must be one of: {allowed}")
    if max_parallel_revisions < 1:
        raise runner_mod.PipelineError("--max-parallel-revisions must be >= 1")

    baseline_file = _resolve_baseline_file(novel_dir, str(args.baseline_file))
    workspace_dir = novel_dir / str(args.workspace_name).strip()
    workspace_dir.mkdir(parents=True, exist_ok=True)

    seed_info = _seed_posthoc_inputs(
        novel_dir=novel_dir,
        source_run_dir=source_run_dir,
        workspace_dir=workspace_dir,
    )
    premise = _load_text_if_exists(workspace_dir / "input" / "premise.txt")

    runner = _build_posthoc_runner(
        repo_root=repo_root,
        workspace_dir=workspace_dir,
        source_run_config=source_run_config,
        premise=premise,
        max_parallel_revisions=max_parallel_revisions,
        validation_mode=validation_mode,
        job_timeout_seconds=args.job_timeout_seconds,
        job_idle_timeout_seconds=args.job_idle_timeout_seconds,
        dry_run=bool(args.dry_run),
        skip_cross_chapter_audit=bool(args.skip_cross_chapter_audit),
        review_provider=str(args.review_provider).strip() or None,
        review_agent_bin=str(args.review_agent_bin).strip() or None,
        review_model=str(args.review_model).strip() or None,
        review_effort=str(args.review_effort).strip() or None,
        audit_provider=str(args.audit_provider).strip() or None,
        audit_agent_bin=str(args.audit_agent_bin).strip() or None,
        audit_model=str(args.audit_model).strip() or None,
        audit_effort=str(args.audit_effort).strip() or None,
        revision_provider=str(args.revision_provider).strip() or None,
        revision_agent_bin=str(args.revision_agent_bin).strip() or None,
        revision_model=str(args.revision_model).strip() or None,
        revision_effort=str(args.revision_effort).strip() or None,
    )

    runner._prepare_run_dir()
    runner.selected_premise = premise
    runner.premise_source = "user" if premise else ""
    runner.chapter_specs = runner._load_and_validate_chapter_specs()
    runner.style_bible = runner._load_and_validate_style_bible()
    runner.novel_title = runner._load_title()

    baseline_match_verified = _verify_baseline_matches_chapters(
        baseline_file=baseline_file,
        title=runner.novel_title,
        chapter_specs=runner.chapter_specs,
        chapters_dir=seed_info["chapters_dir"],
        allow_mismatch=bool(args.allow_final_mismatch),
    )

    runner._assemble_snapshot(1)
    runner._build_cycle_context_packs(1)
    _write_placeholder_chapter_reviews(runner, cycle=1)

    print(
        "[posthoc-revision] novel_dir="
        f"{novel_dir} workspace_dir={workspace_dir} baseline={baseline_file}"
    )
    print(
        "[posthoc-revision] full_review_provider="
        f"{runner.cfg.stage_profiles['full_review'].provider} "
        f"audit_provider={runner.cfg.stage_profiles['cross_chapter_audit'].provider} "
        f"revision_provider={runner.cfg.stage_profiles['revision'].provider}"
    )
    print(
        "[posthoc-revision] step=full_book_reviews "
        f"cross_chapter_audit={'off' if runner.cfg.skip_cross_chapter_audit else 'on'} "
        f"cycle={runner._cpad(1)}"
    )
    runner._run_parallel_full_book_review_stages(1)

    full_review = _load_validated_full_award(runner, cycle=1)
    if _is_fallback_full_award_review(full_review):
        raise runner_mod.PipelineError(
            "full-book review fell back to a synthetic payload; refusing to continue with posthoc revision"
        )
    if not runner.cfg.skip_cross_chapter_audit:
        audit_data = _load_validated_cross_chapter_audit(runner, cycle=1)
        if runner._is_cross_chapter_audit_fallback_payload(audit_data, 1):
            raise runner_mod.PipelineError(
                "cross-chapter audit fell back to a synthetic payload; refusing to continue with posthoc revision"
            )

    print("[posthoc-revision] step=aggregate_findings")
    aggregate = runner._aggregate_findings(1)
    if aggregate.get("cross_chapter_audit_failed", False):
        raise runner_mod.PipelineError(
            "cross-chapter audit was marked failed during aggregation; refusing to continue"
        )
    touched_chapters = aggregate["summary"]["chapters_touched"]

    if args.review_only:
        print("[posthoc-revision] review-only mode; skipping revisions")
    elif touched_chapters:
        print(
            "[posthoc-revision] step=build_revision_packets "
            f"chapters={len(touched_chapters)}"
        )
        runner._build_revision_packets(1, aggregate["by_chapter"])
        print(
            "[posthoc-revision] step=revise_chapters "
            f"chapters={len(touched_chapters)} concurrency={max_parallel_revisions}"
        )
        runner._run_revision_stage(1, touched_chapters)
    else:
        print("[posthoc-revision] no actionable findings; skipping revisions")

    runner._assemble_post_revision_snapshot(1)
    runner._build_post_revision_boundary_context(
        1, [spec.chapter_id for spec in runner.chapter_specs]
    )
    compiled_path = workspace_dir / "FINAL_NOVEL.posthoc_revision.md"
    post_revision_novel = workspace_dir / "snapshots" / "cycle_01" / "FINAL_NOVEL.post_revision.md"
    compiled_path.write_text(post_revision_novel.read_text(encoding="utf-8"), encoding="utf-8")

    _write_posthoc_summary(
        workspace_dir=workspace_dir,
        novel_dir=novel_dir,
        baseline_file=baseline_file,
        source_run_dir=source_run_dir,
        runner=runner,
        aggregate=aggregate,
        review_only=bool(args.review_only),
        baseline_match_verified=baseline_match_verified,
    )

    print("[posthoc-revision] complete")
    print(
        "[posthoc-revision] full_review="
        f"{workspace_dir / 'reviews' / 'cycle_01' / 'full_award.review.json'}"
    )
    if not runner.cfg.skip_cross_chapter_audit:
        print(
            "[posthoc-revision] cross_chapter_audit="
            f"{workspace_dir / runner._cross_chapter_audit_rel(1)}"
        )
    print(f"[posthoc-revision] compiled_novel={compiled_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except runner_mod.PipelineError as exc:
        print(f"[posthoc-revision][error] {exc}", file=sys.stderr)
        raise SystemExit(1)
