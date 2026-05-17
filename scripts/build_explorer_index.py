#!/usr/bin/env python3
"""Build an index manifest for the pipeline explorer HTML.

Walks runs/* and prompts/ and writes runs/_explorer_index.json with metadata
that pipeline_explorer.html consumes (so the static page can fetch only what
the user clicks instead of slurping every artifact at load time).

Usage:
    python scripts/build_explorer_index.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / "runs"
PROMPTS = REPO / "prompts"
OUT = RUNS / "_explorer_index.json"

CYCLE_RE = re.compile(r"^cycle_(\d+)$")
CHAPTER_RE = re.compile(r"^chapter_(\d+)\.md$")


def list_dir(p: Path) -> list[str]:
    if not p.is_dir():
        return []
    return sorted(x.name for x in p.iterdir() if not x.name.startswith("."))


def file_meta(p: Path, root: Path) -> dict | None:
    if not p.exists() or not p.is_file():
        return None
    return {
        "path": str(p.relative_to(root)).replace("\\", "/"),
        "size": p.stat().st_size,
    }


def maybe(p: Path, root: Path) -> str | None:
    return str(p.relative_to(root)).replace("\\", "/") if p.exists() else None


def collect_chapter_revision_files(rev_dir: Path, run_root: Path, ch_id: str) -> dict:
    """Find aggregate + per-pass revision report files for a chapter."""
    out: dict[str, str | None] = {
        "aggregate": None,
        "p1_structural_craft": None,
        "p2_dialogue_idiolect_cadence": None,
        "p3_prose_copyedit": None,
    }
    if not rev_dir.is_dir():
        return out
    for f in rev_dir.iterdir():
        n = f.name
        if not n.startswith(f"{ch_id}.") or not n.endswith(".revision_report.json"):
            continue
        if n == f"{ch_id}.revision_report.json":
            out["aggregate"] = maybe(f, run_root)
        elif ".p1_structural_craft." in n:
            out["p1_structural_craft"] = maybe(f, run_root)
        elif ".p2_dialogue_idiolect_cadence." in n:
            out["p2_dialogue_idiolect_cadence"] = maybe(f, run_root)
        elif ".p3_prose_copyedit." in n:
            out["p3_prose_copyedit"] = maybe(f, run_root)
    return out


def collect_chapter_packet_files(pkt_dir: Path, run_root: Path, ch_id: str) -> dict:
    out: dict[str, str | None] = {
        "aggregate": None,
        "p1_structural_craft": None,
        "p2_dialogue_idiolect_cadence": None,
        "p3_prose_copyedit": None,
    }
    if not pkt_dir.is_dir():
        return out
    for f in pkt_dir.iterdir():
        n = f.name
        if not n.startswith(f"{ch_id}.") or not n.endswith(".revision_packet.json"):
            continue
        if n == f"{ch_id}.revision_packet.json":
            out["aggregate"] = maybe(f, run_root)
        elif ".p1_structural_craft." in n:
            out["p1_structural_craft"] = maybe(f, run_root)
        elif ".p2_dialogue_idiolect_cadence." in n:
            out["p2_dialogue_idiolect_cadence"] = maybe(f, run_root)
        elif ".p3_prose_copyedit." in n:
            out["p3_prose_copyedit"] = maybe(f, run_root)
    return out


def discover_chapter_ids(run_root: Path) -> list[str]:
    snap_root = run_root / "snapshots"
    ch_ids: set[str] = set()
    if snap_root.is_dir():
        for cycle_dir in snap_root.iterdir():
            ch_dir = cycle_dir / "chapters"
            if ch_dir.is_dir():
                for f in ch_dir.iterdir():
                    m = CHAPTER_RE.match(f.name)
                    if m:
                        ch_ids.add(f"chapter_{m.group(1)}")
    final_ch = run_root / "chapters"
    if final_ch.is_dir():
        for f in final_ch.iterdir():
            m = CHAPTER_RE.match(f.name)
            if m:
                ch_ids.add(f"chapter_{m.group(1)}")
    return sorted(ch_ids)


def index_cycle(run_root: Path, cycle_dir_name: str) -> dict:
    cycle = {"id": cycle_dir_name}
    snap_dir = run_root / "snapshots" / cycle_dir_name
    rev_dir = run_root / "reviews" / cycle_dir_name
    pkt_dir = run_root / "packets" / cycle_dir_name
    revs_dir = run_root / "revisions" / cycle_dir_name
    fnd_dir = run_root / "findings" / cycle_dir_name
    gate_path = run_root / "gate" / cycle_dir_name / "gate.json"
    status_path = run_root / "status" / cycle_dir_name / "cycle_status.json"
    ctx_dir = run_root / "context" / cycle_dir_name

    cycle["snapshot"] = {
        "manifest_pre": maybe(snap_dir / "snapshot_manifest.json", run_root),
        "manifest_post": maybe(snap_dir / "snapshot_manifest.post_revision.json", run_root),
        "final_novel_pre_review": maybe(snap_dir / "FINAL_NOVEL.pre_review.md", run_root),
        "final_novel_post_revision": maybe(snap_dir / "FINAL_NOVEL.post_revision.md", run_root),
        "final_novel": maybe(snap_dir / "FINAL_NOVEL.md", run_root),
    }

    chapters: dict[str, dict] = {}
    for ch_id in discover_chapter_ids(run_root):
        snap_pre = snap_dir / "chapters" / f"{ch_id}.md"
        snap_post = snap_dir / "post_revision" / "chapters" / f"{ch_id}.md"
        review_path = rev_dir / f"{ch_id}.review.json"
        chapters[ch_id] = {
            "snapshot_pre": maybe(snap_pre, run_root),
            "snapshot_post": maybe(snap_post, run_root),
            "review": maybe(review_path, run_root),
            "packets": collect_chapter_packet_files(pkt_dir, run_root, ch_id),
            "revisions": collect_chapter_revision_files(revs_dir, run_root, ch_id),
        }
    cycle["chapters"] = chapters

    # Cross-chapter / global review artifacts
    cycle["full_award_review"] = maybe(rev_dir / "full_award.review.json", run_root)
    cycle["full_award_review_invalid"] = maybe(rev_dir / "full_award.review.invalid.original.json", run_root)
    cycle["cross_chapter_audit"] = maybe(rev_dir / "cross_chapter_audit.json", run_root)
    cycle["cross_chapter_audit_invalid"] = maybe(rev_dir / "cross_chapter_audit.invalid.original.json", run_root)
    cycle["continuity_conflicts"] = maybe(rev_dir / "continuity_conflicts.json", run_root)
    cycle["local_windows"] = []
    if rev_dir.is_dir():
        for f in sorted(rev_dir.iterdir()):
            if f.name.startswith("local_window_") and f.suffix == ".json":
                cycle["local_windows"].append(maybe(f, run_root))

    cycle["findings"] = {
        "all": maybe(fnd_dir / "all_findings.jsonl", run_root),
        "summary": maybe(fnd_dir / "summary.json", run_root),
        "target_list": maybe(fnd_dir / "chapter_target_list.txt", run_root),
    }
    cycle["aggregation_decisions"] = maybe(pkt_dir / "aggregation_decisions.json", run_root)
    cycle["aggregator_input"] = maybe(pkt_dir / "compact_aggregator_input.json", run_root)
    cycle["gate"] = maybe(gate_path, run_root)
    cycle["status"] = maybe(status_path, run_root)
    cycle["context"] = {
        "global": maybe(ctx_dir / "global_cycle_context.json", run_root),
        "continuity_sheet": maybe(ctx_dir / "continuity_sheet.json", run_root),
        "chapter_line_index": maybe(ctx_dir / "chapter_line_index.json", run_root),
        "boundary_dir": str((ctx_dir / "boundary").relative_to(run_root)).replace("\\", "/")
        if (ctx_dir / "boundary").is_dir() else None,
    }
    return cycle


def index_manifests(run_root: Path) -> list[dict]:
    """Collect job manifests with parsed metadata."""
    out = []
    mdir = run_root / "manifests"
    if not mdir.is_dir():
        return out
    for f in sorted(mdir.iterdir()):
        if f.suffix != ".json":
            continue
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        out.append({
            "manifest_path": str(f.relative_to(run_root)).replace("\\", "/"),
            "job_id": data.get("job_id"),
            "stage": data.get("stage"),
            "stage_group": data.get("stage_group"),
            "cycle": data.get("cycle"),
            "chapter_id": data.get("chapter_id"),
            "provider": data.get("provider"),
            "model": data.get("model"),
            "reasoning_effort": data.get("reasoning_effort"),
            "allowed_inputs": data.get("allowed_inputs", []),
            "required_outputs": data.get("required_outputs", []),
        })
    return out


def index_logs(run_root: Path) -> list[dict]:
    out = []
    ldir = run_root / "logs" / "jobs"
    if not ldir.is_dir():
        return out
    seen_jobs: set[str] = set()
    for f in sorted(ldir.iterdir()):
        # group by job_id (everything before the suffix .jsonl/.last_message.txt/.stderr.txt)
        name = f.name
        for suffix in (".jsonl", ".last_message.txt", ".stderr.txt"):
            if name.endswith(suffix):
                job_id = name[: -len(suffix)]
                if job_id in seen_jobs:
                    break
                seen_jobs.add(job_id)
                jsonl = ldir / f"{job_id}.jsonl"
                lastmsg = ldir / f"{job_id}.last_message.txt"
                stderr = ldir / f"{job_id}.stderr.txt"
                out.append({
                    "job_id": job_id,
                    "jsonl": maybe(jsonl, run_root),
                    "last_message": maybe(lastmsg, run_root),
                    "stderr": maybe(stderr, run_root),
                })
                break
    return out


def index_outline(run_root: Path) -> dict:
    o = run_root / "outline"
    if not o.is_dir():
        return {}
    files = {
        "outline_md": maybe(o / "outline.md", run_root),
        "chapter_specs_jsonl": maybe(o / "chapter_specs.jsonl", run_root),
        "scene_plan_tsv": maybe(o / "scene_plan.tsv", run_root),
        "style_bible": maybe(o / "style_bible.json", run_root),
        "static_story_context": maybe(o / "static_story_context.json", run_root),
        "continuity_sheet": maybe(o / "continuity_sheet.json", run_root),
        "continuity_sheet_outline": maybe(o / "continuity_sheet.outline.json", run_root),
        "spatial_layout": maybe(o / "spatial_layout.json", run_root),
        "title": maybe(o / "title.txt", run_root),
    }
    # outline review/revision iterations
    files["reviews"] = sorted(
        maybe(f, run_root) for f in o.glob("outline_review_cycle_*.json") if maybe(f, run_root)
    )
    files["revisions"] = sorted(
        maybe(f, run_root) for f in o.glob("outline_revision_cycle_*.json") if maybe(f, run_root)
    )
    # per-chapter spec files
    specs_dir = o / "chapter_specs"
    files["chapter_specs"] = (
        sorted(str(p.relative_to(run_root)).replace("\\", "/") for p in specs_dir.iterdir() if p.suffix == ".json")
        if specs_dir.is_dir() else []
    )
    return files


def index_premise(run_root: Path) -> dict:
    p = run_root / "premise"
    inp = run_root / "input"
    out = {
        "input_premise": maybe(inp / "premise.txt", run_root),
        "search_plan": maybe(p / "premise_search_plan.json", run_root),
        "candidates": maybe(p / "premise_candidates.jsonl", run_root),
        "uniqueness_clusters": maybe(p / "uniqueness_clusters.json", run_root),
        "selection": maybe(p / "selection.json", run_root),
        "brainstorming": maybe(p / "premise_brainstorming.md", run_root),
    }
    return out


def index_run(run_root: Path) -> dict:
    title_txt = run_root / "outline" / "title.txt"
    title = title_txt.read_text().strip() if title_txt.exists() else run_root.name
    cycle_names = sorted(
        (d.name for d in (run_root / "snapshots").iterdir() if d.is_dir() and CYCLE_RE.match(d.name))
        if (run_root / "snapshots").is_dir() else [],
        key=lambda n: int(CYCLE_RE.match(n).group(1)),
    )
    chapters = discover_chapter_ids(run_root)
    cycles = [index_cycle(run_root, cn) for cn in cycle_names]

    return {
        "id": run_root.name,
        "title": title or run_root.name,
        "chapters": chapters,
        "premise": index_premise(run_root),
        "outline": index_outline(run_root),
        "cycles": cycles,
        "final_novel": maybe(run_root / "FINAL_NOVEL.md", run_root),
        "final_report": maybe(run_root / "reports" / "final_report.json", run_root),
        "final_status": maybe(run_root / "reports" / "final_status.json", run_root),
        "validation_warnings": maybe(run_root / "reports" / "validation_warnings.json", run_root),
        "manifests": index_manifests(run_root),
        "logs": index_logs(run_root),
    }


def main() -> None:
    if not RUNS.is_dir():
        raise SystemExit(f"runs/ directory not found at {RUNS}")
    runs = {}
    for run_dir in sorted(RUNS.iterdir()):
        if not run_dir.is_dir() or run_dir.name.startswith("_") or run_dir.name.startswith("."):
            continue
        runs[run_dir.name] = index_run(run_dir)

    shared_prompts = []
    if PROMPTS.is_dir():
        for f in sorted(PROMPTS.iterdir()):
            if f.suffix == ".md":
                shared_prompts.append({
                    "name": f.name,
                    "path": str(f.relative_to(REPO)).replace("\\", "/"),
                    "size": f.stat().st_size,
                })

    payload = {
        "runs": runs,
        "shared_prompts": shared_prompts,
        "default_run": "the_arabic_room" if "the_arabic_room" in runs else next(iter(runs), None),
    }
    OUT.write_text(json.dumps(payload, indent=2))
    print(f"wrote {OUT.relative_to(REPO)} with {len(runs)} run(s)")


if __name__ == "__main__":
    main()
