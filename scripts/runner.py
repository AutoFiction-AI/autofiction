#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import concurrent.futures
import hashlib
import json
import math
import os
import random
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import textwrap
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _env_non_negative_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "")
    if not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(0, value)


CHAPTER_ID_RE = re.compile(r"^chapter_(\d{2})$")
VERDICT_VALUES = {"PASS", "FAIL"}
SEVERITY_VALUES = {"MEDIUM", "HIGH", "CRITICAL"}
FULL_AWARD_SEVERITY_VALUES = {"LOW", *SEVERITY_VALUES}
VALIDATION_MODES = {"strict", "balanced", "lenient"}
PROVIDER_VALUES = {"codex", "claude"}
STAGE_GROUP_VALUES = (
    "premise",
    "outline",
    "draft",
    "review",
    "full_review",
    "cross_chapter_audit",
    "revision",
)
STAGE_PROVIDER_OVERRIDE_SPECS = {
    "outline_revision": ("outline", "outline_revision_provider"),
    "local_window_audit": ("cross_chapter_audit", "local_window_audit_provider"),
    "llm_aggregator": ("revision", "aggregation_provider"),
}
OBSERVABILITY_STAGE_KEYS = (
    "outline_review",
    "outline_revision",
    "spatial_layout",
    "assemble_snapshot",
    "build_cycle_context_packs",
    "chapter_review",
    "full_award_review",
    "cross_chapter_audit",
    "local_window_audit",
    "aggregate_findings",
    "build_revision_packets",
    "llm_aggregator",
    "materialize_aggregation_decisions",
    "revision",
    "assemble_post_revision_snapshot",
    "continuity_reconciliation",
)
REVISION_DIALOGUE_PASS_KEY = "p2_dialogue_idiolect_cadence"
PRIMARY_REVIEW_LENS = "award"
PRIMARY_GLOBAL_FINDING_SOURCE = "award_global"
DEFAULT_MODEL_BY_PROVIDER = {
    "codex": "gpt-5.4",
    "claude": "claude-opus-4-6",
}
DEFAULT_REASONING_EFFORT_BY_PROVIDER = {
    "codex": "xhigh",
    "claude": "max",
}
CLAUDE_EFFORT_MAP = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "xhigh": "max",
    "max": "max",
}
PREMISE_AXIS_DEFS: tuple[dict[str, str], ...] = (
    {"name": "comic_energy", "label": "comic energy"},
    {"name": "tragic_gravity", "label": "tragic gravity"},
    {"name": "satiric_bite", "label": "satiric bite"},
    {"name": "tenderness", "label": "tenderness"},
    {"name": "erotic_charge", "label": "erotic charge"},
    {"name": "psychological_interiority", "label": "psychological interiority"},
    {"name": "external_event_pressure", "label": "external event pressure"},
    {"name": "procedurality", "label": "procedurality"},
    {"name": "secrecy_deception", "label": "secrecy and deception"},
    {"name": "obsession_compulsion", "label": "obsession and compulsion"},
    {"name": "epistemic_uncertainty", "label": "epistemic uncertainty"},
    {"name": "time_span", "label": "long time-span pressure"},
    {"name": "protagonist_plurality", "label": "protagonist plurality"},
    {"name": "life_stage_skew", "label": "life-stage skew"},
    {"name": "romantic_centrality", "label": "romantic centrality"},
    {"name": "family_entanglement", "label": "family entanglement"},
    {"name": "communal_entanglement", "label": "communal entanglement"},
    {"name": "public_civic_scale", "label": "public-civic scale"},
    {"name": "institutional_density", "label": "institutional density"},
    {"name": "class_economic_pressure", "label": "class and economic pressure"},
    {"name": "embodied_labor_specificity", "label": "embodied labor specificity"},
    {"name": "documentality_legibility", "label": "documentality and legibility"},
    {"name": "ecological_biome_specificity", "label": "ecological and biome specificity"},
    {"name": "mobility_migration", "label": "mobility and migration"},
    {"name": "historical_embeddedness", "label": "historical embeddedness"},
    {"name": "worldbuilding_density", "label": "worldbuilding density"},
    {"name": "fantasy_mythic_pressure", "label": "fantasy and mythic pressure"},
    {"name": "science_technology_pressure", "label": "science and technology pressure"},
    {"name": "spiritual_metaphysical_pressure", "label": "spiritual and metaphysical pressure"},
    {"name": "ontological_instability", "label": "ontological instability"},
)
PREMISE_AXIS_MODEL_LABEL_OVERRIDES: dict[str, str] = {
    "public_civic_scale": "shared social consequence",
    "institutional_density": "rule-bound collective life",
    "documentality_legibility": "formal recognition, naming, and social legibility",
    "procedurality": "stepwise task pressure",
    "epistemic_uncertainty": "contested knowledge and unstable truth",
}
PREMISE_SCAFFOLD_SCENE_SOURCE_DEFS: tuple[dict[str, Any], ...] = (
    {
        "name": "household",
        "label": "household life",
        "gloss": "Let scenes arise from shared living arrangements, chores, privacy, kin obligation, and domestic leverage.",
        "affinity": ("family_entanglement", "tenderness", "romantic_centrality", "class_economic_pressure"),
    },
    {
        "name": "work",
        "label": "craft or work",
        "gloss": "Let scenes arise from making, mending, tending, selling, or surviving through skilled labor.",
        "affinity": ("embodied_labor_specificity", "class_economic_pressure", "procedurality"),
    },
    {
        "name": "journey",
        "label": "journey or route",
        "gloss": "Let scenes arise from movement, crossings, stops, departures, arrivals, and who gets carried along.",
        "affinity": ("mobility_migration", "external_event_pressure", "public_civic_scale"),
    },
    {
        "name": "ritual",
        "label": "ritual or observance",
        "gloss": "Let scenes arise from repeated observances, sacred work, ceremony, taboo, and what must be enacted in public or private.",
        "affinity": ("spiritual_metaphysical_pressure", "communal_entanglement", "historical_embeddedness"),
    },
    {
        "name": "performance",
        "label": "performance or staged display",
        "gloss": "Let scenes arise from rehearsal, public display, spectacle, scripting, embarrassment, and the gap between role and appetite.",
        "affinity": ("comic_energy", "satiric_bite", "public_civic_scale", "romantic_centrality"),
    },
    {
        "name": "market",
        "label": "market or bargaining",
        "gloss": "Let scenes arise from buying, selling, hustling, bargaining, scarcity, and unequal exchange.",
        "affinity": ("class_economic_pressure", "secrecy_deception", "public_civic_scale"),
    },
    {
        "name": "service",
        "label": "care or attendance",
        "gloss": "Let scenes arise from tending bodies, serving others, caregiving, waiting on power, and what care costs.",
        "affinity": ("tenderness", "life_stage_skew", "embodied_labor_specificity", "class_economic_pressure"),
    },
    {
        "name": "maintenance",
        "label": "repair or maintenance",
        "gloss": "Let scenes arise from keeping a system, place, route, or object working under pressure.",
        "affinity": ("procedurality", "science_technology_pressure", "embodied_labor_specificity"),
    },
    {
        "name": "gathering",
        "label": "gathering or convergence",
        "gloss": "Let scenes arise from crowds, meetings, seasonal convergences, celebrations, vigils, or people forced into the same charged space.",
        "affinity": ("communal_entanglement", "public_civic_scale", "comic_energy"),
    },
    {
        "name": "enclosure",
        "label": "shared enclosure",
        "gloss": "Let scenes arise from confinement, proximity, repeated cohabitation, and rules of a bounded place.",
        "affinity": ("institutional_density", "communal_entanglement", "ontological_instability"),
    },
    {
        "name": "pursuit",
        "label": "search or pursuit",
        "gloss": "Let scenes arise from searching, chasing, hunting, tracing, or trying to catch up with something unstable.",
        "affinity": ("obsession_compulsion", "external_event_pressure", "secrecy_deception"),
    },
    {
        "name": "exchange",
        "label": "exchange or smuggling",
        "gloss": "Let scenes arise from hidden transfers, substitutions, favors, smuggling, and what changes hands under pressure.",
        "affinity": ("class_economic_pressure", "secrecy_deception", "documentality_legibility"),
    },
)
PREMISE_SCAFFOLD_SOCIAL_GEOMETRY_DEFS: tuple[dict[str, Any], ...] = (
    {
        "name": "dyad",
        "label": "dyad",
        "gloss": "Center the pressure on two people whose private leverage reshapes the book.",
        "affinity": ("romantic_centrality", "psychological_interiority", "tenderness"),
    },
    {
        "name": "triangle",
        "label": "triangle",
        "gloss": "Let three people lock one another into shifting leverage, desire, secrecy, or loyalty.",
        "affinity": ("romantic_centrality", "secrecy_deception", "erotic_charge"),
    },
    {
        "name": "family_cluster",
        "label": "family cluster",
        "gloss": "Let kinship be the main arrangement through which pressure moves.",
        "affinity": ("family_entanglement", "time_span", "tenderness"),
    },
    {
        "name": "ensemble",
        "label": "ensemble",
        "gloss": "Use a group with multiple centers of gravity rather than one dominant pair.",
        "affinity": ("protagonist_plurality", "public_civic_scale", "communal_entanglement"),
    },
    {
        "name": "rivals",
        "label": "rivals",
        "gloss": "Let pressure move through competition, resentment, one-upmanship, and mutual surveillance.",
        "affinity": ("satiric_bite", "secrecy_deception", "obsession_compulsion"),
    },
    {
        "name": "strangers_forced_together",
        "label": "strangers forced together",
        "gloss": "Bring people together by accident, disaster, transport, work, or temporary necessity.",
        "affinity": ("mobility_migration", "external_event_pressure", "protagonist_plurality"),
    },
    {
        "name": "mentor_apprentice",
        "label": "mentor and apprentice",
        "gloss": "Let asymmetrical skill, authority, and imitation generate scenes.",
        "affinity": ("life_stage_skew", "embodied_labor_specificity", "psychological_interiority"),
    },
    {
        "name": "caretaker_dependent",
        "label": "caretaker and dependent",
        "gloss": "Let obligation, tenderness, resentment, and bodily dependence drive the relationship map.",
        "affinity": ("tenderness", "life_stage_skew", "family_entanglement"),
    },
    {
        "name": "community_field",
        "label": "community field",
        "gloss": "Let the novel move through a neighborhood, town, camp, congregation, or block where everyone presses on everyone else.",
        "affinity": ("communal_entanglement", "public_civic_scale", "class_economic_pressure"),
    },
    {
        "name": "hierarchy",
        "label": "hierarchy",
        "gloss": "Let status, rank, deference, and command shape who can do what to whom.",
        "affinity": ("institutional_density", "class_economic_pressure", "secrecy_deception"),
    },
    {
        "name": "factional_pressure",
        "label": "factional pressure",
        "gloss": "Let several camps, wards, crews, or loyalties compete for people and meaning.",
        "affinity": ("public_civic_scale", "communal_entanglement", "secrecy_deception"),
    },
    {
        "name": "succession_pressure",
        "label": "succession pressure",
        "gloss": "Let inheritance, replacement, and the question of who comes next structure the relationships.",
        "affinity": ("family_entanglement", "life_stage_skew", "time_span", "public_civic_scale"),
    },
)
PREMISE_SCAFFOLD_NARRATIVE_MOTION_DEFS: tuple[dict[str, Any], ...] = (
    {
        "name": "countdown",
        "label": "countdown",
        "gloss": "Let pressure tighten toward a deadline, arrival, storm, ceremony, or imminent break.",
        "affinity": ("external_event_pressure",),
    },
    {
        "name": "return",
        "label": "return",
        "gloss": "Let pressure build through a return to a place, person, name, debt, or old arrangement.",
        "affinity": ("historical_embeddedness", "family_entanglement", "secrecy_deception"),
    },
    {
        "name": "recurrence",
        "label": "recurrence",
        "gloss": "Let the book advance through repeated seasons, rituals, jobs, visits, or anniversaries that keep changing in meaning.",
        "affinity": ("time_span", "spiritual_metaphysical_pressure", "communal_entanglement"),
    },
    {
        "name": "migration",
        "label": "migration",
        "gloss": "Let movement through routes, relocations, crossings, or convoy logic keep changing the book.",
        "affinity": ("mobility_migration", "external_event_pressure"),
    },
    {
        "name": "accumulation",
        "label": "accumulation",
        "gloss": "Let pressure build through layers of debt, mess, longing, gossip, labor, or evidence of prior choices.",
        "affinity": ("obsession_compulsion", "psychological_interiority", "class_economic_pressure"),
    },
    {
        "name": "corruption",
        "label": "corruption",
        "gloss": "Let the book move through compromises that get easier, dirtier, and more expensive over time.",
        "affinity": ("satiric_bite", "class_economic_pressure", "secrecy_deception"),
    },
    {
        "name": "replacement",
        "label": "replacement",
        "gloss": "Let the book move through substitution, doubling, re-identification, or one thing standing in for another.",
        "affinity": ("ontological_instability", "documentality_legibility", "secrecy_deception"),
    },
    {
        "name": "concealment",
        "label": "concealment",
        "gloss": "Let pressure move through what is hidden, withheld, smuggled, staged, or deliberately misread.",
        "affinity": ("secrecy_deception", "epistemic_uncertainty"),
    },
    {
        "name": "escalation",
        "label": "escalation",
        "gloss": "Let scenes keep getting hotter, louder, riskier, or more crowded rather than simply repeating.",
        "affinity": ("external_event_pressure", "comic_energy", "public_civic_scale"),
    },
    {
        "name": "diffusion",
        "label": "diffusion",
        "gloss": "Let an effect spread through a community, network, rumor field, or material environment.",
        "affinity": ("public_civic_scale", "communal_entanglement", "science_technology_pressure"),
    },
    {
        "name": "inheritance",
        "label": "inheritance",
        "gloss": "Let pressure move through what passes between generations, households, names, or bodies.",
        "affinity": ("family_entanglement", "time_span", "historical_embeddedness"),
    },
    {
        "name": "unraveling",
        "label": "unraveling",
        "gloss": "Let the book move through erosion, disintegration, and the slow loss of a once-usable order.",
        "affinity": ("tragic_gravity", "psychological_interiority", "ontological_instability"),
    },
)
PREMISE_SCAFFOLD_MODE_DEFS: tuple[dict[str, Any], ...] = (
    {
        "name": "comic",
        "label": "comic",
        "gloss": "Allow embarrassment, disproportion, appetite, and unruly social behavior to stay genuinely funny.",
        "affinity": ("comic_energy",),
    },
    {
        "name": "satiric",
        "label": "satiric",
        "gloss": "Let appetite, hypocrisy, status behavior, and social systems bite.",
        "affinity": ("satiric_bite", "public_civic_scale"),
    },
    {
        "name": "romantic",
        "label": "romantic",
        "gloss": "Let attraction, idealization, betrayal, and the changing terms of intimacy matter structurally.",
        "affinity": ("romantic_centrality", "tenderness", "erotic_charge"),
    },
    {
        "name": "lyric",
        "label": "lyric",
        "gloss": "Let attention, memory, atmosphere, and sensuous observation carry real narrative weight.",
        "affinity": ("psychological_interiority", "tenderness", "historical_embeddedness"),
    },
    {
        "name": "mythic",
        "label": "mythic",
        "gloss": "Let old stories, symbolic weight, and charged ritual patterns intensify the premise without swallowing it.",
        "affinity": ("fantasy_mythic_pressure", "historical_embeddedness"),
    },
    {
        "name": "speculative",
        "label": "speculative",
        "gloss": "Let invented rules, technologies, altered matter, or unstable realities reshape ordinary human consequence.",
        "affinity": ("science_technology_pressure", "ontological_instability"),
    },
    {
        "name": "grotesque",
        "label": "grotesque",
        "gloss": "Let bodily mess, appetite, alteration, and social ugliness produce pressure rather than polite distance.",
        "affinity": ("embodied_labor_specificity", "bodily_explicitness", "moral_contamination_transgression"),
    },
    {
        "name": "tragic",
        "label": "tragic",
        "gloss": "Let losses, consequences, and irreversible choices gather weight rather than being defused.",
        "affinity": ("tragic_gravity", "time_span"),
    },
    {
        "name": "devotional",
        "label": "devotional",
        "gloss": "Let prayer, observance, taboo, reverence, and contested holiness remain active sources of action.",
        "affinity": ("spiritual_metaphysical_pressure", "communal_entanglement"),
    },
    {
        "name": "sensual",
        "label": "sensual",
        "gloss": "Let texture, bodily appetite, touch, smell, and erotic or tactile immediacy matter on the page.",
        "affinity": ("erotic_charge", "embodied_labor_specificity", "bodily_explicitness"),
    },
)
PREMISE_RISK_AXIS_DEFS: tuple[dict[str, str], ...] = (
    {"name": "messiness_anti_sanitization", "label": "messiness and anti-sanitization"},
    {"name": "profanity_tolerance", "label": "profanity tolerance"},
    {"name": "bodily_explicitness", "label": "bodily explicitness"},
    {"name": "violence_proximity", "label": "violence proximity"},
    {"name": "moral_contamination_transgression", "label": "moral contamination and transgression"},
)
REVIEW_VALIDATION_RETRY_MAX = _env_non_negative_int("REVIEW_VALIDATION_RETRY_MAX", 0)
OUTLINE_REVIEW_VALIDATION_RETRY_MAX = _env_non_negative_int(
    "OUTLINE_REVIEW_VALIDATION_RETRY_MAX", 1
)
FULL_AWARD_VALIDATION_RETRY_MAX = _env_non_negative_int(
    "FULL_AWARD_VALIDATION_RETRY_MAX", 1
)
CROSS_CHAPTER_AUDIT_VALIDATION_RETRY_MAX = _env_non_negative_int(
    "CROSS_CHAPTER_AUDIT_VALIDATION_RETRY_MAX", 1
)
LOCAL_WINDOW_AUDIT_VALIDATION_RETRY_MAX = _env_non_negative_int(
    "LOCAL_WINDOW_AUDIT_VALIDATION_RETRY_MAX", 0
)
SPATIAL_LAYOUT_VALIDATION_RETRY_MAX = _env_non_negative_int(
    "SPATIAL_LAYOUT_VALIDATION_RETRY_MAX", 1
)
OUTLINE_REVISION_VALIDATION_RETRY_MAX = _env_non_negative_int(
    "OUTLINE_REVISION_VALIDATION_RETRY_MAX", 1
)
REVISION_VALIDATION_RETRY_MAX = _env_non_negative_int(
    "REVISION_VALIDATION_RETRY_MAX", 1
)
LOCAL_WINDOW_SIZE = 4
LOCAL_WINDOW_OVERLAP = 2
JOB_EXEC_RETRY_MAX = _env_non_negative_int("JOB_EXEC_RETRY_MAX", 0)
JOB_EXEC_RETRY_BASE_SLEEP_SECONDS = _env_non_negative_int(
    "JOB_EXEC_RETRY_BASE_SLEEP_SECONDS", 2
)
JOB_EXEC_RETRY_MAX_SLEEP_SECONDS = _env_non_negative_int(
    "JOB_EXEC_RETRY_MAX_SLEEP_SECONDS", 30
)
CLAUDE_QUOTA_RESET_BUFFER_SECONDS = _env_non_negative_int(
    "CLAUDE_QUOTA_RESET_BUFFER_SECONDS", 120
)
CLAUDE_QUOTA_RESET_JITTER_SECONDS = _env_non_negative_int(
    "CLAUDE_QUOTA_RESET_JITTER_SECONDS", 30
)
FULL_BOOK_REVIEW_IDLE_TIMEOUT_SECONDS = 1800
REVISION_PASS_DEFS = (
    {
        "key": "p1_structural_craft",
        "label": "HIGH/CRITICAL structural/craft fixes",
        "focus": (
            "Prioritize structural and craft blockers first: causality, chapter architecture, "
            "stakes clarity, continuity logic, and all HIGH/CRITICAL defects."
        ),
    },
    {
        "key": "p2_dialogue_idiolect_cadence",
        "label": "dialogue/idiolect/cadence fixes",
        "focus": (
            "Focus on dialogue realism and voice separation: idiolect fidelity, leverage shifts, "
            "pressure cadence, anti-transcript behavior, natural colloquial texture "
            "(contractions/interruptions/slang when character-true), pressure-true profanity "
            "usage per aesthetic risk policy, and preservation of productive roughness "
            "(false starts, evasions, repetitions, unfinished turns) rather than polishing speech flat."
        ),
    },
    {
        "key": "p3_prose_copyedit",
        "label": "prose/copyedit fixes",
        "focus": (
            "Focus on prose and copyedit finish: diction precision, rhythm control, sentence-level "
            "clarity, grammar, line-level polish without flattening style, and explicit aesthetic-risk "
            "audit (sanitization is the primary risk — do not soften or euphemize; push toward creative risk and specificity)."
        ),
    },
)
REVISION_PASS_KEYS = {row["key"] for row in REVISION_PASS_DEFS}
AGGREGATION_PRIMARY_BUCKET_KEYS = (
    "unchanged",
    "merges",
    "suppressions",
    "unfixable",
    "pass_reassignments",
)
AGGREGATION_DECISION_KEYS = (
    "unchanged",
    "merges",
    "canonical_choices",
    "consistency_directives",
    "context_injections",
    "suppressions",
    "unfixable",
    "pass_reassignments",
)
LOCAL_WINDOW_PASS_HINT_BY_CATEGORY = {
    "pre_scan": "p1_structural_craft",
    "factual_coherence": "p1_structural_craft",
    "pacing_rhythm": "p1_structural_craft",
    "emotional_continuity": "p1_structural_craft",
    "information_flow": "p1_structural_craft",
    "boundary_local_voice_drift": "p2_dialogue_idiolect_cadence",
    "redundant_scene_functions": "p1_structural_craft",
    "cross_chapter_prose_patterns": "p3_prose_copyedit",
    "repetitive_scene_dynamics": "p1_structural_craft",
    "character_decision_coherence": "p1_structural_craft",
    "reading_momentum": "p1_structural_craft",
}
LOCAL_WINDOW_CATEGORY_ALIASES = {
    "pre_scan": "pre_scan",
    "pre_scan_findings": "pre_scan",
    "prescan": "pre_scan",
    "coherence": "factual_coherence",
    "factual_coherence": "factual_coherence",
    "pacing": "pacing_rhythm",
    "pacing_rhythm": "pacing_rhythm",
    "emotional_continuity": "emotional_continuity",
    "emotion": "emotional_continuity",
    "information_flow": "information_flow",
    "info_flow": "information_flow",
    "boundary_local_voice_drift": "boundary_local_voice_drift",
    "voice_drift": "boundary_local_voice_drift",
    "redundant_scene_functions": "redundant_scene_functions",
    "scene_functions": "redundant_scene_functions",
    "cross_chapter_prose_patterns": "cross_chapter_prose_patterns",
    "prose_patterns": "cross_chapter_prose_patterns",
    "repetitive_scene_dynamics": "repetitive_scene_dynamics",
    "scene_dynamics": "repetitive_scene_dynamics",
    "character_decision_coherence": "character_decision_coherence",
    "decision_coherence": "character_decision_coherence",
    "reading_momentum": "reading_momentum",
    "momentum": "reading_momentum",
}


class PipelineError(RuntimeError):
    pass


class ProviderQuotaPause(PipelineError):
    def __init__(
        self,
        *,
        provider: str,
        result_text: str,
        reset_at_epoch: int,
        sleep_seconds: int,
        rate_limit_type: str | None,
    ) -> None:
        self.provider = provider
        self.result_text = result_text
        self.reset_at_epoch = reset_at_epoch
        self.sleep_seconds = sleep_seconds
        self.rate_limit_type = rate_limit_type or ""
        super().__init__(result_text or f"{provider} quota exhausted")


@dataclass(frozen=True)
class ChapterSpec:
    chapter_id: str
    chapter_number: int
    projected_min_words: int
    chapter_engine: str
    pressure_source: str
    state_shift: str
    texture_mode: str
    scene_count_target: int
    scene_count_target_explicit: bool
    must_land_beats: list[str]
    secondary_character_beats: list[str] = field(default_factory=list)
    setups_to_plant: list[dict[str, Any]] = field(default_factory=list)
    payoffs_to_land: list[dict[str, Any]] = field(default_factory=list)

    @property
    def objective(self) -> str:
        return self.chapter_engine

    @property
    def conflict(self) -> str:
        return self.pressure_source

    @property
    def consequence(self) -> str:
        return self.state_shift


@dataclass(frozen=True)
class ExecutionProfile:
    provider: str
    agent_bin: str
    model: str | None
    reasoning_effort: str | None


@dataclass(frozen=True)
class JobSpec:
    job_id: str
    stage: str
    stage_group: str
    cycle: int
    chapter_id: str | None
    allowed_inputs: list[str]
    required_outputs: list[str]
    prompt_text: str
    provider: str
    agent_bin: str
    model: str | None
    reasoning_effort: str | None
    timeout_seconds: int = 3600


@dataclass(frozen=True)
class RunnerConfig:
    premise: str | None
    premise_mode: str
    premise_brief: str | None
    award_profile: str
    premise_seed: str | None
    premise_reroll_max: int
    premise_candidate_count: int
    premise_generation_batch_size: int
    premise_min_unique_clusters: int
    premise_shortlist_size: int
    run_dir: Path
    max_cycles: int
    min_cycles: int
    max_parallel_drafts: int
    max_parallel_reviews: int
    max_parallel_revisions: int
    provider: str
    agent_bin: str
    model: str | None
    reasoning_effort: str | None
    stage_profiles: dict[str, ExecutionProfile]
    revision_pass_profiles: dict[str, ExecutionProfile]
    dry_run: bool
    dry_run_chapter_count: int
    job_timeout_seconds: int
    job_idle_timeout_seconds: int
    validation_mode: str
    outline_review_cycles: int = 1
    final_cycle_global_only: bool = True
    skip_outline_review: bool = False
    skip_cross_chapter_audit: bool = False
    skip_local_window_audit: bool = False
    require_local_window_for_revision: bool = False
    local_window_size: int = LOCAL_WINDOW_SIZE
    local_window_overlap: int = LOCAL_WINDOW_OVERLAP
    add_cycles: int = 0
    base_completed_cycles: int = 0


class NovelPipelineRunner:
    def __init__(self, repo_root: Path, cfg: RunnerConfig) -> None:
        self.repo_root = repo_root
        self.cfg = cfg
        self.run_dir = cfg.run_dir
        self.selected_premise: str = (cfg.premise or "").strip()
        self.premise_source: str = "user" if self.selected_premise else ""
        self.premise_seed: str = (cfg.premise_seed or "").strip()
        self.premise_reroll_count: int = 0
        self.chapter_specs: list[ChapterSpec] = []
        self.style_bible: dict[str, Any] = {}
        self.novel_title: str = ""
        self.spatial_layout: dict[str, Any] | None = None
        self.validation_warnings: list[dict[str, Any]] = []
        self._warning_lock = threading.Lock()
        self._precycle_stage_entries: dict[str, dict[str, Any]] = {}

    def _add_cycles_mode(self) -> bool:
        return self.cfg.add_cycles > 0

    def _profile_for_stage_group(self, stage_group: str) -> ExecutionProfile:
        profile = self.cfg.stage_profiles.get(stage_group)
        if profile is not None:
            return profile
        return ExecutionProfile(
            provider=self.cfg.provider,
            agent_bin=self.cfg.agent_bin,
            model=self.cfg.model,
            reasoning_effort=self.cfg.reasoning_effort,
        )

    def _profile_for_job(
        self,
        stage: str,
        stage_group: str,
        revision_pass_key: str | None = None,
    ) -> ExecutionProfile:
        if stage_group == "revision" and revision_pass_key:
            revision_profile = self.cfg.revision_pass_profiles.get(revision_pass_key)
            if revision_profile is not None:
                return revision_profile
        stage_profile = self.cfg.stage_profiles.get(stage)
        if stage_profile is not None:
            return stage_profile
        return self._profile_for_stage_group(stage_group)

    def _make_job(
        self,
        *,
        job_id: str,
        stage: str,
        stage_group: str,
        revision_pass_key: str | None = None,
        cycle: int,
        chapter_id: str | None,
        allowed_inputs: list[str],
        required_outputs: list[str],
        prompt_text: str,
        timeout_seconds: int | None = None,
    ) -> JobSpec:
        profile = self._profile_for_job(stage, stage_group, revision_pass_key)
        return JobSpec(
            job_id=job_id,
            stage=stage,
            stage_group=stage_group,
            cycle=cycle,
            chapter_id=chapter_id,
            allowed_inputs=allowed_inputs,
            required_outputs=required_outputs,
            prompt_text=prompt_text,
            provider=profile.provider,
            agent_bin=profile.agent_bin,
            model=profile.model,
            reasoning_effort=profile.reasoning_effort,
            timeout_seconds=timeout_seconds or self.cfg.job_timeout_seconds,
        )

    def run(self) -> int:
        self._log(f"run_dir={self.run_dir}")
        self._log(f"validation_mode={self.cfg.validation_mode}")
        self._prepare_run_dir()
        self._resolve_premise()
        self._run_outline_stage()
        self._run_draft_stage()

        gate_records: list[dict[str, Any]] = []
        success_cycle: int | None = None
        start_cycle = self._starting_cycle()
        if self.cfg.add_cycles:
            self._log(
                "add_cycles_resume "
                f"base_completed={self._cpad(self.cfg.base_completed_cycles)} "
                f"new_cycles={self.cfg.add_cycles} "
                f"start_cycle={self._cpad(start_cycle)} "
                f"target_cycle={self._cpad(self.cfg.max_cycles)}"
            )

        for cycle in range(start_cycle, self.cfg.max_cycles + 1):
            cpad = self._cpad(cycle)
            existing_cycle_status = self._load_existing_cycle_status(cycle)
            if existing_cycle_status is None:
                cycle_status = self._new_cycle_status(cycle)
            else:
                cycle_status = self._resume_cycle_status(cycle, existing_cycle_status)
                self._log(
                    f"cycle={cpad} resume_source=cycle_status status_file={self._cycle_status_rel(cycle)}"
                )
            self._write_cycle_status(cycle, cycle_status)

            self._log(f"cycle={cpad} stage=assemble_snapshot")
            snapshot_reused = self._assemble_snapshot(cycle)
            self._update_cycle_stage_status(
                cycle_status,
                "assemble_snapshot",
                "reused" if snapshot_reused else "complete",
                outputs=[
                    f"snapshots/cycle_{cpad}/FINAL_NOVEL.md",
                ],
            )
            self._write_cycle_status(cycle, cycle_status)
            self._log(f"cycle={cpad} stage=build_cycle_context_packs")
            context_reused = self._build_cycle_context_packs(cycle)
            self._update_cycle_stage_status(
                cycle_status,
                "build_cycle_context_packs",
                "reused" if context_reused else "complete",
                artifact_glob=f"context/cycle_{cpad}/**/*.json",
            )
            self._write_cycle_status(cycle, cycle_status)

            if self._is_global_only_final_cycle(cycle):
                self._log(
                    f"cycle={cpad} stage=review_chapters_skip reason=final_cycle_global_only"
                )
                review_summary = {
                    "status": "skipped",
                    "reason": "final_cycle_global_only",
                    "chapter_count": 0,
                    "units": {},
                }
                self._update_cycle_stage_status(
                    cycle_status,
                    "chapter_review",
                    "skipped",
                    reason="final_cycle_global_only",
                    chapter_count=0,
                    units={},
                )
            else:
                self._log(
                    f"cycle={cpad} stage=review_chapters concurrency={self.cfg.max_parallel_reviews}"
                )
                review_summary = self._run_chapter_review_stage(cycle)
                self._update_cycle_stage_status(
                    cycle_status,
                    "chapter_review",
                    review_summary["status"],
                    reason=review_summary.get("reason"),
                    artifact_glob=f"reviews/cycle_{cpad}/chapter_*.review.json",
                    chapter_count=review_summary["chapter_count"],
                    units=review_summary["units"],
                )
            self._write_cycle_status(cycle, cycle_status)

            enabled_local_window = (
                self._local_window_stage_enabled()
                and not self.cfg.skip_local_window_audit
            )
            review_stage_count = 1
            if not self.cfg.skip_cross_chapter_audit:
                review_stage_count += 1
            if enabled_local_window:
                review_stage_count += 1
            if review_stage_count == 1:
                self._log(f"cycle={cpad} stage=full_award_review")
            else:
                self._log(
                    f"cycle={cpad} stage=full_book_reviews concurrency={review_stage_count}"
                )
            review_stage_results = self._run_parallel_full_book_review_stages(cycle)
            self._update_cycle_stage_status(
                cycle_status,
                "full_award_review",
                (
                    "reused"
                    if bool(review_stage_results.get("full_award_review"))
                    else "complete"
                ),
                outputs=[f"reviews/cycle_{cpad}/full_award.review.json"],
            )
            if self.cfg.skip_cross_chapter_audit:
                self._update_cycle_stage_status(
                    cycle_status,
                    "cross_chapter_audit",
                    "skipped",
                    reason="config_skip_cross_chapter_audit",
                )
            else:
                self._update_cycle_stage_status(
                    cycle_status,
                    "cross_chapter_audit",
                    (
                        "reused"
                        if bool(review_stage_results.get("cross_chapter_audit"))
                        else "complete"
                    ),
                    outputs=[self._cross_chapter_audit_rel(cycle)],
                )
            if self.cfg.skip_local_window_audit:
                self._update_cycle_stage_status(
                    cycle_status,
                    "local_window_audit",
                    "skipped",
                    reason="config_skip_local_window_audit",
                    units={},
                )
            elif not self._local_window_stage_enabled():
                self._update_cycle_stage_status(
                    cycle_status,
                    "local_window_audit",
                    "skipped",
                    reason="stage_not_enabled",
                    units={},
                )
            else:
                local_window_summary = review_stage_results.get("local_window_audit")
                if not isinstance(local_window_summary, dict):
                    raise PipelineError(
                        "parallel_full_book_review phase missing local-window stage result"
                    )
                self._update_cycle_stage_status(
                    cycle_status,
                    "local_window_audit",
                    str(local_window_summary.get("status", "failed")).strip() or "failed",
                    reason=str(local_window_summary.get("reason", "")).strip() or None,
                    artifact_glob=f"reviews/cycle_{cpad}/local_window_*.json",
                    units=local_window_summary.get("units", {}),
                )
            self._write_cycle_status(cycle, cycle_status)

            self._log(f"cycle={cpad} stage=aggregate_findings")
            aggregate = self._aggregate_findings(cycle)
            self._update_cycle_stage_status(
                cycle_status,
                "aggregate_findings",
                "complete",
                outputs=[
                    f"findings/cycle_{cpad}/all_findings.jsonl",
                    f"findings/cycle_{cpad}/summary.json",
                ],
                chapter_count=len(aggregate["by_chapter"]),
            )
            self._write_cycle_status(cycle, cycle_status)

            gate = self._write_gate(cycle, aggregate)
            cycle_status["advisory_gate"] = dict(gate)
            self._write_quality_summary(cycle, aggregate, gate, cycle_status=cycle_status)
            gate_records.append(gate)
            self._log(
                f"cycle={cpad} gate={gate['decision']} unresolved_medium_plus={gate['unresolved_medium_plus_count']}"
            )
            self._write_cycle_status(cycle, cycle_status)

            touched_chapters = sorted(aggregate["by_chapter"].keys())
            if not touched_chapters:
                self._log(
                    f"cycle={cpad} skipping revision because aggregate produced no actionable chapter work"
                )
                self._update_cycle_stage_status(
                    cycle_status,
                    "build_revision_packets",
                    "skipped",
                    reason="no_actionable_findings",
                )
                self._update_cycle_stage_status(
                    cycle_status,
                    "llm_aggregator",
                    "skipped",
                    reason="no_actionable_findings",
                )
                self._update_cycle_stage_status(
                    cycle_status,
                    "materialize_aggregation_decisions",
                    "skipped",
                    reason="no_actionable_findings",
                )
                self._update_cycle_stage_status(
                    cycle_status,
                    "revision",
                    "skipped",
                    reason="no_actionable_findings",
                )
                self._log(f"cycle={cpad} stage=assemble_post_revision_snapshot")
                post_snapshot_reused = self._assemble_post_revision_snapshot(cycle)
                self._update_cycle_stage_status(
                    cycle_status,
                    "assemble_post_revision_snapshot",
                    "reused" if post_snapshot_reused else "complete",
                    outputs=[
                        f"snapshots/cycle_{cpad}/FINAL_NOVEL.post_revision.md",
                    ],
                )
                self._write_cycle_status(cycle, cycle_status)
                self._log(f"cycle={cpad} stage=continuity_reconciliation")
                continuity_result = self._run_continuity_reconciliation(cycle)
                continuity_status = "complete"
                continuity_reason = None
                if isinstance(continuity_result, dict):
                    continuity_status = (
                        str(continuity_result.get("status", "complete")).strip()
                        or "complete"
                    )
                    continuity_reason = (
                        str(continuity_result.get("reason", "")).strip() or None
                    )
                else:
                    continuity_status = "reused" if continuity_result else "complete"
                self._update_cycle_stage_status(
                    cycle_status,
                    "continuity_reconciliation",
                    continuity_status,
                    reason=continuity_reason,
                )
                self._write_cycle_status(cycle, cycle_status)
                success_cycle = cycle
                continue

            self._log(
                f"cycle={cpad} stage=build_revision_packets chapters={len(touched_chapters)}"
            )
            self._build_revision_packets(cycle, aggregate["by_chapter"])
            self._update_cycle_stage_status(
                cycle_status,
                "build_revision_packets",
                "complete",
                artifact_glob=f"packets/cycle_{cpad}/*.revision_packet.json",
                chapter_count=len(touched_chapters),
            )
            self._write_cycle_status(cycle, cycle_status)

            self._log(f"cycle={cpad} stage=llm_aggregator")
            aggregator_summary = self._run_llm_aggregator_stage(cycle, touched_chapters)
            self._update_cycle_stage_status(
                cycle_status,
                "llm_aggregator",
                aggregator_summary["status"],
                reason=aggregator_summary.get("reason"),
                outputs=aggregator_summary.get("outputs"),
                chapter_count=len(touched_chapters),
            )
            self._write_cycle_status(cycle, cycle_status)

            self._log(f"cycle={cpad} stage=materialize_aggregation_decisions")
            materialization_summary = self._materialize_aggregation_decisions_stage(
                cycle,
                touched_chapters,
                aggregator_summary,
            )
            self._update_cycle_stage_status(
                cycle_status,
                "materialize_aggregation_decisions",
                materialization_summary["status"],
                reason=materialization_summary.get("reason"),
                outputs=materialization_summary.get("outputs"),
                artifact_glob=f"packets/cycle_{cpad}/*.revision_packet.json",
                chapter_count=len(touched_chapters),
            )
            self._write_cycle_status(cycle, cycle_status)

            self._log(
                f"cycle={cpad} stage=revise_chapters concurrency={self.cfg.max_parallel_revisions}"
            )
            revision_summary = self._run_revision_stage(cycle, touched_chapters)
            self._update_cycle_stage_status(
                cycle_status,
                "revision",
                revision_summary["status"],
                artifact_glob=f"revisions/cycle_{cpad}/*.revision_report.json",
                chapter_count=revision_summary["chapter_count"],
                units=revision_summary["units"],
            )
            self._write_cycle_status(cycle, cycle_status)
            self._log(f"cycle={cpad} stage=assemble_post_revision_snapshot")
            post_snapshot_reused = self._assemble_post_revision_snapshot(cycle)
            self._update_cycle_stage_status(
                cycle_status,
                "assemble_post_revision_snapshot",
                "reused" if post_snapshot_reused else "complete",
                outputs=[
                    f"snapshots/cycle_{cpad}/FINAL_NOVEL.post_revision.md",
                ],
            )
            self._write_cycle_status(cycle, cycle_status)
            self._log(f"cycle={cpad} stage=continuity_reconciliation")
            continuity_result = self._run_continuity_reconciliation(cycle)
            continuity_status = "complete"
            continuity_reason = None
            if isinstance(continuity_result, dict):
                continuity_status = (
                    str(continuity_result.get("status", "complete")).strip()
                    or "complete"
                )
                continuity_reason = (
                    str(continuity_result.get("reason", "")).strip() or None
                )
            else:
                continuity_status = "reused" if continuity_result else "complete"
            self._update_cycle_stage_status(
                cycle_status,
                "continuity_reconciliation",
                continuity_status,
                reason=continuity_reason,
            )
            self._write_cycle_status(cycle, cycle_status)
            success_cycle = cycle

        self._write_final_report(success_cycle, gate_records)
        self._print_cost_summary()
        if success_cycle is None:
            self._log("status=FAIL reason=no_cycles_completed")
            return 1

        self._log(f"status=PASS success_cycle={self._cpad(success_cycle)}")
        return 0

    def _prepare_run_dir(self) -> None:
        required_dirs = [
            "config",
            "config/prompts",
            "config/schemas",
            "input",
            "premise",
            "outline",
            "outline/chapter_specs",
            "chapters",
            "snapshots",
            "context",
            "reviews",
            "findings",
            "packets",
            "revisions",
            "gate",
            "logs/jobs",
            "manifests",
            "workspaces",
            "reports",
        ]
        for rel in required_dirs:
            (self.run_dir / rel).mkdir(parents=True, exist_ok=True)

        prompt_names = [
            "premise_candidates_prompt.md",
            "premise_uniqueness_clustering_prompt.md",
            "outline_prompt.md",
            "outline_review_prompt.md",
            "outline_revision_prompt.md",
            "spatial_layout_prompt.md",
            "chapter_draft_prompt.md",
            "chapter_expand_prompt.md",
            "chapter_review_prompt.md",
            "chapter_revision_prompt.md",
            "revision_aggregator_prompt.md",
            "full_award_review_prompt.md",
            "cross_chapter_audit_prompt.md",
            "local_window_audit_prompt.md",
            "continuity_sheet_prompt.md",
        ]
        for name in prompt_names:
            src = self.repo_root / "prompts" / name
            dst = self.run_dir / "config" / "prompts" / name
            shutil.copy2(src, dst)

        schema_names = [
            "chapter_review.schema.json",
            "full_award_review.schema.json",
            "cross_chapter_audit.schema.json",
            "local_window_audit.schema.json",
            "revision_packet.schema.json",
            "gate.schema.json",
            "style_bible.schema.json",
        ]
        for name in schema_names:
            src = self.repo_root / "schemas" / name
            dst = self.run_dir / "config" / "schemas" / name
            shutil.copy2(src, dst)

        shutil.copy2(
            self.repo_root / "prompts" / "constitution.md",
            self.run_dir / "config" / "constitution.md",
        )
        self._write_run_config()
        existing_warnings = self.run_dir / "reports" / "validation_warnings.json"
        if existing_warnings.is_file():
            try:
                payload = json.loads(existing_warnings.read_text(encoding="utf-8"))
                rows = payload.get("warnings", [])
                if isinstance(rows, list):
                    self.validation_warnings = [r for r in rows if isinstance(r, dict)]
            except Exception:
                self.validation_warnings = []

    def _starting_cycle(self) -> int:
        if self.cfg.add_cycles > 0:
            return self.cfg.base_completed_cycles + 1
        return 1

    def _is_global_only_final_cycle(self, cycle: int) -> bool:
        return bool(
            self.cfg.final_cycle_global_only
            and self.cfg.max_cycles > 1
            and cycle == self.cfg.max_cycles
        )

    def _cross_chapter_audit_rel(self, cycle: int) -> str:
        return f"reviews/cycle_{self._cpad(cycle)}/cross_chapter_audit.json"

    def _write_run_config(self) -> None:
        existing_payload: dict[str, Any] = {}
        config_path = self.run_dir / "config" / "run_config.json"
        if config_path.is_file():
            try:
                loaded = json.loads(config_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    existing_payload = loaded
            except Exception:
                existing_payload = {}

        existing_premise = self._optional_text(existing_payload.get("premise"))
        existing_source = self._optional_text(existing_payload.get("premise_source"))
        existing_seed = self._optional_text(existing_payload.get("premise_seed"))
        existing_reroll_count = existing_payload.get("premise_reroll_count", 0)
        premise = self.selected_premise or ((self.cfg.premise or "").strip()) or existing_premise
        premise_source = self.premise_source or ("user" if premise else None) or existing_source or None
        premise_seed = self.premise_seed or existing_seed or None
        try:
            reroll_count = int(self.premise_reroll_count)
        except Exception:
            reroll_count = 0
        if reroll_count <= 0:
            try:
                reroll_count = int(existing_reroll_count)
            except Exception:
                reroll_count = 0
        created_at_utc = str(existing_payload.get("created_at_utc", "")).strip() or self._utc_now()
        self._write_json(
            "config/run_config.json",
            {
                "created_at_utc": created_at_utc,
                "premise": premise or None,
                "premise_mode": self.cfg.premise_mode,
                "premise_source": premise_source,
                "premise_brief": self.cfg.premise_brief,
                "award_profile": self.cfg.award_profile,
                "premise_seed": premise_seed,
                "premise_reroll_count": reroll_count,
                "premise_reroll_max": self.cfg.premise_reroll_max,
                "premise_candidate_count": self.cfg.premise_candidate_count,
                "premise_generation_batch_size": self.cfg.premise_generation_batch_size,
                "premise_min_unique_clusters": self.cfg.premise_min_unique_clusters,
                "premise_shortlist_size": self.cfg.premise_shortlist_size,
                "max_cycles": self.cfg.max_cycles,
                "min_cycles": self.cfg.min_cycles,
                "max_parallel_drafts": self.cfg.max_parallel_drafts,
                "max_parallel_reviews": self.cfg.max_parallel_reviews,
                "max_parallel_revisions": self.cfg.max_parallel_revisions,
                "provider": self.cfg.provider,
                "agent_bin": self.cfg.agent_bin,
                "model": self.cfg.model,
                "reasoning_effort": self.cfg.reasoning_effort,
                "stage_profiles": {
                    stage_group: {
                        "provider": profile.provider,
                        "agent_bin": profile.agent_bin,
                        "model": profile.model,
                        "reasoning_effort": profile.reasoning_effort,
                    }
                    for stage_group, profile in sorted(self.cfg.stage_profiles.items())
                },
                "revision_pass_profiles": {
                    pass_key: {
                        "provider": profile.provider,
                        "agent_bin": profile.agent_bin,
                        "model": profile.model,
                        "reasoning_effort": profile.reasoning_effort,
                    }
                    for pass_key, profile in sorted(
                        self.cfg.revision_pass_profiles.items()
                    )
                },
                "dry_run": self.cfg.dry_run,
                "validation_mode": self.cfg.validation_mode,
                "outline_review_cycles": self.cfg.outline_review_cycles,
                "final_cycle_global_only": self.cfg.final_cycle_global_only,
                "skip_outline_review": self.cfg.skip_outline_review,
                "skip_cross_chapter_audit": self.cfg.skip_cross_chapter_audit,
                "skip_local_window_audit": self.cfg.skip_local_window_audit,
                "require_local_window_for_revision": (
                    self.cfg.require_local_window_for_revision
                ),
                "local_window_size": self.cfg.local_window_size,
                "local_window_overlap": self.cfg.local_window_overlap,
                "add_cycles": self.cfg.add_cycles,
                "base_completed_cycles": self.cfg.base_completed_cycles,
            },
        )

    def _resolve_premise(self) -> None:
        premise_rel = "input/premise.txt"
        search_plan_rel = "premise/premise_search_plan.json"
        candidates_rel = "premise/premise_candidates.jsonl"
        uniqueness_rel = "premise/uniqueness_clusters.json"
        selection_rel = "premise/selection.json"
        brainstorming_rel = "premise/premise_brainstorming.md"
        premise_path = self.run_dir / premise_rel
        search_plan_path = self.run_dir / search_plan_rel
        candidates_path = self.run_dir / candidates_rel
        uniqueness_path = self.run_dir / uniqueness_rel
        selection_path = self.run_dir / selection_rel
        brainstorming_path = self.run_dir / brainstorming_rel
        invalid_generated_artifacts = False

        if self.cfg.premise_mode == "user":
            premise = (self.cfg.premise or "").strip()
            if not premise:
                raise PipelineError("premise cannot be empty")
            if premise_path.is_file():
                existing = premise_path.read_text(encoding="utf-8").strip()
                if existing != premise:
                    raise PipelineError(
                        f"run-dir premise mismatch for resume: {premise_rel} already exists with different content"
                    )
            self.selected_premise = premise
            self.premise_source = "user"
            self._write_text(premise_rel, premise + "\n")
            self._write_run_config()
            self._log("premise_ready source=user")
            return

        if (
            premise_path.is_file()
            and search_plan_path.is_file()
            and candidates_path.is_file()
            and uniqueness_path.is_file()
            and selection_path.is_file()
            and brainstorming_path.is_file()
        ):
            try:
                self._validate_generated_premise_artifacts()
            except PipelineError as exc:
                self._log(
                    f"premise_resume_invalid reason={exc}; rerunning generated premise search"
                )
                invalid_generated_artifacts = True
            else:
                self.selected_premise = premise_path.read_text(encoding="utf-8").strip()
                self.premise_source = self._existing_premise_source() or "generated"
                self._write_run_config()
                self._log("premise_resume source=generated_artifacts")
                return

        existing_source = self._existing_premise_source()
        if premise_path.is_file() and existing_source == "user" and not invalid_generated_artifacts:
            raise PipelineError(
                "run-dir already contains a user-provided premise; use a new run-dir for --generate-premise"
            )

        self.premise_source = "generated"
        if invalid_generated_artifacts or (
            not self.cfg.premise_seed
            and (
                search_plan_path.is_file()
                or candidates_path.is_file()
                or selection_path.is_file()
                or brainstorming_path.is_file()
                or uniqueness_path.is_file()
            )
        ):
            self._load_existing_premise_metadata()
        self._ensure_premise_seed()
        self._run_generated_premise_search()
        self._validate_generated_premise_artifacts()
        self.selected_premise = premise_path.read_text(encoding="utf-8").strip()
        self._write_run_config()
        self._log(
            "premise_generation_complete "
            f"source=generated words={len(self.selected_premise.split())} "
            f"seed={self.premise_seed} rerolls={self.premise_reroll_count}"
        )

    def _premise_brief_block(self) -> str:
        if not self.cfg.premise_brief:
            return (
                "Creative brief:\n"
                "None provided. Self-direct the search for the strongest genre-fair, award-agnostic premise set.\n"
            )
        return (
            "Creative brief:\n"
            f"{self.cfg.premise_brief}\n"
            "Use the brief as steering, not as a rigid template.\n"
        )

    def _validate_generated_premise(self, premise: str) -> None:
        text = premise.strip()
        if not text:
            raise PipelineError("generated premise cannot be empty")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) > 3:
            raise PipelineError("generated premise must fit within 3 non-empty lines")
        for line in lines:
            lowered = line.lower()
            if re.match(r"^([#>*-]|\d+\.)\s", line):
                raise PipelineError("generated premise must not be a list or heading")
            if lowered.startswith("premise:") or lowered.startswith("selected premise:"):
                raise PipelineError("generated premise must not include labels")
        if len(text.split()) > 160:
            raise PipelineError("generated premise must stay brief (<= 160 words)")

    def _validate_premise_brainstorming(self, premise: str, path: Path) -> None:
        if not path.is_file():
            raise PipelineError("premise brainstorming artifact missing")
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            raise PipelineError("premise brainstorming artifact is empty")
        required_headers = [
            "# Premise Brainstorming",
            "## Seed",
            "## Brief",
            "## Run-Level Search Gloss",
            "## Candidate Set",
            "## Protected Shortlist",
            "## Selected Premise",
        ]
        new_headers = required_headers + ["## Uniqueness Clusters", "## Random Draw"]
        old_headers = required_headers + ["## Diversity Audit Summary", "## Selection Rationale"]
        if any(header not in text for header in new_headers) and any(
            header not in text for header in old_headers
        ):
            raise PipelineError("premise brainstorming artifact missing required sections")
        if premise not in text:
            raise PipelineError(
                "premise brainstorming artifact must include the selected premise text"
            )

    def _write_premise_brainstorming_stub(self, premise: str) -> None:
        content = textwrap.dedent(
            f"""\
            # Premise Brainstorming

            ## Seed
            Unknown (legacy generated run)

            ## Brief
            Unknown (legacy generated run)

            ## Run-Level Search Gloss
            Legacy generated premise resumed without original seeded search plan.

            ## Candidate Set
            Not preserved in this legacy run.

            ## Uniqueness Clusters
            Only one legacy cluster is available because the original candidate field was not preserved.

            ## Protected Shortlist
            Only the legacy selected premise is available.

            ## Random Draw
            No new draw was performed. The legacy selected premise was resumed as-is to preserve continuity.

            ## Selected Premise
            {premise}
            """
        )
        self._write_text("premise/premise_brainstorming.md", content)

    def _optional_text(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _existing_premise_source(self) -> str | None:
        config_path = self.run_dir / "config" / "run_config.json"
        if not config_path.is_file():
            return None
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        source = self._optional_text(payload.get("premise_source"))
        return source or None

    def _load_existing_premise_metadata(self) -> None:
        config_path = self.run_dir / "config" / "run_config.json"
        if not config_path.is_file():
            return
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            return
        seed = self._optional_text(payload.get("premise_seed"))
        if seed:
            self.premise_seed = seed
        try:
            self.premise_reroll_count = int(payload.get("premise_reroll_count", 0))
        except Exception:
            self.premise_reroll_count = 0

    def _ensure_premise_seed(self) -> None:
        if self.premise_seed:
            self.premise_seed = self._normalize_premise_seed(self.premise_seed)
            return
        if self.cfg.premise_seed:
            self.premise_seed = self._normalize_premise_seed(self.cfg.premise_seed)
            return
        self.premise_seed = f"{secrets.randbits(128):032x}"

    def _normalize_premise_seed(self, raw: str) -> str:
        text = str(raw).strip().lower()
        if not text:
            raise PipelineError("premise seed cannot be empty")
        try:
            if text.startswith("0x"):
                value = int(text, 16)
            elif re.fullmatch(r"[0-9a-f]+", text) and any(c.isalpha() for c in text):
                value = int(text, 16)
            else:
                value = int(text, 10)
        except ValueError as exc:
            raise PipelineError(f"invalid premise seed: {raw}") from exc
        if value < 0:
            raise PipelineError("premise seed must be non-negative")
        if value.bit_length() > 128:
            raise PipelineError("premise seed must fit within 128 bits")
        return f"{value:032x}"

    def _derived_premise_seed(self, base_seed: str, reroll_index: int) -> str:
        if reroll_index <= 0:
            return base_seed
        payload = f"{base_seed}:{reroll_index}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:32]

    def _run_generated_premise_search(self) -> None:
        self._ensure_premise_seed()
        max_rerolls = max(0, self.cfg.premise_reroll_max)
        last_summary = ""
        for reroll_index in range(max_rerolls + 1):
            derived_seed = self._derived_premise_seed(self.premise_seed, reroll_index)
            self.premise_reroll_count = reroll_index
            search_plan = self._build_premise_search_plan(derived_seed, reroll_index)
            self._write_json("premise/premise_search_plan.json", search_plan)
            self._write_run_config()
            self._log(
                f"premise_search_plan_ready seed={self.premise_seed} "
                f"derived_seed={derived_seed} reroll={reroll_index}"
            )
            scaffold_assessment = self._assess_scaffold_spread(search_plan)
            if not bool(scaffold_assessment.get("ok")):
                last_summary = str(scaffold_assessment.get("summary", "")).strip()
                if reroll_index >= max_rerolls:
                    break
                self._log(
                    f"premise_scaffold_reroll reroll={reroll_index + 1} reason={last_summary}"
                )
                continue

            candidates = self._run_premise_candidates_stage(search_plan)
            uniqueness = self._run_premise_uniqueness_clustering_stage(
                search_plan, candidates
            )
            unique_count = int(uniqueness.get("unique_cluster_count", 0))
            min_unique = int(
                search_plan.get(
                    "min_unique_clusters", self.cfg.premise_min_unique_clusters
                )
            )
            field_unique = bool(uniqueness.get("field_is_sufficiently_unique"))
            last_summary = str(
                uniqueness.get("insufficient_uniqueness_reason", "")
                or f"unique clusters={unique_count}, minimum required={min_unique}"
            ).strip()
            if field_unique and unique_count >= min_unique:
                selected_premise = self._write_uniqueness_selection_artifacts(
                    search_plan, candidates, uniqueness
                )
                self.selected_premise = selected_premise
                self.premise_source = "generated"
                self._write_run_config()
                return

            if reroll_index >= max_rerolls:
                break
            self._log(
                f"premise_uniqueness_reroll reroll={reroll_index + 1} reason={last_summary}"
            )

        raise PipelineError(
            "premise search exhausted rerolls without sufficient unique clusters"
            + (f": {last_summary}" if last_summary else "")
        )

    def _build_premise_search_plan(
        self, derived_seed: str, reroll_index: int
    ) -> dict[str, Any]:
        rng = random.Random(int(derived_seed, 16))
        candidate_count = max(1, self.cfg.premise_candidate_count)
        selection_anchor = self._midpoint_axis_map(PREMISE_AXIS_DEFS)
        pool = [
            {
                "kind": "independent",
                "vector": self._sample_spread_axis_map(
                    rng,
                    PREMISE_AXIS_DEFS,
                    hot_range=(3, 6),
                    cold_range=(2, 4),
                    high_range=(0.72, 1.0),
                    low_range=(0.0, 0.18),
                    middle_range=(0.14, 0.86),
                ),
                "risk_overlay": self._sample_spread_axis_map(
                    rng,
                    PREMISE_RISK_AXIS_DEFS,
                    hot_range=(1, 3),
                    cold_range=(1, 2),
                    high_range=(0.68, 1.0),
                    low_range=(0.0, 0.20),
                    middle_range=(0.12, 0.82),
                ),
            }
            for _ in range(max(candidate_count * 12, 240))
        ]
        selected_rows = self._greedy_select_vectors(
            pool,
            selection_anchor,
            count=candidate_count,
            diversify_axis_profiles=True,
        )
        scaffold_profiles = self._assign_scaffold_profiles(selected_rows, rng)

        candidates: list[dict[str, Any]] = []
        for idx, (row, scaffold_profile) in enumerate(
            zip(selected_rows, scaffold_profiles), start=1
        ):
            candidate_id = f"candidate_{idx:02d}"
            active_axes, suppressed_axes = self._axis_profile_summary(
                row["vector"],
                PREMISE_AXIS_DEFS,
                active_count=6,
                suppressed_count=3,
                label_overrides=PREMISE_AXIS_MODEL_LABEL_OVERRIDES,
            )
            risk_active, risk_suppressed = self._axis_profile_summary(
                row["risk_overlay"],
                PREMISE_RISK_AXIS_DEFS,
                active_count=3,
                suppressed_count=2,
            )
            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "kind": row["kind"],
                    "vector": row["vector"],
                    "risk_overlay": row["risk_overlay"],
                    "active_axes": active_axes,
                    "suppressed_axes": suppressed_axes,
                    "vector_gloss": self._axis_gloss(active_axes, suppressed_axes),
                    "risk_gloss": self._axis_gloss(risk_active, risk_suppressed),
                    "scaffold_profile": scaffold_profile,
                    "scaffold_gloss": self._scaffold_profile_gloss(scaffold_profile),
                }
            )

        field_centroid = self._mean_axis_map(
            [row["vector"] for row in selected_rows], PREMISE_AXIS_DEFS
        )
        field_risk_centroid = self._mean_axis_map(
            [row["risk_overlay"] for row in selected_rows], PREMISE_RISK_AXIS_DEFS
        )

        return {
            "schema_version": 5,
            "legacy_resume": False,
            "seed": self.premise_seed,
            "derived_seed": derived_seed,
            "reroll_index": reroll_index,
            "candidate_count": len(candidates),
            "generation_batch_size": self.cfg.premise_generation_batch_size,
            "min_unique_clusters": self.cfg.premise_min_unique_clusters,
            "shortlist_size": self.cfg.premise_shortlist_size,
            "brief": self.cfg.premise_brief or "",
            "search_rubric": {
                "award_agnostic": True,
                "criteria": [
                    "long-book viability",
                    "range of scene textures",
                    "character and relational leverage",
                    "pressure that can mutate over time",
                    "world or place specificity",
                    "originality without gimmickry",
                    "aesthetic-risk headroom",
                ],
            },
            "search_strategy": "independent_spread_vectors_with_abstract_scaffolds",
            "core_axes": list(PREMISE_AXIS_DEFS),
            "risk_axes": list(PREMISE_RISK_AXIS_DEFS),
            "field_centroid": field_centroid,
            "field_gloss": self._build_field_gloss(candidates),
            "field_risk_centroid": field_risk_centroid,
            "field_risk_gloss": self._axis_gloss(
                *self._axis_profile_summary(
                    field_risk_centroid,
                    PREMISE_RISK_AXIS_DEFS,
                    active_count=3,
                    suppressed_count=2,
                )
            ),
            "scaffold_dimensions": {
                "scene_source": [
                    {"name": row["name"], "label": row["label"]}
                    for row in PREMISE_SCAFFOLD_SCENE_SOURCE_DEFS
                ],
                "social_geometry": [
                    {"name": row["name"], "label": row["label"]}
                    for row in PREMISE_SCAFFOLD_SOCIAL_GEOMETRY_DEFS
                ],
                "narrative_motion": [
                    {"name": row["name"], "label": row["label"]}
                    for row in PREMISE_SCAFFOLD_NARRATIVE_MOTION_DEFS
                ],
                "mode_overlay": [
                    {"name": row["name"], "label": row["label"]}
                    for row in PREMISE_SCAFFOLD_MODE_DEFS
                ],
            },
            "candidates": candidates,
        }

    def _sample_spread_axis_map(
        self,
        rng: random.Random,
        defs: tuple[dict[str, str], ...],
        *,
        hot_range: tuple[int, int],
        cold_range: tuple[int, int],
        high_range: tuple[float, float],
        low_range: tuple[float, float],
        middle_range: tuple[float, float],
    ) -> dict[str, float]:
        names = [row["name"] for row in defs]
        hot_count = min(len(names), rng.randint(*hot_range))
        hot_names = set(rng.sample(names, hot_count))
        remaining = [name for name in names if name not in hot_names]
        cold_count = min(len(remaining), rng.randint(*cold_range))
        cold_names = set(rng.sample(remaining, cold_count))
        out: dict[str, float] = {}
        for name in names:
            if name in hot_names:
                value = rng.uniform(*high_range)
            elif name in cold_names:
                value = rng.uniform(*low_range)
            else:
                value = rng.uniform(*middle_range)
            out[name] = round(min(1.0, max(0.0, value)), 3)
        return out

    def _midpoint_axis_map(
        self, defs: tuple[dict[str, str], ...]
    ) -> dict[str, float]:
        return {row["name"]: 0.5 for row in defs}

    def _mean_axis_map(
        self,
        rows: list[dict[str, float]],
        defs: tuple[dict[str, str], ...],
    ) -> dict[str, float]:
        if not rows:
            return self._midpoint_axis_map(defs)
        out: dict[str, float] = {}
        for row in defs:
            name = row["name"]
            out[name] = round(
                sum(float(item.get(name, 0.5)) for item in rows) / len(rows), 3
            )
        return out

    def _build_field_gloss(self, candidates: list[dict[str, Any]]) -> str:
        active_counts: dict[str, int] = {}
        label_map: dict[str, str] = {}
        for candidate in candidates:
            for row in candidate.get("active_axes", []):
                axis = str(row.get("axis", "")).strip()
                if axis:
                    active_counts[axis] = active_counts.get(axis, 0) + 1
                    label = str(row.get("label", "")).strip()
                    if label:
                        label_map.setdefault(axis, label)
        active_labels = [
            label_map[axis]
            for axis, _count in sorted(
                active_counts.items(), key=lambda item: (-item[1], item[0])
            )[:4]
            if axis in label_map
        ]
        bits = ["Field built from independently sampled vectors selected for spread."]
        if active_labels:
            bits.append(
                "Recurring strong axes include " + ", ".join(active_labels) + "."
            )
        return " ".join(bits)

    def _sample_axis_map(
        self,
        rng: random.Random,
        defs: tuple[dict[str, str], ...],
        centered: bool,
    ) -> dict[str, float]:
        out: dict[str, float] = {}
        for row in defs:
            if centered:
                value = 0.15 + 0.70 * ((rng.random() + rng.random()) / 2.0)
            else:
                value = rng.random()
            out[row["name"]] = round(value, 3)
        return out

    def _assign_scaffold_profiles(
        self, selected_rows: list[dict[str, Any]], rng: random.Random
    ) -> list[dict[str, Any]]:
        scene_counts: dict[str, int] = {}
        social_counts: dict[str, int] = {}
        motion_counts: dict[str, int] = {}
        mode_counts: dict[str, int] = {}
        profiles: list[dict[str, Any]] = []
        for row in selected_rows:
            active_names, suppressed_names = self._axis_name_profile(
                row["vector"], PREMISE_AXIS_DEFS, active_count=8, suppressed_count=4
            )
            risk_active_names, _risk_suppressed = self._axis_name_profile(
                row["risk_overlay"],
                PREMISE_RISK_AXIS_DEFS,
                active_count=3,
                suppressed_count=1,
            )
            profile = {
                "scene_source": self._pick_scaffold_option(
                    rng,
                    PREMISE_SCAFFOLD_SCENE_SOURCE_DEFS,
                    active_names=active_names,
                    suppressed_names=suppressed_names,
                    counts=scene_counts,
                ),
                "social_geometry": self._pick_scaffold_option(
                    rng,
                    PREMISE_SCAFFOLD_SOCIAL_GEOMETRY_DEFS,
                    active_names=active_names,
                    suppressed_names=suppressed_names,
                    counts=social_counts,
                ),
                "narrative_motion": self._pick_scaffold_option(
                    rng,
                    PREMISE_SCAFFOLD_NARRATIVE_MOTION_DEFS,
                    active_names=active_names,
                    suppressed_names=suppressed_names,
                    counts=motion_counts,
                ),
            }
            mode_pool = active_names + risk_active_names
            primary_mode = self._pick_scaffold_option(
                rng,
                PREMISE_SCAFFOLD_MODE_DEFS,
                active_names=mode_pool,
                suppressed_names=suppressed_names,
                counts=mode_counts,
            )
            secondary_mode = self._pick_scaffold_option(
                rng,
                PREMISE_SCAFFOLD_MODE_DEFS,
                active_names=mode_pool,
                suppressed_names=suppressed_names,
                counts=mode_counts,
                disallow={str(primary_mode.get("name", ""))},
            )
            profile["mode_overlays"] = [primary_mode]
            if secondary_mode:
                profile["mode_overlays"].append(secondary_mode)
            profiles.append(profile)
        return profiles

    def _pick_scaffold_option(
        self,
        rng: random.Random,
        defs: tuple[dict[str, Any], ...],
        *,
        active_names: list[str],
        suppressed_names: list[str],
        counts: dict[str, int],
        disallow: set[str] | None = None,
    ) -> dict[str, str]:
        blocked = disallow or set()
        best_rows: list[tuple[float, dict[str, Any]]] = []
        for row in defs:
            name = str(row.get("name", "")).strip()
            if not name or name in blocked:
                continue
            affinity = tuple(
                str(item).strip()
                for item in row.get("affinity", ())
                if str(item).strip()
            )
            affinity_hits = sum(1 for item in affinity if item in active_names)
            suppressed_penalty = sum(1 for item in affinity if item in suppressed_names)
            count = counts.get(name, 0)
            score = (
                affinity_hits * 1.0
                - suppressed_penalty * 0.45
                + (0.9 if count == 0 else max(0.0, 0.35 - 0.15 * count))
                - 0.22 * count
                + rng.random() * 0.18
            )
            best_rows.append((score, row))
        if not best_rows:
            return {"name": "", "label": "", "gloss": ""}
        best_rows.sort(key=lambda item: item[0], reverse=True)
        top_score = best_rows[0][0]
        viable = [row for score, row in best_rows if score >= top_score - 0.22]
        chosen = dict(rng.choice(viable))
        name = str(chosen.get("name", "")).strip()
        if name:
            counts[name] = counts.get(name, 0) + 1
        return {
            "name": name,
            "label": str(chosen.get("label", "")).strip(),
            "gloss": str(chosen.get("gloss", "")).strip(),
        }

    def _scaffold_profile_gloss(self, profile: dict[str, Any]) -> str:
        scene = profile.get("scene_source", {})
        social = profile.get("social_geometry", {})
        motion = profile.get("narrative_motion", {})
        modes = profile.get("mode_overlays", [])
        mode_labels = [
            str(row.get("label", "")).strip()
            for row in modes
            if isinstance(row, dict) and str(row.get("label", "")).strip()
        ]
        bits = []
        if str(scene.get("label", "")).strip():
            bits.append(f"scene source: {scene['label']}")
        if str(social.get("label", "")).strip():
            bits.append(f"social geometry: {social['label']}")
        if str(motion.get("label", "")).strip():
            bits.append(f"narrative motion: {motion['label']}")
        if mode_labels:
            bits.append("mode overlays: " + ", ".join(mode_labels))
        return "; ".join(bits)

    def _sample_candidate_axis_map(
        self,
        rng: random.Random,
        run_map: dict[str, float],
        scale: float,
        wildcard: bool,
    ) -> dict[str, float]:
        out: dict[str, float] = {}
        for name, base in run_map.items():
            value = base + rng.uniform(-scale, scale)
            if wildcard and rng.random() < 0.35:
                value = rng.uniform(0.0, 0.15) if rng.random() < 0.5 else rng.uniform(0.85, 1.0)
            out[name] = round(min(1.0, max(0.0, value)), 3)
        return out

    def _greedy_select_vectors(
        self,
        pool: list[dict[str, Any]],
        run_vector: dict[str, float],
        count: int,
        existing: list[dict[str, Any]] | None = None,
        diversify_axis_profiles: bool = False,
    ) -> list[dict[str, Any]]:
        if count <= 0 or not pool:
            return []
        selected: list[dict[str, Any]] = []
        taken: set[int] = set()
        anchors = list(existing or [])
        active_counts: dict[str, int] = {}
        suppressed_counts: dict[str, int] = {}
        risk_active_counts: dict[str, int] = {}
        while len(selected) < count and len(taken) < len(pool):
            best_idx = -1
            best_score = -1.0
            for idx, row in enumerate(pool):
                if idx in taken:
                    continue
                distance_to_run = self._vector_distance_score(
                    row["vector"], run_vector, row["risk_overlay"], None
                )
                if selected or anchors:
                    compare_rows = anchors + selected
                    spread = min(
                        self._vector_distance_score(
                            row["vector"],
                            other["vector"],
                            row["risk_overlay"],
                            other["risk_overlay"],
                    )
                        for other in compare_rows
                    )
                    score = distance_to_run * 0.25 + spread
                else:
                    score = distance_to_run
                if diversify_axis_profiles:
                    active_names = self._axis_name_profile(
                        row["vector"], PREMISE_AXIS_DEFS, active_count=6, suppressed_count=3
                    )[0]
                    suppressed_names = self._axis_name_profile(
                        row["vector"], PREMISE_AXIS_DEFS, active_count=6, suppressed_count=3
                    )[1]
                    risk_active_names = self._axis_name_profile(
                        row["risk_overlay"],
                        PREMISE_RISK_AXIS_DEFS,
                        active_count=2,
                        suppressed_count=1,
                    )[0]
                    novelty_bonus = (
                        0.12
                        * sum(1 for name in active_names if active_counts.get(name, 0) == 0)
                        + 0.05
                        * sum(
                            1
                            for name in suppressed_names
                            if suppressed_counts.get(name, 0) == 0
                        )
                        + 0.07
                        * sum(
                            1
                            for name in risk_active_names
                            if risk_active_counts.get(name, 0) == 0
                        )
                    )
                    repetition_penalty = (
                        0.08 * sum(active_counts.get(name, 0) for name in active_names)
                        + 0.03
                        * sum(
                            suppressed_counts.get(name, 0)
                            for name in suppressed_names
                        )
                        + 0.05
                        * sum(
                            risk_active_counts.get(name, 0)
                            for name in risk_active_names
                        )
                    )
                    score += novelty_bonus - repetition_penalty
                if score > best_score:
                    best_idx = idx
                    best_score = score
            if best_idx < 0:
                break
            taken.add(best_idx)
            chosen = pool[best_idx]
            selected.append(chosen)
            if diversify_axis_profiles:
                active_names, suppressed_names = self._axis_name_profile(
                    chosen["vector"], PREMISE_AXIS_DEFS, active_count=6, suppressed_count=3
                )
                risk_active_names, _risk_suppressed = self._axis_name_profile(
                    chosen["risk_overlay"],
                    PREMISE_RISK_AXIS_DEFS,
                    active_count=2,
                    suppressed_count=1,
                )
                for name in active_names:
                    active_counts[name] = active_counts.get(name, 0) + 1
                for name in suppressed_names:
                    suppressed_counts[name] = suppressed_counts.get(name, 0) + 1
                for name in risk_active_names:
                    risk_active_counts[name] = risk_active_counts.get(name, 0) + 1
        return selected

    def _vector_distance_score(
        self,
        a: dict[str, float],
        b: dict[str, float],
        risk_a: dict[str, float] | None,
        risk_b: dict[str, float] | None,
    ) -> float:
        score = 0.0
        for name in a:
            av = float(a.get(name, 0.0))
            bv = float(b.get(name, 0.5))
            score += (av - bv) ** 2
        if risk_a is not None and risk_b is not None:
            for name in risk_a:
                av = float(risk_a.get(name, 0.0))
                bv = float(risk_b.get(name, 0.0))
                score += 0.65 * ((av - bv) ** 2)
        return score

    def _axis_profile_summary(
        self,
        values: dict[str, float],
        defs: tuple[dict[str, str], ...],
        *,
        active_count: int,
        suppressed_count: int,
        label_overrides: dict[str, str] | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        rows = [
            {
                "axis": row["name"],
                "label": (
                    label_overrides.get(row["name"], row["label"])
                    if label_overrides
                    else row["label"]
                ),
                "value": round(float(values.get(row["name"], 0.0)), 3),
            }
            for row in defs
        ]
        active = sorted(rows, key=lambda row: row["value"], reverse=True)[:active_count]
        suppressed = sorted(rows, key=lambda row: row["value"])[:suppressed_count]
        return active, suppressed

    def _axis_name_profile(
        self,
        values: dict[str, float],
        defs: tuple[dict[str, str], ...],
        *,
        active_count: int,
        suppressed_count: int,
    ) -> tuple[list[str], list[str]]:
        active, suppressed = self._axis_profile_summary(
            values,
            defs,
            active_count=active_count,
            suppressed_count=suppressed_count,
        )
        return (
            [str(row.get("axis", "")).strip() for row in active if str(row.get("axis", "")).strip()],
            [
                str(row.get("axis", "")).strip()
                for row in suppressed
                if str(row.get("axis", "")).strip()
            ],
        )

    def _axis_gloss(
        self,
        active_axes: list[dict[str, Any]],
        suppressed_axes: list[dict[str, Any]],
    ) -> str:
        active_bits = [
            f"{self._high_intensity_word(float(row['value']))} {row['label']}"
            for row in active_axes[:4]
        ]
        suppressed_bits = [
            f"{self._low_intensity_word(float(row['value']))} {row['label']}"
            for row in suppressed_axes[:2]
        ]
        bits = active_bits + suppressed_bits
        return ", ".join(bits)

    def _high_intensity_word(self, value: float) -> str:
        if value >= 0.85:
            return "very high"
        if value >= 0.68:
            return "high"
        if value >= 0.55:
            return "moderate-high"
        return "present"

    def _low_intensity_word(self, value: float) -> str:
        if value <= 0.12:
            return "very low"
        if value <= 0.28:
            return "low"
        return "muted"

    def _run_premise_candidates_stage(
        self, search_plan: dict[str, Any]
    ) -> list[dict[str, Any]]:
        reroll_index = int(search_plan.get("reroll_index", 0))
        batch_size = max(
            1,
            int(
                search_plan.get(
                    "generation_batch_size", self.cfg.premise_generation_batch_size
                )
            ),
        )
        all_candidates = list(search_plan.get("candidates", []))
        combined_rows: list[dict[str, Any]] = []
        batch_count = max(1, math.ceil(len(all_candidates) / batch_size))
        for batch_index in range(batch_count):
            batch_candidates = all_candidates[
                batch_index * batch_size : (batch_index + 1) * batch_size
            ]
            batch_plan_rel = f"premise/batches/batch_{batch_index + 1:02d}.search_plan.json"
            batch_output_rel = (
                f"premise/batches/batch_{batch_index + 1:02d}.candidates.jsonl"
            )
            batch_plan = self._build_premise_batch_plan(
                search_plan,
                batch_candidates,
                batch_index + 1,
                batch_count,
                combined_rows,
            )
            self._write_json(batch_plan_rel, batch_plan)
            prompt = self._render_prompt(
                "premise_candidates_prompt.md",
                {
                    "PREMISE_BRIEF_BLOCK": self._premise_brief_block(),
                    "PREMISE_SEARCH_PLAN_FILE": batch_plan_rel,
                    "PREMISE_CANDIDATES_OUTPUT_FILE": batch_output_rel,
                },
            )
            job = self._make_job(
                job_id=(
                    f"premise_candidates_reroll_{reroll_index:02d}_"
                    f"batch_{batch_index + 1:02d}"
                ),
                stage="premise_candidates",
                stage_group="premise",
                cycle=0,
                chapter_id=None,
                allowed_inputs=[
                    batch_plan_rel,
                    "config/prompts/premise_candidates_prompt.md",
                ],
                required_outputs=[batch_output_rel],
                prompt_text=prompt,
            )
            self._run_job(job)
            batch_rows = self._load_jsonl_from_path(
                self.run_dir / batch_output_rel, label=batch_output_rel
            )
            combined_rows.extend(self._validate_premise_candidates(batch_plan, batch_rows))
        self._write_jsonl("premise/premise_candidates.jsonl", combined_rows)
        return self._validate_premise_candidates(search_plan, combined_rows)

    def _build_premise_batch_plan(
        self,
        search_plan: dict[str, Any],
        batch_candidates: list[dict[str, Any]],
        batch_index: int,
        batch_count: int,
        prior_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "schema_version": search_plan.get("schema_version", 0),
            "seed": search_plan.get("seed", ""),
            "derived_seed": search_plan.get("derived_seed", ""),
            "reroll_index": search_plan.get("reroll_index", 0),
            "brief": search_plan.get("brief", ""),
            "search_rubric": search_plan.get("search_rubric", {}),
            "search_strategy": search_plan.get("search_strategy", ""),
            "core_axes": search_plan.get("core_axes", []),
            "risk_axes": search_plan.get("risk_axes", []),
            "scaffold_dimensions": search_plan.get("scaffold_dimensions", {}),
            "batch_index": batch_index,
            "batch_count": batch_count,
            "candidate_count": len(batch_candidates),
            "candidates": batch_candidates,
            "prior_batch_repetition_warning": self._build_prior_batch_repetition_warning(
                search_plan,
                prior_rows,
            ),
        }

    def _build_prior_batch_repetition_warning(
        self,
        search_plan: dict[str, Any],
        prior_rows: list[dict[str, Any]],
    ) -> str:
        if not prior_rows:
            return ""
        prior_text = " ".join(
            " ".join(
                [
                    str(row.get("premise", "")),
                    str(row.get("engine_guess", "")),
                    str(row.get("pressure_descriptor", "")),
                    str(row.get("setting_descriptor", "")),
                ]
                )
            for row in prior_rows
        ).lower()
        warnings: list[str] = []
        plan_candidate_map = {
            str(row.get("candidate_id", "")).strip(): row
            for row in search_plan.get("candidates", [])
            if isinstance(row, dict) and str(row.get("candidate_id", "")).strip()
        }
        scene_counts: dict[str, int] = {}
        motion_counts: dict[str, int] = {}
        scene_motion_counts: dict[tuple[str, str], int] = {}
        scene_label_map = {
            row["name"]: row["label"] for row in PREMISE_SCAFFOLD_SCENE_SOURCE_DEFS
        }
        motion_label_map = {
            row["name"]: row["label"] for row in PREMISE_SCAFFOLD_NARRATIVE_MOTION_DEFS
        }
        for row in prior_rows:
            candidate_id = str(row.get("candidate_id", "")).strip()
            profile = plan_candidate_map.get(candidate_id, {}).get("scaffold_profile", {})
            scene, _social, motion, _modes = self._extract_scaffold_profile_names(profile)
            if scene:
                scene_counts[scene] = scene_counts.get(scene, 0) + 1
            if motion:
                motion_counts[motion] = motion_counts.get(motion, 0) + 1
            if scene and motion:
                key = (scene, motion)
                scene_motion_counts[key] = scene_motion_counts.get(key, 0) + 1
        record_tokens = (
            "record",
            "records",
            "ledger",
            "ledgers",
            "archive",
            "archives",
            "paperwork",
            "certificate",
            "certificates",
            "chart",
            "charts",
            "notice",
            "notices",
            "register",
            "registers",
            "file",
            "files",
            "compliance",
            "protocol",
            "protocols",
            "checklist",
            "checklists",
            "audit",
            "audits",
            "report",
            "reports",
            "claim",
            "claims",
            "book",
            "books",
            "notes",
            "notebook",
        )
        role_tokens = (
            "clerk",
            "inspector",
            "auditor",
            "compliance director",
            "operator",
            "coroner",
            "cashier",
            "probation officer",
            "public defender",
        )
        if sum(prior_text.count(token) for token in record_tokens) >= 4:
            warnings.append(
                "Earlier batches already leaned on formal records, certification, or administrative truth-decisions to make premises concrete. In this batch, prefer other forms of legibility unless a candidate's steering makes documentary machinery unavoidable."
            )
        if sum(prior_text.count(token) for token in role_tokens) >= 3:
            warnings.append(
                "Earlier batches already used several protagonists or scene engines built around clerks, inspectors, compliance staff, or adjacent gatekeeping roles. Push this batch toward other social positions if the remaining vectors allow it."
            )
        if scene_counts:
            top_scene, top_scene_count = max(
                scene_counts.items(), key=lambda item: (item[1], item[0])
            )
            if top_scene_count >= 3:
                warnings.append(
                    "Earlier batches already leaned on the same scene source too often, especially "
                    f"'{scene_label_map.get(top_scene, top_scene)}'. Shift where scenes arise instead of lightly re-skinning the same engine."
                )
        if motion_counts:
            top_motion, top_motion_count = max(
                motion_counts.items(), key=lambda item: (item[1], item[0])
            )
            if top_motion_count >= 3:
                warnings.append(
                    "Earlier batches already repeated one narrative motion too often, especially "
                    f"'{motion_label_map.get(top_motion, top_motion)}'. Change how pressure evolves over the book."
                )
        if scene_motion_counts:
            (top_scene, top_motion), top_pair_count = max(
                scene_motion_counts.items(), key=lambda item: (item[1], item[0])
            )
            if top_pair_count >= 2:
                warnings.append(
                    "Earlier batches already reused the same scaffold pattern, especially "
                    f"'{scene_label_map.get(top_scene, top_scene)}' plus "
                    f"'{motion_label_map.get(top_motion, top_motion)}'. Do not solve this batch by re-skinning that same deeper book-motion."
                )
        if not warnings:
            warnings.append(
                "Earlier batches already established some concrete engines. Do not solve the current batch by lightly re-skinning the same verification, gatekeeping, or record-management scaffold."
            )
        return " ".join(warnings)

    def _run_premise_uniqueness_clustering_stage(
        self, search_plan: dict[str, Any], candidates: list[dict[str, Any]]
    ) -> dict[str, Any]:
        reroll_index = int(search_plan.get("reroll_index", 0))
        prompt = self._render_prompt(
            "premise_uniqueness_clustering_prompt.md",
            {
                "PREMISE_BRIEF_BLOCK": self._premise_brief_block(),
                "PREMISE_MIN_UNIQUE_CLUSTERS": str(
                    search_plan.get(
                        "min_unique_clusters", self.cfg.premise_min_unique_clusters
                    )
                ),
            },
        )
        job = self._make_job(
            job_id=f"premise_uniqueness_clustering_reroll_{reroll_index:02d}",
            stage="premise_uniqueness_clustering",
            stage_group="premise",
            cycle=0,
            chapter_id=None,
            allowed_inputs=[
                "premise/premise_search_plan.json",
                "premise/premise_candidates.jsonl",
                "config/prompts/premise_uniqueness_clustering_prompt.md",
            ],
            required_outputs=["premise/uniqueness_clusters.json"],
            prompt_text=prompt,
        )
        self._run_job(job)
        return self._load_and_validate_premise_uniqueness_clusters(
            search_plan, candidates
        )

    def _load_and_validate_premise_candidates(
        self, search_plan: dict[str, Any]
    ) -> list[dict[str, Any]]:
        rows = self._read_jsonl("premise/premise_candidates.jsonl")
        return self._validate_premise_candidates(search_plan, rows)

    def _load_and_validate_premise_uniqueness_clusters(
        self,
        search_plan: dict[str, Any],
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        data = self._read_json("premise/uniqueness_clusters.json")
        self._validate_premise_uniqueness_clusters(search_plan, candidates, data)
        return data

    def _load_and_validate_premise_selection(
        self,
        search_plan: dict[str, Any],
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        data = self._read_json("premise/selection.json")
        return data

    def _validate_generated_premise_artifacts(self) -> None:
        premise = (self.run_dir / "input" / "premise.txt").read_text(encoding="utf-8").strip()
        self._validate_generated_premise(premise)
        search_plan = self._read_json("premise/premise_search_plan.json")
        self._validate_premise_search_plan(search_plan)
        if self.cfg.premise_seed:
            expected_seed = self._normalize_premise_seed(self.cfg.premise_seed)
            actual_seed = str(search_plan.get("seed", "")).strip()
            if actual_seed != expected_seed:
                raise PipelineError(
                    "generated premise search seed does not match the current CLI seed"
                )
        candidates = self._load_and_validate_premise_candidates(search_plan)
        candidate_map = {row["candidate_id"]: row for row in candidates}
        uniqueness = self._load_and_validate_premise_uniqueness_clusters(
            search_plan, candidates
        )
        selection = self._load_and_validate_premise_selection(search_plan, candidates)
        self._validate_random_premise_selection_json(
            search_plan, candidates, uniqueness, selection
        )
        selected_candidate_id = str(selection["selected_candidate_id"]).strip()
        selected_premise = str(candidate_map[selected_candidate_id]["premise"]).strip()
        if premise != selected_premise:
            raise PipelineError(
                "input/premise.txt does not match the selected candidate premise"
            )
        self._validate_premise_brainstorming(
            selected_premise, self.run_dir / "premise" / "premise_brainstorming.md"
        )
        self.premise_seed = str(search_plan.get("seed", "")).strip() or self.premise_seed
        self.premise_reroll_count = int(search_plan.get("reroll_index", 0))

    def _validate_premise_search_plan(self, data: dict[str, Any]) -> None:
        required_keys = [
            "schema_version",
            "seed",
            "derived_seed",
            "reroll_index",
            "candidate_count",
            "core_axes",
            "risk_axes",
            "candidates",
        ]
        missing = [key for key in required_keys if key not in data]
        if missing:
            raise PipelineError(
                "premise search plan missing required keys: " + ", ".join(missing)
            )
        schema_version = int(data.get("schema_version", 0))
        if schema_version >= 4:
            extra_required = [
                "search_strategy",
                "field_centroid",
                "field_gloss",
                "field_risk_centroid",
            ]
        else:
            extra_required = [
                "run_vector",
                "run_risk_overlay",
            ]
        if schema_version >= 5:
            extra_required.append("scaffold_dimensions")
        extra_missing = [key for key in extra_required if key not in data]
        if extra_missing:
            raise PipelineError(
                "premise search plan missing required keys: " + ", ".join(extra_missing)
            )
        if not isinstance(data["candidates"], list) or not data["candidates"]:
            raise PipelineError("premise search plan candidates must be a non-empty array")
        if int(data.get("candidate_count", 0)) != len(data["candidates"]):
            raise PipelineError("premise search plan candidate_count does not match candidates")
        if int(data.get("candidate_count", 0)) <= 0:
            raise PipelineError("premise search plan candidate_count must be positive")
        scaffold_dimensions = data.get("scaffold_dimensions", {})
        if schema_version >= 5:
            self._validate_premise_scaffold_dimensions(scaffold_dimensions)
        candidate_ids: set[str] = set()
        for idx, row in enumerate(data["candidates"], start=1):
            if not isinstance(row, dict):
                raise PipelineError(f"premise search plan candidate #{idx} must be an object")
            candidate_id = str(row.get("candidate_id", "")).strip()
            if not candidate_id:
                raise PipelineError(f"premise search plan candidate #{idx} missing candidate_id")
            if candidate_id in candidate_ids:
                raise PipelineError(f"duplicate premise search plan candidate_id: {candidate_id}")
            candidate_ids.add(candidate_id)
            vector = row.get("vector")
            risk_overlay = row.get("risk_overlay")
            if not isinstance(vector, dict) or not vector:
                raise PipelineError(
                    f"premise search plan candidate {candidate_id} missing vector"
                )
            if not isinstance(risk_overlay, dict) or not risk_overlay:
                raise PipelineError(
                    f"premise search plan candidate {candidate_id} missing risk_overlay"
                )
            if not isinstance(row.get("active_axes"), list) or not row.get("active_axes"):
                raise PipelineError(
                    f"premise search plan candidate {candidate_id} missing active_axes"
                )
            if not isinstance(row.get("suppressed_axes"), list) or not row.get("suppressed_axes"):
                raise PipelineError(
                    f"premise search plan candidate {candidate_id} missing suppressed_axes"
                )
            if not str(row.get("vector_gloss", "")).strip():
                raise PipelineError(
                    f"premise search plan candidate {candidate_id} missing vector_gloss"
                )
            if not str(row.get("risk_gloss", "")).strip():
                raise PipelineError(
                    f"premise search plan candidate {candidate_id} missing risk_gloss"
                )
            if schema_version >= 5:
                self._validate_premise_scaffold_profile(
                    row.get("scaffold_profile", {}),
                    scaffold_dimensions,
                    candidate_id=candidate_id,
                )
                if not str(row.get("scaffold_gloss", "")).strip():
                    raise PipelineError(
                        f"premise search plan candidate {candidate_id} missing scaffold_gloss"
                    )

    def _validate_premise_scaffold_dimensions(self, data: Any) -> None:
        if not isinstance(data, dict):
            raise PipelineError("premise search plan scaffold_dimensions must be an object")
        required = (
            "scene_source",
            "social_geometry",
            "narrative_motion",
            "mode_overlay",
        )
        missing = [key for key in required if key not in data]
        if missing:
            raise PipelineError(
                "premise search plan scaffold_dimensions missing required keys: "
                + ", ".join(missing)
            )
        for key in required:
            rows = data.get(key)
            if not isinstance(rows, list) or not rows:
                raise PipelineError(
                    f"premise search plan scaffold_dimensions {key} must be a non-empty array"
                )
            seen: set[str] = set()
            for idx, row in enumerate(rows, start=1):
                if not isinstance(row, dict):
                    raise PipelineError(
                        f"premise search plan scaffold_dimensions {key} row #{idx} must be an object"
                    )
                name = str(row.get("name", "")).strip()
                label = str(row.get("label", "")).strip()
                if not name or not label:
                    raise PipelineError(
                        f"premise search plan scaffold_dimensions {key} row #{idx} requires non-empty name and label"
                    )
                if name in seen:
                    raise PipelineError(
                        f"premise search plan scaffold_dimensions {key} duplicates name {name}"
                    )
                seen.add(name)

    def _validate_premise_scaffold_profile(
        self,
        data: Any,
        scaffold_dimensions: Any,
        *,
        candidate_id: str,
    ) -> None:
        if not isinstance(data, dict):
            raise PipelineError(
                f"premise search plan candidate {candidate_id} scaffold_profile must be an object"
            )
        if not isinstance(scaffold_dimensions, dict):
            raise PipelineError("premise search plan scaffold_dimensions must be an object")
        allowed_names = {
            key: {
                str(row.get("name", "")).strip()
                for row in rows
                if isinstance(row, dict) and str(row.get("name", "")).strip()
            }
            for key, rows in scaffold_dimensions.items()
            if isinstance(rows, list)
        }
        for key, dim_key in (
            ("scene_source", "scene_source"),
            ("social_geometry", "social_geometry"),
            ("narrative_motion", "narrative_motion"),
        ):
            row = data.get(key)
            if not isinstance(row, dict):
                raise PipelineError(
                    f"premise search plan candidate {candidate_id} scaffold_profile.{key} must be an object"
                )
            name = str(row.get("name", "")).strip()
            label = str(row.get("label", "")).strip()
            gloss = str(row.get("gloss", "")).strip()
            if not name or not label or not gloss:
                raise PipelineError(
                    f"premise search plan candidate {candidate_id} scaffold_profile.{key} requires non-empty name, label, and gloss"
                )
            if name not in allowed_names.get(dim_key, set()):
                raise PipelineError(
                    f"premise search plan candidate {candidate_id} scaffold_profile.{key} references unknown scaffold option {name}"
                )
        modes = data.get("mode_overlays")
        if not isinstance(modes, list) or not modes:
            raise PipelineError(
                f"premise search plan candidate {candidate_id} scaffold_profile.mode_overlays must be a non-empty array"
            )
        seen_modes: set[str] = set()
        for idx, row in enumerate(modes, start=1):
            if not isinstance(row, dict):
                raise PipelineError(
                    f"premise search plan candidate {candidate_id} scaffold_profile.mode_overlays row #{idx} must be an object"
                )
            name = str(row.get("name", "")).strip()
            label = str(row.get("label", "")).strip()
            gloss = str(row.get("gloss", "")).strip()
            if not name or not label or not gloss:
                raise PipelineError(
                    f"premise search plan candidate {candidate_id} scaffold_profile.mode_overlays row #{idx} requires non-empty name, label, and gloss"
                )
            if name in seen_modes:
                raise PipelineError(
                    f"premise search plan candidate {candidate_id} scaffold_profile.mode_overlays duplicates {name}"
                )
            seen_modes.add(name)
            if name not in allowed_names.get("mode_overlay", set()):
                raise PipelineError(
                    f"premise search plan candidate {candidate_id} scaffold_profile.mode_overlays references unknown scaffold option {name}"
                )

    def _validate_premise_candidates(
        self, search_plan: dict[str, Any], rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if not rows:
            raise PipelineError("premise candidates file is empty")
        expected_ids = [
            str(row.get("candidate_id", "")).strip()
            for row in search_plan.get("candidates", [])
            if str(row.get("candidate_id", "")).strip()
        ]
        got_ids: list[str] = []
        for idx, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                raise PipelineError(f"premise candidates row #{idx} is not a JSON object")
            candidate_id = str(row.get("candidate_id", "")).strip()
            premise = str(row.get("premise", "")).strip()
            if not candidate_id:
                raise PipelineError(f"premise candidates row #{idx} missing candidate_id")
            if candidate_id in got_ids:
                raise PipelineError(f"duplicate candidate_id in premise candidates: {candidate_id}")
            got_ids.append(candidate_id)
            if not premise:
                raise PipelineError(f"premise candidates row #{idx} has empty premise")
            if len(premise.split()) > 220:
                raise PipelineError(
                    f"premise candidates row #{idx} premise is too long (>220 words)"
                )
            for key in (
                "engine_guess",
                "protagonist_descriptor",
                "pressure_descriptor",
                "setting_descriptor",
                "why_it_might_work",
                "risk",
            ):
                if not str(row.get(key, "")).strip():
                    raise PipelineError(
                        f"premise candidates row #{idx} missing non-empty field: {key}"
                    )
        if got_ids != expected_ids:
            raise PipelineError(
                "premise candidates ids do not match search plan candidate ids"
            )
        return rows

    def _validate_premise_uniqueness_clusters(
        self,
        search_plan: dict[str, Any],
        candidates: list[dict[str, Any]],
        data: dict[str, Any],
    ) -> None:
        if str(data.get("seed", "")).strip() != str(search_plan.get("seed", "")).strip():
            raise PipelineError("premise uniqueness clusters seed does not match search plan")
        reroll_index = int(search_plan.get("reroll_index", 0))
        if int(data.get("reroll_index", reroll_index)) != reroll_index:
            raise PipelineError(
                "premise uniqueness clusters reroll_index does not match search plan"
            )
        clusters = data.get("clusters")
        if not isinstance(clusters, list) or not clusters:
            raise PipelineError("premise uniqueness clusters must be a non-empty array")
        candidate_ids = {row["candidate_id"] for row in candidates}
        seen_ids: set[str] = set()
        cluster_ids: set[str] = set()
        for idx, row in enumerate(clusters, start=1):
            if not isinstance(row, dict):
                raise PipelineError(f"premise uniqueness cluster #{idx} must be an object")
            cluster_id = str(row.get("cluster_id", "")).strip()
            if not cluster_id:
                raise PipelineError(f"premise uniqueness cluster #{idx} missing cluster_id")
            if cluster_id in cluster_ids:
                raise PipelineError(f"duplicate premise uniqueness cluster_id: {cluster_id}")
            cluster_ids.add(cluster_id)
            member_ids = row.get("member_ids")
            if not isinstance(member_ids, list) or not member_ids:
                raise PipelineError(
                    f"premise uniqueness cluster {cluster_id} member_ids must be a non-empty array"
                )
            normalized_member_ids = [str(item).strip() for item in member_ids if str(item).strip()]
            if len(set(normalized_member_ids)) != len(normalized_member_ids):
                raise PipelineError(
                    f"premise uniqueness cluster {cluster_id} member_ids contains duplicates"
                )
            for candidate_id in normalized_member_ids:
                if candidate_id not in candidate_ids:
                    raise PipelineError(
                        f"premise uniqueness cluster {cluster_id} references unknown candidate: {candidate_id}"
                    )
                if candidate_id in seen_ids:
                    raise PipelineError(
                        f"premise uniqueness clusters assign candidate more than once: {candidate_id}"
                    )
                seen_ids.add(candidate_id)
            for key in (
                "similarity_summary",
                "shared_engine_shape",
                "shared_pressure_shape",
                "shared_world_shape",
            ):
                if not str(row.get(key, "")).strip():
                    raise PipelineError(
                        f"premise uniqueness cluster {cluster_id} missing non-empty {key}"
                    )
        if seen_ids != candidate_ids:
            missing_ids = sorted(candidate_ids - seen_ids)
            raise PipelineError(
                "premise uniqueness clusters must cover all candidates exactly once: "
                + ", ".join(missing_ids[:10])
            )
        if int(data.get("unique_cluster_count", 0)) != len(clusters):
            raise PipelineError(
                "premise uniqueness clusters unique_cluster_count does not match clusters"
            )
        min_unique = int(
            search_plan.get("min_unique_clusters", self.cfg.premise_min_unique_clusters)
        )
        field_is_unique = data.get("field_is_sufficiently_unique")
        if not isinstance(field_is_unique, bool):
            raise PipelineError(
                "premise uniqueness clusters field_is_sufficiently_unique must be boolean"
            )
        if field_is_unique and len(clusters) < min_unique:
            raise PipelineError(
                "premise uniqueness clusters marked field as sufficiently unique below threshold"
            )
        reason = data.get("insufficient_uniqueness_reason", "")
        if not isinstance(reason, str):
            raise PipelineError(
                "premise uniqueness clusters insufficient_uniqueness_reason must be string"
            )
        if not field_is_unique and not reason.strip():
            raise PipelineError(
                "premise uniqueness clusters must explain insufficient uniqueness"
            )

    def _validate_random_premise_selection_json(
        self,
        search_plan: dict[str, Any],
        candidates: list[dict[str, Any]],
        uniqueness: dict[str, Any],
        data: dict[str, Any],
    ) -> None:
        if str(data.get("selection_mode", "")).strip() != "cluster_dedup_then_seeded_random":
            raise PipelineError("premise selection selection_mode is invalid")
        candidate_ids = {row["candidate_id"] for row in candidates}
        selected_candidate_id = str(data.get("selected_candidate_id", "")).strip()
        if selected_candidate_id not in candidate_ids:
            raise PipelineError("premise selection selected_candidate_id is invalid")
        shortlist_ids = data.get("shortlist_ids")
        if not isinstance(shortlist_ids, list) or not shortlist_ids:
            raise PipelineError("premise selection shortlist_ids must be a non-empty array")
        normalized_shortlist = [str(item).strip() for item in shortlist_ids if str(item).strip()]
        if len(set(normalized_shortlist)) != len(normalized_shortlist):
            raise PipelineError("premise selection shortlist_ids contains duplicates")
        if selected_candidate_id not in normalized_shortlist:
            raise PipelineError("premise selection selected candidate is not in shortlist")
        for candidate_id in normalized_shortlist:
            if candidate_id not in candidate_ids:
                raise PipelineError(
                    f"premise selection shortlist references unknown candidate: {candidate_id}"
                )
        cluster_rows = uniqueness.get("clusters", [])
        cluster_map = {
            str(row.get("cluster_id", "")).strip(): {
                "members": {str(item).strip() for item in row.get("member_ids", []) if str(item).strip()}
            }
            for row in cluster_rows
            if isinstance(row, dict) and str(row.get("cluster_id", "")).strip()
        }
        representatives = data.get("cluster_representatives")
        if not isinstance(representatives, list) or not representatives:
            raise PipelineError(
                "premise selection cluster_representatives must be a non-empty array"
            )
        seen_rep_ids: set[str] = set()
        seen_cluster_ids: set[str] = set()
        rep_ids: set[str] = set()
        for idx, row in enumerate(representatives, start=1):
            if not isinstance(row, dict):
                raise PipelineError(
                    f"premise selection cluster_representatives #{idx} must be object"
                )
            cluster_id = str(row.get("cluster_id", "")).strip()
            representative_id = str(row.get("representative_id", "")).strip()
            member_ids = row.get("member_ids")
            if not cluster_id or cluster_id not in cluster_map:
                raise PipelineError(
                    f"premise selection representative #{idx} references unknown cluster"
                )
            if cluster_id in seen_cluster_ids:
                raise PipelineError(
                    f"premise selection cluster_representatives duplicates cluster {cluster_id}"
                )
            seen_cluster_ids.add(cluster_id)
            if representative_id not in cluster_map[cluster_id]["members"]:
                raise PipelineError(
                    f"premise selection representative {representative_id} not in cluster {cluster_id}"
                )
            if representative_id in seen_rep_ids:
                raise PipelineError(
                    f"premise selection cluster_representatives duplicates representative {representative_id}"
                )
            seen_rep_ids.add(representative_id)
            rep_ids.add(representative_id)
            if not isinstance(member_ids, list) or {
                str(item).strip() for item in member_ids if str(item).strip()
            } != cluster_map[cluster_id]["members"]:
                raise PipelineError(
                    f"premise selection representative #{idx} member_ids do not match cluster {cluster_id}"
                )
        if seen_cluster_ids != set(cluster_map):
            raise PipelineError(
                "premise selection cluster_representatives must cover every uniqueness cluster"
            )
        if not set(normalized_shortlist).issubset(rep_ids):
            raise PipelineError(
                "premise selection shortlist_ids must be drawn from cluster representatives"
            )
        expected_representatives = self._build_cluster_representatives(
            search_plan, uniqueness
        )
        if representatives != expected_representatives:
            raise PipelineError(
                "premise selection cluster_representatives do not match the deterministic representative draw"
            )
        expected_shortlist = self._build_unique_shortlist(
            search_plan, expected_representatives
        )
        if normalized_shortlist != expected_shortlist:
            raise PipelineError(
                "premise selection shortlist_ids do not match the deterministic shortlist"
            )
        selection_seed = str(data.get("selection_seed", "")).strip()
        if not selection_seed:
            raise PipelineError("premise selection selection_seed is empty")
        expected_selection_seed = self._derived_selection_seed(
            str(search_plan.get("derived_seed", "")).strip(),
            "final_selection",
        )
        if selection_seed != expected_selection_seed:
            raise PipelineError(
                "premise selection selection_seed does not match search plan"
            )
        random_draw_index = data.get("random_draw_index")
        if (
            not isinstance(random_draw_index, int)
            or isinstance(random_draw_index, bool)
            or random_draw_index < 0
            or random_draw_index >= len(normalized_shortlist)
        ):
            raise PipelineError("premise selection random_draw_index is invalid")
        if normalized_shortlist[random_draw_index] != selected_candidate_id:
            raise PipelineError(
                "premise selection random_draw_index does not match selected candidate"
            )
        expected_rng = random.Random(int(expected_selection_seed, 16))
        expected_draw_index = expected_rng.randrange(len(expected_shortlist))
        expected_candidate_id = expected_shortlist[expected_draw_index]
        if random_draw_index != expected_draw_index:
            raise PipelineError(
                "premise selection random_draw_index does not match deterministic draw"
            )
        if selected_candidate_id != expected_candidate_id:
            raise PipelineError(
                "premise selection selected candidate does not match deterministic draw"
            )
        if not str(data.get("selection_summary", "")).strip():
            raise PipelineError("premise selection summary is empty")

    def _write_uniqueness_selection_artifacts(
        self,
        search_plan: dict[str, Any],
        candidates: list[dict[str, Any]],
        uniqueness: dict[str, Any],
    ) -> str:
        cluster_representatives = self._build_cluster_representatives(
            search_plan, uniqueness
        )
        shortlist_ids = self._build_unique_shortlist(search_plan, cluster_representatives)
        selection_seed = self._derived_selection_seed(
            str(search_plan.get("derived_seed", "")), "final_selection"
        )
        ordered_shortlist = sorted(shortlist_ids)
        selection_rng = random.Random(int(selection_seed, 16))
        random_draw_index = selection_rng.randrange(len(ordered_shortlist))
        selected_candidate_id = ordered_shortlist[random_draw_index]
        candidate_map = {row["candidate_id"]: row for row in candidates}
        selected_premise = str(candidate_map[selected_candidate_id]["premise"]).strip()
        selection_payload = {
            "selection_mode": "cluster_dedup_then_seeded_random",
            "selected_candidate_id": selected_candidate_id,
            "shortlist_ids": ordered_shortlist,
            "cluster_representatives": cluster_representatives,
            "selection_seed": selection_seed,
            "random_draw_index": random_draw_index,
            "selection_summary": (
                f"Protected shortlist built from {len(cluster_representatives)} uniqueness clusters; "
                f"final premise drawn uniformly at random from {len(ordered_shortlist)} shortlisted representatives."
            ),
        }
        self._write_json("premise/selection.json", selection_payload)
        self._write_text("input/premise.txt", selected_premise + "\n")
        self._write_premise_brainstorming_from_uniqueness(
            search_plan=search_plan,
            candidates=candidates,
            uniqueness=uniqueness,
            cluster_representatives=cluster_representatives,
            shortlist_ids=ordered_shortlist,
            selection_seed=selection_seed,
            random_draw_index=random_draw_index,
            selected_candidate_id=selected_candidate_id,
        )
        self._validate_generated_premise(selected_premise)
        self._validate_premise_brainstorming(
            selected_premise, self.run_dir / "premise" / "premise_brainstorming.md"
        )
        return selected_premise

    def _build_cluster_representatives(
        self, search_plan: dict[str, Any], uniqueness: dict[str, Any]
    ) -> list[dict[str, Any]]:
        clusters = sorted(
            [row for row in uniqueness.get("clusters", []) if isinstance(row, dict)],
            key=lambda row: str(row.get("cluster_id", "")).strip(),
        )
        representatives: list[dict[str, Any]] = []
        derived_seed = str(search_plan.get("derived_seed", "")).strip()
        for row in clusters:
            cluster_id = str(row.get("cluster_id", "")).strip()
            member_ids = sorted(
                [str(item).strip() for item in row.get("member_ids", []) if str(item).strip()]
            )
            rep_seed = self._derived_selection_seed(derived_seed, f"cluster:{cluster_id}")
            rep_rng = random.Random(int(rep_seed, 16))
            representative_id = member_ids[rep_rng.randrange(len(member_ids))]
            representatives.append(
                {
                    "cluster_id": cluster_id,
                    "representative_id": representative_id,
                    "member_ids": member_ids,
                }
            )
        return representatives

    def _build_unique_shortlist(
        self,
        search_plan: dict[str, Any],
        cluster_representatives: list[dict[str, Any]],
    ) -> list[str]:
        shortlist_size = max(
            1, int(search_plan.get("shortlist_size", self.cfg.premise_shortlist_size))
        )
        representative_ids = [
            str(row.get("representative_id", "")).strip()
            for row in cluster_representatives
            if str(row.get("representative_id", "")).strip()
        ]
        if len(representative_ids) <= shortlist_size:
            return sorted(representative_ids)
        plan_candidates = {
            str(row.get("candidate_id", "")).strip(): row
            for row in search_plan.get("candidates", [])
            if str(row.get("candidate_id", "")).strip()
        }
        pool = [
            plan_candidates[candidate_id]
            for candidate_id in representative_ids
            if candidate_id in plan_candidates
        ]
        selected_rows = self._greedy_select_vectors(
            pool,
            search_plan.get("field_centroid", search_plan.get("run_vector", {})),
            count=shortlist_size,
        )
        shortlist = [
            str(row.get("candidate_id", "")).strip()
            for row in selected_rows
            if str(row.get("candidate_id", "")).strip()
        ]
        return sorted(shortlist)

    def _derived_selection_seed(self, base_seed: str, label: str) -> str:
        payload = f"{base_seed}:{label}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:32]

    def _extract_scaffold_profile_names(
        self, profile: dict[str, Any]
    ) -> tuple[str, str, str, list[str]]:
        if not isinstance(profile, dict):
            return "", "", "", []
        scene = str(profile.get("scene_source", {}).get("name", "")).strip()
        social = str(profile.get("social_geometry", {}).get("name", "")).strip()
        motion = str(profile.get("narrative_motion", {}).get("name", "")).strip()
        modes = [
            str(row.get("name", "")).strip()
            for row in profile.get("mode_overlays", [])
            if isinstance(row, dict) and str(row.get("name", "")).strip()
        ]
        return scene, social, motion, modes

    def _assess_scaffold_spread(self, search_plan: dict[str, Any]) -> dict[str, Any]:
        candidates = [
            row for row in search_plan.get("candidates", []) if isinstance(row, dict)
        ]
        if not candidates:
            return {"ok": False, "summary": "search plan recorded no candidates"}
        scene_counts: dict[str, int] = {}
        social_counts: dict[str, int] = {}
        motion_counts: dict[str, int] = {}
        mode_counts: dict[str, int] = {}
        scene_motion_counts: dict[tuple[str, str], int] = {}
        for row in candidates:
            scene, social, motion, modes = self._extract_scaffold_profile_names(
                row.get("scaffold_profile", {})
            )
            if scene:
                scene_counts[scene] = scene_counts.get(scene, 0) + 1
            if social:
                social_counts[social] = social_counts.get(social, 0) + 1
            if motion:
                motion_counts[motion] = motion_counts.get(motion, 0) + 1
            if scene and motion:
                key = (scene, motion)
                scene_motion_counts[key] = scene_motion_counts.get(key, 0) + 1
            primary_mode = modes[0] if modes else ""
            if primary_mode:
                mode_counts[primary_mode] = mode_counts.get(primary_mode, 0) + 1

        candidate_count = len(candidates)
        min_scene = min(
            len(PREMISE_SCAFFOLD_SCENE_SOURCE_DEFS),
            max(4, math.ceil(candidate_count / 6)),
        )
        min_social = min(
            len(PREMISE_SCAFFOLD_SOCIAL_GEOMETRY_DEFS),
            max(4, math.ceil(candidate_count / 6)),
        )
        min_motion = min(
            len(PREMISE_SCAFFOLD_NARRATIVE_MOTION_DEFS),
            max(4, math.ceil(candidate_count / 6)),
        )
        min_mode = min(
            len(PREMISE_SCAFFOLD_MODE_DEFS),
            max(4, math.ceil(candidate_count / 8)),
        )
        max_single = max(5, math.ceil(candidate_count * 0.30))
        max_pair = max(3, math.ceil(candidate_count * 0.13))

        scene_label_map = {
            row["name"]: row["label"] for row in PREMISE_SCAFFOLD_SCENE_SOURCE_DEFS
        }
        social_label_map = {
            row["name"]: row["label"] for row in PREMISE_SCAFFOLD_SOCIAL_GEOMETRY_DEFS
        }
        motion_label_map = {
            row["name"]: row["label"] for row in PREMISE_SCAFFOLD_NARRATIVE_MOTION_DEFS
        }
        mode_label_map = {
            row["name"]: row["label"] for row in PREMISE_SCAFFOLD_MODE_DEFS
        }

        failures: list[str] = []
        if len(scene_counts) < min_scene:
            failures.append(
                f"only {len(scene_counts)} distinct scene sources (need at least {min_scene})"
            )
        if len(social_counts) < min_social:
            failures.append(
                f"only {len(social_counts)} distinct social geometries (need at least {min_social})"
            )
        if len(motion_counts) < min_motion:
            failures.append(
                f"only {len(motion_counts)} distinct narrative motions (need at least {min_motion})"
            )
        if len(mode_counts) < min_mode:
            failures.append(
                f"only {len(mode_counts)} distinct primary mode overlays (need at least {min_mode})"
            )
        if scene_counts:
            top_scene, top_scene_count = max(
                scene_counts.items(), key=lambda item: (item[1], item[0])
            )
            if top_scene_count > max_single:
                failures.append(
                    f"scene source '{scene_label_map.get(top_scene, top_scene)}' dominates {top_scene_count}/{candidate_count} candidates"
                )
        if motion_counts:
            top_motion, top_motion_count = max(
                motion_counts.items(), key=lambda item: (item[1], item[0])
            )
            if top_motion_count > max_single:
                failures.append(
                    f"narrative motion '{motion_label_map.get(top_motion, top_motion)}' dominates {top_motion_count}/{candidate_count} candidates"
                )
        if scene_motion_counts:
            (top_scene, top_motion), top_pair_count = max(
                scene_motion_counts.items(), key=lambda item: (item[1], item[0])
            )
            if top_pair_count > max_pair:
                failures.append(
                    "scene-source and narrative-motion pairing "
                    f"'{scene_label_map.get(top_scene, top_scene)}' + "
                    f"'{motion_label_map.get(top_motion, top_motion)}' repeats too often "
                    f"({top_pair_count}/{candidate_count})"
                )

        summary_bits = [
            f"{len(scene_counts)} scene sources",
            f"{len(social_counts)} social geometries",
            f"{len(motion_counts)} narrative motions",
            f"{len(mode_counts)} primary modes",
        ]
        if scene_motion_counts:
            (top_scene, top_motion), top_pair_count = max(
                scene_motion_counts.items(), key=lambda item: (item[1], item[0])
            )
            summary_bits.append(
                "top scene/motion pair="
                f"{scene_label_map.get(top_scene, top_scene)} + "
                f"{motion_label_map.get(top_motion, top_motion)} ({top_pair_count})"
            )
        if failures:
            return {"ok": False, "summary": "; ".join(failures)}
        return {"ok": True, "summary": "scaffold spread ok: " + ", ".join(summary_bits)}

    def _build_scaffold_spread_summary(self, search_plan: dict[str, Any]) -> str:
        candidates = [
            row
            for row in search_plan.get("candidates", [])
            if isinstance(row, dict)
        ]
        if not candidates:
            return "No scaffold profile data recorded."

        def summarize(
            key: str, nested_key: str | None = None, *, top_n: int = 4
        ) -> str:
            counts: dict[str, int] = {}
            for row in candidates:
                profile = row.get("scaffold_profile", {})
                if not isinstance(profile, dict):
                    continue
                if nested_key is None:
                    value = profile.get(key, [])
                    items = value if isinstance(value, list) else []
                else:
                    value = profile.get(key, {})
                    items = [value] if isinstance(value, dict) else []
                for item in items:
                    label = str(item.get("label", "")).strip()
                    if label:
                        counts[label] = counts.get(label, 0) + 1
            if not counts:
                return ""
            return ", ".join(
                f"{label} ({count})"
                for label, count in sorted(
                    counts.items(), key=lambda item: (-item[1], item[0])
                )[:top_n]
            )

        bits = []
        scene = summarize("scene_source", "single")
        if scene:
            bits.append("scene sources: " + scene)
        social = summarize("social_geometry", "single")
        if social:
            bits.append("social geometries: " + social)
        motion = summarize("narrative_motion", "single")
        if motion:
            bits.append("narrative motions: " + motion)
        modes = summarize("mode_overlays")
        if modes:
            bits.append("mode overlays: " + modes)
        return " | ".join(bits) if bits else "No scaffold profile data recorded."

    def _write_premise_brainstorming_from_uniqueness(
        self,
        *,
        search_plan: dict[str, Any],
        candidates: list[dict[str, Any]],
        uniqueness: dict[str, Any],
        cluster_representatives: list[dict[str, Any]],
        shortlist_ids: list[str],
        selection_seed: str,
        random_draw_index: int,
        selected_candidate_id: str,
    ) -> None:
        candidate_map = {row["candidate_id"]: row for row in candidates}
        plan_candidate_map = {
            str(row.get("candidate_id", "")).strip(): row
            for row in search_plan.get("candidates", [])
            if isinstance(row, dict) and str(row.get("candidate_id", "")).strip()
        }
        scaffold_summary = self._build_scaffold_spread_summary(search_plan)
        candidate_lines = []
        for candidate_id in [
            str(row.get("candidate_id", "")).strip()
            for row in search_plan.get("candidates", [])
            if str(row.get("candidate_id", "")).strip()
        ]:
            row = candidate_map[candidate_id]
            scaffold_gloss = str(
                plan_candidate_map.get(candidate_id, {}).get("scaffold_gloss", "")
            ).strip()
            candidate_lines.append(
                f"- `{candidate_id}`: {row['premise']}\n"
                f"  Scaffold: {scaffold_gloss}\n"
                f"  Why it might work: {row['why_it_might_work']}\n"
                f"  Risk: {row['risk']}"
            )
        cluster_lines = []
        rep_map = {
            str(row.get("cluster_id", "")).strip(): str(row.get("representative_id", "")).strip()
            for row in cluster_representatives
        }
        for row in sorted(
            [item for item in uniqueness.get("clusters", []) if isinstance(item, dict)],
            key=lambda item: str(item.get("cluster_id", "")).strip(),
        ):
            cluster_id = str(row.get("cluster_id", "")).strip()
            member_ids = [
                str(item).strip() for item in row.get("member_ids", []) if str(item).strip()
            ]
            representative_id = rep_map.get(cluster_id, "")
            cluster_lines.append(
                f"- `{cluster_id}` -> {', '.join(f'`{item}`' for item in member_ids)}\n"
                f"  Shared shape: {row.get('similarity_summary', '')}\n"
                f"  Representative: `{representative_id}`"
            )
        shortlist_lines = [
            f"- `{candidate_id}`: {candidate_map[candidate_id]['premise']}\n"
            f"  Scaffold: {str(plan_candidate_map.get(candidate_id, {}).get('scaffold_gloss', '')).strip()}"
            for candidate_id in shortlist_ids
        ]
        selected_premise = str(candidate_map[selected_candidate_id]["premise"]).strip()
        draw_lines = [
            f"Selection seed: `{selection_seed}`",
            "Shortlist order:",
        ]
        for idx, candidate_id in enumerate(shortlist_ids):
            marker = " <- selected" if idx == random_draw_index else ""
            draw_lines.append(f"- [{idx}] `{candidate_id}`{marker}")
        content = textwrap.dedent(
            f"""\
            # Premise Brainstorming

            ## Seed
            Seed: `{search_plan.get('seed', '')}`
            Reroll index: `{search_plan.get('reroll_index', 0)}`

            ## Brief
            {self.cfg.premise_brief or 'No creative brief was provided.'}

            ## Run-Level Search Gloss
            {search_plan.get('field_gloss', search_plan.get('run_vector_gloss', ''))}

            ## Scaffold Spread
            {scaffold_summary}

            ## Candidate Set
            {chr(10).join(candidate_lines)}

            ## Uniqueness Clusters
            {chr(10).join(cluster_lines)}

            ## Protected Shortlist
            {chr(10).join(shortlist_lines)}

            ## Random Draw
            {chr(10).join(draw_lines)}

            ## Selected Premise
            {selected_premise}
            """
        )
        self._write_text("premise/premise_brainstorming.md", content)

    def _set_precycle_stage_entry(
        self,
        stage_key: str,
        stage_status: str,
        *,
        required: bool = True,
        reason: str | None = None,
        outputs: list[str] | None = None,
        units: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        entry: dict[str, Any] = {
            "status": stage_status,
            "required": required,
        }
        if reason:
            entry["reason"] = reason
        if outputs:
            entry["outputs"] = outputs
        if units is not None:
            entry["units"] = units
        if extra:
            entry.update(extra)
        self._precycle_stage_entries[stage_key] = entry

    def _build_outline_review_job(
        self,
        cycle_num: int,
        validation_error: str | None = None,
        retry_attempt: int = 0,
    ) -> JobSpec:
        review_rel = self._outline_review_rel(cycle_num)
        prompt = self._render_prompt(
            "outline_review_prompt.md",
            {
                "OUTLINE_REVIEW_CYCLE": str(cycle_num),
                "OUTLINE_REVIEW_OUTPUT_FILE": review_rel,
            },
        )
        if validation_error:
            safe_error = " ".join(str(validation_error).split())
            prompt += (
                "\n\nValidator feedback from previous attempt:\n"
                f"- {safe_error}\n"
                "Regenerate the full outline review JSON so it satisfies the contract exactly.\n"
            )
        retry_suffix = f"_retry_{retry_attempt}" if retry_attempt > 0 else ""
        return self._make_job(
            job_id=f"outline_review_cycle_{self._cpad(cycle_num)}{retry_suffix}",
            stage="outline_review",
            stage_group="outline",
            cycle=0,
            chapter_id=None,
            allowed_inputs=[
                "input/premise.txt",
                *self._outline_core_output_rels(),
                "config/constitution.md",
                "config/prompts/outline_review_prompt.md",
            ],
            required_outputs=[review_rel],
            prompt_text=prompt,
        )

    def _build_outline_revision_job(
        self,
        cycle_num: int,
        review_rel: str,
        validation_error: str | None = None,
        retry_attempt: int = 0,
    ) -> JobSpec:
        prompt = self._render_prompt(
            "outline_revision_prompt.md",
            {
                "OUTLINE_REVIEW_CYCLE": str(cycle_num),
                "OUTLINE_REVIEW_FILE": review_rel,
                "OUTLINE_FILE": "outline/outline.md",
                "CHAPTER_SPECS_FILE": "outline/chapter_specs.jsonl",
                "SCENE_PLAN_FILE": "outline/scene_plan.tsv",
                "STYLE_BIBLE_FILE": "outline/style_bible.json",
                "CONTINUITY_SHEET_FILE": "outline/continuity_sheet.json",
                "TITLE_FILE": "outline/title.txt",
            },
        )
        if validation_error:
            safe_error = " ".join(str(validation_error).split())
            prompt += (
                "\n\nValidator feedback from previous attempt:\n"
                f"- {safe_error}\n"
                "Regenerate the canonical outline artifacts so they validate together.\n"
            )
        retry_suffix = f"_retry_{retry_attempt}" if retry_attempt > 0 else ""
        return self._make_job(
            job_id=f"outline_revision_cycle_{self._cpad(cycle_num)}{retry_suffix}",
            stage="outline_revision",
            stage_group="outline",
            cycle=0,
            chapter_id=None,
            allowed_inputs=[
                "input/premise.txt",
                review_rel,
                *self._outline_core_output_rels(),
                "config/constitution.md",
                "config/prompts/outline_revision_prompt.md",
            ],
            required_outputs=self._outline_core_output_rels(),
            prompt_text=prompt,
        )

    def _build_spatial_layout_job(
        self,
        validation_error: str | None = None,
        retry_attempt: int = 0,
    ) -> JobSpec:
        layout_rel = self._spatial_layout_rel()
        prompt = self._render_prompt(
            "spatial_layout_prompt.md",
            {
                "SPATIAL_LAYOUT_FILE": layout_rel,
            },
        )
        if validation_error:
            safe_error = " ".join(str(validation_error).split())
            prompt += (
                "\n\nValidator feedback from previous attempt:\n"
                f"- {safe_error}\n"
                "Regenerate the spatial layout JSON so it satisfies the contract exactly.\n"
            )
        retry_suffix = f"_retry_{retry_attempt}" if retry_attempt > 0 else ""
        return self._make_job(
            job_id=f"spatial_layout{retry_suffix}",
            stage="spatial_layout",
            stage_group="outline",
            cycle=0,
            chapter_id=None,
            allowed_inputs=[
                "input/premise.txt",
                *self._outline_core_output_rels(),
                "config/constitution.md",
                "config/prompts/spatial_layout_prompt.md",
            ],
            required_outputs=[layout_rel],
            prompt_text=prompt,
        )

    def _run_outline_review_cycle(self, cycle_num: int) -> str:
        review_rel = self._outline_review_rel(cycle_num)
        review_path = self.run_dir / review_rel
        chapter_ids = {spec.chapter_id for spec in self.chapter_specs}
        self._materialize_output_alias(
            base_dir=self.run_dir,
            required_rel=review_rel,
            stage="outline_review",
            cycle=None,
            chapter_id=None,
        )
        if review_path.is_file():
            try:
                self._load_repaired_outline_review(review_rel, cycle_num, chapter_ids)
                if self._artifact_fresh_against_inputs(
                    review_path, self._outline_review_input_paths()
                ):
                    self._log(
                        f"outline_review_resume cycle={self._cpad(cycle_num)} status=reused"
                    )
                    return "reused"
                self._log(
                    f"outline_review_resume_stale cycle={self._cpad(cycle_num)} "
                    "reason=input_newer_than_review"
                )
            except PipelineError as exc:
                self._log(
                    f"outline_review_resume_invalid cycle={self._cpad(cycle_num)} reason={exc}"
                )

        attempts = 0
        validation_error: str | None = None
        while True:
            job = self._build_outline_review_job(
                cycle_num,
                validation_error=validation_error,
                retry_attempt=attempts,
            )
            self._run_job(job)
            try:
                self._load_repaired_outline_review(review_rel, cycle_num, chapter_ids)
                self._log(f"outline_review_complete cycle={self._cpad(cycle_num)}")
                return "complete"
            except PipelineError as exc:
                if attempts >= OUTLINE_REVIEW_VALIDATION_RETRY_MAX:
                    raise
                attempts += 1
                validation_error = str(exc)
                self._log(
                    f"outline_review_validation_retry cycle={self._cpad(cycle_num)} "
                    f"attempt={attempts}/{OUTLINE_REVIEW_VALIDATION_RETRY_MAX} reason={exc}"
                )

    def _run_outline_revision_cycle(self, cycle_num: int) -> str:
        review_rel = self._outline_review_rel(cycle_num)
        record_rel = self._outline_revision_record_rel(cycle_num)
        record_path = self.run_dir / record_rel
        chapter_ids = {spec.chapter_id for spec in self.chapter_specs}
        if record_path.is_file():
            try:
                self._load_repaired_outline_review(review_rel, cycle_num, chapter_ids)
                record_data = self._read_json(record_rel)
                self._validate_outline_revision_record(record_data, cycle_num, record_rel)
                record_inputs = [
                    self.run_dir / "input" / "premise.txt",
                    self.run_dir / "config" / "constitution.md",
                    self.run_dir / "config" / "prompts" / "outline_review_prompt.md",
                    self.run_dir / "config" / "prompts" / "outline_revision_prompt.md",
                    self.run_dir / review_rel,
                ]
                if (
                    self._artifact_fresh_against_inputs(record_path, record_inputs)
                    and self._outline_revision_record_matches_current_outputs(record_data)
                ):
                    self._load_current_outline_state(refresh_snapshots=False)
                    self._sync_continuity_sheet_spatial_reference()
                    self._log(
                        f"outline_revision_resume cycle={self._cpad(cycle_num)} status=reused"
                    )
                    return "reused"
                self._log(
                    f"outline_revision_resume_stale cycle={self._cpad(cycle_num)} "
                    "reason=record_or_outputs_stale"
                )
            except PipelineError as exc:
                self._log(
                    f"outline_revision_resume_invalid cycle={self._cpad(cycle_num)} "
                    f"reason={exc}"
                )

        self._ensure_outline_pre_revision_snapshot(cycle_num)
        attempts = 0
        validation_error: str | None = None
        while True:
            job = self._build_outline_revision_job(
                cycle_num,
                review_rel,
                validation_error=validation_error,
                retry_attempt=attempts,
            )
            self._run_job(job)
            try:
                self._load_current_outline_state(refresh_snapshots=False)
                self._sync_continuity_sheet_spatial_reference()
                self._validate_continuity_sheet()
                self._write_json(
                    record_rel, self._outline_revision_record_payload(cycle_num, review_rel)
                )
                self._log(f"outline_revision_complete cycle={self._cpad(cycle_num)}")
                return "complete"
            except PipelineError as exc:
                if attempts >= OUTLINE_REVISION_VALIDATION_RETRY_MAX:
                    raise
                attempts += 1
                validation_error = str(exc)
                self._log(
                    f"outline_revision_validation_retry cycle={self._cpad(cycle_num)} "
                    f"attempt={attempts}/{OUTLINE_REVISION_VALIDATION_RETRY_MAX} reason={exc}"
                )

    def _run_spatial_layout_stage(self) -> str:
        layout_rel = self._spatial_layout_rel()
        layout_path = self.run_dir / layout_rel
        self._materialize_output_alias(
            base_dir=self.run_dir,
            required_rel=layout_rel,
            stage="spatial_layout",
            cycle=None,
            chapter_id=None,
        )
        if layout_path.is_file():
            try:
                data = self._load_repaired_spatial_layout(layout_rel)
                layout_inputs = [
                    self.run_dir / "input" / "premise.txt",
                    *self._outline_core_output_paths(),
                    self.run_dir / "config" / "constitution.md",
                    self.run_dir / "config" / "prompts" / "spatial_layout_prompt.md",
                ]
                if self._artifact_fresh_against_inputs(layout_path, layout_inputs):
                    self.spatial_layout = data
                    self._sync_continuity_sheet_spatial_reference()
                    self._log("spatial_layout_resume status=reused")
                    return "reused"
                self._log("spatial_layout_resume_stale reason=input_newer_than_layout")
            except PipelineError as exc:
                self._log(f"spatial_layout_resume_invalid reason={exc}")

        attempts = 0
        validation_error: str | None = None
        while True:
            job = self._build_spatial_layout_job(
                validation_error=validation_error,
                retry_attempt=attempts,
            )
            self._run_job(job)
            try:
                self.spatial_layout = self._load_repaired_spatial_layout(layout_rel)
                self._sync_continuity_sheet_spatial_reference()
                self._log("spatial_layout_complete")
                return "complete"
            except PipelineError as exc:
                if attempts >= SPATIAL_LAYOUT_VALIDATION_RETRY_MAX:
                    raise
                attempts += 1
                validation_error = str(exc)
                self._log(
                    "spatial_layout_validation_retry "
                    f"attempt={attempts}/{SPATIAL_LAYOUT_VALIDATION_RETRY_MAX} reason={exc}"
                )

    def _reuse_outline_review_and_revision_cycle_if_available(self, cycle_num: int) -> bool:
        review_rel = self._outline_review_rel(cycle_num)
        record_rel = self._outline_revision_record_rel(cycle_num)
        record_path = self.run_dir / record_rel
        chapter_ids = {spec.chapter_id for spec in self.chapter_specs}
        if not record_path.is_file():
            return False
        try:
            self._materialize_output_alias(
                base_dir=self.run_dir,
                required_rel=review_rel,
                stage="outline_review",
                cycle=None,
                chapter_id=None,
            )
            self._load_repaired_outline_review(review_rel, cycle_num, chapter_ids)
            record_data = self._read_json(record_rel)
            self._validate_outline_revision_record(record_data, cycle_num, record_rel)
            record_inputs = [
                self.run_dir / "input" / "premise.txt",
                self.run_dir / "config" / "constitution.md",
                self.run_dir / "config" / "prompts" / "outline_review_prompt.md",
                self.run_dir / "config" / "prompts" / "outline_revision_prompt.md",
                self.run_dir / review_rel,
            ]
            if not (
                self._artifact_fresh_against_inputs(record_path, record_inputs)
                and self._outline_revision_record_matches_current_outputs(record_data)
            ):
                return False
            self._load_current_outline_state(refresh_snapshots=False)
            self._sync_continuity_sheet_spatial_reference()
            self._log(
                f"outline_review_revision_resume cycle={self._cpad(cycle_num)} status=reused"
            )
            return True
        except PipelineError as exc:
            self._log(
                f"outline_review_revision_resume_invalid cycle={self._cpad(cycle_num)} "
                f"reason={exc}"
            )
            return False

    def _run_outline_stage(self) -> None:
        self._precycle_stage_entries = {}
        if self._add_cycles_mode():
            self._run_outline_stage_add_cycles()
            return
        existing_outline_ready = all(path.is_file() for path in self._outline_core_output_paths())
        if existing_outline_ready:
            outline_inputs = [
                self.run_dir / "input" / "premise.txt",
                self.run_dir / "config" / "constitution.md",
                self.run_dir / "config" / "prompts" / "outline_prompt.md",
            ]
            if not self._artifacts_fresh_against_inputs(
                self._outline_core_output_paths(), outline_inputs
            ):
                self._log(
                    "outline_resume_stale reason=input_newer_than_outline; rerunning outline stage"
                )
            else:
                try:
                    self._load_current_outline_state(refresh_snapshots=False)
                    self._sync_continuity_sheet_spatial_reference()
                    self._log(
                        f"outline_resume_complete chapters={len(self.chapter_specs)} "
                        f"title={self.novel_title!r}"
                    )
                except PipelineError as exc:
                    self.chapter_specs = []
                    self.style_bible = {}
                    self.novel_title = ""
                    self._log(f"outline_resume_invalid reason={exc}; rerunning outline stage")
                else:
                    existing_outline_ready = True
        if not existing_outline_ready or not self.chapter_specs:
            prompt = self._render_prompt("outline_prompt.md", {})
            job = self._make_job(
                job_id="outline",
                stage="outline",
                stage_group="outline",
                cycle=0,
                chapter_id=None,
                allowed_inputs=[
                    "input/premise.txt",
                    "config/constitution.md",
                    "config/prompts/outline_prompt.md",
                ],
                required_outputs=self._outline_core_output_rels(),
                prompt_text=prompt,
            )
            self._run_job(job)
            self._load_current_outline_state(refresh_snapshots=False)
            self._sync_continuity_sheet_spatial_reference()
            self._log(
                f"outline_complete chapters={len(self.chapter_specs)} title={self.novel_title!r}"
            )

        outline_review_outputs: list[str] = []
        outline_review_units: dict[str, Any] = {}
        outline_revision_outputs: list[str] = []
        outline_revision_units: dict[str, Any] = {}

        if self.cfg.skip_outline_review:
            self._set_precycle_stage_entry(
                "outline_review",
                "skipped",
                required=False,
                reason="config_skip_outline_review",
                units={},
            )
            self._set_precycle_stage_entry(
                "outline_revision",
                "skipped",
                required=False,
                reason="config_skip_outline_review",
                units={},
            )
        else:
            for cycle_num in range(1, self.cfg.outline_review_cycles + 1):
                cycle_key = self._cpad(cycle_num)
                review_rel = self._outline_review_rel(cycle_num)
                revision_rel = self._outline_revision_record_rel(cycle_num)
                if self._reuse_outline_review_and_revision_cycle_if_available(cycle_num):
                    review_status = "reused"
                    revision_status = "reused"
                else:
                    review_status = self._run_outline_review_cycle(cycle_num)
                    revision_status = self._run_outline_revision_cycle(cycle_num)
                outline_review_outputs.append(review_rel)
                outline_review_units[f"cycle_{cycle_key}"] = {
                    "status": review_status,
                    "output": review_rel,
                }
                outline_revision_outputs.append(revision_rel)
                outline_revision_units[f"cycle_{cycle_key}"] = {
                    "status": revision_status,
                    "output": revision_rel,
                }

            outline_review_stage_status = (
                "reused"
                if outline_review_units
                and all(row.get("status") == "reused" for row in outline_review_units.values())
                else "complete"
            )
            outline_revision_stage_status = (
                "reused"
                if outline_revision_units
                and all(
                    row.get("status") == "reused" for row in outline_revision_units.values()
                )
                else "complete"
            )
            self._set_precycle_stage_entry(
                "outline_review",
                outline_review_stage_status,
                outputs=outline_review_outputs,
                units=outline_review_units,
                extra={"review_cycles": self.cfg.outline_review_cycles},
            )
            self._set_precycle_stage_entry(
                "outline_revision",
                outline_revision_stage_status,
                outputs=outline_revision_outputs,
                units=outline_revision_units,
                extra={"review_cycles": self.cfg.outline_review_cycles},
            )

        spatial_layout_status = self._run_spatial_layout_stage()
        self._set_precycle_stage_entry(
            "spatial_layout",
            spatial_layout_status,
            outputs=[self._spatial_layout_rel()],
        )

        self._ensure_outline_continuity_snapshot()
        self._write_chapter_spec_files()
        self._build_static_story_context()

    def _run_outline_stage_add_cycles(self) -> None:
        existing_outline_ready = all(path.is_file() for path in self._outline_core_output_paths())
        if not existing_outline_ready:
            raise PipelineError(
                "--add-cycles requires existing outline artifacts in run-dir; missing canonical outline outputs"
            )
        self._load_current_outline_state(refresh_snapshots=False)
        self._log(
            f"outline_resume_complete chapters={len(self.chapter_specs)} title={self.novel_title!r}"
        )

        if self.cfg.skip_outline_review:
            self._set_precycle_stage_entry(
                "outline_review",
                "skipped",
                required=False,
                reason="config_skip_outline_review",
                units={},
            )
            self._set_precycle_stage_entry(
                "outline_revision",
                "skipped",
                required=False,
                reason="config_skip_outline_review",
                units={},
            )
        else:
            chapter_ids = {spec.chapter_id for spec in self.chapter_specs}
            outline_review_outputs: list[str] = []
            outline_review_units: dict[str, Any] = {}
            outline_revision_outputs: list[str] = []
            outline_revision_units: dict[str, Any] = {}
            for cycle_num in range(1, self.cfg.outline_review_cycles + 1):
                cycle_key = self._cpad(cycle_num)
                review_rel = self._outline_review_rel(cycle_num)
                revision_rel = self._outline_revision_record_rel(cycle_num)
                if not (self.run_dir / review_rel).is_file():
                    raise PipelineError(
                        f"--add-cycles requires existing {review_rel}; rerunning outline review is disabled in additive mode"
                    )
                self._load_repaired_outline_review(review_rel, cycle_num, chapter_ids)
                outline_review_outputs.append(review_rel)
                outline_review_units[f"cycle_{cycle_key}"] = {
                    "status": "reused",
                    "output": review_rel,
                }
                if not (self.run_dir / revision_rel).is_file():
                    raise PipelineError(
                        f"--add-cycles requires existing {revision_rel}; rerunning outline revision is disabled in additive mode"
                    )
                record_data = self._read_json(revision_rel)
                self._validate_outline_revision_record(record_data, cycle_num, revision_rel)
                outline_revision_outputs.append(revision_rel)
                outline_revision_units[f"cycle_{cycle_key}"] = {
                    "status": "reused",
                    "output": revision_rel,
                }

            self._set_precycle_stage_entry(
                "outline_review",
                "reused",
                outputs=outline_review_outputs,
                units=outline_review_units,
                extra={"review_cycles": self.cfg.outline_review_cycles},
            )
            self._set_precycle_stage_entry(
                "outline_revision",
                "reused",
                outputs=outline_revision_outputs,
                units=outline_revision_units,
                extra={"review_cycles": self.cfg.outline_review_cycles},
            )

        layout_rel = self._spatial_layout_rel()
        if not (self.run_dir / layout_rel).is_file():
            raise PipelineError(
                f"--add-cycles requires existing {layout_rel}; rerunning spatial layout is disabled in additive mode"
            )
        self.spatial_layout = self._load_repaired_spatial_layout(layout_rel)
        self._sync_continuity_sheet_spatial_reference()
        self._log("spatial_layout_resume status=reused")
        self._set_precycle_stage_entry(
            "spatial_layout",
            "reused",
            outputs=[layout_rel],
        )

        self._ensure_outline_continuity_snapshot()
        self._write_chapter_spec_files()
        self._build_static_story_context()

    def _run_draft_stage(self) -> None:
        if self._add_cycles_mode():
            missing_chapters: list[str] = []
            for spec in self.chapter_specs:
                chapter_path = self.run_dir / "chapters" / f"{spec.chapter_id}.md"
                if not chapter_path.is_file():
                    missing_chapters.append(spec.chapter_id)
                    continue
                self._validate_chapter_heading(chapter_path, spec.chapter_number)
            if missing_chapters:
                raise PipelineError(
                    "--add-cycles requires drafted chapters in run-dir; missing "
                    + ", ".join(missing_chapters)
                )
            self._log("draft_resume_all_chapters_present")
            self._log("draft_expand_resume_skipped reason=add_cycles_use_current_chapters")
            self._log("draft_complete")
            return
        continuity_sheet_file = self._outline_continuity_snapshot_rel()
        spatial_layout_file = self._spatial_layout_rel()
        jobs: list[JobSpec] = []
        for spec in self.chapter_specs:
            chapter_file = f"chapters/{spec.chapter_id}.md"
            chapter_path = self.run_dir / chapter_file
            chapter_spec_file = f"outline/chapter_specs/{spec.chapter_id}.json"
            needs_draft = True
            if chapter_path.is_file():
                try:
                    self._validate_chapter_heading(chapter_path, spec.chapter_number)
                    draft_inputs = [
                        self.run_dir / "outline" / "outline.md",
                        self.run_dir / "outline" / "scene_plan.tsv",
                        self.run_dir / "outline" / "static_story_context.json",
                        self.run_dir / "outline" / "style_bible.json",
                        self.run_dir / spatial_layout_file,
                        self.run_dir / continuity_sheet_file,
                        self.run_dir / chapter_spec_file,
                        self.run_dir / "config" / "constitution.md",
                        self.run_dir / "config" / "prompts" / "chapter_draft_prompt.md",
                    ]
                    needs_draft = not self._artifact_fresh_against_inputs(
                        chapter_path, draft_inputs
                    )
                except PipelineError:
                    needs_draft = True

            if not needs_draft:
                continue

            prompt = self._render_prompt(
                "chapter_draft_prompt.md",
                    {
                        "CHAPTER_ID": spec.chapter_id,
                        "CHAPTER_NUMBER": str(spec.chapter_number),
                        "CHAPTER_SPEC_FILE": chapter_spec_file,
                        "CHAPTER_OUTPUT_FILE": chapter_file,
                        "SPATIAL_LAYOUT_FILE": spatial_layout_file,
                        "CONTINUITY_SHEET_FILE": continuity_sheet_file,
                    },
                )
            jobs.append(
                self._make_job(
                    job_id=f"draft_{spec.chapter_id}",
                    stage="chapter_draft",
                    stage_group="draft",
                    cycle=0,
                    chapter_id=spec.chapter_id,
                    allowed_inputs=[
                        "outline/outline.md",
                        "outline/scene_plan.tsv",
                        "outline/static_story_context.json",
                        "outline/style_bible.json",
                        spatial_layout_file,
                        continuity_sheet_file,
                        chapter_spec_file,
                        "config/constitution.md",
                        "config/prompts/chapter_draft_prompt.md",
                    ],
                    required_outputs=[chapter_file],
                    prompt_text=prompt,
                )
            )

        if jobs:
            self._run_jobs_parallel(jobs, self.cfg.max_parallel_drafts, "draft")
        else:
            self._log("draft_resume_all_chapters_present")
            self._log("draft_expand_resume_skipped reason=all_chapters_fresh")
            self._log("draft_complete")
            return
        expand_jobs: list[JobSpec] = []
        expand_target_ids: set[str] = set()
        for spec in self.chapter_specs:
            chapter_path = self.run_dir / "chapters" / f"{spec.chapter_id}.md"
            self._validate_chapter_heading(chapter_path, spec.chapter_number)
            words = self._count_words_file(chapter_path)
            if words < spec.projected_min_words:
                self._log(
                    f"draft_expand chapter={spec.chapter_id} words={words} target={spec.projected_min_words}"
                )
                chapter_file = f"chapters/{spec.chapter_id}.md"
                chapter_spec_file = f"outline/chapter_specs/{spec.chapter_id}.json"
                expand_prompt = self._render_prompt(
                    "chapter_expand_prompt.md",
                    {
                        "CHAPTER_ID": spec.chapter_id,
                        "CHAPTER_NUMBER": str(spec.chapter_number),
                        "CHAPTER_INPUT_FILE": chapter_file,
                        "CHAPTER_OUTPUT_FILE": chapter_file,
                        "CHAPTER_SPEC_FILE": chapter_spec_file,
                        "SPATIAL_LAYOUT_FILE": spatial_layout_file,
                        "CONTINUITY_SHEET_FILE": continuity_sheet_file,
                    },
                )
                expand_job = self._make_job(
                    job_id=f"draft_expand_{spec.chapter_id}",
                    stage="chapter_expand",
                    stage_group="draft",
                    cycle=0,
                    chapter_id=spec.chapter_id,
                    allowed_inputs=[
                        chapter_file,
                        chapter_spec_file,
                        "outline/outline.md",
                        "outline/scene_plan.tsv",
                        "outline/static_story_context.json",
                        "outline/style_bible.json",
                        spatial_layout_file,
                        continuity_sheet_file,
                        "config/constitution.md",
                        "config/prompts/chapter_expand_prompt.md",
                    ],
                    required_outputs=[chapter_file],
                    prompt_text=expand_prompt,
                )
                expand_jobs.append(expand_job)
                expand_target_ids.add(spec.chapter_id)
        if expand_jobs:
            self._run_jobs_parallel(
                expand_jobs, self.cfg.max_parallel_drafts, "draft_expand"
            )
        for spec in self.chapter_specs:
            if spec.chapter_id not in expand_target_ids:
                continue
            chapter_path = self.run_dir / "chapters" / f"{spec.chapter_id}.md"
            self._validate_chapter_heading(chapter_path, spec.chapter_number)
            words = self._count_words_file(chapter_path)
            if words < spec.projected_min_words:
                self._log(
                    "draft_expand_unresolved "
                    f"chapter={spec.chapter_id} words={words} target={spec.projected_min_words}; "
                    "continuing and deferring to revision cycles"
                )
        self._log("draft_complete")

    def _run_chapter_review_stage(self, cycle: int) -> dict[str, Any]:
        cpad = self._cpad(cycle)
        continuity_sheet_file = self._ensure_cycle_continuity_snapshot(cycle)
        jobs: list[JobSpec] = []
        units: dict[str, dict[str, Any]] = {}
        for spec in self.chapter_specs:
            chapter_input = f"snapshots/cycle_{cpad}/chapters/{spec.chapter_id}.md"
            review_output = f"reviews/cycle_{cpad}/{spec.chapter_id}.review.json"
            self._materialize_output_alias(
                base_dir=self.run_dir,
                required_rel=review_output,
                stage="chapter_review",
                cycle=cycle,
                chapter_id=spec.chapter_id,
            )
            review_path = self.run_dir / review_output
            if review_path.is_file():
                try:
                    self._load_repaired_chapter_review(
                        review_output,
                        spec.chapter_id,
                        chapter_input,
                    )
                    review_inputs = [
                        self.run_dir / chapter_input,
                        self.run_dir / f"context/cycle_{cpad}/global_cycle_context.json",
                        self.run_dir / f"context/cycle_{cpad}/boundary/{spec.chapter_id}.boundary.json",
                        self.run_dir / "outline" / "style_bible.json",
                        self.run_dir / continuity_sheet_file,
                        self.run_dir / "config" / "constitution.md",
                        self.run_dir / "config" / "prompts" / "chapter_review_prompt.md",
                    ]
                    if self._artifact_fresh_against_inputs(review_path, review_inputs):
                        units[spec.chapter_id] = {
                            "status": "reused",
                            "validated": True,
                            "fresh": True,
                        }
                        continue
                except PipelineError:
                    pass

            jobs.append(self._build_chapter_review_job(cycle, spec))

        if jobs:
            try:
                self._run_jobs_parallel(
                    jobs, self.cfg.max_parallel_reviews, f"review_cycle_{cpad}"
                )
            except PipelineError as exc:
                if not self._soft_validation_enabled():
                    raise
                self._record_validation_warning(
                    stage="chapter_review",
                    cycle=cycle,
                    chapter_id=None,
                    artifact=f"reviews/cycle_{cpad}",
                    reason=str(exc),
                    action="continued_after_parallel_review_failure",
                )
        else:
            self._log(f"cycle={cpad} review_resume_all_chapters_present")
        for spec in self.chapter_specs:
            review_rel = f"reviews/cycle_{cpad}/{spec.chapter_id}.review.json"
            chapter_input = f"snapshots/cycle_{cpad}/chapters/{spec.chapter_id}.md"
            attempts = 0
            while True:
                try:
                    self._materialize_output_alias(
                        base_dir=self.run_dir,
                        required_rel=review_rel,
                        stage="chapter_review",
                        cycle=cycle,
                        chapter_id=spec.chapter_id,
                    )
                    self._load_repaired_chapter_review(
                        review_rel,
                        spec.chapter_id,
                        chapter_input,
                    )
                    break
                except PipelineError as exc:
                    if attempts >= REVIEW_VALIDATION_RETRY_MAX:
                        if not self._soft_validation_enabled():
                            raise
                        fallback = self._fallback_chapter_review_payload(
                            cycle=cycle,
                            chapter_id=spec.chapter_id,
                            chapter_file=chapter_input,
                            reason=str(exc),
                        )
                        self._write_json(review_rel, fallback)
                        self._record_validation_warning(
                            stage="chapter_review",
                            cycle=cycle,
                            chapter_id=spec.chapter_id,
                            artifact=review_rel,
                            reason=str(exc),
                            action="wrote_fallback_chapter_review",
                        )
                        break
                    attempts += 1
                    self._log(
                        "cycle="
                        f"{cpad} chapter_review_validation_retry chapter={spec.chapter_id} "
                        f"attempt={attempts}/{REVIEW_VALIDATION_RETRY_MAX} reason={exc}"
                    )
                    retry_job = self._build_chapter_review_job(
                        cycle,
                        spec,
                        validation_error=str(exc),
                        retry_attempt=attempts,
                    )
                    try:
                        self._run_job(retry_job)
                    except PipelineError as job_exc:
                        if attempts >= REVIEW_VALIDATION_RETRY_MAX:
                            if not self._soft_validation_enabled():
                                raise
                            fallback = self._fallback_chapter_review_payload(
                                cycle=cycle,
                                chapter_id=spec.chapter_id,
                                chapter_file=chapter_input,
                                reason=str(job_exc),
                            )
                            self._write_json(review_rel, fallback)
                            self._record_validation_warning(
                                stage="chapter_review",
                                cycle=cycle,
                                chapter_id=spec.chapter_id,
                                artifact=review_rel,
                                reason=str(job_exc),
                                action="wrote_fallback_after_retry_job_failure",
                            )
                            break
                        self._record_validation_warning(
                            stage="chapter_review",
                            cycle=cycle,
                            chapter_id=spec.chapter_id,
                            artifact=review_rel,
                            reason=str(job_exc),
                            action="retry_job_failed_will_retry",
                        )
            units[spec.chapter_id] = {
                "status": units.get(spec.chapter_id, {}).get("status", "complete"),
                "validated": True,
                "fresh": True,
            }
        self._log(f"cycle={cpad} chapter_reviews_complete")
        reused_count = sum(
            1 for row in units.values() if row.get("status") == "reused"
        )
        return {
            "status": (
                "reused"
                if units and reused_count == len(units)
                else "complete"
            ),
            "chapter_count": len(self.chapter_specs),
            "units": units,
        }

    def _build_chapter_review_job(
        self,
        cycle: int,
        spec: ChapterSpec,
        validation_error: str | None = None,
        retry_attempt: int = 0,
    ) -> JobSpec:
        cpad = self._cpad(cycle)
        chapter_input = f"snapshots/cycle_{cpad}/chapters/{spec.chapter_id}.md"
        review_output = f"reviews/cycle_{cpad}/{spec.chapter_id}.review.json"
        global_context_file = f"context/cycle_{cpad}/global_cycle_context.json"
        boundary_context_file = f"context/cycle_{cpad}/boundary/{spec.chapter_id}.boundary.json"
        continuity_sheet_file = self._ensure_cycle_continuity_snapshot(cycle)
        prompt = self._render_prompt(
            "chapter_review_prompt.md",
            {
                "CHAPTER_ID": spec.chapter_id,
                "CHAPTER_INPUT_FILE": chapter_input,
                "GLOBAL_CYCLE_CONTEXT_FILE": global_context_file,
                "CHAPTER_BOUNDARY_CONTEXT_FILE": boundary_context_file,
                "CONTINUITY_SHEET_FILE": continuity_sheet_file,
                "REVIEW_OUTPUT_FILE": review_output,
            },
        )
        if validation_error:
            safe_error = " ".join(str(validation_error).split())
            prompt += (
                "\n\nValidator feedback from previous attempt:\n"
                f"- {safe_error}\n"
                "Regenerate the full review JSON so it satisfies the contract exactly.\n"
                "Preserve strict evidence and acceptance-test requirements.\n"
            )
            prompt += self._retry_guidance_for_validation_error(
                validation_error=safe_error,
                target_file=chapter_input,
            )
        retry_suffix = f"_retry_{retry_attempt}" if retry_attempt > 0 else ""
        return self._make_job(
            job_id=f"cycle_{cpad}_review_{spec.chapter_id}{retry_suffix}",
            stage="chapter_review",
            stage_group="review",
            cycle=cycle,
            chapter_id=spec.chapter_id,
            allowed_inputs=[
                chapter_input,
                global_context_file,
                boundary_context_file,
                "outline/style_bible.json",
                continuity_sheet_file,
                "config/constitution.md",
                "config/prompts/chapter_review_prompt.md",
            ],
            required_outputs=[review_output],
            prompt_text=prompt,
        )

    def _run_parallel_full_book_review_stages(self, cycle: int) -> dict[str, Any]:
        stage_calls = [("full_award_review", self._run_full_award_review_stage)]
        if not self.cfg.skip_cross_chapter_audit:
            stage_calls.append(("cross_chapter_audit", self._run_cross_chapter_audit_stage))
        if self._local_window_stage_enabled() and not self.cfg.skip_local_window_audit:
            stage_calls.append(("local_window_audit", self._run_local_window_audit_stage))
        if len(stage_calls) == 1:
            stage_name, func = stage_calls[0]
            return {stage_name: func(cycle)}

        failures: list[str] = []
        results: dict[str, Any] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(stage_calls)) as executor:
            future_map = {
                executor.submit(func, cycle): stage_name for stage_name, func in stage_calls
            }
            for future in concurrent.futures.as_completed(future_map):
                stage_name = future_map[future]
                try:
                    results[stage_name] = future.result()
                except Exception as exc:
                    failures.append(f"{stage_name}: {exc}")
        if failures:
            joined = "\n".join(failures[:8])
            raise PipelineError(
                f"parallel_full_book_review phase had stage failures:\n{joined}"
            )
        return results

    def _run_full_award_review_stage(self, cycle: int) -> bool:
        cpad = self._cpad(cycle)
        full_novel_file = f"snapshots/cycle_{cpad}/FINAL_NOVEL.md"
        global_context_file = f"context/cycle_{cpad}/global_cycle_context.json"
        continuity_sheet_file = self._ensure_cycle_continuity_snapshot(cycle)
        spatial_layout_file = self._spatial_layout_rel()
        output_file = f"reviews/cycle_{cpad}/full_award.review.json"
        self._materialize_output_alias(
            base_dir=self.run_dir,
            required_rel=output_file,
            stage="full_award_review",
            cycle=cycle,
            chapter_id=None,
        )
        output_path = self.run_dir / output_file
        chapter_ids = {spec.chapter_id for spec in self.chapter_specs}
        if output_path.is_file():
            try:
                data = self._load_repaired_full_award_review(
                    output_file,
                    cycle,
                    chapter_ids,
                    full_novel_file,
                )
                self._validate_full_award_review_json(
                    data, cycle, chapter_ids, output_file, full_novel_file
                )
                review_inputs = [
                    self.run_dir / full_novel_file,
                    self.run_dir / global_context_file,
                    self.run_dir / "outline" / "style_bible.json",
                    self.run_dir / spatial_layout_file,
                    self.run_dir / continuity_sheet_file,
                    self.run_dir / "config" / "constitution.md",
                    self.run_dir / "config" / "prompts" / "full_award_review_prompt.md",
                ]
                if self._artifact_fresh_against_inputs(output_path, review_inputs):
                    self._log(f"cycle={cpad} full_award_review_resume_present")
                    return True
                self._log(
                    f"cycle={cpad} full_award_review_resume_stale reason=input_newer_than_review"
                )
            except PipelineError as exc:
                if self._soft_validation_enabled():
                    self._record_validation_warning(
                        stage="full_award_review",
                        cycle=cycle,
                        chapter_id=None,
                        artifact=output_file,
                        reason=str(exc),
                        action="resume_artifact_invalid_rerun_stage",
                    )

        job = self._build_full_award_review_job(cycle)
        try:
            self._run_job(job)
        except PipelineError as exc:
            if not self._soft_validation_enabled():
                raise
            preserved_rel = self._preserve_invalid_artifact(output_file)
            fallback = self._fallback_full_award_review_payload(
                cycle=cycle,
                novel_file=full_novel_file,
                reason=str(exc),
            )
            self._write_json(output_file, fallback)
            self._record_validation_warning(
                stage="full_award_review",
                cycle=cycle,
                chapter_id=None,
                artifact=output_file,
                reason=(
                    f"{exc}; preserved original at {preserved_rel}"
                    if preserved_rel
                    else str(exc)
                ),
                action="wrote_fallback_full_award_after_job_failure",
            )

        attempts = 0
        while True:
            try:
                self._materialize_output_alias(
                    base_dir=self.run_dir,
                    required_rel=output_file,
                    stage="full_award_review",
                    cycle=cycle,
                    chapter_id=None,
                )
                data = self._load_repaired_full_award_review(
                    output_file,
                    cycle,
                    chapter_ids,
                    full_novel_file,
                )
                self._validate_full_award_review_json(
                    data, cycle, chapter_ids, output_file, full_novel_file
                )
                break
            except PipelineError as exc:
                if attempts >= FULL_AWARD_VALIDATION_RETRY_MAX:
                    if not self._soft_validation_enabled():
                        raise
                    preserved_rel = self._preserve_invalid_artifact(output_file)
                    fallback = self._fallback_full_award_review_payload(
                        cycle=cycle,
                        novel_file=full_novel_file,
                        reason=str(exc),
                    )
                    self._write_json(output_file, fallback)
                    self._record_validation_warning(
                        stage="full_award_review",
                        cycle=cycle,
                        chapter_id=None,
                        artifact=output_file,
                        reason=(
                            f"{exc}; preserved original at {preserved_rel}"
                            if preserved_rel
                            else str(exc)
                        ),
                        action="wrote_fallback_full_award_after_validation_retries",
                    )
                    break
                attempts += 1
                self._log(
                    "cycle="
                    f"{cpad} full_award_validation_retry attempt={attempts}/"
                    f"{FULL_AWARD_VALIDATION_RETRY_MAX} reason={exc}"
                )
                retry_job = self._build_full_award_review_job(
                    cycle, validation_error=str(exc), retry_attempt=attempts
                )
                try:
                    self._run_job(retry_job)
                except PipelineError as job_exc:
                    if attempts >= FULL_AWARD_VALIDATION_RETRY_MAX:
                        if not self._soft_validation_enabled():
                            raise
                        preserved_rel = self._preserve_invalid_artifact(output_file)
                        fallback = self._fallback_full_award_review_payload(
                            cycle=cycle,
                            novel_file=full_novel_file,
                            reason=str(job_exc),
                        )
                        self._write_json(output_file, fallback)
                        self._record_validation_warning(
                            stage="full_award_review",
                            cycle=cycle,
                            chapter_id=None,
                            artifact=output_file,
                            reason=(
                                f"{job_exc}; preserved original at {preserved_rel}"
                                if preserved_rel
                                else str(job_exc)
                            ),
                            action="wrote_fallback_full_award_after_retry_job_failure",
                        )
                        break
                    self._record_validation_warning(
                        stage="full_award_review",
                        cycle=cycle,
                        chapter_id=None,
                        artifact=output_file,
                        reason=str(job_exc),
                        action="retry_job_failed_will_retry",
                    )
        self._log(f"cycle={cpad} full_award_review_complete")
        return False

    def _build_full_award_review_job(
        self,
        cycle: int,
        validation_error: str | None = None,
        retry_attempt: int = 0,
    ) -> JobSpec:
        cpad = self._cpad(cycle)
        full_novel_file = f"snapshots/cycle_{cpad}/FINAL_NOVEL.md"
        global_context_file = f"context/cycle_{cpad}/global_cycle_context.json"
        continuity_sheet_file = self._ensure_cycle_continuity_snapshot(cycle)
        spatial_layout_file = self._spatial_layout_rel()
        output_file = f"reviews/cycle_{cpad}/full_award.review.json"
        prompt = self._render_prompt(
            "full_award_review_prompt.md",
            {
                "CYCLE_PADDED": cpad,
                "CYCLE_INT": str(cycle),
                "FULL_NOVEL_FILE": full_novel_file,
                "GLOBAL_CYCLE_CONTEXT_FILE": global_context_file,
                "SPATIAL_LAYOUT_FILE": spatial_layout_file,
                "CONTINUITY_SHEET_FILE": continuity_sheet_file,
                "FULL_AWARD_OUTPUT_FILE": output_file,
            },
        )
        if validation_error:
            safe_error = " ".join(str(validation_error).split())
            prompt += (
                "\n\nValidator feedback from previous attempt:\n"
                f"- {safe_error}\n"
                "Regenerate the full-book review JSON so it satisfies the contract exactly.\n"
                "Preserve strict evidence and acceptance-test requirements.\n"
            )
            prompt += self._retry_guidance_for_validation_error(
                validation_error=safe_error,
                target_file=full_novel_file,
            )
        retry_suffix = f"_retry_{retry_attempt}" if retry_attempt > 0 else ""
        return self._make_job(
            job_id=f"cycle_{cpad}_full_award_review{retry_suffix}",
            stage="full_award_review",
            stage_group="full_review",
            cycle=cycle,
            chapter_id=None,
            allowed_inputs=[
                full_novel_file,
                global_context_file,
                "outline/style_bible.json",
                spatial_layout_file,
                continuity_sheet_file,
                "config/constitution.md",
                "config/prompts/full_award_review_prompt.md",
            ],
            required_outputs=[output_file],
            prompt_text=prompt,
        )

    def _run_cross_chapter_audit_stage(self, cycle: int) -> bool:
        cpad = self._cpad(cycle)
        full_novel_file = f"snapshots/cycle_{cpad}/FINAL_NOVEL.md"
        continuity_sheet_file = self._ensure_cycle_continuity_snapshot(cycle)
        spatial_layout_file = self._spatial_layout_rel()
        output_file = self._cross_chapter_audit_rel(cycle)
        self._materialize_output_alias(
            base_dir=self.run_dir,
            required_rel=output_file,
            stage="cross_chapter_audit",
            cycle=cycle,
            chapter_id=None,
        )
        output_path = self.run_dir / output_file
        chapter_ids = {spec.chapter_id for spec in self.chapter_specs}
        if output_path.is_file():
            try:
                data = self._load_repaired_cross_chapter_audit(
                    output_file,
                    cycle,
                    chapter_ids,
                    full_novel_file,
                )
                self._validate_cross_chapter_audit_json(
                    data,
                    cycle,
                    chapter_ids,
                    output_file,
                    full_novel_file,
                )
                audit_inputs = [
                    self.run_dir / full_novel_file,
                    self.run_dir / continuity_sheet_file,
                    self.run_dir / "outline" / "style_bible.json",
                    self.run_dir / "outline" / "outline.md",
                    self.run_dir / spatial_layout_file,
                    self.run_dir / "config" / "constitution.md",
                    self.run_dir / "config" / "prompts" / "cross_chapter_audit_prompt.md",
                ]
                if self._artifact_fresh_against_inputs(output_path, audit_inputs):
                    self._log(f"cycle={cpad} cross_chapter_audit_resume_present")
                    self._log_cross_chapter_audit_convergence(cycle, data)
                    return True
                self._log(
                    f"cycle={cpad} cross_chapter_audit_resume_stale reason=input_newer_than_audit"
                )
            except PipelineError as exc:
                if self._soft_validation_enabled():
                    self._record_validation_warning(
                        stage="cross_chapter_audit",
                        cycle=cycle,
                        chapter_id=None,
                        artifact=output_file,
                        reason=str(exc),
                        action="resume_artifact_invalid_rerun_stage",
                    )

        job = self._build_cross_chapter_audit_job(cycle)
        try:
            self._run_job(job)
        except PipelineError as exc:
            if not self._soft_validation_enabled():
                raise
            preserved_rel = self._preserve_invalid_artifact(output_file)
            fallback = self._fallback_cross_chapter_audit_payload(cycle)
            self._write_json(output_file, fallback)
            self._record_validation_warning(
                stage="cross_chapter_audit",
                cycle=cycle,
                chapter_id=None,
                artifact=output_file,
                reason=(
                    f"{exc}; preserved original at {preserved_rel}"
                    if preserved_rel
                    else str(exc)
                ),
                action="wrote_fallback_cross_chapter_audit_after_job_failure",
            )

        attempts = 0
        while True:
            try:
                self._materialize_output_alias(
                    base_dir=self.run_dir,
                    required_rel=output_file,
                    stage="cross_chapter_audit",
                    cycle=cycle,
                    chapter_id=None,
                )
                data = self._load_repaired_cross_chapter_audit(
                    output_file,
                    cycle,
                    chapter_ids,
                    full_novel_file,
                )
                self._validate_cross_chapter_audit_json(
                    data,
                    cycle,
                    chapter_ids,
                    output_file,
                    full_novel_file,
                )
                break
            except PipelineError as exc:
                if attempts >= CROSS_CHAPTER_AUDIT_VALIDATION_RETRY_MAX:
                    if not self._soft_validation_enabled():
                        raise
                    preserved_rel = self._preserve_invalid_artifact(output_file)
                    fallback = self._fallback_cross_chapter_audit_payload(cycle)
                    self._write_json(output_file, fallback)
                    self._record_validation_warning(
                        stage="cross_chapter_audit",
                        cycle=cycle,
                        chapter_id=None,
                        artifact=output_file,
                        reason=(
                            f"{exc}; preserved original at {preserved_rel}"
                            if preserved_rel
                            else str(exc)
                        ),
                        action="wrote_fallback_cross_chapter_audit_after_validation_retries",
                    )
                    break
                attempts += 1
                self._log(
                    "cycle="
                    f"{cpad} cross_chapter_audit_validation_retry attempt={attempts}/"
                    f"{CROSS_CHAPTER_AUDIT_VALIDATION_RETRY_MAX} reason={exc}"
                )
                retry_job = self._build_cross_chapter_audit_job(
                    cycle, validation_error=str(exc), retry_attempt=attempts
                )
                try:
                    self._run_job(retry_job)
                except PipelineError as job_exc:
                    if attempts >= CROSS_CHAPTER_AUDIT_VALIDATION_RETRY_MAX:
                        if not self._soft_validation_enabled():
                            raise
                        preserved_rel = self._preserve_invalid_artifact(output_file)
                        fallback = self._fallback_cross_chapter_audit_payload(cycle)
                        self._write_json(output_file, fallback)
                        self._record_validation_warning(
                            stage="cross_chapter_audit",
                            cycle=cycle,
                            chapter_id=None,
                            artifact=output_file,
                            reason=(
                                f"{job_exc}; preserved original at {preserved_rel}"
                                if preserved_rel
                                else str(job_exc)
                            ),
                            action="wrote_fallback_cross_chapter_audit_after_retry_job_failure",
                        )
                        break
                    self._record_validation_warning(
                        stage="cross_chapter_audit",
                        cycle=cycle,
                        chapter_id=None,
                        artifact=output_file,
                        reason=str(job_exc),
                        action="retry_job_failed_will_retry",
                    )
        self._log_cross_chapter_audit_convergence(cycle, data)
        self._log(f"cycle={cpad} cross_chapter_audit_complete")
        return False

    def _build_cross_chapter_audit_job(
        self,
        cycle: int,
        validation_error: str | None = None,
        retry_attempt: int = 0,
    ) -> JobSpec:
        cpad = self._cpad(cycle)
        full_novel_file = f"snapshots/cycle_{cpad}/FINAL_NOVEL.md"
        continuity_sheet_file = self._ensure_cycle_continuity_snapshot(cycle)
        spatial_layout_file = self._spatial_layout_rel()
        output_file = self._cross_chapter_audit_rel(cycle)
        prompt = self._render_prompt(
            "cross_chapter_audit_prompt.md",
            {
                "CYCLE_PADDED": cpad,
                "CYCLE_INT": str(cycle),
                "FULL_NOVEL_FILE": full_novel_file,
                "SPATIAL_LAYOUT_FILE": spatial_layout_file,
                "CONTINUITY_SHEET_FILE": continuity_sheet_file,
                "CROSS_CHAPTER_AUDIT_FILE": output_file,
            },
        )
        if validation_error:
            safe_error = " ".join(str(validation_error).split())
            prompt += (
                "\n\nValidator feedback from previous attempt:\n"
                f"- {safe_error}\n"
                "Regenerate the cross-chapter audit JSON so it satisfies the contract exactly.\n"
                "Preserve the required finding structure and category placement.\n"
            )
            prompt += self._retry_guidance_for_validation_error(
                validation_error=safe_error,
                target_file=full_novel_file,
            )
        retry_suffix = f"_retry_{retry_attempt}" if retry_attempt > 0 else ""
        return self._make_job(
            job_id=f"cycle_{cpad}_cross_chapter_audit{retry_suffix}",
            stage="cross_chapter_audit",
            stage_group="cross_chapter_audit",
            cycle=cycle,
            chapter_id=None,
            allowed_inputs=[
                full_novel_file,
                continuity_sheet_file,
                "outline/style_bible.json",
                "outline/outline.md",
                spatial_layout_file,
                "config/constitution.md",
                "config/prompts/cross_chapter_audit_prompt.md",
            ],
            required_outputs=[output_file],
            prompt_text=prompt,
        )

    def _window_id_for_chapters(self, chapters_reviewed: list[str]) -> str:
        windows = self._compute_windows(
            [spec.chapter_id for spec in self.chapter_specs],
            self.cfg.local_window_size,
            self.cfg.local_window_overlap,
        )
        for idx, candidate in enumerate(windows, start=1):
            if candidate == chapters_reviewed:
                return self._window_id_for_index(idx)
        raise PipelineError(
            "window chapters do not match configured local-window layout: "
            + ", ".join(chapters_reviewed)
        )

    def _validate_local_window_window_output(
        self,
        data: dict[str, Any],
        *,
        rel: str,
        window_id: str,
        chapters_reviewed: list[str],
    ) -> None:
        actual_window_id = str(data.get("window_id", "")).strip()
        if actual_window_id != window_id:
            raise PipelineError(f"{rel} window_id mismatch (expected {window_id})")
        actual_chapters = [
            str(chapter_id).strip()
            for chapter_id in data.get("chapters_reviewed", [])
            if str(chapter_id).strip()
        ]
        if actual_chapters != chapters_reviewed:
            raise PipelineError(
                f"{rel} chapters_reviewed mismatch (expected {chapters_reviewed})"
            )

    def _run_local_window_audit_stage(self, cycle: int) -> dict[str, Any]:
        windows = self._compute_windows(
            [spec.chapter_id for spec in self.chapter_specs],
            self.cfg.local_window_size,
            self.cfg.local_window_overlap,
        )
        if not windows:
            return {
                "status": "skipped",
                "reason": "insufficient_chapters",
                "units": {},
                "window_count": 0,
            }

        cpad = self._cpad(cycle)
        units: dict[str, dict[str, Any]] = {}
        jobs: list[JobSpec] = []
        blocking = self._local_window_stage_required()

        try:
            chapter_line_index = self._read_json(self._chapter_line_index_rel(cycle))

            for window in windows:
                window_id = self._window_id_for_chapters(window)
                state = self._local_window_audit_unit_state(cycle, window_id, window)
                if state["status"] == "reused":
                    state["chapters_reviewed"] = list(window)
                    units[window_id] = state
                    continue
                units[window_id] = {
                    "status": state["status"],
                    "validated": bool(state.get("validated", False)),
                    "fresh": bool(state.get("fresh", False)),
                    "artifact": self._local_window_audit_rel(cycle, window_id),
                    "chapter_count": len(window),
                    "chapters_reviewed": list(window),
                }
                if state.get("reason"):
                    units[window_id]["reason"] = state["reason"]
                jobs.append(
                    self._build_local_window_audit_job(
                        cycle,
                        window,
                        chapter_line_index,
                    )
                )
        except PipelineError as exc:
            if blocking:
                raise
            self._record_validation_warning(
                stage="local_window_audit",
                cycle=cycle,
                chapter_id=None,
                artifact=f"reviews/cycle_{cpad}",
                reason=str(exc),
                action="continued_after_local_window_setup_failure",
            )
            return {
                "status": "failed",
                "reason": "setup_failed_nonblocking",
                "units": units,
                "window_count": len(windows),
            }

        if jobs:
            try:
                self._run_jobs_parallel(
                    jobs,
                    self.cfg.max_parallel_reviews,
                    f"local_window_cycle_{cpad}",
                )
            except PipelineError as exc:
                if self._local_window_stage_required():
                    raise
                self._record_validation_warning(
                    stage="local_window_audit",
                    cycle=cycle,
                    chapter_id=None,
                    artifact=f"reviews/cycle_{cpad}",
                    reason=str(exc),
                    action="continued_after_parallel_local_window_failure",
                )
        else:
            self._log(f"cycle={cpad} local_window_resume_all_windows_present")

        all_reused = True
        all_complete = True
        any_complete = False

        for window in windows:
            window_id = self._window_id_for_chapters(window)
            rel = self._local_window_audit_rel(cycle, window_id)
            attempts = 0
            while True:
                try:
                    self._materialize_output_alias(
                        base_dir=self.run_dir,
                        required_rel=rel,
                        stage="local_window_audit",
                        cycle=cycle,
                        chapter_id=None,
                    )
                    data = self._load_repaired_local_window_audit(
                        rel,
                        cycle,
                        {spec.chapter_id for spec in self.chapter_specs},
                        f"snapshots/cycle_{cpad}/FINAL_NOVEL.md",
                    )
                    self._validate_local_window_window_output(
                        data,
                        rel=rel,
                        window_id=window_id,
                        chapters_reviewed=window,
                    )
                    units[window_id] = {
                        "status": (
                            "reused"
                            if units.get(window_id, {}).get("status") == "reused"
                            else "complete"
                        ),
                        "validated": True,
                        "fresh": True,
                        "artifact": rel,
                        "chapter_count": len(window),
                        "chapters_reviewed": list(window),
                    }
                    any_complete = True
                    break
                except PipelineError as exc:
                    if attempts >= LOCAL_WINDOW_AUDIT_VALIDATION_RETRY_MAX:
                        if blocking:
                            raise
                        units[window_id] = {
                            "status": "failed",
                            "validated": False,
                            "fresh": False,
                            "artifact": rel,
                            "chapter_count": len(window),
                            "chapters_reviewed": list(window),
                            "reason": str(exc),
                        }
                        all_complete = False
                        all_reused = False
                        self._record_validation_warning(
                            stage="local_window_audit",
                            cycle=cycle,
                            chapter_id=None,
                            artifact=rel,
                            reason=str(exc),
                            action="left_invalid_local_window_artifact",
                        )
                        break
                    attempts += 1
                    self._log(
                        "cycle="
                        f"{cpad} local_window_validation_retry window={window_id} "
                        f"attempt={attempts}/{LOCAL_WINDOW_AUDIT_VALIDATION_RETRY_MAX} reason={exc}"
                    )
                    retry_job = self._build_local_window_audit_job(
                        cycle,
                        window,
                        chapter_line_index,
                        validation_error=str(exc),
                        retry_attempt=attempts,
                    )
                    try:
                        self._run_job(retry_job)
                    except PipelineError as job_exc:
                        if attempts >= LOCAL_WINDOW_AUDIT_VALIDATION_RETRY_MAX:
                            if blocking:
                                raise
                            units[window_id] = {
                                "status": "failed",
                                "validated": False,
                                "fresh": False,
                                "artifact": rel,
                                "chapter_count": len(window),
                                "chapters_reviewed": list(window),
                                "reason": str(job_exc),
                            }
                            all_complete = False
                            all_reused = False
                            self._record_validation_warning(
                                stage="local_window_audit",
                                cycle=cycle,
                                chapter_id=None,
                                artifact=rel,
                                reason=str(job_exc),
                                action="left_invalid_local_window_artifact_after_retry_job_failure",
                            )
                            break
                        self._record_validation_warning(
                            stage="local_window_audit",
                            cycle=cycle,
                            chapter_id=None,
                            artifact=rel,
                            reason=str(job_exc),
                            action="retry_local_window_job_failed_will_retry",
                        )
            window_status = str(units.get(window_id, {}).get("status", "")).strip()
            if window_status != "reused":
                all_reused = False
            if window_status not in {"reused", "complete"}:
                all_complete = False

        if all_reused:
            status = "reused"
            reason = None
        elif all_complete:
            status = "complete"
            reason = None
        elif any_complete:
            status = "partial"
            reason = "nonblocking_windows_missing_or_invalid"
        else:
            status = "failed"
            reason = "nonblocking_windows_missing_or_invalid"
        self._log(f"cycle={cpad} local_window_audit_complete status={status}")
        result = {
            "status": status,
            "units": units,
            "window_count": len(windows),
        }
        if reason:
            result["reason"] = reason
        return result

    def _build_local_window_audit_job(
        self,
        cycle: int,
        window: list[str],
        chapter_line_index: dict[str, dict[str, int]],
        validation_error: str | None = None,
        retry_attempt: int = 0,
    ) -> JobSpec:
        del chapter_line_index
        cpad = self._cpad(cycle)
        window_id = self._window_id_for_chapters(window)
        full_novel_file = f"snapshots/cycle_{cpad}/FINAL_NOVEL.md"
        chapter_line_index_file = self._chapter_line_index_rel(cycle)
        continuity_sheet_file = self._ensure_cycle_continuity_snapshot(cycle)
        output_file = self._local_window_audit_rel(cycle, window_id)
        window_chapter_specs = [
            f"outline/chapter_specs/{chapter_id}.json" for chapter_id in window
        ]
        prompt = self._render_prompt(
            "local_window_audit_prompt.md",
            {
                "CYCLE_PADDED": cpad,
                "CYCLE_INT": str(cycle),
                "WINDOW_ID": window_id,
                "FULL_NOVEL_FILE": full_novel_file,
                "CHAPTER_LINE_INDEX_FILE": chapter_line_index_file,
                "CONTINUITY_SHEET_FILE": continuity_sheet_file,
                "WINDOW_CHAPTER_IDS": json.dumps(window),
                "WINDOW_CHAPTER_SPECS": "\n".join(
                    f"{idx}. `{rel}`" for idx, rel in enumerate(window_chapter_specs, start=1)
                ),
                "LOCAL_WINDOW_OUTPUT_FILE": output_file,
            },
        )
        if validation_error:
            safe_error = " ".join(str(validation_error).split())
            prompt += (
                "\n\nValidator feedback from previous attempt:\n"
                f"- {safe_error}\n"
                "Regenerate the local-window audit JSON so it satisfies the contract exactly.\n"
                "Prefer repairing malformed shape over inventing new findings.\n"
            )
            prompt += self._retry_guidance_for_validation_error(
                validation_error=safe_error,
                target_file=full_novel_file,
            )
        retry_suffix = f"_retry_{retry_attempt}" if retry_attempt > 0 else ""
        return self._make_job(
            job_id=f"cycle_{cpad}_local_window_{window_id}{retry_suffix}",
            stage="local_window_audit",
            stage_group="cross_chapter_audit",
            cycle=cycle,
            chapter_id=None,
            allowed_inputs=[
                full_novel_file,
                chapter_line_index_file,
                continuity_sheet_file,
                "outline/style_bible.json",
                "config/constitution.md",
                "config/prompts/local_window_audit_prompt.md",
                *window_chapter_specs,
            ],
            required_outputs=[output_file],
            prompt_text=prompt,
        )

    def _log_cross_chapter_audit_convergence(
        self, cycle: int, audit_data: dict[str, Any]
    ) -> None:
        cpad = self._cpad(cycle)
        audit_count = len(audit_data.get("redundancy_findings", [])) + len(
            audit_data.get("consistency_findings", [])
        )
        self._log(f"cycle={cpad} cross_chapter_audit_findings count={audit_count}")
        if cycle <= 1:
            return
        prev_rel = self._cross_chapter_audit_rel(cycle - 1)
        prev_path = self.run_dir / prev_rel
        if not prev_path.is_file():
            return
        try:
            prev_raw = self._read_json(prev_rel)
            prev_data, _ = self._repair_cross_chapter_audit_data(
                copy.deepcopy(prev_raw),
                cycle - 1,
                {spec.chapter_id for spec in self.chapter_specs},
            )
            self._validate_cross_chapter_audit_json(
                prev_data,
                cycle - 1,
                {spec.chapter_id for spec in self.chapter_specs},
                prev_rel,
                f"snapshots/cycle_{self._cpad(cycle - 1)}/FINAL_NOVEL.md",
            )
            prev_count = len(prev_data.get("redundancy_findings", [])) + len(
                prev_data.get("consistency_findings", [])
            )
        except PipelineError:
            return
        if prev_count > 0 and audit_count >= math.ceil(prev_count * 0.9):
            self._log(
                "cross_chapter_audit_not_converging "
                f"cycle_{self._cpad(cycle - 1)}={prev_count} cycle_{cpad}={audit_count}"
            )

    def _build_revision_packets(
        self,
        cycle: int,
        by_chapter: dict[str, list[dict[str, Any]]],
        *,
        extra_non_negotiables: list[str] | None = None,
    ) -> None:
        cpad = self._cpad(cycle)
        dialogue_rules = self.style_bible.get("dialogue_rules", {})
        prose_style_profile = self.style_bible.get("prose_style_profile", {})
        aesthetic_risk_policy = self.style_bible.get("aesthetic_risk_policy", {})
        non_negotiables = [
            "Maintain heading contract exactly (# Chapter N).",
            "Elliptical clipping is not permitted in dialogue or narration.",
            "Avoid transcript cadence in high-stakes dialogue.",
            "Avoid stiff over-formality in dialogue; use contractions and colloquial rhythm where character-true.",
            "Preserve productive dialogue roughness; do not clean living speech into balanced thesis statements.",
            "Reduce procedural drift when it displaces embodied consequence.",
            "Maintain character-specific voice signatures from style bible.",
            "Honor aesthetic risk policy: sanitization is the primary craft risk — do not soften, euphemize, or retreat from the story's established register. When in doubt, err toward rawness.",
        ]
        if extra_non_negotiables:
            combined_non_negotiables: list[str] = []
            seen_non_negotiables: set[str] = set()
            for entry in [*non_negotiables, *extra_non_negotiables]:
                normalized = str(entry).strip()
                if not normalized or normalized in seen_non_negotiables:
                    continue
                seen_non_negotiables.add(normalized)
                combined_non_negotiables.append(normalized)
            non_negotiables = combined_non_negotiables
        for chapter_id, findings in by_chapter.items():
            snapshot_file = (
                self.run_dir
                / "snapshots"
                / f"cycle_{cpad}"
                / "chapters"
                / f"{chapter_id}.md"
            )
            snapshot_hash = self._sha256_file(snapshot_file)
            packet = self._make_revision_packet_payload(
                cycle=cycle,
                chapter_id=chapter_id,
                input_snapshot_hash=snapshot_hash,
                findings=findings,
                non_negotiables=non_negotiables,
                dialogue_rules=dialogue_rules,
                prose_style_profile=prose_style_profile,
                aesthetic_risk_policy=aesthetic_risk_policy,
            )
            rel = self._revision_packet_rel(cycle, chapter_id)
            self._write_json(rel, packet)

            pass_buckets = self._bucket_findings_by_revision_pass(findings)
            for pass_def in REVISION_PASS_DEFS:
                pass_findings = pass_buckets[pass_def["key"]]
                pass_packet = self._make_revision_packet_payload(
                    cycle=cycle,
                    chapter_id=chapter_id,
                    input_snapshot_hash=snapshot_hash,
                    findings=pass_findings,
                    non_negotiables=non_negotiables,
                    dialogue_rules=dialogue_rules,
                    prose_style_profile=prose_style_profile,
                    aesthetic_risk_policy=aesthetic_risk_policy,
                )
                pass_packet["revision_pass"] = {
                    "key": pass_def["key"],
                    "label": pass_def["label"],
                    "focus": pass_def["focus"],
                }
                self._write_json(
                    self._revision_pass_packet_rel(cycle, chapter_id, pass_def["key"]),
                    pass_packet,
                )

    def _compact_aggregator_input_rel(self, cycle: int) -> str:
        return f"packets/cycle_{self._cpad(cycle)}/compact_aggregator_input.json"

    def _aggregation_decisions_rel(self, cycle: int) -> str:
        return f"packets/cycle_{self._cpad(cycle)}/aggregation_decisions.json"

    def _aggregation_materialization_summary_rel(self, cycle: int) -> str:
        return f"packets/cycle_{self._cpad(cycle)}/aggregation_materialization_summary.json"

    def _aggregation_suppressions_rel(self, cycle: int) -> str:
        return f"packets/cycle_{self._cpad(cycle)}/aggregation_suppressions.json"

    def _aggregation_unfixable_rel(self, cycle: int) -> str:
        return f"packets/cycle_{self._cpad(cycle)}/aggregation_unfixable.json"

    def _aggregation_locator_excerpt_pair(
        self, finding: dict[str, Any]
    ) -> tuple[str, str]:
        locator_excerpts = finding.get("locator_excerpts")
        if not isinstance(locator_excerpts, dict):
            return "", ""
        snippets: list[str] = []
        seen: set[str] = set()
        for field_name in (
            "evidence",
            "problem",
            "rewrite_direction",
            "acceptance_test",
        ):
            entries = locator_excerpts.get(field_name, [])
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                excerpt = str(entry.get("excerpt", "")).strip()
                if not excerpt or excerpt in seen:
                    continue
                seen.add(excerpt)
                snippets.append(excerpt)
        if not snippets:
            return "", ""
        locator_excerpt = snippets[0]
        counterpart_excerpt = snippets[1] if len(snippets) > 1 else ""
        return locator_excerpt, counterpart_excerpt

    def _compact_aggregator_source_payload(
        self, finding: dict[str, Any]
    ) -> dict[str, str]:
        raw_source = self._canonical_finding_source_name(finding.get("source", ""))
        raw_severity = str(finding.get("severity", "")).strip().upper()
        payload = {
            "source": raw_source,
            "severity": raw_severity,
        }
        if raw_source in {"award", "craft", "dialogue", "prose"}:
            payload["source"] = "chapter_review"
            payload["review_lens"] = raw_source
        if payload["source"] == "elevation" and raw_severity in {"HIGH", "MEDIUM"}:
            payload["severity"] = f"ELEVATION_{raw_severity}"
        return payload

    def _chapter_local_spans_for_evidence(
        self,
        *,
        cycle: int,
        chapter_id: str,
        evidence: Any,
        chapter_line_index: dict[str, dict[str, int]] | None = None,
    ) -> list[tuple[int, int]]:
        normalized = self._normalize_evidence_field(evidence)
        if not normalized:
            return []
        if chapter_line_index is None:
            try:
                raw_index = self._read_json(self._chapter_line_index_rel(cycle))
            except PipelineError:
                raw_index = {}
            chapter_line_index = raw_index if isinstance(raw_index, dict) else {}
        chapter_bounds = (
            chapter_line_index.get(chapter_id, {})
            if isinstance(chapter_line_index, dict)
            else {}
        )
        compiled_novel_rel = f"snapshots/cycle_{self._cpad(cycle)}/FINAL_NOVEL.md"
        chapter_snapshot_rel = f"snapshots/cycle_{self._cpad(cycle)}/chapters/{chapter_id}.md"
        live_chapter_rel = f"chapters/{chapter_id}.md"
        spans: list[tuple[int, int]] = []
        seen: set[tuple[int, int]] = set()
        for span in self._extract_line_citation_spans(normalized):
            if not isinstance(span, dict):
                continue
            file_rel = str(span.get("file_rel", "")).strip()
            start_line = int(span.get("start_line", 0) or 0)
            end_line = int(span.get("end_line", 0) or 0)
            if start_line <= 0 or end_line <= 0:
                continue
            local_start: int | None = None
            local_end: int | None = None
            if file_rel in {chapter_snapshot_rel, live_chapter_rel}:
                local_start = start_line
                local_end = max(start_line, end_line)
            elif file_rel == compiled_novel_rel:
                chapter_start = int(chapter_bounds.get("start_line", 0) or 0)
                chapter_end = int(chapter_bounds.get("end_line", 0) or 0)
                if chapter_start <= 0 or chapter_end < chapter_start:
                    continue
                overlap_start = max(start_line, chapter_start)
                overlap_end = min(end_line, chapter_end)
                if overlap_end < overlap_start:
                    continue
                local_start = overlap_start - chapter_start + 1
                local_end = overlap_end - chapter_start + 1
            if local_start is None or local_end is None:
                continue
            key = (local_start, local_end)
            if key in seen:
                continue
            seen.add(key)
            spans.append(key)
        return spans

    def _evidence_span_match_score(
        self,
        current_spans: list[tuple[int, int]],
        prior_spans: list[tuple[int, int]],
        *,
        tolerance_lines: int = 20,
    ) -> int | None:
        best_score: int | None = None
        for current_start, current_end in current_spans:
            for prior_start, prior_end in prior_spans:
                gap = 0
                if current_end < prior_start:
                    gap = prior_start - current_end
                elif prior_end < current_start:
                    gap = current_start - prior_end
                if gap > tolerance_lines:
                    continue
                overlap = min(current_end, prior_end) - max(current_start, prior_start) + 1
                if overlap > 0:
                    score = 1000 + overlap
                else:
                    score = max(1, tolerance_lines - gap + 1)
                if best_score is None or score > best_score:
                    best_score = score
        return best_score

    def _load_prior_revision_attempts(
        self, cycle: int, chapter_ids: list[str]
    ) -> dict[str, list[dict[str, Any]]]:
        if cycle <= 1:
            return {}
        previous_cycle = cycle - 1
        try:
            raw_index = self._read_json(self._chapter_line_index_rel(previous_cycle))
        except PipelineError:
            raw_index = {}
        previous_line_index = raw_index if isinstance(raw_index, dict) else {}
        attempts_by_chapter: dict[str, list[dict[str, Any]]] = {}
        for chapter_id in chapter_ids:
            report_rel = self._revision_report_rel(previous_cycle, chapter_id)
            report_path = self.run_dir / report_rel
            if not report_path.is_file():
                continue
            packet_rel = self._revision_packet_rel(previous_cycle, chapter_id)
            expected_ids: set[str] = set()
            source_by_finding_id: dict[str, str] = {}
            if (self.run_dir / packet_rel).is_file():
                try:
                    packet_data = self._read_json(packet_rel)
                    expected_ids = self._finding_ids_from_packet(packet_data)
                    for finding in packet_data.get("findings", []):
                        if not isinstance(finding, dict):
                            continue
                        finding_id = str(finding.get("finding_id", "")).strip()
                        if not finding_id:
                            continue
                        source_by_finding_id[finding_id] = self._compact_aggregator_source_payload(
                            finding
                        )["source"]
                except PipelineError:
                    expected_ids = set()
                    source_by_finding_id = {}
            try:
                report_data = self._load_repaired_revision_report(
                    report_rel,
                    chapter_id,
                    expected_ids,
                    chapter_file=f"chapters/{chapter_id}.md",
                )
            except PipelineError:
                continue
            chapter_attempts: list[dict[str, Any]] = []
            for row in report_data.get("finding_results", []):
                if not isinstance(row, dict):
                    continue
                status = str(row.get("status_after_revision", "")).strip()
                if status not in {"PARTIAL", "UNRESOLVED"}:
                    continue
                revision_note = str(row.get("revision_note", "")).strip()
                if not revision_note:
                    continue
                local_spans = self._chapter_local_spans_for_evidence(
                    cycle=previous_cycle,
                    chapter_id=chapter_id,
                    evidence=row.get("evidence", ""),
                    chapter_line_index=previous_line_index,
                )
                if not local_spans:
                    continue
                finding_id = str(row.get("finding_id", "")).strip()
                chapter_attempts.append(
                    {
                        "cycle": previous_cycle,
                        "finding_id": finding_id,
                        "status": status,
                        "revision_note": revision_note,
                        "local_spans": local_spans,
                        "source": source_by_finding_id.get(finding_id, ""),
                    }
                )
            if chapter_attempts:
                attempts_by_chapter[chapter_id] = chapter_attempts
        return attempts_by_chapter

    def _prior_attempt_context_for_finding(
        self,
        *,
        cycle: int,
        chapter_id: str,
        finding: dict[str, Any],
        chapter_line_index: dict[str, dict[str, int]] | None,
        prior_attempts: list[dict[str, Any]],
    ) -> str | None:
        if not prior_attempts:
            return None
        current_spans = self._chapter_local_spans_for_evidence(
            cycle=cycle,
            chapter_id=chapter_id,
            evidence=finding.get("evidence", ""),
            chapter_line_index=chapter_line_index,
        )
        if not current_spans:
            return None
        current_source = self._compact_aggregator_source_payload(finding)["source"]
        best_attempt: dict[str, Any] | None = None
        best_score: int | None = None
        for attempt in prior_attempts:
            if not isinstance(attempt, dict):
                continue
            prior_spans = attempt.get("local_spans", [])
            if not isinstance(prior_spans, list) or not prior_spans:
                continue
            span_score = self._evidence_span_match_score(current_spans, prior_spans)
            if span_score is None:
                continue
            total_score = span_score
            if str(attempt.get("source", "")).strip() == current_source:
                total_score += 50
            if best_score is None or total_score > best_score:
                best_score = total_score
                best_attempt = attempt
        if best_attempt is None:
            return None
        note = str(best_attempt.get("revision_note", "")).strip()
        if not note:
            return None
        prior_cycle = int(best_attempt.get("cycle", max(1, cycle - 1)) or max(1, cycle - 1))
        prior_status = str(best_attempt.get("status", "")).strip().upper() or "PARTIAL"
        return f"Cycle {prior_cycle} {prior_status} revision note: {note}"

    def _build_compact_aggregator_input(
        self, cycle: int, chapter_ids: list[str]
    ) -> dict[str, Any]:
        continuity_sheet_file = self._ensure_cycle_continuity_snapshot(cycle)
        style_bible = self.style_bible or self._load_and_validate_style_bible()
        try:
            raw_index = self._read_json(self._chapter_line_index_rel(cycle))
        except PipelineError:
            raw_index = {}
        chapter_line_index = raw_index if isinstance(raw_index, dict) else {}
        prior_attempts_by_chapter = self._load_prior_revision_attempts(cycle, chapter_ids)
        chapters_payload: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for chapter_id in chapter_ids:
            pass_payload: dict[str, list[dict[str, Any]]] = {}
            for pass_def in REVISION_PASS_DEFS:
                pass_key = pass_def["key"]
                packet_rel = self._revision_pass_packet_rel(cycle, chapter_id, pass_key)
                packet_data = self._read_json(packet_rel)
                packet_findings = packet_data.get("findings", [])
                if not isinstance(packet_findings, list):
                    continue
                compact_rows: list[dict[str, Any]] = []
                for finding in packet_findings:
                    if not isinstance(finding, dict):
                        continue
                    finding_id = str(finding.get("finding_id", "")).strip()
                    if not finding_id:
                        continue
                    source_payload = self._compact_aggregator_source_payload(finding)
                    locator_excerpt, counterpart_excerpt = (
                        self._aggregation_locator_excerpt_pair(finding)
                    )
                    compact_row = {
                        "finding_id": finding_id,
                        "source": source_payload["source"],
                        "severity": source_payload["severity"],
                        "pass_key": pass_key,
                        "problem": str(finding.get("problem", "")).strip(),
                        "rewrite_direction": str(
                            finding.get("rewrite_direction", "")
                        ).strip(),
                        "acceptance_test": str(
                            finding.get("acceptance_test", "")
                        ).strip(),
                    }
                    review_lens = source_payload.get("review_lens")
                    if review_lens:
                        compact_row["review_lens"] = review_lens
                    if locator_excerpt:
                        compact_row["locator_excerpt"] = locator_excerpt
                    if counterpart_excerpt:
                        compact_row["counterpart_excerpt"] = counterpart_excerpt
                    prior_attempt_context = self._prior_attempt_context_for_finding(
                        cycle=cycle,
                        chapter_id=chapter_id,
                        finding=finding,
                        chapter_line_index=chapter_line_index,
                        prior_attempts=prior_attempts_by_chapter.get(chapter_id, []),
                    )
                    if prior_attempt_context:
                        compact_row["prior_attempt_context"] = prior_attempt_context
                    compact_rows.append(compact_row)
                if compact_rows:
                    pass_payload[pass_key] = compact_rows
            if pass_payload:
                chapters_payload[chapter_id] = pass_payload
        return {
            "shared_context": {
                "continuity_sheet": self._read_json(continuity_sheet_file),
                "style_bible": {
                    "character_voice_profiles": style_bible.get(
                        "character_voice_profiles", []
                    ),
                    "prose_style_profile": style_bible.get("prose_style_profile", {}),
                    "aesthetic_risk_policy": style_bible.get(
                        "aesthetic_risk_policy", {}
                    ),
                },
                "chapter_count": len(self.chapter_specs),
            },
            "chapters": chapters_payload,
        }

    def _compact_aggregator_input_finding_ids(
        self, compact_input: dict[str, Any]
    ) -> set[str]:
        finding_ids: set[str] = set()
        chapters = compact_input.get("chapters", {})
        if not isinstance(chapters, dict):
            return finding_ids
        for chapter_payload in chapters.values():
            if not isinstance(chapter_payload, dict):
                continue
            for pass_payload in chapter_payload.values():
                if not isinstance(pass_payload, list):
                    continue
                for finding in pass_payload:
                    if not isinstance(finding, dict):
                        continue
                    finding_id = str(finding.get("finding_id", "")).strip()
                    if finding_id:
                        finding_ids.add(finding_id)
        return finding_ids

    def _llm_aggregator_input_paths(self, cycle: int) -> list[Path]:
        return [
            self.run_dir / self._compact_aggregator_input_rel(cycle),
            self.run_dir / "outline" / "chapter_specs.jsonl",
            self.run_dir / "config" / "prompts" / "revision_aggregator_prompt.md",
        ]

    def _build_revision_aggregator_job(self, cycle: int) -> JobSpec:
        cpad = self._cpad(cycle)
        compact_input_file = self._compact_aggregator_input_rel(cycle)
        decisions_file = self._aggregation_decisions_rel(cycle)
        prompt = self._render_prompt(
            "revision_aggregator_prompt.md",
            {
                "CYCLE_PADDED": cpad,
                "COMPACT_AGGREGATOR_INPUT_FILE": compact_input_file,
                "AGGREGATION_DECISIONS_OUTPUT_FILE": decisions_file,
            },
        )
        return self._make_job(
            job_id=f"cycle_{cpad}_revision_aggregator",
            stage="llm_aggregator",
            stage_group="revision",
            cycle=cycle,
            chapter_id=None,
            allowed_inputs=[
                compact_input_file,
                "outline/chapter_specs.jsonl",
                "config/prompts/revision_aggregator_prompt.md",
            ],
            required_outputs=[decisions_file],
            prompt_text=prompt,
        )

    def _run_llm_aggregator_stage(
        self, cycle: int, chapter_ids: list[str]
    ) -> dict[str, Any]:
        cpad = self._cpad(cycle)
        compact_input = self._build_compact_aggregator_input(cycle, chapter_ids)
        compact_rel = self._compact_aggregator_input_rel(cycle)
        self._write_json(compact_rel, compact_input)
        input_finding_ids = self._compact_aggregator_input_finding_ids(compact_input)
        outputs = [compact_rel]
        if not input_finding_ids:
            self._log(f"cycle={cpad} llm_aggregator_skip reason=no_packet_findings")
            return {
                "status": "skipped",
                "reason": "no_packet_findings",
                "outputs": outputs,
            }

        decisions_rel = self._aggregation_decisions_rel(cycle)
        decisions_path = self.run_dir / decisions_rel
        if self._artifact_fresh_against_inputs(
            decisions_path, self._llm_aggregator_input_paths(cycle)
        ):
            try:
                decisions = self._load_repaired_aggregation_decisions(
                    decisions_rel, input_finding_ids
                )
                return {
                    "status": "reused",
                    "outputs": outputs + [decisions_rel],
                    "decisions": decisions,
                }
            except PipelineError as exc:
                self._log(
                    f"cycle={cpad} llm_aggregator_resume_invalid reason={exc}"
                )

        try:
            self._run_job(self._build_revision_aggregator_job(cycle))
        except PipelineError as exc:
            if not self._soft_validation_enabled():
                raise
            self._record_validation_warning(
                stage="llm_aggregator",
                cycle=cycle,
                chapter_id=None,
                artifact=decisions_rel,
                reason=str(exc),
                action="continued_with_mechanical_packets_after_llm_aggregator_failure",
            )
            return {
                "status": "failed",
                "reason": "llm_aggregator_failed_fallback_to_mechanical_packets",
                "outputs": outputs,
            }

        try:
            decisions = self._load_repaired_aggregation_decisions(
                decisions_rel, input_finding_ids
            )
        except PipelineError as exc:
            if not self._soft_validation_enabled():
                raise
            self._record_validation_warning(
                stage="llm_aggregator",
                cycle=cycle,
                chapter_id=None,
                artifact=decisions_rel,
                reason=str(exc),
                action="continued_with_mechanical_packets_after_invalid_aggregation_decisions",
            )
            return {
                "status": "failed",
                "reason": "invalid_decisions_fallback_to_mechanical_packets",
                "outputs": outputs,
            }
        return {
            "status": "complete",
            "outputs": outputs + [decisions_rel],
            "decisions": decisions,
        }

    def _materialize_aggregation_decisions_stage(
        self,
        cycle: int,
        chapter_ids: list[str],
        aggregator_summary: dict[str, Any],
    ) -> dict[str, Any]:
        outputs = [
            self._aggregation_materialization_summary_rel(cycle),
            self._aggregation_suppressions_rel(cycle),
            self._aggregation_unfixable_rel(cycle),
        ]
        decisions = aggregator_summary.get("decisions")
        if not isinstance(decisions, dict):
            return {
                "status": "skipped",
                "reason": "llm_aggregator_fallback_to_mechanical_packets",
            }

        decisions_sha1 = self._aggregation_decisions_sha1(decisions)
        if self._aggregation_materialization_is_current(
            cycle, chapter_ids, decisions_sha1
        ):
            return {
                "status": "reused",
                "outputs": outputs,
            }

        baseline_by_chapter = self._load_materializable_packet_findings(
            cycle, chapter_ids
        )
        try:
            self._apply_aggregation_decisions(
                cycle,
                chapter_ids,
                decisions,
                baseline_by_chapter=baseline_by_chapter,
            )
        except PipelineError as exc:
            if not self._soft_validation_enabled():
                raise
            self._build_revision_packets(cycle, baseline_by_chapter)
            self._record_validation_warning(
                stage="materialize_aggregation_decisions",
                cycle=cycle,
                chapter_id=None,
                artifact=self._aggregation_materialization_summary_rel(cycle),
                reason=str(exc),
                action="continued_with_mechanical_packets_after_materialization_failure",
            )
            return {
                "status": "failed",
                "reason": "materialization_failed_fallback_to_mechanical_packets",
                "outputs": outputs,
            }
        return {
            "status": "complete",
            "outputs": outputs,
        }

    def _load_materializable_packet_findings(
        self, cycle: int, chapter_ids: list[str]
    ) -> dict[str, list[dict[str, Any]]]:
        by_chapter: dict[str, list[dict[str, Any]]] = {}
        for chapter_id in chapter_ids:
            packet_data = self._read_json(self._revision_packet_rel(cycle, chapter_id))
            packet_findings = packet_data.get("findings", [])
            if not isinstance(packet_findings, list):
                raise PipelineError(
                    f"{self._revision_packet_rel(cycle, chapter_id)} findings must be an array"
                )
            rows: list[dict[str, Any]] = []
            for finding in packet_findings:
                if isinstance(finding, dict):
                    rows.append(copy.deepcopy(finding))
            by_chapter[chapter_id] = rows
        return by_chapter

    def _aggregation_decisions_sha1(self, decisions: dict[str, Any]) -> str:
        rendered = json.dumps(decisions, ensure_ascii=True, sort_keys=True)
        return hashlib.sha1(rendered.encode("utf-8")).hexdigest()

    def _aggregation_materialization_is_current(
        self, cycle: int, chapter_ids: list[str], decisions_sha1: str
    ) -> bool:
        summary_rel = self._aggregation_materialization_summary_rel(cycle)
        try:
            summary_data = self._read_json(summary_rel)
        except PipelineError:
            return False
        if summary_data.get("decisions_sha1") != decisions_sha1:
            return False
        for rel in (
            self._aggregation_suppressions_rel(cycle),
            self._aggregation_unfixable_rel(cycle),
        ):
            if not (self.run_dir / rel).is_file():
                return False
        for chapter_id in chapter_ids:
            packet_rels = [self._revision_packet_rel(cycle, chapter_id)]
            packet_rels.extend(
                self._revision_pass_packet_rel(cycle, chapter_id, pass_def["key"])
                for pass_def in REVISION_PASS_DEFS
            )
            for rel in packet_rels:
                try:
                    packet_data = self._read_json(rel)
                except PipelineError:
                    return False
                applied = packet_data.get("aggregation_applied")
                if not isinstance(applied, dict):
                    return False
                if applied.get("decisions_sha1") != decisions_sha1:
                    return False
        return True

    def _append_aggregation_guidance(
        self, base_text: str, notes: list[str]
    ) -> str:
        cleaned_notes = [str(note).strip() for note in notes if str(note).strip()]
        if not cleaned_notes:
            return base_text
        guidance = "\n".join(f"- {note}" for note in cleaned_notes)
        base = str(base_text).strip()
        if base:
            return f"{base}\n\nAggregator guidance:\n{guidance}"
        return f"Aggregator guidance:\n{guidance}"

    def _apply_aggregation_decisions(
        self,
        cycle: int,
        chapter_ids: list[str],
        decisions: dict[str, Any],
        *,
        baseline_by_chapter: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        baseline = (
            baseline_by_chapter
            if baseline_by_chapter is not None
            else self._load_materializable_packet_findings(cycle, chapter_ids)
        )
        finding_by_id: dict[str, dict[str, Any]] = {}
        ordered_ids_by_chapter: dict[str, list[str]] = {}
        for chapter_id in chapter_ids:
            ordered_ids: list[str] = []
            for finding in baseline.get(chapter_id, []):
                finding_id = str(finding.get("finding_id", "")).strip()
                if not finding_id:
                    continue
                if finding_id in finding_by_id:
                    raise PipelineError(f"duplicate finding_id in packets: {finding_id}")
                finding_by_id[finding_id] = copy.deepcopy(finding)
                ordered_ids.append(finding_id)
            ordered_ids_by_chapter[chapter_id] = ordered_ids

        for row in decisions.get("merges", []):
            if not isinstance(row, dict):
                continue
            target_id = str(row.get("target_finding", "")).strip()
            target = finding_by_id.get(target_id)
            if target is None:
                continue
            merged_direction = str(row.get("merged_rewrite_direction", "")).strip()
            if merged_direction:
                target["rewrite_direction"] = merged_direction
            absorbed_findings = row.get("absorbed_findings", [])
            if not isinstance(absorbed_findings, list):
                continue
            for absorbed_id_raw in absorbed_findings:
                absorbed_id = str(absorbed_id_raw).strip()
                if not absorbed_id or absorbed_id == target_id:
                    continue
                absorbed = finding_by_id.pop(absorbed_id, None)
                if absorbed is None:
                    continue
                target["evidence"] = self._merge_evidence_citations(
                    str(target.get("evidence", "")),
                    str(absorbed.get("evidence", "")),
                )

        for bucket_key in ("suppressions", "unfixable"):
            for row in decisions.get(bucket_key, []):
                if not isinstance(row, dict):
                    continue
                finding_id = str(row.get("finding_id", "")).strip()
                if finding_id:
                    finding_by_id.pop(finding_id, None)

        for row in decisions.get("pass_reassignments", []):
            if not isinstance(row, dict):
                continue
            finding_id = str(row.get("finding_id", "")).strip()
            finding = finding_by_id.get(finding_id)
            if finding is None:
                continue
            to_pass = str(row.get("to_pass", "")).strip()
            if to_pass:
                finding["aggregated_pass_key"] = to_pass

        guidance_by_finding_id: dict[str, list[str]] = {}
        for row in decisions.get("canonical_choices", []):
            if not isinstance(row, dict):
                continue
            choice_id = str(row.get("choice_id", "")).strip()
            value = str(row.get("value", "")).strip()
            grounding = str(row.get("grounding", "")).strip()
            if not (choice_id and value and grounding):
                continue
            note = f"Canonical choice [{choice_id}]: {value}. Grounding: {grounding}"
            affected_findings = row.get("affected_findings", [])
            if not isinstance(affected_findings, list):
                continue
            for finding_id_raw in affected_findings:
                finding_id = str(finding_id_raw).strip()
                if finding_id in finding_by_id:
                    guidance_by_finding_id.setdefault(finding_id, []).append(note)

        consistency_directive_rules: list[str] = []
        for row in decisions.get("consistency_directives", []):
            if not isinstance(row, dict):
                continue
            rule = str(row.get("rule", "")).strip()
            if rule:
                consistency_directive_rules.append(rule)

        for row in decisions.get("context_injections", []):
            if not isinstance(row, dict):
                continue
            target_id = str(row.get("target_finding", "")).strip()
            context = str(row.get("cross_chapter_context", "")).strip()
            if target_id in finding_by_id and context:
                finding_by_id[target_id]["cross_chapter_context"] = context

        for finding_id, notes in guidance_by_finding_id.items():
            finding = finding_by_id.get(finding_id)
            if finding is None:
                continue
            finding["rewrite_direction"] = self._append_aggregation_guidance(
                str(finding.get("rewrite_direction", "")),
                notes,
            )

        materialized_by_chapter: dict[str, list[dict[str, Any]]] = {}
        for chapter_id in chapter_ids:
            rows: list[dict[str, Any]] = []
            for finding_id in ordered_ids_by_chapter.get(chapter_id, []):
                finding = finding_by_id.get(finding_id)
                if finding is not None:
                    rows.append(copy.deepcopy(finding))
            materialized_by_chapter[chapter_id] = rows

        self._build_revision_packets(
            cycle,
            materialized_by_chapter,
            extra_non_negotiables=consistency_directive_rules,
        )
        decisions_sha1 = self._aggregation_decisions_sha1(decisions)
        self._tag_aggregation_applied_metadata(cycle, chapter_ids, decisions_sha1)

        summary = {
            "cycle": cycle,
            "decisions_sha1": decisions_sha1,
            "chapters_materialized": len(chapter_ids),
            "finding_count_after_materialization": sum(
                len(rows) for rows in materialized_by_chapter.values()
            ),
            "merge_count": len(
                [row for row in decisions.get("merges", []) if isinstance(row, dict)]
            ),
            "canonical_choice_count": len(
                [
                    row
                    for row in decisions.get("canonical_choices", [])
                    if isinstance(row, dict)
                ]
            ),
            "consistency_directive_count": len(
                [
                    row
                    for row in decisions.get("consistency_directives", [])
                    if isinstance(row, dict)
                ]
            ),
            "context_injection_count": len(
                [
                    row
                    for row in decisions.get("context_injections", [])
                    if isinstance(row, dict)
                ]
            ),
            "suppression_count": len(
                [
                    row
                    for row in decisions.get("suppressions", [])
                    if isinstance(row, dict)
                ]
            ),
            "unfixable_count": len(
                [
                    row
                    for row in decisions.get("unfixable", [])
                    if isinstance(row, dict)
                ]
            ),
            "pass_reassignment_count": len(
                [
                    row
                    for row in decisions.get("pass_reassignments", [])
                    if isinstance(row, dict)
                ]
            ),
        }
        self._write_json(self._aggregation_materialization_summary_rel(cycle), summary)
        self._write_json(
            self._aggregation_suppressions_rel(cycle),
            {
                "cycle": cycle,
                "decisions_sha1": decisions_sha1,
                "suppressions": [
                    row
                    for row in decisions.get("suppressions", [])
                    if isinstance(row, dict)
                ],
            },
        )
        self._write_json(
            self._aggregation_unfixable_rel(cycle),
            {
                "cycle": cycle,
                "decisions_sha1": decisions_sha1,
                "unfixable": [
                    row
                    for row in decisions.get("unfixable", [])
                    if isinstance(row, dict)
                ],
            },
        )

    def _tag_aggregation_applied_metadata(
        self, cycle: int, chapter_ids: list[str], decisions_sha1: str
    ) -> None:
        metadata = {
            "decisions_sha1": decisions_sha1,
            "decisions_file": self._aggregation_decisions_rel(cycle),
        }
        for chapter_id in chapter_ids:
            packet_rels = [self._revision_packet_rel(cycle, chapter_id)]
            packet_rels.extend(
                self._revision_pass_packet_rel(cycle, chapter_id, pass_def["key"])
                for pass_def in REVISION_PASS_DEFS
            )
            for rel in packet_rels:
                packet_data = self._read_json(rel)
                packet_data["aggregation_applied"] = metadata
                self._write_json(rel, packet_data)

    def _run_revision_stage(self, cycle: int, chapter_ids: list[str]) -> dict[str, Any]:
        cpad = self._cpad(cycle)
        global_context_file = f"context/cycle_{cpad}/global_cycle_context.json"
        continuity_sheet_file = self._ensure_cycle_continuity_snapshot(cycle)
        units: dict[str, dict[str, Any]] = {}

        for pass_index, pass_def in enumerate(REVISION_PASS_DEFS, start=1):
            pass_key = pass_def["key"]
            pass_label = pass_def["label"]
            terminal_pass = pass_index == len(REVISION_PASS_DEFS)
            jobs: list[JobSpec] = []

            for chapter_id in chapter_ids:
                chapter_number = self._chapter_number(chapter_id)
                chapter_file = f"chapters/{chapter_id}.md"
                chapter_path = self.run_dir / chapter_file
                self._validate_chapter_heading(chapter_path, chapter_number)

                packet_file = self._revision_pass_packet_rel(cycle, chapter_id, pass_key)
                packet_path = self.run_dir / packet_file
                packet_data = self._read_json(packet_file)
                expected_ids = self._finding_ids_from_packet(packet_data)

                report_file = self._revision_pass_report_rel(cycle, chapter_id, pass_key)
                report_path = self.run_dir / report_file

                if not expected_ids:
                    no_op_report = {
                        "chapter_id": chapter_id,
                        "finding_results": [],
                        "summary": f"{pass_label}: no assigned findings.",
                    }
                    if report_path.is_file():
                        try:
                            self._load_repaired_revision_report(
                                report_file,
                                chapter_id,
                                expected_ids,
                                chapter_file=chapter_file,
                            )
                            units[f"{chapter_id}.{pass_key}"] = {
                                "status": "reused",
                                "validated": True,
                                "fresh": True,
                            }
                            continue
                        except PipelineError:
                            pass
                    self._write_json(report_file, no_op_report)
                    units[f"{chapter_id}.{pass_key}"] = {
                        "status": "complete",
                        "validated": True,
                        "fresh": True,
                    }
                    continue

                if report_path.is_file():
                    try:
                        report_mtime = report_path.stat().st_mtime
                        chapter_mtime = chapter_path.stat().st_mtime
                        self._load_repaired_revision_report(
                            report_file,
                            chapter_id,
                            expected_ids,
                            chapter_file=chapter_file,
                        )
                        freshness_floor = packet_path.stat().st_mtime
                        if terminal_pass or not self._has_valid_later_revision_pass_report(
                            cycle=cycle,
                            chapter_id=chapter_id,
                            current_pass_index=pass_index,
                            chapter_file=chapter_file,
                            chapter_mtime=chapter_mtime,
                        ):
                            freshness_floor = max(freshness_floor, chapter_mtime)
                        if report_mtime >= freshness_floor:
                            units[f"{chapter_id}.{pass_key}"] = {
                                "status": "reused",
                                "validated": True,
                                "fresh": True,
                            }
                            continue
                    except PipelineError:
                        pass

                jobs.append(
                    self._build_chapter_revision_job(
                        cycle=cycle,
                        chapter_id=chapter_id,
                        chapter_number=chapter_number,
                        pass_def=pass_def,
                        global_context_file=global_context_file,
                        continuity_sheet_file=continuity_sheet_file,
                        packet_data=packet_data,
                    )
                )

            if jobs:
                try:
                    self._run_jobs_parallel(
                        jobs,
                        self.cfg.max_parallel_revisions,
                        f"revise_cycle_{cpad}_{pass_key}",
                    )
                except PipelineError as exc:
                    if not self._soft_validation_enabled():
                        raise
                    self._record_validation_warning(
                        stage="chapter_revision",
                        cycle=cycle,
                        chapter_id=None,
                        artifact=f"revisions/cycle_{cpad}",
                        reason=str(exc),
                        action=f"continued_after_parallel_revision_failure_{pass_key}",
                    )
            else:
                self._log(
                    f"cycle={cpad} revise_resume_{pass_key} all_chapters_present"
                )

            for chapter_id in chapter_ids:
                chapter_path = self.run_dir / "chapters" / f"{chapter_id}.md"
                self._validate_chapter_heading(
                    chapter_path, self._chapter_number(chapter_id)
                )
                packet_rel = self._revision_pass_packet_rel(cycle, chapter_id, pass_key)
                packet_data = self._read_json(packet_rel)
                expected_ids = self._finding_ids_from_packet(packet_data)
                report_rel = self._revision_pass_report_rel(cycle, chapter_id, pass_key)
                attempts = 0
                while True:
                    try:
                        self._materialize_output_alias(
                            base_dir=self.run_dir,
                            required_rel=report_rel,
                            stage="chapter_revision",
                            cycle=cycle,
                            chapter_id=chapter_id,
                        )
                        self._load_repaired_revision_report(
                            report_rel,
                            chapter_id,
                            expected_ids,
                            chapter_file=f"chapters/{chapter_id}.md",
                        )
                        break
                    except PipelineError as exc:
                        if attempts >= REVISION_VALIDATION_RETRY_MAX:
                            if not self._soft_validation_enabled():
                                raise
                            fallback = self._fallback_revision_report_payload(
                                chapter_id=chapter_id,
                                chapter_file=f"chapters/{chapter_id}.md",
                                expected_ids=expected_ids,
                                reason=str(exc),
                            )
                            self._write_json(report_rel, fallback)
                            self._record_validation_warning(
                                stage="chapter_revision",
                                cycle=cycle,
                                chapter_id=chapter_id,
                                artifact=report_rel,
                                reason=str(exc),
                                action=f"wrote_fallback_revision_report_{pass_key}",
                            )
                            break
                        attempts += 1
                        self._log(
                            "cycle="
                            f"{cpad} revision_validation_retry pass={pass_key} "
                            f"chapter={chapter_id} attempt={attempts}/"
                            f"{REVISION_VALIDATION_RETRY_MAX} reason={exc}"
                        )
                        retry_job = self._build_chapter_revision_job(
                            cycle=cycle,
                            chapter_id=chapter_id,
                            chapter_number=self._chapter_number(chapter_id),
                            pass_def=pass_def,
                            global_context_file=global_context_file,
                            continuity_sheet_file=continuity_sheet_file,
                            packet_data=packet_data,
                            validation_error=str(exc),
                            retry_attempt=attempts,
                        )
                        try:
                            self._run_job(retry_job)
                        except PipelineError as job_exc:
                            if attempts >= REVISION_VALIDATION_RETRY_MAX:
                                if not self._soft_validation_enabled():
                                    raise
                                fallback = self._fallback_revision_report_payload(
                                    chapter_id=chapter_id,
                                    chapter_file=f"chapters/{chapter_id}.md",
                                    expected_ids=expected_ids,
                                    reason=str(job_exc),
                                )
                                self._write_json(report_rel, fallback)
                                self._record_validation_warning(
                                    stage="chapter_revision",
                                    cycle=cycle,
                                    chapter_id=chapter_id,
                                    artifact=report_rel,
                                    reason=str(job_exc),
                                    action=(
                                        f"wrote_fallback_revision_report_after_retry_job_failure_{pass_key}"
                                    ),
                                )
                                break
                            self._record_validation_warning(
                                stage="chapter_revision",
                                cycle=cycle,
                                chapter_id=chapter_id,
                                artifact=report_rel,
                                reason=str(job_exc),
                                action=f"retry_job_failed_will_retry_{pass_key}",
                            )
                units[f"{chapter_id}.{pass_key}"] = {
                    "status": units.get(f"{chapter_id}.{pass_key}", {}).get(
                        "status", "complete"
                    ),
                    "validated": True,
                    "fresh": True,
                }
            self._log(
                f"cycle={cpad} revision_pass_complete pass={pass_key} chapters={len(chapter_ids)}"
            )

        for chapter_id in chapter_ids:
            chapter_file = f"chapters/{chapter_id}.md"
            chapter_path = self.run_dir / chapter_file
            self._validate_chapter_heading(chapter_path, self._chapter_number(chapter_id))

            report_rel = self._revision_report_rel(cycle, chapter_id)
            merged_report = self._merge_revision_pass_reports(cycle, chapter_id)
            self._write_json(report_rel, merged_report)

            packet_rel = self._revision_packet_rel(cycle, chapter_id)
            packet_data = self._read_json(packet_rel)
            expected_ids = self._finding_ids_from_packet(packet_data)
            try:
                merged_report = self._load_repaired_revision_report(
                    report_rel,
                    chapter_id,
                    expected_ids,
                    chapter_file=chapter_file,
                )
            except PipelineError as exc:
                if not self._soft_validation_enabled():
                    raise
                fallback = self._fallback_revision_report_payload(
                    chapter_id=chapter_id,
                    chapter_file=chapter_file,
                    expected_ids=expected_ids,
                    reason=str(exc),
                )
                self._write_json(report_rel, fallback)
                self._record_validation_warning(
                    stage="chapter_revision",
                    cycle=cycle,
                    chapter_id=chapter_id,
                    artifact=report_rel,
                    reason=str(exc),
                    action="replaced_invalid_merged_revision_report_with_fallback",
                )
        self._log(f"cycle={cpad} revisions_complete chapters={len(chapter_ids)}")
        reused_count = sum(
            1 for row in units.values() if row.get("status") == "reused"
        )
        return {
            "status": (
                "reused"
                if units and reused_count == len(units)
                else "complete"
            ),
            "chapter_count": len(chapter_ids),
            "units": units,
        }

    def _has_valid_later_revision_pass_report(
        self,
        *,
        cycle: int,
        chapter_id: str,
        current_pass_index: int,
        chapter_file: str,
        chapter_mtime: float,
    ) -> bool:
        later_pass_defs = REVISION_PASS_DEFS[current_pass_index:]
        for pass_def in later_pass_defs:
            packet_rel = self._revision_pass_packet_rel(cycle, chapter_id, pass_def["key"])
            packet_path = self.run_dir / packet_rel
            if not packet_path.is_file():
                continue
            try:
                packet_data = self._read_json(packet_rel)
            except PipelineError:
                continue
            expected_ids = self._finding_ids_from_packet(packet_data)
            report_rel = self._revision_pass_report_rel(cycle, chapter_id, pass_def["key"])
            report_path = self.run_dir / report_rel
            if not report_path.is_file():
                continue
            report_mtime = report_path.stat().st_mtime
            try:
                self._load_repaired_revision_report(
                    report_rel,
                    chapter_id,
                    expected_ids,
                    chapter_file=chapter_file,
                )
                if report_mtime >= chapter_mtime:
                    return True
            except PipelineError:
                continue
        return False

    def _build_chapter_revision_job(
        self,
        *,
        cycle: int,
        chapter_id: str,
        chapter_number: int,
        pass_def: dict[str, str],
        global_context_file: str,
        continuity_sheet_file: str,
        packet_data: dict[str, Any],
        validation_error: str | None = None,
        retry_attempt: int = 0,
    ) -> JobSpec:
        cpad = self._cpad(cycle)
        pass_key = pass_def["key"]
        pass_label = pass_def["label"]
        chapter_file = f"chapters/{chapter_id}.md"
        packet_file = self._revision_pass_packet_rel(cycle, chapter_id, pass_key)
        report_file = self._revision_pass_report_rel(cycle, chapter_id, pass_key)
        boundary_context_file = f"context/cycle_{cpad}/boundary/{chapter_id}.boundary.json"
        packet_has_locator_excerpts = bool(packet_data.get("has_locator_excerpts"))
        packet_original_snapshot_file = str(
            packet_data.get("original_snapshot_file", "")
        ).strip()
        dialogue_anchor_file = (
            f"snapshots/cycle_{cpad}/chapters/{chapter_id}.md"
            if pass_key == REVISION_DIALOGUE_PASS_KEY
            else None
        )
        locator_snapshot_input_line = ""
        locator_snapshot_instruction = ""
        dialogue_anchor_input_line = ""
        dialogue_anchor_instruction = ""
        additional_allowed_inputs: list[str] = []
        if (
            packet_has_locator_excerpts
            and pass_key != REVISION_DIALOGUE_PASS_KEY
            and packet_original_snapshot_file
        ):
            locator_snapshot_input_line = (
                "Additional input: original pre-review chapter snapshot for locator use: "
                f"`{packet_original_snapshot_file}`"
            )
            locator_snapshot_instruction = (
                "Locator guidance: If the revision packet includes `locator_excerpts`, use "
                "those excerpted spans to locate the target passage in the live chapter. "
                "When earlier passes have shifted lines enough to make that hard, consult "
                f"the original snapshot `{packet_original_snapshot_file}` only as a locator "
                "and texture-preservation aid. Do not copy stale wording back in wholesale."
            )
            additional_allowed_inputs.append(packet_original_snapshot_file)
        if dialogue_anchor_file is not None:
            dialogue_anchor_input_line = (
                f"Additional input: original pre-revision chapter snapshot: `{dialogue_anchor_file}`"
            )
            dialogue_anchor_instruction = (
                "Dialogue anchor guidance: "
                f"If `{chapter_file}` has drifted into cleaner or more thesis-like speech, "
                f"compare against `{dialogue_anchor_file}` and preserve the earlier spoken "
                "texture wherever it is already alive. Fix only the packet's cited dialogue "
                "defect; do not replace the chapter's living speech with a tidier default."
            )
            additional_allowed_inputs.append(dialogue_anchor_file)
        prompt = self._render_prompt(
            "chapter_revision_prompt.md",
            {
                "CHAPTER_ID": chapter_id,
                "CHAPTER_NUMBER": str(chapter_number),
                "CHAPTER_INPUT_FILE": chapter_file,
                "CHAPTER_OUTPUT_FILE": chapter_file,
                "REVISION_PACKET_FILE": packet_file,
                "GLOBAL_CYCLE_CONTEXT_FILE": global_context_file,
                "CHAPTER_BOUNDARY_CONTEXT_FILE": boundary_context_file,
                "CONTINUITY_SHEET_FILE": continuity_sheet_file,
                "REVISION_REPORT_FILE": report_file,
                "REVISION_PASS_LABEL": pass_label,
                "REVISION_PASS_FOCUS": pass_def["focus"],
                "OPTIONAL_ORIGINAL_SNAPSHOT_INPUT_LINE": locator_snapshot_input_line,
                "OPTIONAL_ORIGINAL_SNAPSHOT_INSTRUCTION": locator_snapshot_instruction,
                "DIALOGUE_ANCHOR_INPUT_LINE": dialogue_anchor_input_line,
                "DIALOGUE_ANCHOR_INSTRUCTION": dialogue_anchor_instruction,
            },
        )
        if validation_error:
            safe_error = " ".join(str(validation_error).split())
            prompt += (
                "\n\nValidator feedback from previous attempt:\n"
                f"- {safe_error}\n"
                "Regenerate the revision report JSON so it satisfies the contract exactly.\n"
                "Preserve resolved chapter edits while correcting report-format defects.\n"
            )
            prompt += self._retry_guidance_for_validation_error(
                validation_error=safe_error,
                target_file=chapter_file,
            )
        retry_suffix = f"_retry_{retry_attempt}" if retry_attempt > 0 else ""
        return self._make_job(
            job_id=f"cycle_{cpad}_revise_{pass_key}_{chapter_id}{retry_suffix}",
            stage="chapter_revision",
            stage_group="revision",
            revision_pass_key=pass_key,
            cycle=cycle,
            chapter_id=chapter_id,
            allowed_inputs=[
                chapter_file,
                packet_file,
                global_context_file,
                boundary_context_file,
                "outline/style_bible.json",
                continuity_sheet_file,
                "config/constitution.md",
                "config/prompts/chapter_revision_prompt.md",
            ]
            + additional_allowed_inputs,
            required_outputs=[chapter_file, report_file],
            prompt_text=prompt,
        )

    def _make_revision_packet_payload(
        self,
        cycle: int,
        chapter_id: str,
        input_snapshot_hash: str,
        findings: list[dict[str, Any]],
        non_negotiables: list[str],
        dialogue_rules: dict[str, Any],
        prose_style_profile: dict[str, Any],
        aesthetic_risk_policy: dict[str, Any],
    ) -> dict[str, Any]:
        enriched_findings: list[dict[str, Any]] = []
        has_locator_excerpts = False
        for finding in findings:
            enriched = self._enrich_finding_for_revision_packet(cycle, finding)
            if enriched.get("locator_excerpts"):
                has_locator_excerpts = True
            enriched_findings.append(enriched)

        packet = {
            "chapter_id": chapter_id,
            "cycle": cycle,
            "input_snapshot_hash": input_snapshot_hash,
            "findings": enriched_findings,
            "must_fix_count": len(enriched_findings),
            "non_negotiables": non_negotiables,
            "acceptance_targets": [
                f"[{f['finding_id']}] {f['acceptance_test']}" for f in enriched_findings
            ],
            "style_constraints": {
                "dialogue_rules": dialogue_rules,
                "prose_style_profile": prose_style_profile,
                "aesthetic_risk_policy": aesthetic_risk_policy,
            },
            "do_not_change": [],
        }
        if has_locator_excerpts:
            packet["has_locator_excerpts"] = True
            packet["original_snapshot_file"] = (
                f"snapshots/cycle_{self._cpad(cycle)}/chapters/{chapter_id}.md"
            )
        return packet

    def _bucket_findings_by_revision_pass(
        self, findings: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        buckets = {row["key"]: [] for row in REVISION_PASS_DEFS}
        for finding in findings:
            key = self._assign_revision_pass_key(finding)
            buckets[key].append(finding)
        return buckets

    def _assign_revision_pass_key(self, finding: dict[str, Any]) -> str:
        aggregated_pass_key = str(finding.get("aggregated_pass_key", "")).strip()
        if aggregated_pass_key in REVISION_PASS_KEYS:
            return aggregated_pass_key
        source = self._canonical_finding_source_name(finding.get("source", ""))
        if source in {"local_window", "elevation"}:
            pass_hint = str(finding.get("pass_hint", "")).strip()
            if pass_hint in REVISION_PASS_KEYS:
                return pass_hint
            return "p1_structural_craft"
        severity = str(finding.get("severity", "")).strip().upper()
        if severity in {"HIGH", "CRITICAL"}:
            return "p1_structural_craft"
        if source in {
            PRIMARY_REVIEW_LENS,
            "craft",
            PRIMARY_GLOBAL_FINDING_SOURCE,
            "length_guardrail",
            "cross_chapter",
        }:
            return "p1_structural_craft"
        if source == "dialogue":
            return "p2_dialogue_idiolect_cadence"
        return "p3_prose_copyedit"

    def _revision_packet_rel(self, cycle: int, chapter_id: str) -> str:
        return f"packets/cycle_{self._cpad(cycle)}/{chapter_id}.revision_packet.json"

    def _revision_pass_packet_rel(self, cycle: int, chapter_id: str, pass_key: str) -> str:
        return (
            f"packets/cycle_{self._cpad(cycle)}/{chapter_id}.{pass_key}.revision_packet.json"
        )

    def _revision_report_rel(self, cycle: int, chapter_id: str) -> str:
        return f"revisions/cycle_{self._cpad(cycle)}/{chapter_id}.revision_report.json"

    def _revision_pass_report_rel(self, cycle: int, chapter_id: str, pass_key: str) -> str:
        return (
            f"revisions/cycle_{self._cpad(cycle)}/{chapter_id}.{pass_key}.revision_report.json"
        )

    def _finding_ids_from_packet(self, packet_data: dict[str, Any]) -> set[str]:
        packet_findings = packet_data.get("findings", [])
        return {
            str(f.get("finding_id", "")).strip()
            for f in packet_findings
            if isinstance(f, dict) and str(f.get("finding_id", "")).strip()
        }

    def _merge_revision_pass_reports(self, cycle: int, chapter_id: str) -> dict[str, Any]:
        merged_rows: list[dict[str, Any]] = []
        pass_summaries: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        status_counts = {"FIXED": 0, "PARTIAL": 0, "UNRESOLVED": 0}

        for pass_def in REVISION_PASS_DEFS:
            pass_key = pass_def["key"]
            report_rel = self._revision_pass_report_rel(cycle, chapter_id, pass_key)
            data = self._read_json(report_rel)
            pass_summaries.append(
                {
                    "pass_key": pass_key,
                    "pass_label": pass_def["label"],
                    "summary": str(data.get("summary", "")).strip(),
                }
            )
            for row in data.get("finding_results", []):
                if not isinstance(row, dict):
                    continue
                fid = str(row.get("finding_id", "")).strip()
                if not fid or fid in seen_ids:
                    continue
                seen_ids.add(fid)
                status = str(row.get("status_after_revision", "")).strip()
                if status in status_counts:
                    status_counts[status] += 1
                merged_rows.append(row)

        summary = (
            "Merged three-pass revision report "
            f"(FIXED={status_counts['FIXED']}, PARTIAL={status_counts['PARTIAL']}, "
            f"UNRESOLVED={status_counts['UNRESOLVED']})."
        )
        return {
            "chapter_id": chapter_id,
            "finding_results": merged_rows,
            "summary": summary,
            "pass_summaries": pass_summaries,
        }

    def _aggregate_findings(self, cycle: int) -> dict[str, Any]:
        cpad = self._cpad(cycle)
        chapter_ids = [spec.chapter_id for spec in self.chapter_specs]
        by_chapter: dict[str, list[dict[str, Any]]] = {cid: [] for cid in chapter_ids}
        findings: list[dict[str, Any]] = []
        chapter_review_failures = 0
        chapter_review_skipped = self._is_global_only_final_cycle(cycle)
        cross_chapter_audit_failed = False

        if not chapter_review_skipped:
            for chapter_id in chapter_ids:
                rel = f"reviews/cycle_{cpad}/{chapter_id}.review.json"
                chapter_file = f"snapshots/cycle_{cpad}/chapters/{chapter_id}.md"
                self._materialize_output_alias(
                    base_dir=self.run_dir,
                    required_rel=rel,
                    stage="aggregate_findings",
                    cycle=cycle,
                    chapter_id=chapter_id,
                )
                try:
                    review = self._load_repaired_chapter_review(
                        rel,
                        chapter_id,
                        chapter_file,
                    )
                except PipelineError as exc:
                    if not self._soft_validation_enabled():
                        raise
                    review = self._fallback_chapter_review_payload(
                        cycle=cycle,
                        chapter_id=chapter_id,
                        chapter_file=chapter_file,
                        reason=str(exc),
                    )
                    self._write_json(rel, review)
                    self._record_validation_warning(
                        stage="aggregate_findings",
                        cycle=cycle,
                        chapter_id=chapter_id,
                        artifact=rel,
                        reason=str(exc),
                        action="replaced_invalid_chapter_review_with_fallback",
                    )
                if any(v == "FAIL" for v in review["verdicts"].values()):
                    chapter_review_failures += 1
                for raw in review["findings"]:
                    finding = self._normalize_finding(raw, cycle)
                    findings.append(finding)
                    by_chapter[chapter_id].append(finding)

        full_rel = f"reviews/cycle_{cpad}/full_award.review.json"
        full_novel_file = f"snapshots/cycle_{cpad}/FINAL_NOVEL.md"
        self._materialize_output_alias(
            base_dir=self.run_dir,
            required_rel=full_rel,
            stage="aggregate_findings",
            cycle=cycle,
            chapter_id=None,
        )
        try:
            full_review = self._load_repaired_full_award_review(
                full_rel,
                cycle,
                set(chapter_ids),
                full_novel_file,
            )
            self._validate_full_award_review_json(
                full_review,
                cycle,
                set(chapter_ids),
                full_rel,
                full_novel_file,
            )
        except PipelineError as exc:
            if not self._soft_validation_enabled():
                raise
            preserved_rel = self._preserve_invalid_artifact(full_rel)
            full_review = self._fallback_full_award_review_payload(
                cycle=cycle,
                novel_file=full_novel_file,
                reason=str(exc),
            )
            self._write_json(full_rel, full_review)
            self._record_validation_warning(
                stage="aggregate_findings",
                cycle=cycle,
                chapter_id=None,
                artifact=full_rel,
                reason=(
                    f"{exc}; preserved original at {preserved_rel}"
                    if preserved_rel
                    else str(exc)
                ),
                action="replaced_invalid_full_award_with_fallback",
            )
        for raw in full_review["findings"]:
            raw_source, _normalized_severity = (
                self._normalize_full_award_finding_source_and_severity(
                    str(raw.get("source", "")).strip(),
                    str(raw.get("severity", "")).strip(),
                )
            )
            force_source = "elevation" if raw_source == "elevation" else "award_global"
            finding = self._normalize_finding(raw, cycle, force_source=force_source)
            findings.append(finding)
            by_chapter[finding["chapter_id"]].append(finding)
        for finding in self._expand_full_award_pattern_findings(
            full_review=full_review,
            cycle=cycle,
            chapter_ids=set(chapter_ids),
            rel=full_rel,
            novel_file=full_novel_file,
        ):
            findings.append(finding)
            by_chapter[finding["chapter_id"]].append(finding)

        if not self.cfg.skip_cross_chapter_audit:
            audit_rel = self._cross_chapter_audit_rel(cycle)
            audit_path = self.run_dir / audit_rel
            if not audit_path.is_file():
                if not self._soft_validation_enabled():
                    raise PipelineError(
                        f"missing cross-chapter audit before aggregation: {audit_rel}"
                    )
                cross_chapter_audit_failed = True
                self._record_validation_warning(
                    stage="aggregate_findings",
                    cycle=cycle,
                    chapter_id=None,
                    artifact=audit_rel,
                    reason="cross-chapter audit artifact missing before aggregation",
                    action="cross_chapter_audit_missing_before_aggregation",
                )
            else:
                self._materialize_output_alias(
                    base_dir=self.run_dir,
                    required_rel=audit_rel,
                    stage="aggregate_findings",
                    cycle=cycle,
                    chapter_id=None,
                )
                try:
                    audit_data = self._load_repaired_cross_chapter_audit(
                        audit_rel,
                        cycle,
                        set(chapter_ids),
                        full_novel_file,
                    )
                    self._validate_cross_chapter_audit_json(
                        audit_data,
                        cycle,
                        set(chapter_ids),
                        audit_rel,
                        full_novel_file,
                    )
                except PipelineError as exc:
                    if not self._soft_validation_enabled():
                        raise
                    preserved_rel = self._preserve_invalid_artifact(audit_rel)
                    audit_data = self._fallback_cross_chapter_audit_payload(cycle)
                    cross_chapter_audit_failed = True
                    self._write_json(audit_rel, audit_data)
                    self._record_validation_warning(
                        stage="aggregate_findings",
                        cycle=cycle,
                        chapter_id=None,
                        artifact=audit_rel,
                        reason=(
                            f"{exc}; preserved original at {preserved_rel}"
                            if preserved_rel
                            else str(exc)
                        ),
                        action="replaced_invalid_cross_chapter_audit_with_fallback",
                    )
                if self._is_cross_chapter_audit_fallback_payload(audit_data, cycle):
                    cross_chapter_audit_failed = True
                for raw in audit_data.get("redundancy_findings", []):
                    finding = self._normalize_finding(raw, cycle, force_source="cross_chapter")
                    findings.append(finding)
                    by_chapter[finding["chapter_id"]].append(finding)
                for raw in audit_data.get("consistency_findings", []):
                    finding = self._normalize_finding(raw, cycle, force_source="cross_chapter")
                    findings.append(finding)
                    by_chapter[finding["chapter_id"]].append(finding)

        local_window_available = 0
        local_window_expected = 0
        if self._local_window_stage_enabled() and not self.cfg.skip_local_window_audit:
            windows = self._compute_windows(
                chapter_ids,
                self.cfg.local_window_size,
                self.cfg.local_window_overlap,
            )
            local_window_expected = len(windows)
            for window in windows:
                window_id = self._window_id_for_chapters(window)
                rel = self._local_window_audit_rel(cycle, window_id)
                path = self.run_dir / rel
                if not path.is_file():
                    self._record_validation_warning(
                        stage="aggregate_findings",
                        cycle=cycle,
                        chapter_id=None,
                        artifact=rel,
                        reason="local-window audit artifact missing before aggregation",
                        action="local_window_audit_missing_before_aggregation",
                    )
                    continue
                self._materialize_output_alias(
                    base_dir=self.run_dir,
                    required_rel=rel,
                    stage="aggregate_findings",
                    cycle=cycle,
                    chapter_id=None,
                )
                try:
                    audit_data = self._load_repaired_local_window_audit(
                        rel,
                        cycle,
                        set(chapter_ids),
                        full_novel_file,
                    )
                    self._validate_local_window_window_output(
                        audit_data,
                        rel=rel,
                        window_id=window_id,
                        chapters_reviewed=window,
                    )
                except PipelineError as exc:
                    if self._local_window_stage_required():
                        raise
                    self._record_validation_warning(
                        stage="aggregate_findings",
                        cycle=cycle,
                        chapter_id=None,
                        artifact=rel,
                        reason=str(exc),
                        action="ignored_invalid_local_window_audit_before_aggregation",
                    )
                    continue
                local_window_available += 1
                for raw in audit_data.get("findings", []):
                    finding = self._normalize_finding(raw, cycle, force_source="local_window")
                    findings.append(finding)
                    by_chapter[finding["chapter_id"]].append(finding)
        else:
            local_window_expected = 0
            local_window_available = 0

        for finding in self._build_min_word_findings(cycle):
            findings.append(finding)
            by_chapter[finding["chapter_id"]].append(finding)

        unique_findings = self._dedupe_findings(findings)
        by_chapter = {cid: [] for cid in chapter_ids}
        for finding in unique_findings:
            by_chapter[finding["chapter_id"]].append(finding)
        by_chapter = {cid: rows for cid, rows in by_chapter.items() if rows}

        if chapter_review_failures > 0 and not unique_findings:
            if not self._soft_validation_enabled():
                raise PipelineError(
                    f"cycle={cpad} chapter reviews contain FAIL verdicts but no actionable findings"
                )
            self._record_validation_warning(
                stage="aggregate_findings",
                cycle=cycle,
                chapter_id=None,
                artifact=f"findings/cycle_{cpad}/all_findings.jsonl",
                reason=(
                    "chapter reviews contain FAIL verdicts but no actionable findings; "
                    "injecting fallback finding"
                ),
                action="injected_fallback_actionable_finding",
            )
            fallback = self._normalize_finding(
                {
                    "finding_id": f"fallback_cycle_{cpad}_actionable",
                    "severity": "HIGH",
                    "chapter_id": chapter_ids[0] if chapter_ids else "chapter_01",
                    "evidence": f"snapshots/cycle_{cpad}/FINAL_NOVEL.md:1",
                    "problem": "Fallback actionable finding inserted to keep revision flow live.",
                    "rewrite_direction": (
                        f"Revise snapshots/cycle_{cpad}/FINAL_NOVEL.md:1-200 for contract cleanup."
                    ),
                    "acceptance_test": (
                        f"At least 1 measurable correction is made in snapshots/cycle_{cpad}/FINAL_NOVEL.md:1-200."
                    ),
                },
                cycle,
                force_source="award_global",
            )
            unique_findings.append(fallback)
            by_chapter = {cid: [] for cid in chapter_ids}
            for finding in unique_findings:
                by_chapter[finding["chapter_id"]].append(finding)
            by_chapter = {cid: rows for cid, rows in by_chapter.items() if rows}
        if full_review["verdict"] == "FAIL":
            has_global = any(f["source"] == "award_global" for f in unique_findings)
            if not has_global:
                if not self._soft_validation_enabled():
                    raise PipelineError(
                        f"cycle={cpad} full_award verdict is FAIL but produced no actionable global findings"
                    )
                self._record_validation_warning(
                    stage="aggregate_findings",
                    cycle=cycle,
                    chapter_id=None,
                    artifact=full_rel,
                    reason=(
                        "full_award verdict is FAIL but produced no actionable global findings; "
                        "injecting fallback global finding"
                    ),
                    action="injected_fallback_global_finding",
                )
                fallback = self._normalize_finding(
                    {
                        "finding_id": f"fallback_cycle_{cpad}_global",
                        "severity": "HIGH",
                        "chapter_id": chapter_ids[0] if chapter_ids else "chapter_01",
                        "evidence": f"snapshots/cycle_{cpad}/FINAL_NOVEL.md:1",
                        "problem": "Fallback global finding inserted after invalid FAIL-without-findings output.",
                        "rewrite_direction": (
                            f"Add actionable full-book correction anchored to snapshots/cycle_{cpad}/FINAL_NOVEL.md:1-260."
                        ),
                        "acceptance_test": (
                            f"At least 1 measurable full-book correction is made in snapshots/cycle_{cpad}/FINAL_NOVEL.md:1-260."
                        ),
                    },
                    cycle,
                    force_source="award_global",
                )
                unique_findings.append(fallback)
                by_chapter = {cid: [] for cid in chapter_ids}
                for finding in unique_findings:
                    by_chapter[finding["chapter_id"]].append(finding)
                by_chapter = {cid: rows for cid, rows in by_chapter.items() if rows}

        findings_dir = self.run_dir / "findings" / f"cycle_{cpad}"
        findings_dir.mkdir(parents=True, exist_ok=True)
        all_findings_path = findings_dir / "all_findings.jsonl"
        with all_findings_path.open("w", encoding="utf-8") as f:
            for finding in unique_findings:
                f.write(json.dumps(finding, ensure_ascii=True, sort_keys=True) + "\n")

        summary = {
            "cycle": cycle,
            "total_unresolved_medium_plus": self._count_medium_plus_findings(unique_findings),
            "by_severity": self._count_by_key(unique_findings, "severity"),
            "by_source": self._count_by_key(unique_findings, "source"),
            "chapters_touched": sorted(by_chapter.keys()),
            "chapter_review_failures": chapter_review_failures,
            "chapter_review_skipped": chapter_review_skipped,
            "full_award_verdict": full_review["verdict"],
            "cross_chapter_audit_failed": cross_chapter_audit_failed,
            "local_window_windows_expected": local_window_expected,
            "local_window_windows_available": local_window_available,
        }
        self._write_json(f"findings/cycle_{cpad}/summary.json", summary)
        self._write_text(
            f"findings/cycle_{cpad}/chapter_target_list.txt",
            "\n".join(sorted(by_chapter.keys())) + ("\n" if by_chapter else ""),
        )
        return {
            "summary": summary,
            "all_findings": unique_findings,
            "by_chapter": by_chapter,
            "full_award_verdict": full_review["verdict"],
            "chapter_review_failures": chapter_review_failures,
            "chapter_review_skipped": chapter_review_skipped,
            "cross_chapter_audit_failed": cross_chapter_audit_failed,
        }

    def _build_min_word_findings(self, cycle: int) -> list[dict[str, Any]]:
        cpad = self._cpad(cycle)
        findings: list[dict[str, Any]] = []
        for spec in self.chapter_specs:
            chapter_rel = f"snapshots/cycle_{cpad}/chapters/{spec.chapter_id}.md"
            chapter_path = self.run_dir / chapter_rel
            if not chapter_path.is_file():
                raise PipelineError(f"missing chapter snapshot for min-word check: {chapter_rel}")
            words = self._count_words_file(chapter_path)
            if words >= spec.projected_min_words:
                continue
            raw = {
                "finding_id": f"length_{spec.chapter_id}_min_words",
                "severity": "HIGH",
                "chapter_id": spec.chapter_id,
                "evidence": f"{chapter_rel}:1",
                "problem": (
                    f"Chapter is below projected_min_words ({words} < {spec.projected_min_words})."
                ),
                "rewrite_direction": (
                    "Add causally necessary scene material that strengthens the chapter engine, increases pressure, and lands the planned state shift "
                    "without filler."
                ),
                "acceptance_test": (
                    f"Chapter word count is >= {spec.projected_min_words} while preserving heading contract."
                ),
            }
            findings.append(
                self._normalize_finding(raw, cycle, force_source="length_guardrail")
            )
        return findings

    def _cycle_status_rel(self, cycle: int) -> str:
        return f"status/cycle_{self._cpad(cycle)}/cycle_status.json"

    def _quality_summary_rel(self, cycle: int) -> str:
        return f"status/cycle_{self._cpad(cycle)}/quality_summary.json"

    def _local_window_stage_enabled(self) -> bool:
        return True

    def _local_window_stage_required(self) -> bool:
        return bool(self.cfg.require_local_window_for_revision)

    def _load_existing_cycle_status(self, cycle: int) -> dict[str, Any] | None:
        rel = self._cycle_status_rel(cycle)
        path = self.run_dir / rel
        if not path.is_file():
            return None
        try:
            data = self._read_json(rel)
        except PipelineError as exc:
            self._log(
                f"cycle={self._cpad(cycle)} cycle_status_resume_invalid reason={exc}"
            )
            return None
        if not isinstance(data, dict):
            self._log(
                f"cycle={self._cpad(cycle)} cycle_status_resume_invalid reason=not_object"
            )
            return None
        if data.get("cycle") != cycle:
            self._log(
                f"cycle={self._cpad(cycle)} cycle_status_resume_invalid reason=cycle_mismatch"
            )
            return None
        if not isinstance(data.get("stages"), dict):
            self._log(
                f"cycle={self._cpad(cycle)} cycle_status_resume_invalid reason=missing_stages"
            )
            return None
        return data

    def _resume_cycle_status(
        self, cycle: int, existing_cycle_status: dict[str, Any]
    ) -> dict[str, Any]:
        cycle_status = self._new_cycle_status(cycle)
        existing_stages = existing_cycle_status.get("stages", {})
        if isinstance(existing_stages, dict):
            for stage_key in OBSERVABILITY_STAGE_KEYS:
                if stage_key in self._precycle_stage_entries:
                    cycle_status["stages"][stage_key] = copy.deepcopy(
                        self._precycle_stage_entries[stage_key]
                    )
                    continue
                existing_entry = existing_stages.get(stage_key)
                if not isinstance(existing_entry, dict):
                    continue
                merged_entry = copy.deepcopy(existing_entry)
                merged_entry["required"] = cycle_status["stages"][stage_key]["required"]
                if stage_key == "chapter_review" and self._is_global_only_final_cycle(cycle):
                    merged_entry["status"] = "skipped"
                    merged_entry["reason"] = "final_cycle_global_only"
                    merged_entry["units"] = {}
                elif stage_key == "cross_chapter_audit" and self.cfg.skip_cross_chapter_audit:
                    merged_entry["status"] = "skipped"
                    merged_entry["reason"] = "config_skip_cross_chapter_audit"
                    merged_entry.pop("units", None)
                elif stage_key == "local_window_audit" and (
                    self.cfg.skip_local_window_audit or not self._local_window_stage_enabled()
                ):
                    merged_entry["status"] = "skipped"
                    merged_entry["reason"] = (
                        "config_skip_local_window_audit"
                        if self.cfg.skip_local_window_audit
                        else "stage_not_enabled"
                    )
                    merged_entry["units"] = {}
                cycle_status["stages"][stage_key] = merged_entry
        cycle_status["run_mode"] = "resume"
        if isinstance(existing_cycle_status.get("advisory_gate"), dict):
            cycle_status["advisory_gate"] = copy.deepcopy(
                existing_cycle_status["advisory_gate"]
            )
        cycle_status["resume"] = {
            "source": "cycle_status",
            "status_file": self._cycle_status_rel(cycle),
        }
        return cycle_status

    def _new_cycle_status(self, cycle: int) -> dict[str, Any]:
        stages: dict[str, dict[str, Any]] = {}
        for stage_key in OBSERVABILITY_STAGE_KEYS:
            required = True
            status = "pending"
            reason = None
            if stage_key in self._precycle_stage_entries:
                stages[stage_key] = copy.deepcopy(self._precycle_stage_entries[stage_key])
                continue
            if stage_key == "chapter_review" and self._is_global_only_final_cycle(cycle):
                required = False
                status = "skipped"
                reason = "final_cycle_global_only"
            elif stage_key == "cross_chapter_audit" and self.cfg.skip_cross_chapter_audit:
                required = False
                status = "skipped"
                reason = "config_skip_cross_chapter_audit"
            elif stage_key == "local_window_audit":
                required = self._local_window_stage_required()
                if self.cfg.skip_local_window_audit or not self._local_window_stage_enabled():
                    required = False
                    status = "skipped"
                    reason = (
                        "config_skip_local_window_audit"
                        if self.cfg.skip_local_window_audit
                        else "stage_not_enabled"
                    )
            elif stage_key in {
                "llm_aggregator",
                "materialize_aggregation_decisions",
            }:
                required = False
            entry: dict[str, Any] = {
                "status": status,
                "required": required,
            }
            if stage_key == "local_window_audit":
                entry["units"] = {}
            if reason:
                entry["reason"] = reason
            stages[stage_key] = entry

        return {
            "cycle": cycle,
            "max_cycles": self.cfg.max_cycles,
            "min_cycles": self.cfg.min_cycles,
            "run_mode": "fresh",
            "completion_policy": {
                "terminate_on_quality_pass": False,
                "terminate_on_max_cycles": True,
            },
            "stages": stages,
            "warnings_file": "reports/validation_warnings.json",
            "updated_at_utc": self._utc_now(),
        }

    def _refresh_cycle_resume_metadata(self, cycle_status: dict[str, Any]) -> None:
        stages = cycle_status.get("stages", {})
        reusable_stages: list[str] = []
        earliest_rerun_stage: str | None = None
        for stage_key in OBSERVABILITY_STAGE_KEYS:
            entry = stages.get(stage_key, {})
            status = entry.get("status")
            required = bool(entry.get("required", True))
            if status in {"complete", "reused", "skipped"}:
                reusable_stages.append(stage_key)
                continue
            if earliest_rerun_stage is None and required:
                earliest_rerun_stage = stage_key
        existing_resume = cycle_status.get("resume", {})
        resume: dict[str, Any] = {}
        if isinstance(existing_resume, dict):
            for key in ("source", "status_file"):
                if key in existing_resume:
                    resume[key] = existing_resume[key]
        resume["earliest_rerun_stage"] = earliest_rerun_stage
        resume["reusable_stages"] = reusable_stages
        resume["next_action"] = (
            f"run_{earliest_rerun_stage}"
            if earliest_rerun_stage is not None
            else "cycle_complete"
        )
        cycle_status["resume"] = resume

    def _update_cycle_stage_status(
        self,
        cycle_status: dict[str, Any],
        stage_key: str,
        stage_status: str,
        *,
        reason: str | None = None,
        outputs: list[str] | None = None,
        artifact_glob: str | None = None,
        chapter_count: int | None = None,
        units: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        stages = cycle_status.setdefault("stages", {})
        entry = stages.setdefault(stage_key, {})
        entry["status"] = stage_status
        if reason:
            entry["reason"] = reason
        elif "reason" in entry and stage_status not in {"skipped", "failed"}:
            entry.pop("reason", None)
        if outputs is not None:
            entry["outputs"] = outputs
        elif stage_status == "skipped":
            entry.pop("outputs", None)
        if artifact_glob is not None:
            entry["artifact_glob"] = artifact_glob
        elif stage_status == "skipped":
            entry.pop("artifact_glob", None)
        if chapter_count is not None:
            entry["chapter_count"] = chapter_count
        elif stage_status == "skipped":
            entry.pop("chapter_count", None)
        if units is not None:
            entry["units"] = units
        elif stage_status == "skipped":
            entry.pop("units", None)
        self._refresh_cycle_resume_metadata(cycle_status)
        cycle_status["updated_at_utc"] = self._utc_now()

    def _write_cycle_status(self, cycle: int, cycle_status: dict[str, Any]) -> None:
        payload = copy.deepcopy(cycle_status)
        self._refresh_cycle_resume_metadata(payload)
        payload["updated_at_utc"] = self._utc_now()
        self._write_json(self._cycle_status_rel(cycle), payload)

    def _write_quality_summary(
        self,
        cycle: int,
        aggregate: dict[str, Any],
        advisory_gate: dict[str, Any] | None = None,
        *,
        cycle_status: dict[str, Any] | None = None,
    ) -> None:
        summary = dict(aggregate.get("summary", {}))
        summary["cycle"] = cycle
        summary["advisory_only"] = True
        summary["validation_warning_count"] = len(self.validation_warnings)
        if cycle_status is not None:
            stages = cycle_status.get("stages", {})
            if isinstance(stages, dict):
                local_window_stage = stages.get("local_window_audit")
                if isinstance(local_window_stage, dict):
                    summary["local_window_audit"] = copy.deepcopy(local_window_stage)
        if advisory_gate is not None:
            summary["advisory_gate"] = {
                "decision": advisory_gate.get("decision"),
                "reason": advisory_gate.get("reason"),
                "full_award_verdict": advisory_gate.get("full_award_verdict"),
                "unresolved_medium_plus_count": advisory_gate.get(
                    "unresolved_medium_plus_count"
                ),
            }
        self._write_json(self._quality_summary_rel(cycle), summary)

    def _write_gate(self, cycle: int, aggregate: dict[str, Any]) -> dict[str, Any]:
        cpad = self._cpad(cycle)
        unresolved = self._count_medium_plus_findings(aggregate["all_findings"])
        full_award_verdict = aggregate["full_award_verdict"]
        chapter_review_failures = aggregate["chapter_review_failures"]
        cross_chapter_audit_failed = bool(
            aggregate.get("cross_chapter_audit_failed", False)
        )
        if (
            unresolved == 0
            and full_award_verdict == "PASS"
            and chapter_review_failures == 0
            and not cross_chapter_audit_failed
            and cycle >= self.cfg.min_cycles
        ):
            decision = "PASS"
            reason = "all_unresolved_medium_plus_closed_and_full_award_pass"
        elif (
            unresolved == 0
            and full_award_verdict == "PASS"
            and chapter_review_failures == 0
            and not cross_chapter_audit_failed
            and cycle < self.cfg.min_cycles
        ):
            decision = "FAIL"
            reason = "min_cycles_not_reached_but_current_quality_passes"
        elif (
            unresolved == 0
            and full_award_verdict == "PASS"
            and chapter_review_failures == 0
            and cross_chapter_audit_failed
        ):
            decision = "FAIL"
            reason = "cross_chapter_audit_failed"
        else:
            decision = "FAIL"
            reason = "unresolved_medium_plus_or_review_failures_or_full_award_fail"

        gate = {
            "cycle": cycle,
            "full_award_verdict": full_award_verdict,
            "unresolved_medium_plus_count": unresolved,
            "chapter_review_failures": chapter_review_failures,
            "cross_chapter_audit_failed": cross_chapter_audit_failed,
            "decision": decision,
            "reason": reason,
        }
        self._write_json(f"gate/cycle_{cpad}/gate.json", gate)
        return gate

    def _assemble_snapshot(self, cycle: int) -> bool:
        cpad = self._cpad(cycle)
        snapshot_outputs = [
            self.run_dir / "snapshots" / f"cycle_{cpad}" / "FINAL_NOVEL.md",
            self.run_dir / "snapshots" / f"cycle_{cpad}" / "FINAL_NOVEL.pre_review.md",
            self.run_dir / "snapshots" / f"cycle_{cpad}" / "snapshot_manifest.json",
        ]
        snapshot_outputs.extend(
            self.run_dir
            / "snapshots"
            / f"cycle_{cpad}"
            / "chapters"
            / f"{spec.chapter_id}.md"
            for spec in self.chapter_specs
        )
        live_inputs = [
            self.run_dir / "chapters" / f"{spec.chapter_id}.md"
            for spec in self.chapter_specs
        ]
        if snapshot_outputs and self._artifacts_fresh_against_inputs(
            snapshot_outputs, live_inputs
        ):
            self._log(f"cycle={cpad} snapshot_resume_present")
            return True
        snapshot_chapters_dir = self.run_dir / "snapshots" / f"cycle_{cpad}" / "chapters"
        snapshot_chapters_dir.mkdir(parents=True, exist_ok=True)

        for spec in self.chapter_specs:
            src = self.run_dir / "chapters" / f"{spec.chapter_id}.md"
            dst = snapshot_chapters_dir / f"{spec.chapter_id}.md"
            shutil.copy2(src, dst)

        final_novel = self.run_dir / "snapshots" / f"cycle_{cpad}" / "FINAL_NOVEL.md"
        self._write_compiled_novel(final_novel, snapshot_chapters_dir)

        # Explicitly named pre-review artifact for human/runtime clarity.
        pre_review_novel = (
            self.run_dir / "snapshots" / f"cycle_{cpad}" / "FINAL_NOVEL.pre_review.md"
        )
        self._write_compiled_novel(pre_review_novel, snapshot_chapters_dir)

        chapter_hashes = {}
        for spec in self.chapter_specs:
            chapter_file = snapshot_chapters_dir / f"{spec.chapter_id}.md"
            chapter_hashes[spec.chapter_id] = self._sha256_file(chapter_file)
        manifest = {
            "cycle": cycle,
            "final_novel_sha256": self._sha256_file(final_novel),
            "chapter_sha256": chapter_hashes,
        }
        self._write_json(f"snapshots/cycle_{cpad}/snapshot_manifest.json", manifest)
        return False

    def _assemble_post_revision_snapshot(self, cycle: int) -> bool:
        cpad = self._cpad(cycle)
        snapshot_outputs = [
            self.run_dir / "snapshots" / f"cycle_{cpad}" / "FINAL_NOVEL.post_revision.md",
            self.run_dir / "snapshots" / f"cycle_{cpad}" / "snapshot_manifest.post_revision.json",
            self.run_dir / "FINAL_NOVEL.md",
        ]
        snapshot_outputs.extend(
            self.run_dir
            / "snapshots"
            / f"cycle_{cpad}"
            / "post_revision"
            / "chapters"
            / f"{spec.chapter_id}.md"
            for spec in self.chapter_specs
        )
        live_inputs = [
            self.run_dir / "chapters" / f"{spec.chapter_id}.md"
            for spec in self.chapter_specs
        ]
        if snapshot_outputs and self._artifacts_fresh_against_inputs(
            snapshot_outputs, live_inputs
        ):
            self._log(f"cycle={cpad} post_revision_snapshot_resume_present")
            return True
        post_dir = self.run_dir / "snapshots" / f"cycle_{cpad}" / "post_revision" / "chapters"
        post_dir.mkdir(parents=True, exist_ok=True)

        for spec in self.chapter_specs:
            src = self.run_dir / "chapters" / f"{spec.chapter_id}.md"
            dst = post_dir / f"{spec.chapter_id}.md"
            shutil.copy2(src, dst)

        post_novel = (
            self.run_dir / "snapshots" / f"cycle_{cpad}" / "FINAL_NOVEL.post_revision.md"
        )
        self._write_compiled_novel(post_novel, post_dir)
        shutil.copy2(post_novel, self.run_dir / "FINAL_NOVEL.md")

        chapter_hashes = {}
        for spec in self.chapter_specs:
            chapter_file = post_dir / f"{spec.chapter_id}.md"
            chapter_hashes[spec.chapter_id] = self._sha256_file(chapter_file)
        manifest = {
            "cycle": cycle,
            "phase": "post_revision",
            "final_novel_sha256": self._sha256_file(post_novel),
            "chapter_sha256": chapter_hashes,
        }
        self._write_json(f"snapshots/cycle_{cpad}/snapshot_manifest.post_revision.json", manifest)
        return False

    def _run_continuity_reconciliation(self, cycle: int) -> dict[str, Any]:
        cpad = self._cpad(cycle)
        full_novel_file = (
            f"snapshots/cycle_{cpad}/FINAL_NOVEL.post_revision.md"
        )
        full_novel_path = self.run_dir / full_novel_file
        if not full_novel_path.is_file():
            self._log(
                f"cycle={cpad} continuity_reconciliation_skip reason=no_post_revision_snapshot"
            )
            return {
                "status": "skipped",
                "reason": "no_post_revision_snapshot",
            }

        continuity_sheet_file = "outline/continuity_sheet.json"
        spatial_layout_file = self._spatial_layout_rel()
        conflict_log_file = f"reviews/cycle_{cpad}/continuity_conflicts.json"
        global_context_file = f"context/cycle_{cpad}/global_cycle_context.json"

        continuity_sheet_path = self.run_dir / continuity_sheet_file
        conflict_log_path = self.run_dir / conflict_log_file
        base_inputs = [
            full_novel_path,
            self.run_dir / global_context_file,
            self.run_dir / spatial_layout_file,
            self.run_dir / "config" / "constitution.md",
            self.run_dir / "config" / "prompts" / "continuity_sheet_prompt.md",
        ]
        if continuity_sheet_path.is_file() and conflict_log_path.is_file():
            continuity_fresh = self._artifact_fresh_against_inputs(
                continuity_sheet_path,
                base_inputs,
            )
            conflict_fresh = self._artifact_fresh_against_inputs(
                conflict_log_path,
                base_inputs,
            )
            if continuity_fresh and conflict_fresh:
                self._log(f"cycle={cpad} continuity_reconciliation_resume_present")
                return {"status": "reused"}
            self._log(
                f"cycle={cpad} continuity_reconciliation_resume_stale reason=input_newer_than_reconciliation"
            )
        elif conflict_log_path.is_file():
            self._log(
                f"cycle={cpad} continuity_reconciliation_resume_stale reason=missing_continuity_sheet"
            )

        prompt = self._render_prompt(
            "continuity_sheet_prompt.md",
            {
                "CYCLE_PADDED": cpad,
                "FULL_NOVEL_FILE": full_novel_file,
                "GLOBAL_CYCLE_CONTEXT_FILE": global_context_file,
                "SPATIAL_LAYOUT_FILE": spatial_layout_file,
                "CONTINUITY_SHEET_OUTPUT_FILE": continuity_sheet_file,
                "CONFLICT_LOG_OUTPUT_FILE": conflict_log_file,
            },
        )
        job = self._make_job(
            job_id=f"cycle_{cpad}_continuity_reconciliation",
            stage="continuity_reconciliation",
            stage_group="revision",
            cycle=cycle,
            chapter_id=None,
            allowed_inputs=[
                full_novel_file,
                continuity_sheet_file,
                global_context_file,
                spatial_layout_file,
                "config/constitution.md",
                "config/prompts/continuity_sheet_prompt.md",
            ],
            required_outputs=[
                continuity_sheet_file,
                conflict_log_file,
            ],
            prompt_text=prompt,
        )
        try:
            self._run_job(job)
        except PipelineError as exc:
            if not self._soft_validation_enabled():
                raise
            self._record_validation_warning(
                stage="continuity_reconciliation",
                cycle=cycle,
                chapter_id=None,
                artifact=conflict_log_file,
                reason=str(exc),
                action="continuity_reconciliation_failed_soft",
            )
            return {
                "status": "failed",
                "reason": "job_failed_soft",
            }
        try:
            self._validate_continuity_sheet()
        except PipelineError as exc:
            if not self._soft_validation_enabled():
                raise
            self._record_validation_warning(
                stage="continuity_reconciliation",
                cycle=cycle,
                chapter_id=None,
                artifact=continuity_sheet_file,
                reason=str(exc),
                action="continuity_sheet_post_reconciliation_validation_warning",
            )
        try:
            conflict_data = self._read_json(conflict_log_file)
            num_conflicts = len(conflict_data.get("conflicts", []))
            new_facts = conflict_data.get("new_facts_added", 0)
            updated_facts = conflict_data.get("facts_updated", 0)
        except PipelineError:
            num_conflicts = -1
            new_facts = -1
            updated_facts = -1
        self._log(
            f"cycle={cpad} continuity_reconciliation_complete "
            f"conflicts={num_conflicts} new_facts={new_facts} updated={updated_facts}"
        )
        return {"status": "complete"}

    def _validate_continuity_sheet(self) -> None:
        rel = "outline/continuity_sheet.json"
        data = self._read_json(rel)
        required_keys = [
            "characters",
            "timeline",
            "geography",
            "world_rules",
            "power_structure",
            "objects",
            "financial_state",
            "knowledge_state",
            "environmental_constants",
        ]
        missing = [k for k in required_keys if k not in data]
        if missing:
            raise PipelineError(
                f"{rel} missing required keys: {', '.join(missing)}"
            )
        expected_arrays = [
            "characters", "world_rules", "power_structure",
            "objects", "knowledge_state", "environmental_constants",
        ]
        for key in expected_arrays:
            if not isinstance(data[key], list):
                raise PipelineError(f"{rel} '{key}' must be an array")
        expected_objects = ["timeline", "geography", "financial_state"]
        for key in expected_objects:
            if not isinstance(data[key], dict):
                raise PipelineError(f"{rel} '{key}' must be an object")
        for char in data["characters"]:
            if not isinstance(char, dict):
                raise PipelineError(f"{rel} each character entry must be an object")
            if not char.get("character_id"):
                raise PipelineError(f"{rel} character entry missing 'character_id'")

    def _outline_continuity_snapshot_rel(self) -> str:
        return "outline/continuity_sheet.outline.json"

    def _cycle_continuity_snapshot_rel(self, cycle: int) -> str:
        return f"context/cycle_{self._cpad(cycle)}/continuity_sheet.json"

    def _outline_review_rel(self, cycle_num: int) -> str:
        return f"outline/outline_review_cycle_{self._cpad(cycle_num)}.json"

    def _outline_revision_record_rel(self, cycle_num: int) -> str:
        return f"outline/outline_revision_cycle_{self._cpad(cycle_num)}.json"

    def _spatial_layout_rel(self) -> str:
        return "outline/spatial_layout.json"

    def _chapter_line_index_rel(self, cycle: int) -> str:
        return f"context/cycle_{self._cpad(cycle)}/chapter_line_index.json"

    def _window_id_for_index(self, index: int) -> str:
        return f"window_{index:02d}"

    def _local_window_audit_rel(self, cycle: int, window_id: str) -> str:
        suffix = window_id
        if suffix.startswith("window_"):
            suffix = suffix.removeprefix("window_")
        return f"reviews/cycle_{self._cpad(cycle)}/local_window_{suffix}.json"

    def _ensure_outline_continuity_snapshot(self) -> None:
        live_path = self.run_dir / "outline" / "continuity_sheet.json"
        if not live_path.is_file():
            raise PipelineError("outline continuity sheet missing before snapshot creation")
        snapshot_rel = self._outline_continuity_snapshot_rel()
        snapshot_path = self.run_dir / snapshot_rel
        existing_cycle_artifacts = any(
            (self.run_dir / "status").glob("cycle_*/cycle_status.json")
        ) or any((self.run_dir / "gate").glob("cycle_*/gate.json"))
        if snapshot_path.is_file() and existing_cycle_artifacts:
            return
        self._write_text(snapshot_rel, live_path.read_text(encoding="utf-8"))

    def _ensure_cycle_continuity_snapshot(self, cycle: int) -> str:
        live_path = self.run_dir / "outline" / "continuity_sheet.json"
        if not live_path.is_file():
            raise PipelineError("outline continuity sheet missing before cycle snapshot creation")
        snapshot_rel = self._cycle_continuity_snapshot_rel(cycle)
        snapshot_path = self.run_dir / snapshot_rel
        if not snapshot_path.is_file():
            self._write_text(snapshot_rel, live_path.read_text(encoding="utf-8"))
        return snapshot_rel

    def _load_title(self) -> str:
        title_path = self.run_dir / "outline" / "title.txt"
        if not title_path.is_file():
            self._log("title_file_missing defaulting_to=Untitled")
            return "Untitled"
        raw = title_path.read_text(encoding="utf-8").strip()
        if not raw:
            self._log("title_file_empty defaulting_to=Untitled")
            return "Untitled"
        title = raw.splitlines()[0].strip()
        self._log(f"title_loaded title={title!r}")
        return title

    def _outline_core_output_rels(self) -> list[str]:
        return [
            "outline/outline.md",
            "outline/chapter_specs.jsonl",
            "outline/scene_plan.tsv",
            "outline/style_bible.json",
            "outline/continuity_sheet.json",
            "outline/title.txt",
        ]

    def _outline_core_output_paths(self) -> list[Path]:
        return [self.run_dir / rel for rel in self._outline_core_output_rels()]

    def _outline_review_input_paths(self) -> list[Path]:
        return [
            self.run_dir / "input" / "premise.txt",
            *self._outline_core_output_paths(),
            self.run_dir / "config" / "constitution.md",
            self.run_dir / "config" / "prompts" / "outline_review_prompt.md",
        ]

    def _outline_pre_revision_snapshot_rels(self, cycle_num: int) -> list[str]:
        prefix = f"outline/pre_revision/cycle_{self._cpad(cycle_num)}"
        return [f"{prefix}/{Path(rel).name}" for rel in self._outline_core_output_rels()]

    def _ensure_outline_pre_revision_snapshot(self, cycle_num: int) -> list[str]:
        snapshot_rels = self._outline_pre_revision_snapshot_rels(cycle_num)
        for source_rel, snapshot_rel in zip(
            self._outline_core_output_rels(),
            snapshot_rels,
            strict=True,
        ):
            source_path = self.run_dir / source_rel
            if not source_path.is_file():
                raise PipelineError(
                    f"cannot snapshot pre-revision outline; missing {source_rel}"
                )
            snapshot_path = self.run_dir / snapshot_rel
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            if snapshot_path.is_file():
                continue
            shutil.copy2(source_path, snapshot_path)
        return snapshot_rels

    def _outline_revision_record_payload(self, cycle_num: int, review_rel: str) -> dict[str, Any]:
        snapshot_rels = self._outline_pre_revision_snapshot_rels(cycle_num)
        return {
            "cycle": cycle_num,
            "review_file": review_rel,
            "outline_outputs": self._outline_core_output_rels(),
            "outline_output_hashes": {
                rel: self._sha256_file(self.run_dir / rel)
                for rel in self._outline_core_output_rels()
            },
            "pre_revision_outline_outputs": snapshot_rels,
            "pre_revision_outline_output_hashes": {
                rel: self._sha256_file(self.run_dir / rel)
                for rel in snapshot_rels
                if (self.run_dir / rel).is_file()
            },
            "updated_at_utc": self._utc_now(),
        }

    def _validate_outline_revision_record(
        self, data: dict[str, Any], cycle_num: int, rel: str
    ) -> None:
        if data.get("cycle") != cycle_num:
            raise PipelineError(f"{rel} cycle must equal {cycle_num}")
        review_file = self._optional_text(data.get("review_file"))
        if review_file != self._outline_review_rel(cycle_num):
            raise PipelineError(
                f"{rel} review_file must equal {self._outline_review_rel(cycle_num)}"
            )
        outputs = data.get("outline_outputs")
        if outputs != self._outline_core_output_rels():
            raise PipelineError(f"{rel} outline_outputs mismatch")
        hashes = data.get("outline_output_hashes")
        if not isinstance(hashes, dict):
            raise PipelineError(f"{rel} outline_output_hashes must be an object")
        for output_rel in self._outline_core_output_rels():
            expected_hash = self._optional_text(hashes.get(output_rel))
            if len(expected_hash) != 64:
                raise PipelineError(
                    f"{rel} outline_output_hashes missing valid hash for {output_rel}"
                )

    def _outline_revision_record_matches_current_outputs(self, data: dict[str, Any]) -> bool:
        hashes = data.get("outline_output_hashes")
        if not isinstance(hashes, dict):
            return False
        for output_rel in self._outline_core_output_rels():
            output_path = self.run_dir / output_rel
            if not output_path.is_file():
                return False
            if self._optional_text(hashes.get(output_rel)) != self._sha256_file(output_path):
                return False
        return True

    def _load_current_outline_state(self, *, refresh_snapshots: bool = True) -> None:
        self.chapter_specs = self._load_and_validate_chapter_specs()
        self._validate_scene_plan()
        self.style_bible = self._load_and_validate_style_bible()
        self._validate_continuity_sheet()
        self.novel_title = self._load_title()
        if refresh_snapshots:
            self._ensure_outline_continuity_snapshot()

    def _sync_continuity_sheet_spatial_reference(self) -> None:
        rel = "outline/continuity_sheet.json"
        data = self._read_json(rel)
        geography = data.get("geography")
        if not isinstance(geography, dict):
            raise PipelineError(f"{rel} 'geography' must be an object")
        if geography.get("spatial_layout_ref") == self._spatial_layout_rel():
            return
        geography["spatial_layout_ref"] = self._spatial_layout_rel()
        self._write_json(rel, data)

    def _write_compiled_novel(
        self, output_path: Path, chapters_dir: Path
    ) -> None:
        title = self.novel_title or "Untitled"
        parts = [f"# {title}\n\n"]
        for idx, spec in enumerate(self.chapter_specs):
            chapter_file = chapters_dir / f"{spec.chapter_id}.md"
            content = chapter_file.read_text(encoding="utf-8")
            parts.append(content.strip() + "\n")
            if idx != len(self.chapter_specs) - 1:
                parts.append("\n\n")
        rendered = "".join(parts)
        if output_path.is_file() and output_path.read_text(encoding="utf-8") == rendered:
            return
        output_path.write_text(rendered, encoding="utf-8")

    def _compute_windows(
        self, chapter_ids: list[str], window_size: int, overlap: int
    ) -> list[list[str]]:
        if window_size < 2:
            raise PipelineError("local window size must be >= 2")
        if overlap < 0:
            raise PipelineError("local window overlap must be >= 0")
        if overlap >= window_size:
            raise PipelineError("local window overlap must be smaller than window size")
        if len(chapter_ids) <= window_size:
            return [list(chapter_ids)] if len(chapter_ids) >= 2 else []
        step = window_size - overlap
        windows: list[list[str]] = []
        start = 0
        while start < len(chapter_ids):
            window = chapter_ids[start : start + window_size]
            if len(window) >= 2:
                windows.append(window)
            if start + window_size >= len(chapter_ids):
                break
            start += step
        return windows

    def _build_chapter_line_index(
        self, compiled_novel_path: Path
    ) -> dict[str, dict[str, int]]:
        if not compiled_novel_path.is_file():
            raise PipelineError(f"compiled novel missing for line index: {compiled_novel_path}")
        lines = compiled_novel_path.read_text(encoding="utf-8").splitlines()
        starts: dict[str, int] = {}
        spec_index = 0
        for line_number, line in enumerate(lines, start=1):
            if spec_index >= len(self.chapter_specs):
                break
            expected_heading = f"# Chapter {self.chapter_specs[spec_index].chapter_number}"
            if line.strip() != expected_heading:
                continue
            starts[self.chapter_specs[spec_index].chapter_id] = line_number
            spec_index += 1
        if len(starts) != len(self.chapter_specs):
            missing = [
                spec.chapter_id
                for spec in self.chapter_specs
                if spec.chapter_id not in starts
            ]
            raise PipelineError(
                "compiled novel missing expected chapter headings for line index: "
                + ", ".join(missing)
            )
        index: dict[str, dict[str, int]] = {}
        for idx, spec in enumerate(self.chapter_specs):
            start_line = starts[spec.chapter_id]
            if idx + 1 < len(self.chapter_specs):
                next_start = starts[self.chapter_specs[idx + 1].chapter_id]
                end_line = next_start - 1
            else:
                end_line = len(lines)
            index[spec.chapter_id] = {
                "start_line": start_line,
                "end_line": max(start_line, end_line),
            }
        return index

    def _build_static_story_context(self) -> None:
        style_bible = self.style_bible or self._load_and_validate_style_bible()
        chapter_spine = [
            {
                "chapter_id": spec.chapter_id,
                "chapter_number": spec.chapter_number,
                "chapter_engine": spec.chapter_engine,
                "pressure_source": spec.pressure_source,
                "state_shift": spec.state_shift,
                "texture_mode": spec.texture_mode,
                "scene_count_target": spec.scene_count_target,
                "objective": spec.objective,
                "conflict": spec.conflict,
                "consequence": spec.consequence,
                "must_land_beats": spec.must_land_beats,
                "secondary_character_beats": spec.secondary_character_beats,
                "setups_to_plant": spec.setups_to_plant,
                "payoffs_to_land": spec.payoffs_to_land,
            }
            for spec in self.chapter_specs
        ]
        character_ids = [
            str(row.get("character_id", "")).strip()
            for row in style_bible.get("character_voice_profiles", [])
            if str(row.get("character_id", "")).strip()
        ]
        payload = {
            "premise": self.selected_premise,
            "chapter_count": len(self.chapter_specs),
            "chapter_spine": chapter_spine,
            "character_ids": sorted(set(character_ids)),
            "dialogue_rules": style_bible.get("dialogue_rules", {}),
            "prose_style_profile": style_bible.get("prose_style_profile", {}),
            "aesthetic_risk_policy": style_bible.get("aesthetic_risk_policy", {}),
        }
        self._write_json("outline/static_story_context.json", payload)

    def _build_cycle_context_packs(self, cycle: int) -> bool:
        cpad = self._cpad(cycle)
        cycle_context_dir = self.run_dir / "context" / f"cycle_{cpad}"
        boundary_dir = cycle_context_dir / "boundary"
        boundary_dir.mkdir(parents=True, exist_ok=True)
        continuity_snapshot_rel = self._ensure_cycle_continuity_snapshot(cycle)
        context_outputs = [
            self.run_dir / f"context/cycle_{cpad}/global_cycle_context.json",
            self.run_dir / self._chapter_line_index_rel(cycle),
        ]
        context_outputs.extend(
            self.run_dir / f"context/cycle_{cpad}/boundary/{spec.chapter_id}.boundary.json"
            for spec in self.chapter_specs
        )
        context_inputs = [
            self.run_dir / "input" / "premise.txt",
            self.run_dir / "outline" / "chapter_specs.jsonl",
            self.run_dir / "outline" / "scene_plan.tsv",
            self.run_dir / "outline" / "style_bible.json",
            self.run_dir / continuity_snapshot_rel,
        ]
        context_inputs.extend(
            self.run_dir
            / "snapshots"
            / f"cycle_{cpad}"
            / "chapters"
            / f"{spec.chapter_id}.md"
            for spec in self.chapter_specs
        )
        context_inputs.append(self.run_dir / "snapshots" / f"cycle_{cpad}" / "FINAL_NOVEL.md")
        if context_outputs and self._artifacts_fresh_against_inputs(
            context_outputs, context_inputs
        ):
            self._log(f"cycle={cpad} cycle_context_resume_present")
            return True

        style_bible = self.style_bible or self._load_and_validate_style_bible()
        scene_counts = self._scene_counts_by_chapter()
        chapter_spine = []
        for spec in self.chapter_specs:
            chapter_spine.append(
                {
                    "chapter_id": spec.chapter_id,
                    "chapter_number": spec.chapter_number,
                    "chapter_engine": spec.chapter_engine,
                    "pressure_source": spec.pressure_source,
                    "state_shift": spec.state_shift,
                    "texture_mode": spec.texture_mode,
                    "scene_count_target": spec.scene_count_target,
                    "objective": spec.objective,
                    "conflict": spec.conflict,
                    "consequence": spec.consequence,
                    "must_land_beats": spec.must_land_beats,
                    "secondary_character_beats": spec.secondary_character_beats,
                    "setups_to_plant": spec.setups_to_plant,
                    "payoffs_to_land": spec.payoffs_to_land,
                    "planned_scene_count": scene_counts.get(spec.chapter_id, 0),
                }
            )

        character_state_table = []
        for row in style_bible.get("character_voice_profiles", []):
            character_state_table.append(
                {
                    "character_id": str(row.get("character_id", "")).strip(),
                    "public_register": row.get("public_register", ""),
                    "private_register": row.get("private_register", ""),
                    "stress_tells": row.get("stress_tells", ""),
                    "interruption_habit": row.get("interruption_habit", ""),
                    "self_correction_tendency": row.get(
                        "self_correction_tendency", ""
                    ),
                    "indirectness": row.get("indirectness", ""),
                    "repetition_tolerance": row.get("repetition_tolerance", ""),
                    "evasion_style": row.get("evasion_style", ""),
                    "sentence_completion_style": row.get(
                        "sentence_completion_style", ""
                    ),
                }
            )

        global_context = {
            "cycle": cycle,
            "premise": self.selected_premise,
            "theme_spine": "Maintain narrative consequence and causal storytelling over tidy resolution.",
            "chapter_spine": chapter_spine,
            "character_state_table": character_state_table,
            "dialogue_rules": style_bible.get("dialogue_rules", {}),
            "prose_style_profile": style_bible.get("prose_style_profile", {}),
            "aesthetic_risk_policy": style_bible.get("aesthetic_risk_policy", {}),
        }
        self._write_json(f"context/cycle_{cpad}/global_cycle_context.json", global_context)
        chapter_line_index = self._build_chapter_line_index(
            self.run_dir / "snapshots" / f"cycle_{cpad}" / "FINAL_NOVEL.md"
        )
        self._write_json(self._chapter_line_index_rel(cycle), chapter_line_index)

        chapters_dir = self.run_dir / "snapshots" / f"cycle_{cpad}" / "chapters"
        chapter_ids = [spec.chapter_id for spec in self.chapter_specs]
        for idx, chapter_id in enumerate(chapter_ids):
            prev_id = chapter_ids[idx - 1] if idx > 0 else None
            next_id = chapter_ids[idx + 1] if idx < len(chapter_ids) - 1 else None

            prev_tail_excerpt = ""
            next_head_excerpt = ""
            if prev_id:
                prev_path = chapters_dir / f"{prev_id}.md"
                prev_tail_excerpt = self._tail_excerpt(prev_path, max_lines=30, max_chars=1600)
            if next_id:
                next_path = chapters_dir / f"{next_id}.md"
                next_head_excerpt = self._head_excerpt(next_path, max_lines=30, max_chars=1600)

            spec = self.chapter_specs[idx]
            payload = {
                "chapter_id": chapter_id,
                "prev_chapter_id": prev_id,
                "next_chapter_id": next_id,
                "prev_tail_excerpt": prev_tail_excerpt,
                "next_head_excerpt": next_head_excerpt,
                "open_hooks_to_carry": spec.must_land_beats,
                "secondary_character_beats": spec.secondary_character_beats,
                "setups_to_plant": spec.setups_to_plant,
                "payoffs_to_land": spec.payoffs_to_land,
                "state_deltas_required": [
                    spec.pressure_source,
                    spec.state_shift,
                ],
            }
            rel = f"context/cycle_{cpad}/boundary/{chapter_id}.boundary.json"
            self._write_json(rel, payload)
        return False

    def _scene_counts_by_chapter(self) -> dict[str, int]:
        path = self.run_dir / "outline" / "scene_plan.tsv"
        if not path.is_file():
            return {}
        lines = path.read_text(encoding="utf-8").splitlines()
        counts: dict[str, int] = {}
        for line in lines[1:]:
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            chapter_id = parts[1].strip()
            if not chapter_id:
                continue
            counts[chapter_id] = counts.get(chapter_id, 0) + 1
        return counts

    def _run_jobs_parallel(
        self, jobs: list[JobSpec], max_workers: int, label: str
    ) -> None:
        if not jobs:
            return

        failures: list[str] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(self._run_job, job): job for job in jobs}
            for future in concurrent.futures.as_completed(future_map):
                job = future_map[future]
                try:
                    future.result()
                except Exception as exc:
                    failures.append(f"{job.job_id}: {exc}")

        if failures:
            joined = "\n".join(failures[:8])
            raise PipelineError(f"{label} phase had job failures:\n{joined}")

    def _run_job(self, job: JobSpec) -> None:
        manifest = {
            "job_id": job.job_id,
            "stage": job.stage,
            "stage_group": job.stage_group,
            "cycle": job.cycle,
            "chapter_id": job.chapter_id,
            "provider": job.provider,
            "agent_bin": job.agent_bin,
            "model": job.model,
            "reasoning_effort": job.reasoning_effort,
            "allowed_inputs": job.allowed_inputs,
            "required_outputs": job.required_outputs,
            "prompt_sha256": hashlib.sha256(job.prompt_text.encode("utf-8")).hexdigest(),
            "timeout_seconds": job.timeout_seconds,
            "idle_timeout_seconds": self._job_idle_timeout_seconds(job),
            "dry_run": self.cfg.dry_run,
        }
        self._write_json(f"manifests/{job.job_id}.json", manifest)
        max_retries = JOB_EXEC_RETRY_MAX if not self.cfg.dry_run else 0
        attempt = 0
        while True:
            attempt += 1
            workspace = Path(
                tempfile.mkdtemp(
                    prefix=f"{job.job_id}_attempt_{attempt}_",
                    dir=self.run_dir / "workspaces",
                )
            )
            try:
                before_hashes = self._copy_inputs_to_workspace(job.allowed_inputs, workspace)

                if self.cfg.dry_run:
                    self._mock_job_outputs(job, workspace)
                else:
                    self._execute_agent_job(job, workspace)

                self._validate_job_workspace(job, workspace, before_hashes)
                self._copy_outputs_from_workspace(job, workspace)
                return
            except ProviderQuotaPause as exc:
                reset_utc = datetime.fromtimestamp(
                    exc.reset_at_epoch, timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ")
                self._log(
                    f"job_quota_pause job={job.job_id} stage={job.stage} "
                    f"provider={exc.provider} rate_limit_type={exc.rate_limit_type or 'unknown'} "
                    f"reset_at_utc={reset_utc} sleep_s={exc.sleep_seconds} "
                    f"reason={exc.result_text}"
                )
                if exc.sleep_seconds > 0:
                    time.sleep(exc.sleep_seconds)
                continue
            except PipelineError as exc:
                if attempt > max_retries or not self._is_retryable_job_error(exc):
                    raise
                sleep_s = self._retry_backoff_seconds(attempt)
                self._log(
                    f"job_retry job={job.job_id} stage={job.stage} "
                    f"attempt={attempt}/{max_retries} sleep_s={sleep_s} reason={exc}"
                )
                if sleep_s > 0:
                    time.sleep(sleep_s)
            finally:
                shutil.rmtree(workspace, ignore_errors=True)

    def _execute_agent_job(self, job: JobSpec, workspace: Path) -> None:
        if job.provider == "codex":
            self._execute_codex_job(job, workspace)
            return
        if job.provider == "claude":
            self._execute_claude_job(job, workspace)
            return
        raise PipelineError(f"unsupported provider: {job.provider}")

    def _build_codex_exec_cmd(self, job: JobSpec, workspace: Path, message_file: Path) -> list[str]:
        cmd = [
            job.agent_bin,
            "exec",
            "--full-auto",
            "--sandbox",
            "workspace-write",
            "--skip-git-repo-check",
            "-C",
            str(workspace),
            "--json",
            "-o",
            str(message_file),
        ]
        if job.model:
            cmd.extend(["-m", job.model])
        if job.reasoning_effort:
            cmd.extend(["-c", f"model_reasoning_effort=\"{job.reasoning_effort}\""])
        return cmd

    def _build_claude_exec_cmd(self, job: JobSpec) -> list[str]:
        cmd = [
            job.agent_bin,
            "-p",
            "--output-format",
            "stream-json",
            "--verbose",
            "--no-session-persistence",
            "--dangerously-skip-permissions",
        ]
        if job.model:
            cmd.extend(["--model", job.model])
        if job.reasoning_effort:
            cmd.extend(["--effort", job.reasoning_effort])
        return cmd

    def _run_agent_process(
        self,
        *,
        job: JobSpec,
        workspace: Path,
        cmd: list[str],
        provider_label: str,
        cwd: Path | None = None,
    ) -> tuple[int, Path, Path]:
        log_file = self.run_dir / "logs" / "jobs" / f"{job.job_id}.jsonl"
        stderr_file = self.run_dir / "logs" / "jobs" / f"{job.job_id}.stderr.txt"

        idle_limit = self._job_idle_timeout_seconds(job)
        wall_limit = job.timeout_seconds

        with log_file.open("w", encoding="utf-8") as out, stderr_file.open(
            "w", encoding="utf-8"
        ) as err:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=out,
                stderr=err,
                text=True,
                cwd=str(cwd) if cwd is not None else None,
            )
            # Send prompt on stdin and close to signal EOF.
            try:
                if proc.stdin is not None:
                    proc.stdin.write(job.prompt_text)
                    proc.stdin.close()
            except BrokenPipeError:
                pass  # process may have exited early; we'll catch via returncode

            # --- idle-watchdog polling loop ---
            poll_interval = 10  # seconds between checks
            last_jsonl_size = 0
            idle_elapsed = 0.0
            wall_elapsed = 0.0
            idle_killed = False

            while proc.poll() is None:
                time.sleep(poll_interval)
                wall_elapsed += poll_interval

                # Check wall-clock timeout
                if wall_elapsed >= wall_limit:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                    raise PipelineError(
                        f"job timed out after {wall_limit}s (wall clock)"
                    )

                # Check JSONL activity
                if idle_limit > 0:
                    try:
                        current_size = log_file.stat().st_size
                    except OSError:
                        current_size = 0

                    if current_size > last_jsonl_size:
                        # Activity detected — reset idle timer
                        last_jsonl_size = current_size
                        idle_elapsed = 0.0
                    else:
                        idle_elapsed += poll_interval

                    if idle_elapsed >= idle_limit:
                        self._log(
                            f"job_idle_timeout job={job.job_id} "
                            f"idle_seconds={idle_elapsed:.0f} "
                            f"jsonl_bytes={current_size}"
                        )
                        idle_killed = True
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait()
                        break

        returncode = proc.returncode
        if idle_killed:
            raise PipelineError(
                f"{provider_label} exec stalled (no JSONL output for {idle_limit}s, "
                f"killed after {wall_elapsed:.0f}s wall time)"
            )
        return returncode, log_file, stderr_file

    def _execute_codex_job(self, job: JobSpec, workspace: Path) -> None:
        message_file = self.run_dir / "logs" / "jobs" / f"{job.job_id}.last_message.txt"
        cmd = self._build_codex_exec_cmd(job, workspace, message_file)
        returncode, _log_file, stderr_file = self._run_agent_process(
            job=job,
            workspace=workspace,
            cmd=cmd,
            provider_label="codex",
        )
        if returncode != 0:
            stderr_tail = self._tail_file(stderr_file, max_lines=20)
            raise PipelineError(
                f"codex exec failed rc={returncode} stderr_tail={stderr_tail}"
            )

    def _load_provider_events(self, log_file: Path) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for raw_line in log_file.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                events.append(row)
        return events

    def _extract_claude_result_event(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        for event in reversed(events):
            if event.get("type") == "result":
                return event
        raise PipelineError("claude exec log missing final result event")

    def _extract_claude_last_message_text(self, events: list[dict[str, Any]]) -> str:
        result_event = self._extract_claude_result_event(events)
        result_text = str(result_event.get("result", "")).strip()
        if result_text:
            return result_text
        fragments: list[str] = []
        for event in events:
            if event.get("type") != "assistant":
                continue
            message = event.get("message")
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "text":
                    text = str(item.get("text", "")).strip()
                    if text:
                        fragments.append(text)
        if fragments:
            return "\n".join(fragments).strip()
        raise PipelineError("claude exec log missing assistant text content")

    def _extract_claude_usage(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        result_event = self._extract_claude_result_event(events)
        usage = result_event.get("usage")
        if isinstance(usage, dict):
            return usage
        return {}

    def _extract_claude_rejected_rate_limit_info(
        self, events: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        for event in reversed(events):
            if event.get("type") != "rate_limit_event":
                continue
            info = event.get("rate_limit_info")
            if not isinstance(info, dict):
                continue
            if str(info.get("status", "")).strip().lower() == "rejected":
                return info
        return None

    def _claude_quota_pause_from_events(
        self, events: list[dict[str, Any]], result_text: str
    ) -> ProviderQuotaPause | None:
        info = self._extract_claude_rejected_rate_limit_info(events)
        if info is None:
            return None
        raw_reset = info.get("resetsAt")
        try:
            reset_at_epoch = int(raw_reset)
        except (TypeError, ValueError):
            return None
        now_epoch = int(time.time())
        base_sleep = max(0, reset_at_epoch - now_epoch)
        buffer_s = max(0, CLAUDE_QUOTA_RESET_BUFFER_SECONDS)
        jitter_cap = max(0, CLAUDE_QUOTA_RESET_JITTER_SECONDS)
        jitter_s = random.randint(0, jitter_cap) if jitter_cap > 0 else 0
        sleep_seconds = base_sleep + buffer_s + jitter_s
        return ProviderQuotaPause(
            provider="claude",
            result_text=result_text or "You've hit your limit",
            reset_at_epoch=reset_at_epoch,
            sleep_seconds=sleep_seconds,
            rate_limit_type=str(info.get("rateLimitType", "")).strip() or None,
        )

    def _execute_claude_job(self, job: JobSpec, workspace: Path) -> None:
        message_file = self.run_dir / "logs" / "jobs" / f"{job.job_id}.last_message.txt"
        cmd = self._build_claude_exec_cmd(job)
        returncode, log_file, stderr_file = self._run_agent_process(
            job=job,
            workspace=workspace,
            cmd=cmd,
            provider_label="claude",
            cwd=workspace,
        )
        events = self._load_provider_events(log_file)
        try:
            result_event = self._extract_claude_result_event(events)
            last_message = self._extract_claude_last_message_text(events)
        except PipelineError as exc:
            stderr_tail = self._tail_file(stderr_file, max_lines=20)
            raise PipelineError(
                f"claude exec failed rc={returncode} stderr_tail={stderr_tail} parse_error={exc}"
            ) from exc
        message_file.write_text(last_message + "\n", encoding="utf-8")
        if returncode != 0 or bool(result_event.get("is_error")):
            stderr_tail = self._tail_file(stderr_file, max_lines=20)
            result_text = str(result_event.get("result", "")).strip()
            quota_pause = self._claude_quota_pause_from_events(events, result_text)
            if quota_pause is not None:
                raise quota_pause
            raise PipelineError(
                f"claude exec failed rc={returncode} result={result_text or '<empty>'} stderr_tail={stderr_tail}"
            )

    def _job_idle_timeout_seconds(self, job: JobSpec) -> int:
        idle_limit = self.cfg.job_idle_timeout_seconds
        if job.stage == "full_award_review":
            return max(idle_limit, FULL_BOOK_REVIEW_IDLE_TIMEOUT_SECONDS)
        return idle_limit

    def _copy_inputs_to_workspace(
        self, allowed_inputs: list[str], workspace: Path
    ) -> dict[str, str]:
        before_hashes: dict[str, str] = {}
        for rel in allowed_inputs:
            self._assert_rel_path(rel)
            src = self.run_dir / rel
            if not src.is_file():
                raise PipelineError(f"missing required input file for job: {rel}")
            dst = workspace / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            before_hashes[rel] = self._sha256_file(dst)
        return before_hashes

    def _copy_outputs_from_workspace(self, job: JobSpec, workspace: Path) -> None:
        for rel in job.required_outputs:
            self._assert_rel_path(rel)
            src = workspace / rel
            if not src.is_file():
                self._materialize_output_alias(
                    base_dir=workspace,
                    required_rel=rel,
                    stage=job.stage,
                    cycle=job.cycle if job.cycle > 0 else None,
                    chapter_id=job.chapter_id,
                )
                src = workspace / rel
            if not src.is_file():
                raise PipelineError(f"job did not produce required output: {rel}")
            dst = self.run_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    def _validate_job_workspace(
        self, job: JobSpec, workspace: Path, before_hashes: dict[str, str]
    ) -> None:
        for rel in job.required_outputs:
            if not (workspace / rel).is_file():
                self._materialize_output_alias(
                    base_dir=workspace,
                    required_rel=rel,
                    stage=job.stage,
                    cycle=job.cycle if job.cycle > 0 else None,
                    chapter_id=job.chapter_id,
                )
            if not (workspace / rel).is_file():
                raise PipelineError(f"required output missing in workspace: {rel}")

        files_in_workspace = self._list_workspace_files(workspace)
        allowed = set(job.allowed_inputs) | set(job.required_outputs)
        undeclared_files = sorted(
            rel
            for rel in (files_in_workspace - allowed)
            if not self._is_allowed_aux_workspace_file(rel)
        )
        if undeclared_files:
            preview = ", ".join(undeclared_files[:10])
            if not self._soft_validation_enabled():
                raise PipelineError(f"undeclared files written by job: {preview}")
            self._record_validation_warning(
                stage=job.stage,
                cycle=job.cycle if job.cycle > 0 else None,
                chapter_id=job.chapter_id,
                artifact="workspace",
                reason=f"undeclared files written by job: {preview}",
                action="ignored_undeclared_workspace_files",
            )

        for rel, before_hash in before_hashes.items():
            fpath = workspace / rel
            if rel in job.required_outputs:
                continue
            if not fpath.exists():
                raise PipelineError(f"input file unexpectedly removed by job: {rel}")
            after_hash = self._sha256_file(fpath)
            if after_hash != before_hash:
                raise PipelineError(
                    f"input file mutated without declaration in required_outputs: {rel}"
                )

    def _mock_job_outputs(self, job: JobSpec, workspace: Path) -> None:
        if job.stage == "premise_candidates":
            self._mock_premise_candidates_output(job, workspace)
            return
        if job.stage == "premise_uniqueness_clustering":
            self._mock_premise_uniqueness_clustering_output(workspace)
            return
        if job.stage == "outline":
            self._mock_outline_outputs(workspace)
            return
        if job.stage == "outline_review":
            self._mock_outline_review_output(job, workspace)
            return
        if job.stage == "outline_revision":
            self._mock_outline_revision_output(job, workspace)
            return
        if job.stage == "spatial_layout":
            self._mock_spatial_layout_output(workspace)
            return
        if job.stage == "chapter_draft":
            self._mock_chapter_draft_output(job, workspace)
            return
        if job.stage == "chapter_expand":
            self._mock_chapter_expand_output(job, workspace)
            return
        if job.stage == "chapter_review":
            self._mock_chapter_review_output(job, workspace)
            return
        if job.stage == "full_award_review":
            self._mock_full_award_output(job, workspace)
            return
        if job.stage == "cross_chapter_audit":
            self._mock_cross_chapter_audit_output(job, workspace)
            return
        if job.stage == "local_window_audit":
            self._mock_local_window_audit_output(job, workspace)
            return
        if job.stage == "llm_aggregator":
            self._mock_revision_aggregator_output(job, workspace)
            return
        if job.stage == "chapter_revision":
            self._mock_chapter_revision_output(job, workspace)
            return
        if job.stage == "continuity_reconciliation":
            self._mock_continuity_reconciliation_output(job, workspace)
            return
        raise PipelineError(f"unsupported mock stage: {job.stage}")

    def _mock_premise_candidates_output(self, job: JobSpec, workspace: Path) -> None:
        batch_plan_rel = next(
            (
                rel
                for rel in job.allowed_inputs
                if rel.endswith(".search_plan.json") and "premise/batches/" in rel
            ),
            "premise/premise_search_plan.json",
        )
        search_plan = json.loads((workspace / batch_plan_rel).read_text(encoding="utf-8"))
        rows: list[dict[str, Any]] = []
        seen_premises: dict[str, int] = {}
        repetition_warning = str(
            search_plan.get("prior_batch_repetition_warning", "")
        ).strip()
        for idx, row in enumerate(search_plan.get("candidates", []), start=1):
            candidate_id = str(row.get("candidate_id", "")).strip()
            active_axes = row.get("active_axes", [])
            risk_axes = row.get("risk_overlay", {})
            active_names = [
                str(item.get("axis", "")).strip()
                for item in active_axes
                if isinstance(item, dict) and str(item.get("axis", "")).strip()
            ]
            risk_names = [
                name
                for name, value in risk_axes.items()
                if float(value) >= 0.66
            ]
            seed_key = "|".join(
                [
                    str(search_plan.get("derived_seed", "")),
                    candidate_id,
                    row.get("kind", ""),
                    ",".join(active_names[:4]),
                    ",".join(sorted(risk_names)[:3]),
                ]
            )
            seed_value = int(hashlib.sha256(seed_key.encode("utf-8")).hexdigest()[:16], 16)
            rng = random.Random(seed_value)
            premise, engine_guess, protagonist_descriptor, pressure_descriptor, setting_descriptor = (
                self._mock_premise_candidate_from_profile(
                    rng=rng,
                    scaffold_profile=row.get("scaffold_profile", {}),
                    active_names=active_names,
                    risk_names=risk_names,
                    ordinal=idx,
                    repetition_warning=repetition_warning,
                )
            )
            base_premise = premise
            duplicate_count = seen_premises.get(base_premise, 0)
            if duplicate_count > 0:
                duplicate_tails = [
                    "The town starts testing whether the lie can be inherited.",
                    "A rival claimant realizes the story can be turned into leverage.",
                    "What looked private becomes the one scandal the whole place needs.",
                ]
                premise = premise.rstrip()
                tail = duplicate_tails[(duplicate_count - 1) % len(duplicate_tails)]
                if premise.endswith(tail):
                    premise = premise[: -len(tail)].rstrip()
                premise = premise + " " + tail
            seen_premises[base_premise] = duplicate_count + 1
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "premise": premise,
                    "engine_guess": engine_guess,
                    "protagonist_descriptor": protagonist_descriptor,
                    "pressure_descriptor": pressure_descriptor,
                    "setting_descriptor": setting_descriptor,
                    "why_it_might_work": (
                        "The premise opens multiple scene registers and has enough pressure to sustain a long novel."
                    ),
                    "risk": (
                        "The premise will fail if the execution collapses its strangeness or tonal range into a single register."
                    ),
                }
            )
        output_rel = next(
            (
                rel
                for rel in job.required_outputs
                if rel.endswith(".candidates.jsonl") and "premise/batches/" in rel
            ),
            "premise/premise_candidates.jsonl",
        )
        self._write_jsonl(workspace / output_rel, rows)

    def _mock_premise_candidate_from_profile(
        self,
        *,
        rng: random.Random,
        scaffold_profile: dict[str, Any],
        active_names: list[str],
        risk_names: list[str],
        ordinal: int,
        repetition_warning: str,
    ) -> tuple[str, str, str, str, str]:
        scene_name, social_name, motion_name, mode_names = self._extract_scaffold_profile_names(
            scaffold_profile
        )
        scene_gloss = {
            "household": ("boardinghouse keeper", "an overcrowded lodging house"),
            "work": ("repair-yard cutter", "a cash-starved workshop district"),
            "journey": ("route guide", "a ferry chain that keeps changing its stops"),
            "ritual": ("shrine attendant", "a pilgrimage town built around seasonal vows"),
            "performance": ("pageant prompter", "a city that runs on staged displays"),
            "market": ("stall broker", "a bargaining quarter where favors set prices"),
            "service": ("private attendant", "a household economy of debt and care"),
            "maintenance": ("signal mechanic", "a failing infrastructure corridor"),
            "gathering": ("festival marshal", "a town that keeps convening under pressure"),
            "enclosure": ("tenant steward", "a tightly ruled compound"),
            "pursuit": ("tracker for hire", "a landscape full of trails and disappearances"),
            "exchange": ("smuggling go-between", "a port of hidden transfers"),
        }
        relation_gloss = {
            "dyad": "the one person who understands the arrangement best is also the one who can ruin it",
            "triangle": "two different loyalties start demanding incompatible versions of the same truth",
            "family_cluster": "each relative turns the same pressure into a different claim on the future",
            "ensemble": "too many bystanders realize they can use the scheme for their own needs",
            "rivals": "a competitor begins copying the trick with better timing",
            "strangers_forced_together": "the people trapped alongside the protagonist discover they need opposite outcomes",
            "mentor_apprentice": "the person teaching the work has been training a successor into a lie",
            "caretaker_dependent": "need itself becomes a weapon between the person giving care and the person taking it",
            "community_field": "the whole neighborhood begins reorganizing itself around the pressure",
            "hierarchy": "those above and below the protagonist demand opposite forms of obedience",
            "factional_pressure": "several camps each decide the protagonist already belongs to them",
            "succession_pressure": "everyone starts gambling on who will be replaced next",
        }
        motion_gloss = {
            "countdown": "before the season closes for good",
            "return": "when something long gone returns with new terms",
            "recurrence": "as the same charged event keeps repeating with worse consequences",
            "migration": "while the route keeps moving and taking people with it",
            "accumulation": "as small bargains pile up into a public crisis",
            "corruption": "while the arrangement rots from a useful secret into open damage",
            "replacement": "when the substitute starts becoming harder to remove than the original",
            "concealment": "while everyone protects the wrong fact from the wrong person",
            "escalation": "until private leverage becomes collective danger",
            "diffusion": "as consequences leak outward into people who were never meant to know",
            "inheritance": "after an old debt passes to the wrong heir",
            "unraveling": "when the story holding the place together begins to come apart",
        }
        mode_tail_gloss = {
            "comic": "What begins as a workable arrangement turns embarrassing fast once the wrong audience learns how it functions.",
            "tragic": "The thing meant as protection starts demanding sacrifices that cannot stay private.",
            "satiric": "Every institution that touches the situation discovers a new excuse to make it worse.",
            "mythic": "Local explanation and impossible explanation keep changing places until nobody can stand outside the story anymore.",
            "speculative": "The mechanism behind the pressure keeps proving stranger and more socially useful than anyone admitted.",
            "devotional": "Piety, appetite, and fear start using the same language for opposite ends.",
            "sensual": "Desire keeps changing who can remain professional and who gets named as compromised.",
            "grotesque": "Bodies, objects, and status all begin showing the damage more openly than the town can tolerate.",
            "austere": "The more carefully people speak around the problem, the more visible the cost becomes.",
        }
        scene_role, setting = scene_gloss.get(
            scene_name,
            ("local fixer", "a place under quiet pressure"),
        )
        if "science_technology_pressure" in active_names:
            setting = rng.choice(
                [
                    "a prototype district nobody can afford to shut down",
                    "a failing systems corridor where repair has become politics",
                    "an improvised technical frontier full of borrowed machinery",
                ]
            )
        elif "fantasy_mythic_pressure" in active_names or "spiritual_metaphysical_pressure" in active_names:
            setting = rng.choice(
                [
                    "a vow-soaked town where ritual and appetite share the same streets",
                    "a shrine economy living off miracles nobody can fully verify",
                    "a valley where superstition and local governance have fused",
                ]
            )
        elif "ecological_biome_specificity" in active_names:
            setting = rng.choice(
                [
                    "an estuary settlement learning the weather has preferences",
                    "a storm-eaten coast where labor and survival use the same tools",
                    "a river plain whose seasons keep rewriting daily life",
                ]
            )
        elif "historical_embeddedness" in active_names:
            setting = rng.choice(
                [
                    "a town still governed by inherited arrangements nobody fully believes in",
                    "a decaying regional capital where old obligations outlive the people who made them",
                    "a trade settlement thick with unfinished debts and public memory",
                ]
            )

        documentary_pressure = (
            "formal recognition, inheritance, and who gets believed"
            if any(
                axis in active_names
                for axis in ("documentality_legibility", "institutional_density")
            )
            else ""
        )
        if documentary_pressure and any(
            token in repetition_warning.lower()
            for token in (
                "record",
                "paperwork",
                "administrative",
                "verification",
                "gatekeeping",
                "archive",
                "audit",
            )
        ):
            documentary_pressure = "status, legitimacy, and the names people can live under"

        pressure_pool = []
        axis_pressure_bits = {
            "secrecy_deception": "a lie that keeps looking more useful than the truth",
            "obsession_compulsion": "a private fixation nobody else can afford",
            "romantic_centrality": "desire crossing into leverage",
            "family_entanglement": "kinship treated like property",
            "communal_entanglement": "a neighborhood appetite for other people's business",
            "class_economic_pressure": "debts, status hunger, and unequal bargains",
            "public_civic_scale": "shared consequence that refuses to stay private",
            "psychological_interiority": "self-deception that starts shaping reality around it",
            "external_event_pressure": "an approaching disruption nobody can delay",
            "ontological_instability": "reality slipping just enough to become negotiable",
            "mobility_migration": "the risk of being moved, rerouted, or left behind",
            "science_technology_pressure": "a tool or process proving more socially dangerous than advertised",
            "spiritual_metaphysical_pressure": "belief hardening into a material claim on daily life",
            "fantasy_mythic_pressure": "old explanation suddenly behaving like law",
            "ecological_biome_specificity": "weather and terrain acting like interested parties",
        }
        for axis in active_names:
            bit = axis_pressure_bits.get(axis)
            if bit and bit not in pressure_pool:
                pressure_pool.append(bit)
        if documentary_pressure:
            pressure_pool.append(documentary_pressure)
        if not pressure_pool:
            pressure_pool.append("private leverage turning public")
        pressure_bits = pressure_pool[:2]
        relation = relation_gloss.get(
            social_name,
            "the people around the protagonist want mutually incompatible outcomes",
        )
        motion = motion_gloss.get(
            motion_name,
            "as the cost of the arrangement keeps spreading",
        )
        mood_sentence = ""
        if mode_names:
            for mode_name in mode_names:
                tail = mode_tail_gloss.get(mode_name)
                if tail:
                    mood_sentence = tail
                    break
        if not mood_sentence and "violence_proximity" in risk_names:
            mood_sentence = "The first unmistakable injury tied to the arrangement makes retreat impossible."
        elif not mood_sentence and (
            "erotic_charge" in active_names or "bodily_explicitness" in risk_names
        ):
            mood_sentence = "Desire keeps changing who can still pretend the arrangement is practical."
        elif not mood_sentence and "messiness_anti_sanitization" in risk_names:
            mood_sentence = "Every attempt to clean the situation up leaves fresher stains in public view."

        premise = (
            f"A {scene_role} in {setting} discovers that {pressure_bits[0]}, "
            f"and {relation} {motion}."
        )
        if len(pressure_bits) > 1:
            premise = premise.rstrip(".") + f", with {pressure_bits[1]} tightening the cost."
        premise = premise.rstrip()
        if not premise.endswith((".", "!", "?")):
            premise += "."
        if mood_sentence:
            premise += " " + mood_sentence

        protagonist_descriptor = {
            "household": "domestic negotiator under economic strain",
            "work": "skilled worker whose labor exposes private leverage",
            "journey": "route-dependent operator caught between passengers and destination",
            "ritual": "ritual worker pulled between faith and appetite",
            "performance": "staged public figure losing control of the script",
            "market": "bargaining specialist trapped by unequal exchange",
            "service": "caretaking worker whose intimacy becomes politically costly",
            "maintenance": "repair worker keeping a failing system alive",
            "gathering": "local organizer exposed by crowd logic",
            "enclosure": "bounded-place insider navigating pressure and rank",
            "pursuit": "searching protagonist who cannot stay outside the chase",
            "exchange": "go-between whose hidden transfers stop staying hidden",
        }.get(scene_name, "protagonist under layered social pressure")
        setting_descriptor = setting
        pressure_descriptor = "; ".join(pressure_bits)
        mode_label_text = ", ".join(mode_names[:2]) if mode_names else "mixed-mode"
        engine_guess = (
            f"{scene_name or 'mixed'}-{motion_name or 'drift'} engine with "
            f"{mode_label_text} pressure [dry-run profile {ordinal:02d}]"
        )
        return premise, engine_guess, protagonist_descriptor, pressure_descriptor, setting_descriptor

    def _mock_premise_uniqueness_clustering_output(self, workspace: Path) -> None:
        search_plan = json.loads(
            (workspace / "premise" / "premise_search_plan.json").read_text(encoding="utf-8")
        )
        candidates = self._read_workspace_jsonl(workspace / "premise" / "premise_candidates.jsonl")
        clusters: list[dict[str, Any]] = []
        plan_candidates = {
            str(row.get("candidate_id", "")).strip(): row
            for row in search_plan.get("candidates", [])
            if isinstance(row, dict) and str(row.get("candidate_id", "")).strip()
        }
        by_scaffold: dict[tuple[str, str, str], list[str]] = {}
        for row in candidates:
            candidate_id = str(row.get("candidate_id", "")).strip()
            plan_row = plan_candidates.get(candidate_id, {})
            scene, social, motion, _modes = self._extract_scaffold_profile_names(
                plan_row.get("scaffold_profile", {})
            )
            key = (
                scene or f"scene_{candidate_id}",
                social or f"social_{candidate_id}",
                motion or f"motion_{candidate_id}",
            )
            by_scaffold.setdefault(key, []).append(candidate_id)
        cluster_index = 1
        for key, member_ids in sorted(by_scaffold.items()):
            normalized_members = sorted(member_ids)
            chunk_size = 2 if len(normalized_members) > 1 else 1
            for start in range(0, len(normalized_members), chunk_size):
                chunk = normalized_members[start : start + chunk_size]
                scene, social, motion = key
                clusters.append(
                    {
                        "cluster_id": f"cluster_{cluster_index:02d}",
                        "member_ids": chunk,
                        "similarity_summary": (
                            "These premises share a deeper scaffold pattern in scene source, social geometry, and narrative motion."
                        ),
                        "shared_engine_shape": f"{scene.replace('_', ' ')} + {motion.replace('_', ' ')}",
                        "shared_pressure_shape": social.replace("_", " "),
                        "shared_world_shape": scene.replace("_", " "),
                    }
                )
                cluster_index += 1
        data = {
            "seed": search_plan.get("seed"),
            "reroll_index": search_plan.get("reroll_index", 0),
            "clusters": clusters,
            "unique_cluster_count": len(clusters),
            "field_is_sufficiently_unique": len(clusters)
            >= int(search_plan.get("min_unique_clusters", 1)),
            "insufficient_uniqueness_reason": (
                ""
                if len(clusters) >= int(search_plan.get("min_unique_clusters", 1))
                else "Dry-run candidate field collapsed into too few distinct premise families."
            ),
        }
        self._write_workspace_json(workspace, "premise/uniqueness_clusters.json", data)

    def _mock_outline_outputs(self, workspace: Path) -> None:
        chapter_count = min(max(self.cfg.dry_run_chapter_count, 16), 20)
        outline = textwrap.dedent(
            f"""\
            # Outline

            Premise:
            {self.selected_premise}

            Chapter count: {chapter_count}
            """
        )
        self._write_workspace_text(workspace, "outline/outline.md", outline)

        rows = []
        for i in range(1, chapter_count + 1):
            chapter_id = f"chapter_{i:02d}"
            scene_count_target = 1 if i % 5 == 0 else 2
            row = {
                "chapter_id": chapter_id,
                "chapter_number": i,
                "projected_min_words": 2300,
                "chapter_engine": (
                    f"aftermath and inventory in {chapter_id}"
                    if scene_count_target == 1
                    else f"pressure confrontation in {chapter_id}"
                ),
                "pressure_source": f"Pressure escalates in {chapter_id}",
                "state_shift": f"A decision closes options in {chapter_id}",
                "texture_mode": "quiet aftermath" if scene_count_target == 1 else "hot pressure",
                "scene_count_target": scene_count_target,
                "objective": (
                    f"aftermath and inventory in {chapter_id}"
                    if scene_count_target == 1
                    else f"pressure confrontation in {chapter_id}"
                ),
                "conflict": f"Pressure escalates in {chapter_id}",
                "consequence": f"A decision closes options in {chapter_id}",
                "must_land_beats": [
                    f"Beat A for {chapter_id}",
                    f"Beat B for {chapter_id}",
                ],
            }
            rows.append(row)
        chapter_specs_text = "\n".join(json.dumps(r, ensure_ascii=True) for r in rows) + "\n"
        self._write_workspace_text(
            workspace, "outline/chapter_specs.jsonl", chapter_specs_text
        )

        scene_plan_lines = [
            "scene_id\tchapter_id\tscene_order\tobjective\topposition\tturn\tconsequence_cost\ttension_peak"
        ]
        for i in range(1, chapter_count + 1):
            chapter_id = f"chapter_{i:02d}"
            if i % 5 == 0:
                scene_plan_lines.append(
                    f"scene_{i:02d}_a\t{chapter_id}\t1\tHold pressure in place\tMemory, bureaucracy, or aftermath\tPerception shifts\tA path narrows\tYES"
                )
            else:
                scene_plan_lines.append(
                    f"scene_{i:02d}_a\t{chapter_id}\t1\tSet pressure\tCountermove\tComplication\tLoss\tNO"
                )
                scene_plan_lines.append(
                    f"scene_{i:02d}_b\t{chapter_id}\t2\tEscalate pressure\tHard opposition\tDecision\tIrreversible shift\tYES"
                )
        self._write_workspace_text(
            workspace, "outline/scene_plan.tsv", "\n".join(scene_plan_lines) + "\n"
        )

        style_bible = {
            "character_voice_profiles": [
                {
                    "character_id": "protagonist",
                    "public_register": "controlled, sparse, strategic",
                    "private_register": "raw, self-accusing, volatile",
                    "syntax_signature": "short clauses under stress, longer masking sentences under scrutiny",
                    "lexical_signature": "Uses concise operational language in public, then shifts to concrete moral vocabulary under pressure; avoid repeated keyword motifs.",
                    "forbidden_generic_lines": "Avoid platitudes, stock reassurances, and generic cinematic filler.",
                    "stress_tells": "Under stress, cadence shortens and self-corrections increase; vary manifestations instead of repeating a single tell.",
                    "profanity_profile": "high under threat, low in formal hearings",
                    "contraction_level": "high",
                    "interruption_habit": "Cuts in when leverage is slipping; interruptions should feel tactical or panicked rather than decorative.",
                    "self_correction_tendency": "Corrects course mid-sentence when concealing emotion or recalibrating risk; vary the form of those repairs.",
                    "indirectness": "Public speech stays guarded and angled; private speech becomes blunt only after resistance fails.",
                    "repetition_tolerance": "Allows light repetition under pressure, but never mantra-like reuse of the same phrase.",
                    "evasion_style": "Deflects by returning to logistics, procedure, or concrete task language instead of answering head-on.",
                    "sentence_completion_style": "Can trail off or restart under pressure, but unfinished turns should remain legible and character-specific."
                },
                {
                    "character_id": "antagonist",
                    "public_register": "bureaucratic precision with moral certainty",
                    "private_register": "coldly intimate and coercive",
                    "syntax_signature": "balanced clauses; clipped corrections when challenged",
                    "lexical_signature": "Prefers institutional framing and liability language; maintain variance and avoid mantra repetition.",
                    "forbidden_generic_lines": "Avoid vague evasion and generic reassurance formulas.",
                    "stress_tells": "Pressure appears as increased procedural precision and controlling redirects, expressed with variation.",
                    "profanity_profile": "rare but surgical",
                    "contraction_level": "low",
                    "interruption_habit": "Interrupts to restore control or correct framing, not to bluster.",
                    "self_correction_tendency": "Rarely self-corrects; when it happens, the correction should read as strategic recalibration.",
                    "indirectness": "Prefers direct institutional framing in public and cooler insinuation in private.",
                    "repetition_tolerance": "Low tolerance for repeated wording; pressure should sharpen rather than loop.",
                    "evasion_style": "Redirects through reframing, technicalities, or narrowed definitions rather than obvious dodge lines.",
                    "sentence_completion_style": "Usually finishes sentences cleanly; any break in completion should signal loss of control or deliberate intimidation."
                }
            ],
            "dialogue_rules": {
                "anti_transcript_cadence": True,
                "required_leverage_shifts_per_scene": 1,
                "max_consecutive_low_info_replies": 2,
                "idiolect_separation_required": True,
                "default_contraction_use": (
                    "high — contractions are the norm; uncontracted forms reserved "
                    "for emphasis or character-specific formality"
                )
            },
            "prose_style_profile": {
                "narrative_tense": "past tense",
                "narrative_distance": "close-third with pressure-tight interiority",
                "rhythm_target": "mixed sentence lengths; rhythm responsive to scene intensity",
                "sensory_bias": ["touch", "sound", "spatial pressure"],
                "diction": "concrete, unsanitized, low-abstraction",
                "forbidden_drift_patterns": [
                    "bureaucratic briefing blocks",
                    "generic cinematic phrasing"
                ],
                "chapter_texture_variance": (
                    "Alternate high-intensity scenes with reflective interiority; vary scene count, "
                    "dialogue density, and pacing so no two consecutive chapters feel "
                    "structurally identical."
                )
            },
            "aesthetic_risk_policy": {
                "sanitization_disallowed": True,
                "dark_content_allowed_when_character_true": True,
                "profanity_allowed_when_scene_pressure_warrants": True,
                "euphemism_penalty": "high",
                "creative_risk_policy": "Push toward uncomfortable specificity. Render difficult material with full presence. A draft that risks too much is easier to refine than one that risks nothing."
            }
        }
        self._write_workspace_json(workspace, "outline/style_bible.json", style_bible)

        continuity_sheet = {
            "characters": [
                {
                    "character_id": "protagonist",
                    "age_at_story_start": 35,
                    "physical_details": "average build",
                    "key_relationships": {"antagonist": "adversary"},
                    "occupation_status": "employed",
                    "aliases": ["protagonist"],
                    "literacy_languages": "fluent in English",
                    "state_transitions": [],
                    "availability": "present throughout",
                }
            ],
            "timeline": {
                "story_start": "present day",
                "estimated_span": "several months",
                "seasonal_track": [],
                "key_events": [],
            },
            "geography": {
                "primary_setting": "urban",
                "key_locations": [],
                "distances": [],
            },
            "world_rules": [],
            "power_structure": [],
            "objects": [],
            "financial_state": {"debts": [], "income_sources": []},
            "knowledge_state": [],
            "environmental_constants": [],
        }
        self._write_workspace_json(
            workspace, "outline/continuity_sheet.json", continuity_sheet
        )

        self._write_workspace_text(workspace, "outline/title.txt", "Untitled Novel\n")

    def _mock_outline_review_output(self, job: JobSpec, workspace: Path) -> None:
        output = next(
            (p for p in job.required_outputs if p.startswith("outline/outline_review_cycle_")),
            None,
        )
        if not output:
            raise PipelineError("mock outline review missing output")
        cycle_match = re.search(r"cycle_(\d+)", output)
        cycle_num = int(cycle_match.group(1)) if cycle_match else 1
        payload = {
            "cycle": cycle_num,
            "premise_criteria": [
                {
                    "criterion": "Exploit the premise's specific pressure instead of falling back to generic genre scaffolding.",
                    "met": False,
                    "evidence": "The middle stretch relies on bridge chapters rather than premise-specific turns.",
                    "suggestion": "Force one irreversible choice in the middle third that only this premise can produce.",
                },
                {
                    "criterion": "Give the ending a conceptual or emotional aftershock beyond plot closure.",
                    "met": True,
                    "evidence": "The late chapters already aim at a public/private reframe rather than simple resolution.",
                    "suggestion": "Keep sharpening the final chapter's recontextualizing pressure.",
                },
            ],
            "structural_findings": [
                {
                    "finding_id": f"OR-{cycle_num:03d}",
                    "severity": "HIGH",
                    "check": "midpoint_turn",
                    "chapters_affected": ["chapter_08", "chapter_09"],
                    "problem": "The middle currently bridges pressure rather than changing the story's direction.",
                    "rewrite_direction": "Move a genuine reversal or revelation into chapter 8 so chapter 9 must absorb fallout instead of repeating setup work.",
                }
            ],
            "elevation_suggestions": [
                {
                    "suggestion": "Let one supporting character make a structurally disruptive choice that complicates the protagonist's engine rather than servicing it.",
                    "chapters_affected": ["chapter_06", "chapter_11"],
                }
            ],
            "summary": "Dry-run outline review found a soft middle and recommended a stronger midpoint turn.",
        }
        self._write_workspace_json(workspace, output, payload)

    def _mock_outline_revision_output(self, job: JobSpec, workspace: Path) -> None:
        outline_file = workspace / "outline" / "outline.md"
        if outline_file.is_file():
            current = outline_file.read_text(encoding="utf-8").rstrip()
            if "[Dry-run outline revision applied]" not in current:
                current += "\n\n[Dry-run outline revision applied]\n"
                self._write_workspace_text(workspace, "outline/outline.md", current)

    def _mock_spatial_layout_output(self, workspace: Path) -> None:
        payload = {
            "summary": "Dry-run spatial layout generated a confined-setting map to anchor movement and adjacency.",
            "micro": {
                "setting_name": "Municipal Annex",
                "structure_type": "three-story civic building",
                "locations": [
                    {
                        "name": "records office",
                        "floor": 1,
                        "adjacent_to": ["public hallway", "copy room"],
                        "access": "public during office hours",
                        "notable": "fluorescent lights and overflowing archive carts",
                    },
                    {
                        "name": "roof landing",
                        "floor": 3,
                        "adjacent_to": ["stairwell", "maintenance closet"],
                        "access": "staff only",
                        "notable": "wind-exposed and half screened by ductwork",
                    },
                ],
                "floor_summary": {
                    "1": "lobby, records office, copy room",
                    "2": "administrative offices, meeting room",
                    "3": "archives overflow, maintenance access, roof landing",
                },
                "key_routes": [
                    "records office to roof landing: west stairwell, two flights, roughly 45 seconds at a run",
                ],
            },
            "macro": None,
        }
        self._write_workspace_json(workspace, self._spatial_layout_rel(), payload)

    def _mock_continuity_reconciliation_output(
        self, job: JobSpec, workspace: Path
    ) -> None:
        sheet_file = next(
            (p for p in job.required_outputs if p.endswith("continuity_sheet.json")),
            None,
        )
        conflict_file = next(
            (p for p in job.required_outputs if p.endswith("continuity_conflicts.json")),
            None,
        )
        if not sheet_file or not conflict_file:
            raise PipelineError("mock continuity reconciliation missing output paths")
        existing_sheet_path = workspace / sheet_file
        if existing_sheet_path.is_file():
            try:
                continuity_sheet = json.loads(existing_sheet_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continuity_sheet = {
                    "characters": [],
                    "timeline": {"story_start": "", "estimated_span": "", "seasonal_track": [], "key_events": []},
                    "geography": {"primary_setting": "", "key_locations": [], "distances": []},
                    "world_rules": [],
                    "power_structure": [],
                    "objects": [],
                    "financial_state": {"debts": [], "income_sources": []},
                    "knowledge_state": [],
                    "environmental_constants": [],
                }
        else:
            continuity_sheet = {
                "characters": [],
                "timeline": {"story_start": "", "estimated_span": "", "seasonal_track": [], "key_events": []},
                "geography": {"primary_setting": "", "key_locations": [], "distances": []},
                "world_rules": [],
                "power_structure": [],
                "objects": [],
                "financial_state": {"debts": [], "income_sources": []},
                "knowledge_state": [],
                "environmental_constants": [],
            }
        sheet_path = workspace / sheet_file
        sheet_path.parent.mkdir(parents=True, exist_ok=True)
        sheet_path.write_text(
            json.dumps(continuity_sheet, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        conflict_log = {
            "cycle": job.cycle,
            "conflicts": [],
            "new_facts_added": 0,
            "facts_updated": 0,
        }
        self._write_workspace_json(workspace, conflict_file, conflict_log)

    def _mock_chapter_draft_output(self, job: JobSpec, workspace: Path) -> None:
        if not job.chapter_id:
            raise PipelineError("mock chapter draft missing chapter_id")
        number = self._chapter_number(job.chapter_id)
        chapter_file = next((p for p in job.required_outputs if p.startswith("chapters/")), None)
        if not chapter_file:
            raise PipelineError("mock chapter draft missing chapter output path")
        projected_min_words = 2300
        spec_file = workspace / "outline" / "chapter_specs" / f"{job.chapter_id}.json"
        if spec_file.is_file():
            try:
                spec_data = json.loads(spec_file.read_text(encoding="utf-8"))
                candidate = int(spec_data.get("projected_min_words", projected_min_words))
                if candidate > 0:
                    projected_min_words = candidate
            except Exception:
                projected_min_words = 2300

        target_words = max(projected_min_words + 50, 2400)
        filler_sentence = (
            f"This dry run paragraph for {job.chapter_id} maintains pressure, consequence, and voice continuity."
        )
        filler_words = filler_sentence.split()
        body_words: list[str] = []
        while len(body_words) < target_words:
            body_words.extend(filler_words)
        body_text = " ".join(body_words[:target_words])
        text = f"# Chapter {number}\n\n{body_text}\n"
        self._write_workspace_text(workspace, chapter_file, text)

    def _mock_chapter_expand_output(self, job: JobSpec, workspace: Path) -> None:
        chapter_file = next((p for p in job.required_outputs if p.startswith("chapters/")), None)
        if not chapter_file:
            raise PipelineError("mock chapter expand missing chapter output path")
        current = (workspace / chapter_file).read_text(encoding="utf-8")
        expanded = (
            current.rstrip()
            + "\n\n"
            + "Additional scene pressure and consequence texture is added in dry-run expansion mode.\n"
        )
        self._write_workspace_text(workspace, chapter_file, expanded)

    def _mock_chapter_review_output(self, job: JobSpec, workspace: Path) -> None:
        if not job.chapter_id:
            raise PipelineError("mock chapter review missing chapter_id")
        output = next((p for p in job.required_outputs if p.endswith(".review.json")), None)
        if not output:
            raise PipelineError("mock chapter review missing output path")
        review = {
            "chapter_id": job.chapter_id,
            "verdicts": {
                "award": "PASS",
                "craft": "PASS",
                "dialogue": "PASS",
                "prose": "PASS",
            },
            "findings": [],
            "summary": f"Dry-run review pass for {job.chapter_id}.",
        }
        self._write_workspace_json(workspace, output, review)

    def _mock_full_award_output(self, job: JobSpec, workspace: Path) -> None:
        output = next(
            (p for p in job.required_outputs if p.endswith("full_award.review.json")), None
        )
        if not output:
            raise PipelineError("mock full award review missing output path")
        review = {
            "cycle": job.cycle,
            "verdict": "PASS",
            "summary": "Dry-run full-book review pass.",
            "findings": [],
        }
        self._write_workspace_json(workspace, output, review)

    def _mock_cross_chapter_audit_output(self, job: JobSpec, workspace: Path) -> None:
        output = next(
            (p for p in job.required_outputs if p.endswith("cross_chapter_audit.json")), None
        )
        if not output:
            raise PipelineError("mock cross-chapter audit missing output path")
        audit = {
            "cycle": job.cycle,
            "summary": "Dry-run cross-chapter audit pass.",
            "redundancy_findings": [],
            "consistency_findings": [],
        }
        self._write_workspace_json(workspace, output, audit)

    def _mock_local_window_audit_output(self, job: JobSpec, workspace: Path) -> None:
        output = next(
            (
                p
                for p in job.required_outputs
                if "/local_window_" in p and p.endswith(".json")
            ),
            None,
        )
        if not output:
            raise PipelineError("mock local-window audit missing output path")
        match = re.search(r"local_window_(\d+)\.json$", output)
        if not match:
            raise PipelineError("mock local-window audit output path missing window suffix")
        chapters_reviewed = sorted(
            {
                Path(rel).stem
                for rel in job.allowed_inputs
                if rel.startswith("outline/chapter_specs/") and rel.endswith(".json")
            }
        )
        audit = {
            "cycle": job.cycle,
            "window_id": f"window_{int(match.group(1)):02d}",
            "chapters_reviewed": chapters_reviewed,
            "summary": "Dry-run local-window audit pass.",
            "findings": [],
        }
        self._write_workspace_json(workspace, output, audit)

    def _mock_revision_aggregator_output(self, job: JobSpec, workspace: Path) -> None:
        input_file = next(
            (
                p
                for p in job.allowed_inputs
                if p.endswith("compact_aggregator_input.json")
            ),
            None,
        )
        output_file = next(
            (
                p
                for p in job.required_outputs
                if p.endswith("aggregation_decisions.json")
            ),
            None,
        )
        if not input_file or not output_file:
            raise PipelineError("mock revision aggregator missing input or output path")
        compact_input = json.loads((workspace / input_file).read_text(encoding="utf-8"))
        unchanged = sorted(self._compact_aggregator_input_finding_ids(compact_input))
        payload = {
            "unchanged": unchanged,
            "merges": [],
            "canonical_choices": [],
            "consistency_directives": [],
            "context_injections": [],
            "suppressions": [],
            "unfixable": [],
            "pass_reassignments": [],
        }
        self._write_workspace_json(workspace, output_file, payload)

    def _mock_chapter_revision_output(self, job: JobSpec, workspace: Path) -> None:
        if not job.chapter_id:
            raise PipelineError("mock chapter revision missing chapter_id")
        chapter_file = next((p for p in job.required_outputs if p.startswith("chapters/")), None)
        report_file = next(
            (p for p in job.required_outputs if p.endswith(".revision_report.json")), None
        )
        if not chapter_file or not report_file:
            raise PipelineError("mock chapter revision missing outputs")

        packet_file = next(
            (p for p in job.allowed_inputs if p.endswith(".revision_packet.json")), None
        )
        finding_rows: list[dict[str, Any]] = []
        if packet_file:
            packet_path = workspace / packet_file
            if packet_path.is_file():
                try:
                    packet_data = json.loads(packet_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    raise PipelineError(
                        f"mock chapter revision invalid packet JSON: {packet_file}"
                    ) from exc
                findings = packet_data.get("findings", [])
                for finding in findings:
                    if not isinstance(finding, dict):
                        continue
                    finding_id = str(finding.get("finding_id", "")).strip()
                    if not finding_id:
                        continue
                    finding_rows.append(
                        {
                            "finding_id": finding_id,
                            "status_after_revision": "FIXED",
                            "evidence": f"{chapter_file}:1",
                            "notes": "Dry-run revision marked this finding as fixed.",
                        }
                    )

        current = (workspace / chapter_file).read_text(encoding="utf-8")
        revised = current.rstrip() + "\n\n[Dry-run revision applied]\n"
        self._write_workspace_text(workspace, chapter_file, revised)
        report = {
            "chapter_id": job.chapter_id,
            "finding_results": finding_rows,
            "summary": f"Dry-run revision for {job.chapter_id}.",
        }
        self._write_workspace_json(workspace, report_file, report)

    def _normalize_outline_review_chapter_ids(self, raw: Any) -> list[str]:
        chapter_ids: list[str] = []
        if isinstance(raw, list):
            candidates = raw
        elif isinstance(raw, str):
            candidates = re.findall(r"chapter_\d{2}", raw)
            if not candidates and CHAPTER_ID_RE.match(raw.strip()):
                candidates = [raw.strip()]
        else:
            candidates = []
        seen: set[str] = set()
        for item in candidates:
            chapter_id = str(item).strip()
            if not CHAPTER_ID_RE.match(chapter_id) or chapter_id in seen:
                continue
            seen.add(chapter_id)
            chapter_ids.append(chapter_id)
        return chapter_ids

    def _repair_outline_review_data(
        self, data: dict[str, Any]
    ) -> tuple[dict[str, Any], list[str]]:
        if not isinstance(data, dict):
            return data, []
        repaired = copy.deepcopy(data)
        repairs: list[str] = []

        cycle_value = repaired.get("cycle")
        if isinstance(cycle_value, str) and cycle_value.strip().isdigit():
            repaired["cycle"] = int(cycle_value.strip())
            repairs.append("coerced cycle to int")

        if "premise_criteria" not in repaired and isinstance(repaired.get("criteria"), list):
            repaired["premise_criteria"] = repaired.pop("criteria")
            repairs.append("mapped criteria to premise_criteria")
        if "structural_findings" not in repaired and isinstance(repaired.get("findings"), list):
            repaired["structural_findings"] = repaired.pop("findings")
            repairs.append("mapped findings to structural_findings")
        if repaired.get("elevation_suggestions") is None:
            repaired["elevation_suggestions"] = []
            repairs.append("defaulted missing elevation_suggestions")

        criteria = repaired.get("premise_criteria")
        if isinstance(criteria, list):
            normalized_criteria: list[dict[str, Any]] = []
            for idx, row in enumerate(criteria, start=1):
                if not isinstance(row, dict):
                    continue
                met_value = row.get("met", row.get("is_met"))
                if isinstance(met_value, str):
                    token = met_value.strip().lower()
                    met_value = token in {"true", "yes", "y", "1", "met"}
                criterion = self._optional_text(row.get("criterion")) or self._optional_text(
                    row.get("name")
                )
                evidence = self._optional_text(row.get("evidence")) or self._optional_text(
                    row.get("problem")
                )
                suggestion = self._optional_text(row.get("suggestion")) or self._optional_text(
                    row.get("rewrite_direction")
                )
                normalized_criteria.append(
                    {
                        "criterion": criterion,
                        "met": bool(met_value),
                        "evidence": evidence,
                        "suggestion": suggestion,
                    }
                )
                if normalized_criteria[-1] != row:
                    repairs.append(f"normalized premise_criteria[{idx}]")
            repaired["premise_criteria"] = normalized_criteria

        findings = repaired.get("structural_findings")
        if isinstance(findings, list):
            normalized_findings: list[dict[str, Any]] = []
            for idx, row in enumerate(findings, start=1):
                if not isinstance(row, dict):
                    continue
                finding_id = self._optional_text(row.get("finding_id")) or self._optional_text(
                    row.get("id")
                ) or f"OR-{idx:03d}"
                severity = self._optional_text(row.get("severity")).upper() or "HIGH"
                if severity not in FULL_AWARD_SEVERITY_VALUES:
                    severity = "HIGH"
                chapters_affected = self._normalize_outline_review_chapter_ids(
                    row.get("chapters_affected", row.get("chapter_id"))
                )
                normalized_findings.append(
                    {
                        "finding_id": finding_id,
                        "severity": severity,
                        "check": self._optional_text(row.get("check"))
                        or self._optional_text(row.get("category"))
                        or "structural",
                        "chapters_affected": chapters_affected,
                        "problem": self._optional_text(row.get("problem"))
                        or self._optional_text(row.get("description")),
                        "rewrite_direction": self._optional_text(
                            row.get("rewrite_direction")
                        )
                        or self._optional_text(row.get("revision_directive"))
                        or self._optional_text(row.get("suggestion")),
                    }
                )
                if normalized_findings[-1] != row:
                    repairs.append(f"normalized structural_findings[{idx}]")
            repaired["structural_findings"] = normalized_findings

        suggestions = repaired.get("elevation_suggestions")
        if isinstance(suggestions, list):
            normalized_suggestions: list[dict[str, Any]] = []
            for idx, row in enumerate(suggestions, start=1):
                if not isinstance(row, dict):
                    continue
                normalized_suggestions.append(
                    {
                        "suggestion": self._optional_text(row.get("suggestion"))
                        or self._optional_text(row.get("opportunity"))
                        or self._optional_text(row.get("rewrite_direction")),
                        "chapters_affected": self._normalize_outline_review_chapter_ids(
                            row.get("chapters_affected", row.get("chapter_id"))
                        ),
                    }
                )
                if normalized_suggestions[-1] != row:
                    repairs.append(f"normalized elevation_suggestions[{idx}]")
            repaired["elevation_suggestions"] = normalized_suggestions

        return repaired, repairs

    def _validate_outline_review_json(
        self, data: dict[str, Any], cycle_num: int, chapter_ids: set[str], rel: str
    ) -> None:
        if data.get("cycle") != cycle_num:
            raise PipelineError(f"{rel} cycle must equal {cycle_num}")
        criteria = data.get("premise_criteria")
        if not isinstance(criteria, list) or not criteria:
            raise PipelineError(f"{rel} premise_criteria must be a non-empty array")
        for idx, row in enumerate(criteria, start=1):
            if not isinstance(row, dict):
                raise PipelineError(f"{rel} premise_criteria[{idx}] must be an object")
            if not self._optional_text(row.get("criterion")):
                raise PipelineError(f"{rel} premise_criteria[{idx}] missing criterion")
            if not isinstance(row.get("met"), bool):
                raise PipelineError(f"{rel} premise_criteria[{idx}] met must be boolean")
            if not self._optional_text(row.get("evidence")):
                raise PipelineError(f"{rel} premise_criteria[{idx}] missing evidence")
            if not self._optional_text(row.get("suggestion")):
                raise PipelineError(f"{rel} premise_criteria[{idx}] missing suggestion")

        findings = data.get("structural_findings")
        if not isinstance(findings, list):
            raise PipelineError(f"{rel} structural_findings must be an array")
        for idx, row in enumerate(findings, start=1):
            if not isinstance(row, dict):
                raise PipelineError(f"{rel} structural_findings[{idx}] must be an object")
            if not self._optional_text(row.get("finding_id")):
                raise PipelineError(f"{rel} structural_findings[{idx}] missing finding_id")
            severity = self._optional_text(row.get("severity")).upper()
            if severity not in FULL_AWARD_SEVERITY_VALUES:
                raise PipelineError(
                    f"{rel} structural_findings[{idx}] invalid severity: {severity}"
                )
            if not self._optional_text(row.get("check")):
                raise PipelineError(f"{rel} structural_findings[{idx}] missing check")
            chapters_affected = row.get("chapters_affected")
            if not isinstance(chapters_affected, list):
                raise PipelineError(
                    f"{rel} structural_findings[{idx}] chapters_affected must be an array"
                )
            for chapter_id in chapters_affected:
                if chapter_id not in chapter_ids:
                    raise PipelineError(
                        f"{rel} structural_findings[{idx}] invalid chapter_id: {chapter_id}"
                    )
            if not self._optional_text(row.get("problem")):
                raise PipelineError(f"{rel} structural_findings[{idx}] missing problem")
            if not self._optional_text(row.get("rewrite_direction")):
                raise PipelineError(
                    f"{rel} structural_findings[{idx}] missing rewrite_direction"
                )

        suggestions = data.get("elevation_suggestions")
        if not isinstance(suggestions, list):
            raise PipelineError(f"{rel} elevation_suggestions must be an array")
        for idx, row in enumerate(suggestions, start=1):
            if not isinstance(row, dict):
                raise PipelineError(f"{rel} elevation_suggestions[{idx}] must be an object")
            if not self._optional_text(row.get("suggestion")):
                raise PipelineError(f"{rel} elevation_suggestions[{idx}] missing suggestion")
            chapters_affected = row.get("chapters_affected")
            if not isinstance(chapters_affected, list):
                raise PipelineError(
                    f"{rel} elevation_suggestions[{idx}] chapters_affected must be an array"
                )
            for chapter_id in chapters_affected:
                if chapter_id not in chapter_ids:
                    raise PipelineError(
                        f"{rel} elevation_suggestions[{idx}] invalid chapter_id: {chapter_id}"
                    )
        if not self._optional_text(data.get("summary")):
            raise PipelineError(f"{rel} summary must be non-empty")

    def _load_repaired_outline_review(
        self, rel: str, cycle_num: int, chapter_ids: set[str]
    ) -> dict[str, Any]:
        data = self._read_json(rel)
        repaired_data, repairs = self._repair_outline_review_data(data)
        if repairs:
            self._write_json(rel, repaired_data)
            self._log(
                f"outline_review_repair cycle={self._cpad(cycle_num)} "
                f"applied={len(repairs)} details={' | '.join(repairs)}"
            )
            data = repaired_data
        self._validate_outline_review_json(data, cycle_num, chapter_ids, rel)
        return data

    def _repair_spatial_layout_data(
        self, data: dict[str, Any]
    ) -> tuple[dict[str, Any], list[str]]:
        if not isinstance(data, dict):
            return data, []
        repaired = copy.deepcopy(data)
        repairs: list[str] = []
        if "summary" not in repaired:
            repaired["summary"] = "Spatial layout not required for this premise."
            repairs.append("defaulted missing summary")
        for key in ("micro", "macro"):
            if key not in repaired:
                repaired[key] = None
                repairs.append(f"defaulted missing {key}")
            elif repaired[key] in ("", [], {}):
                repaired[key] = None
                repairs.append(f"normalized empty {key} to null")
        return repaired, repairs

    def _validate_spatial_layout_data(self, data: dict[str, Any], rel: str) -> None:
        if not self._optional_text(data.get("summary")):
            raise PipelineError(f"{rel} summary must be non-empty")
        for key in ("micro", "macro"):
            section = data.get(key)
            if section is None:
                continue
            if not isinstance(section, dict):
                raise PipelineError(f"{rel} {key} must be an object or null")
            locations = section.get("locations")
            if not isinstance(locations, list) or not locations:
                raise PipelineError(f"{rel} {key}.locations must be a non-empty array")
            for idx, row in enumerate(locations, start=1):
                if not isinstance(row, dict) or not self._optional_text(row.get("name")):
                    raise PipelineError(
                        f"{rel} {key}.locations[{idx}] must be an object with a name"
                    )
            if key == "micro":
                if not self._optional_text(section.get("setting_name")):
                    raise PipelineError(f"{rel} micro.setting_name must be non-empty")
                if not self._optional_text(section.get("structure_type")):
                    raise PipelineError(f"{rel} micro.structure_type must be non-empty")
                if "floor_summary" in section and not isinstance(
                    section.get("floor_summary"), dict
                ):
                    raise PipelineError(f"{rel} micro.floor_summary must be an object")
                if "key_routes" in section and not isinstance(
                    section.get("key_routes"), list
                ):
                    raise PipelineError(f"{rel} micro.key_routes must be an array")
            if key == "macro":
                if not self._optional_text(section.get("world_name")):
                    raise PipelineError(f"{rel} macro.world_name must be non-empty")
                if "routes" in section and not isinstance(section.get("routes"), list):
                    raise PipelineError(f"{rel} macro.routes must be an array")
                if "routes" in section:
                    for idx, route in enumerate(section.get("routes", []), start=1):
                        if not isinstance(route, dict):
                            raise PipelineError(
                                f"{rel} macro.routes[{idx}] must be an object"
                            )
                        if not self._optional_text(route.get("from")) or not self._optional_text(
                            route.get("to")
                        ):
                            raise PipelineError(
                                f"{rel} macro.routes[{idx}] must include from/to"
                            )

    def _load_repaired_spatial_layout(self, rel: str) -> dict[str, Any]:
        data = self._read_json(rel)
        repaired_data, repairs = self._repair_spatial_layout_data(data)
        if repairs:
            self._write_json(rel, repaired_data)
            self._log(
                f"spatial_layout_repair applied={len(repairs)} details={' | '.join(repairs)}"
            )
            data = repaired_data
        self._validate_spatial_layout_data(data, rel)
        return data

    def _load_and_validate_chapter_specs(self) -> list[ChapterSpec]:
        rel = "outline/chapter_specs.jsonl"
        path = self.run_dir / rel
        if not path.is_file():
            raise PipelineError(f"missing chapter specs file: {rel}")

        specs: list[ChapterSpec] = []
        with path.open("r", encoding="utf-8") as f:
            for idx, raw_line in enumerate(f, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise PipelineError(f"invalid JSON in {rel}:{idx}") from exc

                chapter_id = str(data.get("chapter_id", "")).strip()
                chapter_number = data.get("chapter_number")
                projected_min_words = data.get("projected_min_words")
                chapter_engine = str(data.get("chapter_engine", "")).strip()
                pressure_source = str(data.get("pressure_source", "")).strip()
                state_shift = str(data.get("state_shift", "")).strip()
                texture_mode = str(data.get("texture_mode", "")).strip()
                scene_count_target = data.get("scene_count_target")
                scene_count_target_explicit = scene_count_target is not None
                if not chapter_engine:
                    chapter_engine = str(data.get("objective", "")).strip()
                if not pressure_source:
                    pressure_source = str(data.get("conflict", "")).strip()
                if not state_shift:
                    state_shift = str(data.get("consequence", "")).strip()
                if not texture_mode:
                    texture_mode = "pressure-driven"
                if scene_count_target is None:
                    scene_count_target = 2
                beats_raw = data.get("must_land_beats", [])
                secondary_beats_raw = data.get("secondary_character_beats", [])
                setups_raw = data.get("setups_to_plant", [])
                payoffs_raw = data.get("payoffs_to_land", [])
                if secondary_beats_raw is None:
                    secondary_beats_raw = []
                if setups_raw is None:
                    setups_raw = []
                if payoffs_raw is None:
                    payoffs_raw = []

                if not CHAPTER_ID_RE.match(chapter_id):
                    raise PipelineError(f"invalid chapter_id in {rel}:{idx}: {chapter_id}")
                if (
                    not isinstance(chapter_number, int)
                    or isinstance(chapter_number, bool)
                    or chapter_number < 1
                ):
                    raise PipelineError(
                        f"invalid chapter_number in {rel}:{idx}: {chapter_number}"
                    )
                if (
                    not isinstance(projected_min_words, int)
                    or isinstance(projected_min_words, bool)
                    or projected_min_words <= 0
                ):
                    raise PipelineError(
                        f"invalid projected_min_words in {rel}:{idx}: {projected_min_words}"
                    )
                if (
                    not chapter_engine
                    or not pressure_source
                    or not state_shift
                    or not texture_mode
                ):
                    raise PipelineError(
                        f"missing required narrative fields in {rel}:{idx} for {chapter_id}"
                    )
                if (
                    not isinstance(scene_count_target, int)
                    or isinstance(scene_count_target, bool)
                    or scene_count_target < 1
                    or scene_count_target > 4
                ):
                    raise PipelineError(
                        f"invalid scene_count_target in {rel}:{idx}: {scene_count_target}"
                    )
                if not isinstance(beats_raw, list) or not all(
                    isinstance(x, str) and x.strip() for x in beats_raw
                ):
                    raise PipelineError(f"invalid must_land_beats in {rel}:{idx}")
                if not isinstance(secondary_beats_raw, list) or not all(
                    isinstance(x, str) and x.strip() for x in secondary_beats_raw
                ):
                    raise PipelineError(
                        f"invalid secondary_character_beats in {rel}:{idx}"
                    )
                if not isinstance(setups_raw, list):
                    raise PipelineError(f"invalid setups_to_plant in {rel}:{idx}")
                if not isinstance(payoffs_raw, list):
                    raise PipelineError(f"invalid payoffs_to_land in {rel}:{idx}")

                normalized_setups: list[dict[str, Any]] = []
                for entry in setups_raw:
                    if not isinstance(entry, dict):
                        raise PipelineError(f"invalid setups_to_plant in {rel}:{idx}")
                    setup_id = str(entry.get("setup_id", "")).strip()
                    description = str(entry.get("description", "")).strip()
                    if not setup_id or not description:
                        raise PipelineError(
                            f"invalid setups_to_plant in {rel}:{idx}: setup_id/description required"
                        )
                    normalized_entry: dict[str, Any] = {
                        "setup_id": setup_id,
                        "description": description,
                    }
                    payoff_window = str(entry.get("payoff_window", "")).strip()
                    visibility = str(entry.get("visibility", "")).strip()
                    if payoff_window:
                        normalized_entry["payoff_window"] = payoff_window
                    if visibility:
                        normalized_entry["visibility"] = visibility
                    normalized_setups.append(normalized_entry)

                normalized_payoffs: list[dict[str, Any]] = []
                for entry in payoffs_raw:
                    if not isinstance(entry, dict):
                        raise PipelineError(f"invalid payoffs_to_land in {rel}:{idx}")
                    setup_id = str(entry.get("setup_id", "")).strip()
                    description = str(entry.get("description", "")).strip()
                    if not setup_id or not description:
                        raise PipelineError(
                            f"invalid payoffs_to_land in {rel}:{idx}: setup_id/description required"
                        )
                    normalized_entry = {
                        "setup_id": setup_id,
                        "description": description,
                    }
                    seeded_by_raw = entry.get("seeded_by", [])
                    if seeded_by_raw is None:
                        seeded_by_raw = []
                    if not isinstance(seeded_by_raw, list) or not all(
                        isinstance(ch, str) and CHAPTER_ID_RE.match(ch.strip())
                        for ch in seeded_by_raw
                    ):
                        raise PipelineError(
                            f"invalid payoffs_to_land in {rel}:{idx}: seeded_by must be chapter ids"
                        )
                    if seeded_by_raw:
                        normalized_entry["seeded_by"] = [
                            ch.strip() for ch in seeded_by_raw
                        ]
                    payoff_type = str(entry.get("payoff_type", "")).strip()
                    if payoff_type:
                        normalized_entry["payoff_type"] = payoff_type
                    normalized_payoffs.append(normalized_entry)

                expected_number = self._chapter_number(chapter_id)
                if chapter_number != expected_number:
                    raise PipelineError(
                        f"chapter_number mismatch in {rel}:{idx}: {chapter_id} vs {chapter_number}"
                    )

                specs.append(
                    ChapterSpec(
                        chapter_id=chapter_id,
                        chapter_number=chapter_number,
                        projected_min_words=projected_min_words,
                        chapter_engine=chapter_engine,
                        pressure_source=pressure_source,
                        state_shift=state_shift,
                        texture_mode=texture_mode,
                        scene_count_target=scene_count_target,
                        scene_count_target_explicit=scene_count_target_explicit,
                        must_land_beats=[x.strip() for x in beats_raw],
                        secondary_character_beats=[
                            x.strip() for x in secondary_beats_raw
                        ],
                        setups_to_plant=normalized_setups,
                        payoffs_to_land=normalized_payoffs,
                    )
                )

        if not (16 <= len(specs) <= 20):
            raise PipelineError(
                f"chapter count must be between 16 and 20; found {len(specs)} in {rel}"
            )
        for idx, spec in enumerate(specs, start=1):
            expected = f"chapter_{idx:02d}"
            if spec.chapter_id != expected:
                raise PipelineError(
                    f"chapter_specs must be contiguous from chapter_01; expected {expected}, found {spec.chapter_id}"
                )
        return specs

    def _validate_scene_plan(self) -> None:
        rel = "outline/scene_plan.tsv"
        path = self.run_dir / rel
        if not path.is_file():
            raise PipelineError(f"missing scene plan file: {rel}")

        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines:
            raise PipelineError(f"scene plan file is empty: {rel}")

        expected_header = (
            "scene_id\tchapter_id\tscene_order\tobjective\topposition\tturn\tconsequence_cost\ttension_peak"
        )
        if lines[0].strip() != expected_header:
            raise PipelineError(f"scene plan header mismatch in {rel}")

        scene_count_by_chapter: dict[str, int] = {}
        for i, line in enumerate(lines[1:], start=2):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) != 8:
                raise PipelineError(f"scene plan row must have 8 columns ({rel}:{i})")
            scene_id, chapter_id, scene_order, *_rest, tension_peak = parts
            if not scene_id.strip():
                raise PipelineError(f"empty scene_id in {rel}:{i}")
            if not CHAPTER_ID_RE.match(chapter_id):
                raise PipelineError(f"invalid chapter_id in {rel}:{i}: {chapter_id}")
            if not scene_order.isdigit() or int(scene_order) < 1:
                raise PipelineError(f"invalid scene_order in {rel}:{i}: {scene_order}")
            tp = tension_peak.strip().upper()
            if tp not in {"YES", "NO"}:
                raise PipelineError(f"invalid tension_peak in {rel}:{i}: {tension_peak}")
            scene_count_by_chapter[chapter_id] = scene_count_by_chapter.get(chapter_id, 0) + 1

        for spec in self.chapter_specs:
            actual = scene_count_by_chapter.get(spec.chapter_id, 0)
            if spec.scene_count_target_explicit:
                if actual != spec.scene_count_target:
                    raise PipelineError(
                        f"scene plan must include exactly {spec.scene_count_target} scenes for {spec.chapter_id}"
                    )
                continue
            if actual < 2:
                raise PipelineError(
                    f"legacy scene plan must include at least 2 scenes for {spec.chapter_id}"
                )

    def _load_and_validate_style_bible(self) -> dict[str, Any]:
        rel = "outline/style_bible.json"
        data = self._read_json(rel)
        repaired_data, repairs = self._repair_style_bible_data(data)
        if repairs:
            self._write_json(rel, repaired_data)
            self._log(
                f"style_bible_repair applied={len(repairs)} details={' | '.join(repairs)}"
            )
            data = repaired_data
        self._validate_style_bible_data(data, rel)
        return data

    def _repair_style_bible_data(
        self, data: dict[str, Any]
    ) -> tuple[dict[str, Any], list[str]]:
        if not isinstance(data, dict):
            return data, []

        def parse_bool(value: Any, default: bool) -> tuple[bool, bool]:
            if isinstance(value, bool):
                return value, False
            if isinstance(value, (int, float)) and value in (0, 1):
                return bool(value), True
            if isinstance(value, str):
                token = value.strip().lower()
                if token in {"true", "yes", "y", "1", "on", "allow", "allowed"}:
                    return True, True
                if token in {"false", "no", "n", "0", "off", "forbid", "forbidden"}:
                    return False, True
            return default, True

        def parse_int(value: Any, default: int) -> tuple[int, bool]:
            if isinstance(value, int) and not isinstance(value, bool):
                return max(0, value), False
            if isinstance(value, str):
                m = re.search(r"-?\d+", value)
                if m:
                    return max(0, int(m.group(0))), True
            if isinstance(value, (float, bool)):
                return max(0, int(value)), True
            return max(0, default), True

        repairs: list[str] = []
        profiles = data.get("character_voice_profiles")
        if isinstance(profiles, list):
            for idx, row in enumerate(profiles, start=1):
                if not isinstance(row, dict):
                    continue
                voice_guidance_defaults = {
                    "lexical_signature": (
                        "Lexical choices should reflect background and scene pressure without "
                        "relying on repeated keyword motifs."
                    ),
                    "forbidden_generic_lines": (
                        "Avoid platitudes, stock reassurances, and generic cinematic filler."
                    ),
                    "stress_tells": (
                        "Stress behavior should vary across scenes and stay subtle, embodied, "
                        "and non-repetitive."
                    ),
                    "interruption_habit": (
                        "Interruptions should be pressure-true and character-specific rather "
                        "than generic overlap."
                    ),
                    "self_correction_tendency": (
                        "Self-corrections may appear under pressure but should vary in form and "
                        "not become a repeated tic."
                    ),
                    "indirectness": (
                        "Describe how directly or evasively this character speaks when stakes rise."
                    ),
                    "repetition_tolerance": (
                        "State how much purposeful repetition this character allows before it feels "
                        "uncharacteristic or mechanical."
                    ),
                    "evasion_style": (
                        "When this character avoids the truth, specify how they redirect, hedge, "
                        "or narrow the subject."
                    ),
                    "sentence_completion_style": (
                        "Describe whether this character tends to finish, trail off, restart, or "
                        "repair sentences under pressure while staying legible."
                    ),
                }
                for field, default in voice_guidance_defaults.items():
                    raw = row.get(field)
                    if isinstance(raw, str) and raw.strip():
                        row[field] = raw.strip()
                        continue
                    if isinstance(raw, list):
                        row[field] = default
                        repairs.append(
                            f"character_voice_profiles[{idx}].{field} normalized from list to guidance string"
                        )
                        continue
                    row[field] = default
                    repairs.append(
                        f"character_voice_profiles[{idx}].{field} defaulted"
                    )
                profanity_profile = row.get("profanity_profile")
                if not (isinstance(profanity_profile, str) and profanity_profile.strip()):
                    row["profanity_profile"] = (
                        "pressure-conditional; restrained in formal settings, sharper under threat"
                    )
                    repairs.append(
                        f"character_voice_profiles[{idx}].profanity_profile defaulted"
                    )
                contraction_level = row.get("contraction_level")
                valid_contraction_levels = {"high", "moderate", "low", "variable"}
                if not (
                    isinstance(contraction_level, str)
                    and contraction_level.strip().lower() in valid_contraction_levels
                ):
                    row["contraction_level"] = "moderate"
                    repairs.append(
                        f"character_voice_profiles[{idx}].contraction_level defaulted to moderate"
                    )
                else:
                    row["contraction_level"] = contraction_level.strip().lower()

        dialogue_rules = data.get("dialogue_rules")
        if not isinstance(dialogue_rules, dict):
            dialogue_rules = {}
            data["dialogue_rules"] = dialogue_rules
            repairs.append("dialogue_rules defaulted to object")

        anti_val, anti_coerced = parse_bool(
            dialogue_rules.get("anti_transcript_cadence", dialogue_rules.get("pressure_first")),
            True,
        )
        if anti_coerced or "anti_transcript_cadence" not in dialogue_rules:
            dialogue_rules["anti_transcript_cadence"] = anti_val
            repairs.append("dialogue_rules.anti_transcript_cadence normalized")

        leverage_val, leverage_coerced = parse_int(
            dialogue_rules.get(
                "required_leverage_shifts_per_scene",
                dialogue_rules.get("power_shift_requirement"),
            ),
            1,
        )
        if leverage_coerced or "required_leverage_shifts_per_scene" not in dialogue_rules:
            dialogue_rules["required_leverage_shifts_per_scene"] = leverage_val
            repairs.append("dialogue_rules.required_leverage_shifts_per_scene normalized")

        low_info_val, low_info_coerced = parse_int(
            dialogue_rules.get(
                "max_consecutive_low_info_replies",
                dialogue_rules.get("silence_usage"),
            ),
            2,
        )
        if low_info_val < 2:
            low_info_val = 2
            low_info_coerced = True
        if low_info_coerced or "max_consecutive_low_info_replies" not in dialogue_rules:
            dialogue_rules["max_consecutive_low_info_replies"] = low_info_val
            repairs.append("dialogue_rules.max_consecutive_low_info_replies normalized")

        idiolect_val, idiolect_coerced = parse_bool(
            dialogue_rules.get(
                "idiolect_separation_required",
                dialogue_rules.get("idiolect_guardrails"),
            ),
            True,
        )
        if idiolect_coerced or "idiolect_separation_required" not in dialogue_rules:
            dialogue_rules["idiolect_separation_required"] = idiolect_val
            repairs.append("dialogue_rules.idiolect_separation_required normalized")

        default_contraction = dialogue_rules.get("default_contraction_use")
        if not (isinstance(default_contraction, str) and default_contraction.strip()):
            dialogue_rules["default_contraction_use"] = (
                "high — contractions are the norm; uncontracted forms reserved for emphasis "
                "or character-specific formality"
            )
            repairs.append("dialogue_rules.default_contraction_use defaulted")

        prose = data.get("prose_style_profile")
        if not isinstance(prose, dict):
            prose = {}
            data["prose_style_profile"] = prose
            repairs.append("prose_style_profile defaulted to object")

        narrative_tense = prose.get("narrative_tense")
        if not isinstance(narrative_tense, str) or not narrative_tense.strip():
            prose["narrative_tense"] = "past tense"
            repairs.append("prose_style_profile.narrative_tense defaulted")

        narrative_distance = prose.get("narrative_distance")
        if not isinstance(narrative_distance, str) or not narrative_distance.strip():
            prose["narrative_distance"] = "close-third with pressure-tight interiority"
            repairs.append("prose_style_profile.narrative_distance defaulted")

        rhythm_target = prose.get("rhythm_target")
        if not isinstance(rhythm_target, str) or not rhythm_target.strip():
            source = prose.get("sentence_music", prose.get("pacing_law"))
            if isinstance(source, str) and source.strip():
                prose["rhythm_target"] = source.strip()
                repairs.append("prose_style_profile.rhythm_target mapped")
            else:
                prose["rhythm_target"] = "mixed sentence lengths; rhythm responsive to scene intensity"
                repairs.append("prose_style_profile.rhythm_target defaulted")

        sensory_bias = prose.get("sensory_bias")
        if not isinstance(sensory_bias, list) or not all(
            isinstance(x, str) and x.strip() for x in sensory_bias
        ):
            source = prose.get("imagery_domain", prose.get("thematic_threads"))
            mapped: list[str] = []
            if isinstance(source, str) and source.strip():
                mapped = [source.strip()]
            elif isinstance(source, list):
                mapped = [
                    str(x).strip()
                    for x in source
                    if isinstance(x, str) and str(x).strip()
                ]
            if not mapped:
                mapped = ["touch", "sound", "spatial pressure"]
                repairs.append("prose_style_profile.sensory_bias defaulted")
            else:
                repairs.append("prose_style_profile.sensory_bias mapped")
            prose["sensory_bias"] = mapped

        diction = prose.get("diction")
        if not isinstance(diction, str) or not diction.strip():
            prose["diction"] = "concrete, unsanitized, low-abstraction"
            repairs.append("prose_style_profile.diction defaulted")

        forbidden_drift = prose.get("forbidden_drift_patterns")
        if not isinstance(forbidden_drift, list) or not all(
            isinstance(x, str) and x.strip() for x in forbidden_drift
        ):
            source = prose.get("anti_generic_constraints")
            mapped: list[str] = []
            if isinstance(source, str) and source.strip():
                mapped = [source.strip()]
            elif isinstance(source, list):
                mapped = [
                    str(x).strip()
                    for x in source
                    if isinstance(x, str) and str(x).strip()
                ]
            if not mapped:
                mapped = ["generic cinematic phrasing"]
                repairs.append("prose_style_profile.forbidden_drift_patterns defaulted")
            else:
                repairs.append("prose_style_profile.forbidden_drift_patterns mapped")
            prose["forbidden_drift_patterns"] = mapped

        chapter_texture = prose.get("chapter_texture_variance")
        if not (isinstance(chapter_texture, str) and chapter_texture.strip()):
            prose["chapter_texture_variance"] = (
                "Alternate high-intensity scenes with reflective interiority; vary scene count, "
                "dialogue density, and pacing so no two consecutive chapters feel "
                "structurally identical."
            )
            repairs.append("prose_style_profile.chapter_texture_variance defaulted")

        aesthetic = data.get("aesthetic_risk_policy")
        if not isinstance(aesthetic, dict):
            aesthetic = {}
            data["aesthetic_risk_policy"] = aesthetic
            repairs.append("aesthetic_risk_policy defaulted to object")

        sanitization_val, sanitization_coerced = parse_bool(
            aesthetic.get("sanitization_disallowed", aesthetic.get("safeguard_principle")),
            True,
        )
        if sanitization_coerced or "sanitization_disallowed" not in aesthetic:
            aesthetic["sanitization_disallowed"] = sanitization_val
            repairs.append("aesthetic_risk_policy.sanitization_disallowed normalized")

        dark_val, dark_coerced = parse_bool(
            aesthetic.get(
                "dark_content_allowed_when_character_true",
                aesthetic.get("dark_content_allowed_when_narratively_warranted"),
            ),
            True,
        )
        if dark_coerced or "dark_content_allowed_when_character_true" not in aesthetic:
            aesthetic["dark_content_allowed_when_character_true"] = dark_val
            repairs.append(
                "aesthetic_risk_policy.dark_content_allowed_when_character_true normalized"
            )

        profanity_val, profanity_coerced = parse_bool(
            aesthetic.get(
                "profanity_allowed_when_scene_pressure_warrants",
                aesthetic.get("profanity_allowed_when_narratively_warranted"),
            ),
            True,
        )
        if (
            profanity_coerced
            or "profanity_allowed_when_scene_pressure_warrants" not in aesthetic
        ):
            aesthetic["profanity_allowed_when_scene_pressure_warrants"] = profanity_val
            repairs.append(
                "aesthetic_risk_policy.profanity_allowed_when_scene_pressure_warrants normalized"
            )

        euphemism = aesthetic.get("euphemism_penalty")
        if not isinstance(euphemism, str) or not euphemism.strip():
            aesthetic["euphemism_penalty"] = "high"
            repairs.append("aesthetic_risk_policy.euphemism_penalty defaulted")

        risk = aesthetic.get("creative_risk_policy")
        if not isinstance(risk, str) or not risk.strip():
            aesthetic["creative_risk_policy"] = (
                "Push toward uncomfortable specificity and full presence when rendering difficult material."
            )
            repairs.append("aesthetic_risk_policy.creative_risk_policy defaulted")
        return data, repairs

    def _preserved_invalid_artifact_rel(self, rel: str) -> str:
        if rel.endswith(".json"):
            return rel[:-5] + ".invalid.original.json"
        return rel + ".invalid.original"

    def _preserve_invalid_artifact(self, rel: str) -> str | None:
        path = self.run_dir / rel
        if not path.is_file():
            return None
        preserved_rel = self._preserved_invalid_artifact_rel(rel)
        preserved_path = self.run_dir / preserved_rel
        preserved_path.parent.mkdir(parents=True, exist_ok=True)
        payload = path.read_text(encoding="utf-8")
        if preserved_path.is_file() and preserved_path.read_text(encoding="utf-8") == payload:
            return preserved_rel
        preserved_path.write_text(payload, encoding="utf-8")
        return preserved_rel

    def _coerce_full_award_chapter_id(
        self, raw: Any, chapter_ids: set[str]
    ) -> tuple[str, bool]:
        chapter_id = str(raw).strip()
        if chapter_id in chapter_ids:
            return chapter_id, False

        lowered = chapter_id.lower()
        for pattern in (
            r"^ch(?:apter)?[_-]?(\d{1,2})$",
            r"^chapter[_-]?(\d{1,2})$",
        ):
            match = re.fullmatch(pattern, lowered)
            if not match:
                continue
            normalized = f"chapter_{int(match.group(1)):02d}"
            if normalized in chapter_ids:
                return normalized, True
        return chapter_id, False

    def _flatten_full_award_evidence(self, raw: Any) -> str:
        if isinstance(raw, str):
            return raw.strip()
        if isinstance(raw, dict):
            location = str(raw.get("location", "")).strip()
            description = str(raw.get("description", "")).strip()
            if location and description:
                return f"{location} - {description}"
            if location:
                return location
            if description:
                return description
            return ""
        if isinstance(raw, list):
            parts: list[str] = []
            for item in raw:
                flattened = self._flatten_full_award_evidence(item)
                if flattened:
                    parts.append(flattened)
            deduped: list[str] = []
            seen: set[str] = set()
            for item in parts:
                if item in seen:
                    continue
                seen.add(item)
                deduped.append(item)
            return "; ".join(deduped)
        return str(raw).strip()

    def _extract_locator_citations(self, text: str, target_file: str) -> list[str]:
        pattern = re.compile(rf"{re.escape(target_file)}:\d+(?:-\d+)?")
        seen: set[str] = set()
        citations: list[str] = []
        for match in pattern.finditer(str(text)):
            token = match.group(0)
            if token in seen:
                continue
            seen.add(token)
            citations.append(token)
        return citations

    def _augment_full_award_rewrite_direction(
        self, rewrite_direction: Any, evidence: str, target_file: str
    ) -> str:
        text = str(rewrite_direction).strip()
        if not text:
            return ""
        if target_file in text:
            return text
        citations = self._extract_locator_citations(evidence, target_file)
        if not citations:
            return text
        citation_blob = "; ".join(citations[:3])
        return f"Revise {citation_blob}. {text}"

    def _synthesize_full_award_acceptance_test(
        self, evidence: str, target_file: str
    ) -> str:
        citations = self._extract_locator_citations(evidence, target_file)
        if citations:
            citation_blob = "; ".join(citations[:3])
            return (
                f"Pass if the revised material at {citation_blob} now follows the rewrite "
                "direction and no longer exhibits the described defect. Fail if a cold reader "
                "would still identify the same underlying problem in those cited passages."
            )
        return (
            "Pass if the revised material now follows the rewrite direction and no longer "
            "exhibits the described defect. Fail if a cold reader would still identify the "
            "same underlying problem."
        )

    def _normalize_full_award_finding_source_and_severity(
        self, source: str, severity: str
    ) -> tuple[str, str]:
        normalized_source = self._canonical_finding_source_name(source)
        normalized_severity = str(severity).strip().upper()
        if normalized_severity == "ELEVATION_HIGH":
            if not normalized_source:
                normalized_source = "elevation"
            return normalized_source, "HIGH"
        if normalized_severity == "ELEVATION_MEDIUM":
            if not normalized_source:
                normalized_source = "elevation"
            return normalized_source, "MEDIUM"
        return normalized_source, normalized_severity

    def _repair_full_award_review_data(
        self,
        data: dict[str, Any],
        cycle: int,
        chapter_ids: set[str],
        novel_file: str,
    ) -> tuple[dict[str, Any], list[str]]:
        if not isinstance(data, dict):
            return data, []

        repairs: list[str] = []

        raw_cycle = data.get("cycle")
        if raw_cycle != cycle:
            if isinstance(raw_cycle, str):
                match = re.fullmatch(r"0*(\d+)", raw_cycle.strip())
                if match:
                    data["cycle"] = int(match.group(1))
                    repairs.append("cycle normalized from string to int")
            elif isinstance(raw_cycle, float) and raw_cycle.is_integer():
                data["cycle"] = int(raw_cycle)
                repairs.append("cycle normalized from numeric float to int")

        verdict = data.get("verdict")
        if isinstance(verdict, str):
            normalized_verdict = verdict.strip().upper()
            canonical_verdict = re.sub(r"[\s-]+", "_", normalized_verdict)
            if canonical_verdict in {
                "REVISE",
                "CONDITIONAL_PASS",
                "PASS_WITH_CONDITIONS",
            }:
                data["verdict"] = "FAIL"
                repairs.append(f"verdict normalized from {normalized_verdict} to FAIL")
            elif normalized_verdict != verdict:
                data["verdict"] = normalized_verdict
                repairs.append("verdict normalized")

        findings = data.get("findings")
        if findings is None:
            data["findings"] = []
            findings = data["findings"]
            repairs.append("findings defaulted to empty array")
        if isinstance(findings, list):
            for idx, finding in enumerate(findings, start=1):
                if not isinstance(finding, dict):
                    continue
                source = str(finding.get("source", "")).strip()
                severity = str(finding.get("severity", "")).strip()
                normalized_source, normalized_severity = (
                    self._normalize_full_award_finding_source_and_severity(
                        source,
                        severity,
                    )
                )
                if normalized_source and normalized_source != source:
                    finding["source"] = normalized_source
                    repairs.append(f"findings[{idx}].source normalized")
                if normalized_severity and normalized_severity != severity:
                    finding["severity"] = normalized_severity
                    repairs.append(f"findings[{idx}].severity normalized")
                if not str(finding.get("finding_id", "")).strip():
                    legacy_finding_id = str(finding.get("id", "")).strip()
                    if legacy_finding_id:
                        finding["finding_id"] = legacy_finding_id
                        repairs.append(f"findings[{idx}].finding_id mapped from id")

                chapter_id, changed = self._coerce_full_award_chapter_id(
                    finding.get("chapter_id", ""), chapter_ids
                )
                if changed:
                    finding["chapter_id"] = chapter_id
                    repairs.append(f"findings[{idx}].chapter_id normalized")

                if not str(finding.get("problem", "")).strip():
                    description = str(finding.get("description", "")).strip()
                    if description:
                        finding["problem"] = description
                        repairs.append(f"findings[{idx}].problem mapped from description")

                if not str(finding.get("rewrite_direction", "")).strip():
                    legacy_fix = str(finding.get("fix", "")).strip()
                    if legacy_fix:
                        finding["rewrite_direction"] = legacy_fix
                        repairs.append(
                            f"findings[{idx}].rewrite_direction mapped from fix"
                        )

                evidence = self._flatten_full_award_evidence(finding.get("evidence", ""))
                if evidence and evidence != finding.get("evidence"):
                    finding["evidence"] = evidence
                    repairs.append(f"findings[{idx}].evidence flattened")

                rewrite_direction = self._augment_full_award_rewrite_direction(
                    finding.get("rewrite_direction", ""),
                    str(finding.get("evidence", "")).strip(),
                    novel_file,
                )
                if rewrite_direction and rewrite_direction != finding.get("rewrite_direction"):
                    finding["rewrite_direction"] = rewrite_direction
                    repairs.append(f"findings[{idx}].rewrite_direction anchored")

                if not str(finding.get("acceptance_test", "")).strip():
                    finding["acceptance_test"] = self._synthesize_full_award_acceptance_test(
                        str(finding.get("evidence", "")).strip(),
                        novel_file,
                    )
                    repairs.append(f"findings[{idx}].acceptance_test synthesized")

        pattern_findings = data.get("pattern_findings")
        if isinstance(pattern_findings, list):
            repaired_patterns: list[dict[str, Any]] = []
            for idx, pattern in enumerate(pattern_findings, start=1):
                if not isinstance(pattern, dict):
                    continue
                severity = str(pattern.get("severity", "")).strip()
                normalized_severity = severity.upper()
                if normalized_severity and normalized_severity != severity:
                    pattern["severity"] = normalized_severity
                    repairs.append(f"pattern_findings[{idx}].severity normalized")

                pattern_id = str(pattern.get("pattern_id", "")).strip()
                if not pattern_id:
                    legacy_finding_id = str(pattern.get("finding_id", "")).strip()
                    if legacy_finding_id:
                        pattern["pattern_id"] = legacy_finding_id
                        repairs.append(
                            f"pattern_findings[{idx}].pattern_id mapped from finding_id"
                        )
                    else:
                        legacy_id = str(pattern.get("id", "")).strip()
                        if legacy_id:
                            pattern["pattern_id"] = legacy_id
                            repairs.append(
                                f"pattern_findings[{idx}].pattern_id mapped from id"
                            )
                            pattern_id = legacy_id
                        problem_basis = (
                            str(pattern.get("global_problem", "")).strip()
                            or str(pattern.get("problem", "")).strip()
                            or str(pattern.get("description", "")).strip()
                        )
                        slug = re.sub(r"[^A-Z0-9]+", "_", problem_basis.upper()).strip("_")
                        if slug and not str(pattern.get("pattern_id", "")).strip():
                            pattern["pattern_id"] = slug[:48]
                            repairs.append(
                                f"pattern_findings[{idx}].pattern_id synthesized"
                            )
                if not str(pattern.get("global_problem", "")).strip():
                    description = str(pattern.get("description", "")).strip()
                    if description:
                        pattern["global_problem"] = description
                        repairs.append(
                            f"pattern_findings[{idx}].global_problem mapped from description"
                        )

                if not isinstance(pattern.get("affected_chapters"), list):
                    legacy_affected = pattern.get("chapter_ids")
                    if isinstance(legacy_affected, list):
                        pattern["affected_chapters"] = legacy_affected
                        repairs.append(
                            f"pattern_findings[{idx}].affected_chapters mapped from chapter_ids"
                        )

                pattern_rewrite_seed = (
                    str(pattern.get("rewrite_direction", "")).strip()
                    or str(pattern.get("fix", "")).strip()
                )

                chapter_hits = pattern.get("chapter_hits")
                if not isinstance(chapter_hits, list):
                    legacy_chapter_id, changed = self._coerce_full_award_chapter_id(
                        pattern.get("chapter_id", ""),
                        chapter_ids,
                    )
                    if changed:
                        pattern["chapter_id"] = legacy_chapter_id
                        repairs.append(
                            f"pattern_findings[{idx}].chapter_id normalized"
                        )
                    if legacy_chapter_id in chapter_ids:
                        legacy_problem = (
                            str(pattern.get("problem", "")).strip()
                            or str(pattern.get("description", "")).strip()
                            or str(pattern.get("global_problem", "")).strip()
                        )
                        legacy_evidence = self._flatten_full_award_evidence(
                            pattern.get("evidence", "")
                        )
                        legacy_rewrite_direction = self._augment_full_award_rewrite_direction(
                            pattern_rewrite_seed,
                            legacy_evidence,
                            novel_file,
                        )
                        legacy_acceptance = str(
                            pattern.get("acceptance_test", "")
                        ).strip() or self._synthesize_full_award_acceptance_test(
                            legacy_evidence,
                            novel_file,
                        )
                        if (
                            legacy_problem
                            and legacy_evidence
                            and legacy_rewrite_direction
                            and legacy_acceptance
                        ):
                            chapter_hit: dict[str, Any] = {
                                "chapter_id": legacy_chapter_id,
                                "evidence": legacy_evidence,
                                "problem": legacy_problem,
                                "rewrite_direction": legacy_rewrite_direction,
                                "acceptance_test": legacy_acceptance,
                            }
                            legacy_hit_id = (
                                str(pattern.get("finding_id", "")).strip()
                                or str(pattern.get("id", "")).strip()
                            )
                            if legacy_hit_id:
                                chapter_hit["finding_id"] = legacy_hit_id
                            pattern["chapter_hits"] = [chapter_hit]
                            if not isinstance(pattern.get("affected_chapters"), list):
                                pattern["affected_chapters"] = [legacy_chapter_id]
                            repairs.append(
                                f"pattern_findings[{idx}] coerced from legacy single-hit shape"
                            )
                            chapter_hits = pattern["chapter_hits"]

                affected_chapters = pattern.get("affected_chapters")
                normalized_affected: list[str] = []
                if isinstance(affected_chapters, list):
                    for raw_chapter_id in affected_chapters:
                        chapter_id, _changed = self._coerce_full_award_chapter_id(
                            raw_chapter_id, chapter_ids
                        )
                        if chapter_id in chapter_ids and chapter_id not in normalized_affected:
                            normalized_affected.append(chapter_id)
                    if normalized_affected != affected_chapters:
                        pattern["affected_chapters"] = normalized_affected
                        repairs.append(
                            f"pattern_findings[{idx}].affected_chapters normalized"
                        )

                if not isinstance(chapter_hits, list):
                    repairs.append(f"pattern_findings[{idx}] dropped as malformed")
                    continue
                derived_affected: list[str] = []
                for hit_idx, hit in enumerate(chapter_hits, start=1):
                    if not isinstance(hit, dict):
                        continue
                    if not str(hit.get("finding_id", "")).strip():
                        legacy_hit_id = str(hit.get("id", "")).strip()
                        if legacy_hit_id:
                            hit["finding_id"] = legacy_hit_id
                            repairs.append(
                                f"pattern_findings[{idx}].chapter_hits[{hit_idx}].finding_id mapped from id"
                            )
                    severity = str(hit.get("severity", "")).strip()
                    normalized_severity = severity.upper()
                    if normalized_severity and normalized_severity != severity:
                        hit["severity"] = normalized_severity
                        repairs.append(
                            f"pattern_findings[{idx}].chapter_hits[{hit_idx}].severity normalized"
                        )

                    chapter_id, changed = self._coerce_full_award_chapter_id(
                        hit.get("chapter_id", ""), chapter_ids
                    )
                    if changed:
                        hit["chapter_id"] = chapter_id
                        repairs.append(
                            f"pattern_findings[{idx}].chapter_hits[{hit_idx}].chapter_id normalized"
                        )
                    if chapter_id in chapter_ids and chapter_id not in derived_affected:
                        derived_affected.append(chapter_id)

                    if not str(hit.get("problem", "")).strip():
                        local_description = str(hit.get("description", "")).strip()
                        if local_description:
                            hit["problem"] = local_description
                            repairs.append(
                                f"pattern_findings[{idx}].chapter_hits[{hit_idx}].problem mapped from description"
                            )
                        else:
                            local_problem = str(hit.get("local_problem", "")).strip()
                            if local_problem:
                                hit["problem"] = local_problem
                                repairs.append(
                                    f"pattern_findings[{idx}].chapter_hits[{hit_idx}].problem mapped from local_problem"
                                )
                            else:
                                local_note = str(hit.get("local_note", "")).strip()
                                if local_note:
                                    hit["problem"] = local_note
                                    repairs.append(
                                        f"pattern_findings[{idx}].chapter_hits[{hit_idx}].problem mapped from local_note"
                                    )
                        if (
                            not str(hit.get("problem", "")).strip()
                            and str(pattern.get("global_problem", "")).strip()
                        ):
                            hit["problem"] = str(pattern.get("global_problem", "")).strip()
                            repairs.append(
                                f"pattern_findings[{idx}].chapter_hits[{hit_idx}].problem defaulted from global_problem"
                            )

                    evidence = self._flatten_full_award_evidence(hit.get("evidence", ""))
                    if evidence and evidence != hit.get("evidence"):
                        hit["evidence"] = evidence
                        repairs.append(
                            f"pattern_findings[{idx}].chapter_hits[{hit_idx}].evidence flattened"
                        )

                    if not str(hit.get("rewrite_direction", "")).strip():
                        local_fix = str(hit.get("fix", "")).strip()
                        rewrite_seed = local_fix or pattern_rewrite_seed
                        if rewrite_seed:
                            hit["rewrite_direction"] = rewrite_seed
                            source = "fix" if local_fix else "pattern rewrite/fix"
                            repairs.append(
                                f"pattern_findings[{idx}].chapter_hits[{hit_idx}].rewrite_direction mapped from {source}"
                            )

                    rewrite_direction = self._augment_full_award_rewrite_direction(
                        hit.get("rewrite_direction", ""),
                        str(hit.get("evidence", "")).strip(),
                        novel_file,
                    )
                    if rewrite_direction and rewrite_direction != hit.get("rewrite_direction"):
                        hit["rewrite_direction"] = rewrite_direction
                        repairs.append(
                            f"pattern_findings[{idx}].chapter_hits[{hit_idx}].rewrite_direction anchored"
                        )

                    if not str(hit.get("acceptance_test", "")).strip():
                        hit["acceptance_test"] = self._synthesize_full_award_acceptance_test(
                            str(hit.get("evidence", "")).strip(),
                            novel_file,
                        )
                        repairs.append(
                            f"pattern_findings[{idx}].chapter_hits[{hit_idx}].acceptance_test synthesized"
                        )

                if not normalized_affected and derived_affected:
                    pattern["affected_chapters"] = derived_affected
                    repairs.append(
                        f"pattern_findings[{idx}].affected_chapters derived from chapter_hits"
                    )
                try:
                    self._validate_full_award_pattern_findings_json(
                        {"pattern_findings": [pattern]},
                        chapter_ids,
                        "pattern_repair",
                        novel_file,
                    )
                    repaired_patterns.append(pattern)
                except PipelineError:
                    repairs.append(f"pattern_findings[{idx}] dropped after failed repair")
            if repaired_patterns != pattern_findings:
                data["pattern_findings"] = repaired_patterns

        return data, repairs

    def _load_repaired_full_award_review(
        self,
        rel: str,
        cycle: int,
        chapter_ids: set[str],
        novel_file: str,
    ) -> dict[str, Any]:
        data = self._read_json(rel)
        repaired_data, repairs = self._repair_full_award_review_data(
            data,
            cycle,
            chapter_ids,
            novel_file,
        )
        if repairs:
            preserved_rel = self._preserve_invalid_artifact(rel)
            self._write_json(rel, repaired_data)
            detail_blob = " | ".join(repairs[:8])
            if len(repairs) > 8:
                detail_blob += f" | ... (+{len(repairs) - 8} more)"
            preserve_note = f" preserved={preserved_rel}" if preserved_rel else ""
            self._log(
                f"cycle={self._cpad(cycle)} full_award_review_repair applied={len(repairs)} "
                f"artifact={rel}{preserve_note} details={detail_blob}"
            )
            data = repaired_data
        return data

    def _validate_style_bible_data(self, data: dict[str, Any], rel: str) -> None:
        required_keys = [
            "character_voice_profiles",
            "dialogue_rules",
            "prose_style_profile",
            "aesthetic_risk_policy",
        ]
        for key in required_keys:
            if key not in data:
                raise PipelineError(f"{rel} missing required key: {key}")

        profiles = data.get("character_voice_profiles")
        if not isinstance(profiles, list) or not profiles:
            raise PipelineError(f"{rel} character_voice_profiles must be a non-empty array")

        for idx, row in enumerate(profiles, start=1):
            if not isinstance(row, dict):
                raise PipelineError(f"{rel} character_voice_profiles[{idx}] must be object")
            profile_required = [
                "character_id",
                "public_register",
                "private_register",
                "syntax_signature",
                "lexical_signature",
                "forbidden_generic_lines",
                "stress_tells",
                "profanity_profile",
                "contraction_level",
                "interruption_habit",
                "self_correction_tendency",
                "indirectness",
                "repetition_tolerance",
                "evasion_style",
                "sentence_completion_style",
            ]
            for key in profile_required:
                if key not in row:
                    raise PipelineError(
                        f"{rel} character_voice_profiles[{idx}] missing {key}"
                    )
            if not str(row.get("character_id", "")).strip():
                raise PipelineError(f"{rel} character_voice_profiles[{idx}] empty character_id")
            for text_key in (
                "public_register",
                "private_register",
                "syntax_signature",
                "lexical_signature",
                "forbidden_generic_lines",
                "stress_tells",
                "profanity_profile",
                "interruption_habit",
                "self_correction_tendency",
                "indirectness",
                "repetition_tolerance",
                "evasion_style",
                "sentence_completion_style",
            ):
                if not isinstance(row.get(text_key), str) or not row.get(text_key).strip():
                    raise PipelineError(
                        f"{rel} character_voice_profiles[{idx}] {text_key} must be non-empty string"
                    )
            contraction_level = row.get("contraction_level")
            if not isinstance(contraction_level, str) or contraction_level.strip().lower() not in {
                "high", "moderate", "low", "variable"
            }:
                raise PipelineError(
                    f"{rel} character_voice_profiles[{idx}] contraction_level must be "
                    f"one of: high, moderate, low, variable"
                )

        dialogue_rules = data.get("dialogue_rules")
        if not isinstance(dialogue_rules, dict):
            raise PipelineError(f"{rel} dialogue_rules must be object")
        for key in (
            "anti_transcript_cadence",
            "required_leverage_shifts_per_scene",
            "max_consecutive_low_info_replies",
            "idiolect_separation_required",
            "default_contraction_use",
        ):
            if key not in dialogue_rules:
                raise PipelineError(f"{rel} dialogue_rules missing {key}")
        if not isinstance(dialogue_rules["anti_transcript_cadence"], bool):
            raise PipelineError(f"{rel} dialogue_rules anti_transcript_cadence must be boolean")
        if not isinstance(dialogue_rules["idiolect_separation_required"], bool):
            raise PipelineError(
                f"{rel} dialogue_rules idiolect_separation_required must be boolean"
            )
        leverage_value = dialogue_rules["required_leverage_shifts_per_scene"]
        if (
            not isinstance(leverage_value, int)
            or isinstance(leverage_value, bool)
            or leverage_value < 0
        ):
            raise PipelineError(
                f"{rel} dialogue_rules required_leverage_shifts_per_scene must be integer >= 0"
            )
        low_info_value = dialogue_rules["max_consecutive_low_info_replies"]
        if (
            not isinstance(low_info_value, int)
            or isinstance(low_info_value, bool)
            or low_info_value < 2
        ):
            raise PipelineError(
                f"{rel} dialogue_rules max_consecutive_low_info_replies must be integer >= 2"
            )
        default_contraction = dialogue_rules.get("default_contraction_use")
        if not isinstance(default_contraction, str) or not default_contraction.strip():
            raise PipelineError(
                f"{rel} dialogue_rules default_contraction_use must be non-empty string"
            )

        prose_style = data.get("prose_style_profile")
        if not isinstance(prose_style, dict):
            raise PipelineError(f"{rel} prose_style_profile must be object")
        for key in (
            "narrative_tense",
            "narrative_distance",
            "rhythm_target",
            "sensory_bias",
            "diction",
            "forbidden_drift_patterns",
            "chapter_texture_variance",
        ):
            if key not in prose_style:
                raise PipelineError(f"{rel} prose_style_profile missing {key}")
        for text_key in ("narrative_tense", "narrative_distance", "rhythm_target", "diction", "chapter_texture_variance"):
            if not isinstance(prose_style[text_key], str) or not prose_style[text_key].strip():
                raise PipelineError(
                    f"{rel} prose_style_profile {text_key} must be non-empty string"
                )
        for list_key in ("sensory_bias", "forbidden_drift_patterns"):
            value = prose_style[list_key]
            if not isinstance(value, list) or not value:
                raise PipelineError(
                    f"{rel} prose_style_profile {list_key} must be non-empty array"
                )
            if not all(isinstance(x, str) and x.strip() for x in value):
                raise PipelineError(
                    f"{rel} prose_style_profile {list_key} must contain non-empty strings"
                )

        aesthetic_policy = data.get("aesthetic_risk_policy")
        if not isinstance(aesthetic_policy, dict):
            raise PipelineError(f"{rel} aesthetic_risk_policy must be object")
        for key in (
            "sanitization_disallowed",
            "dark_content_allowed_when_character_true",
            "profanity_allowed_when_scene_pressure_warrants",
            "euphemism_penalty",
            "creative_risk_policy",
        ):
            if key not in aesthetic_policy:
                raise PipelineError(f"{rel} aesthetic_risk_policy missing {key}")
        for bool_key in (
            "sanitization_disallowed",
            "dark_content_allowed_when_character_true",
            "profanity_allowed_when_scene_pressure_warrants",
        ):
            if not isinstance(aesthetic_policy[bool_key], bool):
                raise PipelineError(
                    f"{rel} aesthetic_risk_policy {bool_key} must be boolean"
                )
        for text_key in ("euphemism_penalty", "creative_risk_policy"):
            if not isinstance(aesthetic_policy[text_key], str) or not aesthetic_policy[
                text_key
            ].strip():
                raise PipelineError(
                    f"{rel} aesthetic_risk_policy {text_key} must be non-empty string"
                )

    def _write_chapter_spec_files(self) -> None:
        for spec in self.chapter_specs:
            rel = f"outline/chapter_specs/{spec.chapter_id}.json"
            payload = {
                "chapter_id": spec.chapter_id,
                "chapter_number": spec.chapter_number,
                "projected_min_words": spec.projected_min_words,
                "chapter_engine": spec.chapter_engine,
                "pressure_source": spec.pressure_source,
                "state_shift": spec.state_shift,
                "texture_mode": spec.texture_mode,
                "scene_count_target": spec.scene_count_target,
                "objective": spec.objective,
                "conflict": spec.conflict,
                "consequence": spec.consequence,
                "must_land_beats": spec.must_land_beats,
            }
            if spec.secondary_character_beats:
                payload["secondary_character_beats"] = spec.secondary_character_beats
            if spec.setups_to_plant:
                payload["setups_to_plant"] = spec.setups_to_plant
            if spec.payoffs_to_land:
                payload["payoffs_to_land"] = spec.payoffs_to_land
            self._write_json(rel, payload)

    def _validate_chapter_heading(self, chapter_path: Path, chapter_number: int) -> None:
        if not chapter_path.is_file():
            raise PipelineError(f"missing chapter file: {chapter_path}")
        expected = f"# Chapter {chapter_number}"
        for raw in chapter_path.read_text(encoding="utf-8").splitlines():
            stripped = raw.strip()
            if not stripped:
                continue
            if stripped != expected:
                raise PipelineError(
                    f"heading contract violation in {chapter_path}: expected '{expected}', found '{stripped}'"
                )
            return
        raise PipelineError(f"chapter file has no non-empty content: {chapter_path}")

    def _count_words_file(self, chapter_path: Path) -> int:
        if not chapter_path.is_file():
            raise PipelineError(f"missing chapter file for word count: {chapter_path}")
        text = chapter_path.read_text(encoding="utf-8")
        return len(re.findall(r"\S+", text))

    def _canonical_review_lens(self, value: str) -> str:
        return str(value).strip().lower()

    def _canonical_finding_source_name(self, value: str) -> str:
        return str(value).strip().lower()

    def _extract_review_verdicts(self, data: dict[str, Any], rel: str) -> dict[str, str]:
        verdicts = data.get("verdicts")
        if not isinstance(verdicts, dict):
            raise PipelineError(f"{rel} missing verdicts object")
        primary_value = verdicts.get(PRIMARY_REVIEW_LENS)
        normalized = {
            PRIMARY_REVIEW_LENS: primary_value,
            "craft": verdicts.get("craft"),
            "dialogue": verdicts.get("dialogue"),
            "prose": verdicts.get("prose"),
        }
        for key, value in normalized.items():
            if value not in VERDICT_VALUES:
                raise PipelineError(f"{rel} invalid verdict {key}: {value}")
        return normalized

    def _validate_chapter_review_json(
        self,
        data: dict[str, Any],
        chapter_id: str,
        rel: str,
        chapter_file: str,
    ) -> None:
        if not isinstance(data, dict):
            raise PipelineError(f"{rel} must be a JSON object")
        if data.get("chapter_id") != chapter_id:
            raise PipelineError(f"{rel} chapter_id mismatch (expected {chapter_id})")

        verdicts = self._extract_review_verdicts(data, rel)

        findings = data.get("findings")
        if not isinstance(findings, list):
            raise PipelineError(f"{rel} findings must be an array")
        for idx, finding in enumerate(findings, start=1):
            if not isinstance(finding, dict):
                raise PipelineError(f"{rel} finding #{idx} must be an object")
            required = [
                "finding_id",
                "source",
                "severity",
                "chapter_id",
                "evidence",
                "problem",
                "rewrite_direction",
                "acceptance_test",
            ]
            for key in required:
                if key not in finding or not str(finding[key]).strip():
                    raise PipelineError(f"{rel} finding #{idx} missing {key}")
            source = self._canonical_finding_source_name(finding["source"])
            if source not in {PRIMARY_REVIEW_LENS, "craft", "dialogue", "prose"}:
                raise PipelineError(f"{rel} finding #{idx} invalid source")
            if finding["severity"] not in FULL_AWARD_SEVERITY_VALUES:
                raise PipelineError(f"{rel} finding #{idx} invalid severity")
            if finding["chapter_id"] != chapter_id:
                raise PipelineError(
                    f"{rel} finding #{idx} chapter_id mismatch ({finding['chapter_id']})"
                )
            evidence = self._normalize_evidence_field(finding["evidence"])
            if not self._evidence_citations_valid(evidence, chapter_file):
                raise PipelineError(
                    f"{rel} finding #{idx} evidence must cite {chapter_file}:<line>"
                )
            self._validate_rewrite_direction(
                rewrite_direction=str(finding["rewrite_direction"]),
                target_file=chapter_file,
                rel=rel,
                finding_index=idx,
            )
            self._validate_acceptance_test(
                acceptance_test=str(finding["acceptance_test"]),
                target_file=chapter_file,
                rel=rel,
                finding_index=idx,
            )

        all_pass = all(
            verdicts[k] == "PASS" for k in (PRIMARY_REVIEW_LENS, "craft", "dialogue", "prose")
        )
        if all_pass and findings:
            raise PipelineError(
                f"{rel} is logically inconsistent: all verdicts PASS but findings are present"
            )
        if (not all_pass) and (not findings):
            raise PipelineError(
                f"{rel} is logically inconsistent: at least one verdict is FAIL but findings are empty"
            )

        summary = data.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise PipelineError(f"{rel} missing non-empty summary")

    def _repair_chapter_review_data(
        self,
        data: dict[str, Any],
        chapter_id: str,
    ) -> tuple[dict[str, Any], list[str]]:
        if not isinstance(data, dict):
            return data, []

        repairs: list[str] = []
        expected_ids = {chapter_id}

        normalized_chapter_id, changed = self._coerce_full_award_chapter_id(
            data.get("chapter_id", ""),
            expected_ids,
        )
        if changed:
            data["chapter_id"] = normalized_chapter_id
            repairs.append("chapter_id normalized")

        verdicts = data.get("verdicts")
        if isinstance(verdicts, dict):
            for lens in (PRIMARY_REVIEW_LENS, "craft", "dialogue", "prose"):
                value = verdicts.get(lens)
                if isinstance(value, str):
                    normalized = value.strip().upper()
                    if normalized != value:
                        verdicts[lens] = normalized
                        repairs.append(f"verdicts.{lens} normalized")

        findings = data.get("findings")
        if isinstance(findings, list):
            for idx, finding in enumerate(findings, start=1):
                if not isinstance(finding, dict):
                    continue
                source = str(finding.get("source", "")).strip()
                canonical_source = self._canonical_finding_source_name(source)
                if canonical_source and canonical_source != source:
                    finding["source"] = canonical_source
                    repairs.append(f"findings[{idx}].source normalized")

                severity = str(finding.get("severity", "")).strip()
                normalized_severity = severity.upper()
                if normalized_severity != severity and normalized_severity:
                    finding["severity"] = normalized_severity
                    repairs.append(f"findings[{idx}].severity normalized")

                finding_chapter_id, finding_changed = self._coerce_full_award_chapter_id(
                    finding.get("chapter_id", ""),
                    expected_ids,
                )
                if finding_changed:
                    finding["chapter_id"] = finding_chapter_id
                    repairs.append(f"findings[{idx}].chapter_id normalized")

                if not str(finding.get("problem", "")).strip():
                    description = str(finding.get("description", "")).strip()
                    if description:
                        finding["problem"] = description
                        repairs.append(f"findings[{idx}].problem mapped from description")

                evidence = self._normalize_evidence_field(finding.get("evidence", ""))
                if evidence and evidence != finding.get("evidence"):
                    finding["evidence"] = evidence
                    repairs.append(f"findings[{idx}].evidence flattened")

        summary = data.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            verdict_bits: list[str] = []
            if isinstance(verdicts, dict):
                for lens in (PRIMARY_REVIEW_LENS, "craft", "dialogue", "prose"):
                    verdict = str(verdicts.get(lens, "")).strip().upper()
                    if verdict:
                        verdict_bits.append(f"{lens}={verdict}")
            finding_count = len(findings) if isinstance(findings, list) else 0
            summary_parts: list[str] = []
            if verdict_bits:
                summary_parts.append("Verdicts: " + ", ".join(verdict_bits))
            summary_parts.append(f"Findings: {finding_count}.")
            data["summary"] = " ".join(summary_parts)
            repairs.append("summary synthesized from verdicts/findings")

        return data, repairs

    def _load_repaired_chapter_review(
        self,
        rel: str,
        chapter_id: str,
        chapter_file: str,
    ) -> dict[str, Any]:
        data = self._read_json(rel)
        repaired_data, repairs = self._repair_chapter_review_data(data, chapter_id)
        if repairs:
            preserved_rel = self._preserve_invalid_artifact(rel)
            self._write_json(rel, repaired_data)
            detail_blob = " | ".join(repairs[:8])
            if len(repairs) > 8:
                detail_blob += f" | ... (+{len(repairs) - 8} more)"
            preserve_note = f" preserved={preserved_rel}" if preserved_rel else ""
            self._log(
                f"chapter_review_repair chapter={chapter_id} artifact={rel}"
                f"{preserve_note} details={detail_blob}"
            )
            data = repaired_data
        self._validate_chapter_review_json(data, chapter_id, rel, chapter_file)
        return data

    def _validate_full_award_review_json(
        self,
        data: dict[str, Any],
        cycle: int,
        chapter_ids: set[str],
        rel: str,
        novel_file: str,
    ) -> None:
        if not isinstance(data, dict):
            raise PipelineError(f"{rel} must be a JSON object")
        if data.get("cycle") != cycle:
            raise PipelineError(f"{rel} cycle mismatch (expected {cycle})")
        if data.get("verdict") not in VERDICT_VALUES:
            raise PipelineError(f"{rel} verdict must be PASS or FAIL")
        summary = data.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise PipelineError(f"{rel} missing non-empty summary")

        findings = data.get("findings")
        if not isinstance(findings, list):
            raise PipelineError(f"{rel} findings must be an array")
        for idx, finding in enumerate(findings, start=1):
            if not isinstance(finding, dict):
                raise PipelineError(f"{rel} finding #{idx} must be object")
            required = [
                "finding_id",
                "severity",
                "chapter_id",
                "evidence",
                "problem",
                "rewrite_direction",
                "acceptance_test",
            ]
            for key in required:
                if key not in finding or not str(finding[key]).strip():
                    raise PipelineError(f"{rel} finding #{idx} missing {key}")
            if finding["severity"] not in FULL_AWARD_SEVERITY_VALUES:
                raise PipelineError(f"{rel} finding #{idx} invalid severity")
            if finding["chapter_id"] not in chapter_ids:
                raise PipelineError(
                    f"{rel} finding #{idx} chapter_id must map to chapter_XX in this manuscript"
                )
            evidence = self._normalize_evidence_field(finding["evidence"])
            if not self._evidence_citations_valid(evidence, novel_file):
                raise PipelineError(
                    f"{rel} finding #{idx} evidence must cite {novel_file}:<line>"
                )
            self._validate_rewrite_direction(
                rewrite_direction=str(finding["rewrite_direction"]),
                target_file=novel_file,
                rel=rel,
                finding_index=idx,
            )
            self._validate_acceptance_test(
                acceptance_test=str(finding["acceptance_test"]),
                target_file=novel_file,
                rel=rel,
                finding_index=idx,
            )

        self._validate_full_award_pattern_findings_json(
            data,
            chapter_ids,
            rel,
            novel_file,
        )

        has_pattern_hits = self._full_award_has_pattern_hits(data)

        if data["verdict"] == "PASS" and (findings or has_pattern_hits):
            raise PipelineError(
                f"{rel} is logically inconsistent: verdict PASS but findings are present"
            )
        if data["verdict"] == "FAIL" and not findings and not has_pattern_hits:
            raise PipelineError(
                f"{rel} is logically inconsistent: verdict FAIL but findings are empty"
            )

    def _validate_full_award_pattern_findings_json(
        self,
        data: dict[str, Any],
        chapter_ids: set[str],
        rel: str,
        novel_file: str,
    ) -> None:
        pattern_findings = data.get("pattern_findings")
        if pattern_findings is None:
            return
        if not isinstance(pattern_findings, list):
            raise PipelineError(f"{rel} pattern_findings must be an array when present")

        for idx, pattern in enumerate(pattern_findings, start=1):
            pattern_ref = f"pattern_findings[{idx}]"
            if not isinstance(pattern, dict):
                raise PipelineError(f"{rel} {pattern_ref} must be an object")

            pattern_id = str(pattern.get("pattern_id", "")).strip()
            severity = str(pattern.get("severity", "")).strip().upper()
            global_problem = str(pattern.get("global_problem", "")).strip()
            affected_chapters = pattern.get("affected_chapters")
            chapter_hits = pattern.get("chapter_hits")

            if not pattern_id:
                raise PipelineError(f"{rel} {pattern_ref} missing pattern_id")
            if severity not in FULL_AWARD_SEVERITY_VALUES:
                raise PipelineError(f"{rel} {pattern_ref} invalid severity")
            if not global_problem:
                raise PipelineError(f"{rel} {pattern_ref} missing global_problem")
            if not isinstance(affected_chapters, list) or not affected_chapters:
                raise PipelineError(f"{rel} {pattern_ref} affected_chapters must be a non-empty array")
            if not isinstance(chapter_hits, list) or not chapter_hits:
                raise PipelineError(f"{rel} {pattern_ref} chapter_hits must be a non-empty array")

            claimed_chapters: set[str] = set()
            for raw_chapter_id in affected_chapters:
                chapter_id = str(raw_chapter_id).strip()
                if chapter_id not in chapter_ids:
                    raise PipelineError(
                        f"{rel} {pattern_ref}.affected_chapters includes unknown chapter_id {chapter_id}"
                    )
                claimed_chapters.add(chapter_id)

            hit_chapters: set[str] = set()
            for hit_idx, hit in enumerate(chapter_hits, start=1):
                hit_ref = f"{pattern_ref}.chapter_hits[{hit_idx}]"
                if not isinstance(hit, dict):
                    raise PipelineError(f"{rel} {hit_ref} must be an object")

                chapter_id = str(hit.get("chapter_id", "")).strip()
                hit_severity = str(hit.get("severity", severity)).strip().upper()
                if chapter_id not in chapter_ids:
                    raise PipelineError(
                        f"{rel} {hit_ref} chapter_id must map to chapter_XX in this manuscript"
                    )
                if hit_severity not in FULL_AWARD_SEVERITY_VALUES:
                    raise PipelineError(f"{rel} {hit_ref} invalid severity")

                for key in ("evidence", "problem", "rewrite_direction", "acceptance_test"):
                    if not str(hit.get(key, "")).strip():
                        raise PipelineError(f"{rel} {hit_ref} missing {key}")

                evidence = self._normalize_evidence_field(hit["evidence"])
                if not self._evidence_citations_valid(evidence, novel_file):
                    raise PipelineError(
                        f"{rel} {hit_ref} evidence must cite {novel_file}:<line>"
                    )
                self._validate_rewrite_direction(
                    rewrite_direction=str(hit["rewrite_direction"]),
                    target_file=novel_file,
                    rel=rel,
                    finding_index=hit_idx,
                )
                self._validate_acceptance_test(
                    acceptance_test=str(hit["acceptance_test"]),
                    target_file=novel_file,
                    rel=rel,
                    finding_index=hit_idx,
                )
                hit_chapters.add(chapter_id)


    def _full_award_has_pattern_hits(self, data: dict[str, Any]) -> bool:
        pattern_findings = data.get("pattern_findings")
        if not isinstance(pattern_findings, list):
            return False
        for pattern in pattern_findings:
            if not isinstance(pattern, dict):
                continue
            chapter_hits = pattern.get("chapter_hits")
            if not isinstance(chapter_hits, list):
                continue
            if any(isinstance(hit, dict) for hit in chapter_hits):
                return True
        return False

    def _expand_full_award_pattern_findings(
        self,
        *,
        full_review: dict[str, Any],
        cycle: int,
        chapter_ids: set[str],
        rel: str,
        novel_file: str,
    ) -> list[dict[str, Any]]:
        pattern_findings = full_review.get("pattern_findings")
        if pattern_findings is None:
            return []
        if not isinstance(pattern_findings, list):
            self._record_validation_warning(
                stage="aggregate_findings",
                cycle=cycle,
                chapter_id=None,
                artifact=rel,
                reason="pattern_findings must be an array when present; ignoring malformed value",
                action="ignored_malformed_full_award_pattern_findings",
            )
            return []

        out: list[dict[str, Any]] = []
        for idx, pattern in enumerate(pattern_findings, start=1):
            pattern_ref = f"pattern_findings[{idx}]"
            if not isinstance(pattern, dict):
                self._record_validation_warning(
                    stage="aggregate_findings",
                    cycle=cycle,
                    chapter_id=None,
                    artifact=rel,
                    reason=f"{pattern_ref} must be an object; ignoring malformed pattern",
                    action="ignored_malformed_full_award_pattern",
                )
                continue

            pattern_id = str(pattern.get("pattern_id", "")).strip()
            global_problem = str(pattern.get("global_problem", "")).strip()
            global_rewrite_principles = str(
                pattern.get("global_rewrite_principles", "")
            ).strip()
            default_severity = str(pattern.get("severity", "")).strip().upper()
            chapter_hits = pattern.get("chapter_hits")
            affected_chapters = pattern.get("affected_chapters")

            if (
                not pattern_id
                or default_severity not in FULL_AWARD_SEVERITY_VALUES
                or not global_problem
            ):
                self._record_validation_warning(
                    stage="aggregate_findings",
                    cycle=cycle,
                    chapter_id=None,
                    artifact=rel,
                    reason=(
                        f"{pattern_ref} is missing pattern_id, severity, or global_problem; "
                        "ignoring malformed pattern"
                    ),
                    action="ignored_malformed_full_award_pattern",
                )
                continue
            if not isinstance(chapter_hits, list):
                self._record_validation_warning(
                    stage="aggregate_findings",
                    cycle=cycle,
                    chapter_id=None,
                    artifact=rel,
                    reason=f"{pattern_ref}.chapter_hits must be an array; ignoring malformed pattern",
                    action="ignored_malformed_full_award_pattern",
                )
                continue

            claimed_chapters: set[str] = set()
            if affected_chapters is None:
                self._record_validation_warning(
                    stage="aggregate_findings",
                    cycle=cycle,
                    chapter_id=None,
                    artifact=rel,
                    reason=(
                        f"{pattern_ref} omitted affected_chapters; pattern hits will still expand, "
                        "but coverage cannot be checked"
                    ),
                    action="missing_pattern_affected_chapters",
                )
            elif not isinstance(affected_chapters, list):
                self._record_validation_warning(
                    stage="aggregate_findings",
                    cycle=cycle,
                    chapter_id=None,
                    artifact=rel,
                    reason=f"{pattern_ref}.affected_chapters must be an array; ignoring coverage claim",
                    action="ignored_invalid_pattern_coverage_claim",
                )
            else:
                for raw_chapter_id in affected_chapters:
                    claimed_chapter_id = str(raw_chapter_id).strip()
                    if claimed_chapter_id not in chapter_ids:
                        self._record_validation_warning(
                            stage="aggregate_findings",
                            cycle=cycle,
                            chapter_id=None,
                            artifact=rel,
                            reason=(
                                f"{pattern_ref}.affected_chapters includes unknown chapter_id "
                                f"{claimed_chapter_id}; ignoring that coverage entry"
                            ),
                            action="ignored_invalid_pattern_coverage_entry",
                        )
                        continue
                    claimed_chapters.add(claimed_chapter_id)

            hit_chapters: set[str] = set()
            for hit_idx, hit in enumerate(chapter_hits, start=1):
                hit_ref = f"{pattern_ref}.chapter_hits[{hit_idx}]"
                if not isinstance(hit, dict):
                    self._record_validation_warning(
                        stage="aggregate_findings",
                        cycle=cycle,
                        chapter_id=None,
                        artifact=rel,
                        reason=f"{hit_ref} must be an object; ignoring malformed chapter hit",
                        action="ignored_malformed_full_award_pattern_hit",
                    )
                    continue

                chapter_id = str(hit.get("chapter_id", "")).strip()
                severity = str(hit.get("severity", default_severity)).strip().upper()
                evidence = str(hit.get("evidence", "")).strip()
                problem = str(hit.get("problem", "")).strip() or global_problem
                rewrite_direction = str(hit.get("rewrite_direction", "")).strip()
                if not rewrite_direction and global_rewrite_principles:
                    rewrite_direction = global_rewrite_principles
                acceptance_test = str(hit.get("acceptance_test", "")).strip()
                finding_id = str(hit.get("finding_id", "")).strip() or f"{pattern_id}_{chapter_id}"

                if chapter_id not in chapter_ids:
                    self._record_validation_warning(
                        stage="aggregate_findings",
                        cycle=cycle,
                        chapter_id=None,
                        artifact=rel,
                        reason=(
                            f"{hit_ref} chapter_id must map to a chapter in this manuscript; "
                            "ignoring malformed chapter hit"
                        ),
                        action="ignored_malformed_full_award_pattern_hit",
                    )
                    continue
                if severity not in FULL_AWARD_SEVERITY_VALUES:
                    self._record_validation_warning(
                        stage="aggregate_findings",
                        cycle=cycle,
                        chapter_id=chapter_id,
                        artifact=rel,
                        reason=f"{hit_ref} has invalid severity {severity}; ignoring malformed chapter hit",
                        action="ignored_malformed_full_award_pattern_hit",
                    )
                    continue
                if not evidence or not problem or not rewrite_direction or not acceptance_test:
                    self._record_validation_warning(
                        stage="aggregate_findings",
                        cycle=cycle,
                        chapter_id=chapter_id or None,
                        artifact=rel,
                        reason=(
                            f"{hit_ref} is missing evidence, problem, rewrite_direction, or acceptance_test; "
                            "ignoring malformed chapter hit"
                        ),
                        action="ignored_malformed_full_award_pattern_hit",
                    )
                    continue

                normalized_evidence = self._normalize_evidence_field(evidence)
                if not self._evidence_citations_valid(normalized_evidence, novel_file):
                    self._record_validation_warning(
                        stage="aggregate_findings",
                        cycle=cycle,
                        chapter_id=chapter_id,
                        artifact=rel,
                        reason=(
                            f"{hit_ref} evidence must cite {novel_file}:<line>; "
                            "ignoring malformed chapter hit"
                        ),
                        action="ignored_malformed_full_award_pattern_hit",
                    )
                    continue

                try:
                    self._validate_rewrite_direction(
                        rewrite_direction=rewrite_direction,
                        target_file=novel_file,
                        rel=rel,
                        finding_index=hit_idx,
                    )
                    self._validate_acceptance_test(
                        acceptance_test=acceptance_test,
                        target_file=novel_file,
                        rel=rel,
                        finding_index=hit_idx,
                    )
                except PipelineError as exc:
                    self._record_validation_warning(
                        stage="aggregate_findings",
                        cycle=cycle,
                        chapter_id=chapter_id,
                        artifact=rel,
                        reason=f"{hit_ref} invalid local contract: {exc}",
                        action="ignored_malformed_full_award_pattern_hit",
                    )
                    continue

                hit_chapters.add(chapter_id)
                out.append(
                    self._normalize_finding(
                        {
                            "finding_id": finding_id,
                            "severity": severity,
                            "chapter_id": chapter_id,
                            "evidence": normalized_evidence,
                            "problem": problem,
                            "rewrite_direction": rewrite_direction,
                            "acceptance_test": acceptance_test,
                        },
                        cycle,
                        force_source="award_global",
                    )
                )

            if claimed_chapters:
                missing_chapters = sorted(claimed_chapters - hit_chapters)
                if missing_chapters:
                    self._record_validation_warning(
                        stage="aggregate_findings",
                        cycle=cycle,
                        chapter_id=None,
                        artifact=rel,
                        reason=(
                            f"{pattern_ref} claims coverage for {', '.join(missing_chapters)} "
                            "without actionable chapter_hits; partial fan-out only"
                        ),
                        action="underfan_full_award_pattern_claim",
                    )
        return out

    def _validate_cross_chapter_audit_json(
        self,
        data: dict[str, Any],
        cycle: int,
        chapter_ids: set[str],
        rel: str,
        novel_file: str,
    ) -> None:
        if not isinstance(data, dict):
            raise PipelineError(f"{rel} must be a JSON object")
        if data.get("cycle") != cycle:
            raise PipelineError(f"{rel} cycle mismatch (expected {cycle})")
        summary = data.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise PipelineError(f"{rel} missing non-empty summary")

        seen_ids: set[str] = set()
        for array_name, expected_category in (
            ("redundancy_findings", "redundancy"),
            ("consistency_findings", "consistency"),
        ):
            findings = data.get(array_name)
            if not isinstance(findings, list):
                raise PipelineError(f"{rel} {array_name} must be an array")
            for idx, finding in enumerate(findings, start=1):
                if not isinstance(finding, dict):
                    raise PipelineError(f"{rel} {array_name}[{idx}] must be object")
                required = [
                    "finding_id",
                    "category",
                    "subcategory",
                    "severity",
                    "chapter_id",
                    "evidence",
                    "problem",
                    "rewrite_direction",
                    "acceptance_test",
                ]
                for key in required:
                    if key not in finding or not str(finding[key]).strip():
                        raise PipelineError(f"{rel} {array_name}[{idx}] missing {key}")
                if str(finding["category"]).strip().lower() != expected_category:
                    raise PipelineError(
                        f"{rel} {array_name}[{idx}] category must be {expected_category}"
                    )
                if finding["severity"] not in SEVERITY_VALUES:
                    raise PipelineError(f"{rel} {array_name}[{idx}] invalid severity")
                if finding["chapter_id"] not in chapter_ids:
                    raise PipelineError(
                        f"{rel} {array_name}[{idx}] chapter_id must map to chapter_XX in this manuscript"
                    )
                evidence = self._normalize_evidence_field(finding["evidence"])
                if not self._evidence_citations_valid(evidence, novel_file):
                    raise PipelineError(
                        f"{rel} {array_name}[{idx}] evidence must cite {novel_file}:<line>"
                    )
                self._validate_rewrite_direction(
                    rewrite_direction=str(finding["rewrite_direction"]),
                    target_file=novel_file,
                    rel=rel,
                    finding_index=idx,
                )
                self._validate_acceptance_test(
                    acceptance_test=str(finding["acceptance_test"]),
                    target_file=novel_file,
                    rel=rel,
                    finding_index=idx,
                )
                finding_id = str(finding["finding_id"]).strip()
                if finding_id in seen_ids:
                    raise PipelineError(
                        f"{rel} duplicate finding_id across audit arrays: {finding_id}"
                    )
                seen_ids.add(finding_id)

    def _repair_cross_chapter_audit_data(
        self,
        data: dict[str, Any],
        cycle: int,
        chapter_ids: set[str],
    ) -> tuple[dict[str, Any], list[str]]:
        if not isinstance(data, dict):
            return data, []

        repairs: list[str] = []
        raw_cycle = data.get("cycle")
        if isinstance(raw_cycle, str):
            stripped = raw_cycle.strip()
            if stripped.isdigit():
                coerced = int(stripped)
                if coerced != raw_cycle:
                    data["cycle"] = coerced
                    repairs.append("cycle coerced to integer")

        seen_ids: dict[str, int] = {}
        for array_name, expected_category in (
            ("redundancy_findings", "redundancy"),
            ("consistency_findings", "consistency"),
        ):
            findings = data.get(array_name)
            if not isinstance(findings, list):
                continue
            for idx, finding in enumerate(findings, start=1):
                if not isinstance(finding, dict):
                    continue
                finding_id = str(finding.get("finding_id", "")).strip()
                if not finding_id:
                    finding_id = f"{expected_category}_{idx}"
                    finding["finding_id"] = finding_id
                    repairs.append(f"{array_name}[{idx}].finding_id synthesized")

                raw_category = str(finding.get("category", "")).strip()
                category = raw_category.lower()
                if raw_category != expected_category:
                    finding["category"] = expected_category
                    repairs.append(f"{array_name}[{idx}].category normalized")

                subcategory = str(finding.get("subcategory", "")).strip()
                if not subcategory:
                    finding["subcategory"] = "unspecified"
                    repairs.append(f"{array_name}[{idx}].subcategory synthesized")

                severity = str(finding.get("severity", "")).strip()
                normalized_severity = severity.upper()
                if normalized_severity and normalized_severity != severity:
                    finding["severity"] = normalized_severity
                    repairs.append(f"{array_name}[{idx}].severity normalized")

                normalized_chapter_id, changed = self._coerce_full_award_chapter_id(
                    finding.get("chapter_id", ""),
                    chapter_ids,
                )
                if changed:
                    finding["chapter_id"] = normalized_chapter_id
                    repairs.append(f"{array_name}[{idx}].chapter_id normalized")

                if not str(finding.get("problem", "")).strip():
                    description = str(finding.get("description", "")).strip()
                    if description:
                        finding["problem"] = description
                        repairs.append(f"{array_name}[{idx}].problem mapped from description")

                evidence = self._normalize_evidence_field(finding.get("evidence", ""))
                if evidence and evidence != finding.get("evidence"):
                    finding["evidence"] = evidence
                    repairs.append(f"{array_name}[{idx}].evidence flattened")

                if not str(finding.get("rewrite_direction", "")).strip():
                    revision_directive = str(
                        finding.get("revision_directive", "")
                    ).strip()
                    if revision_directive:
                        finding["rewrite_direction"] = revision_directive
                        repairs.append(
                            f"{array_name}[{idx}].rewrite_direction mapped from revision_directive"
                        )

                base_id = str(finding.get("finding_id", "")).strip()
                if base_id:
                    dup_count = seen_ids.get(base_id, 0)
                    if dup_count:
                        finding["finding_id"] = f"{base_id}_{dup_count + 1}"
                        repairs.append(f"{array_name}[{idx}].finding_id deduplicated")
                    seen_ids[base_id] = dup_count + 1

        summary = data.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            redundancy_count = len(data.get("redundancy_findings", [])) if isinstance(
                data.get("redundancy_findings"), list
            ) else 0
            consistency_count = len(data.get("consistency_findings", [])) if isinstance(
                data.get("consistency_findings"), list
            ) else 0
            data["summary"] = (
                f"Cross-chapter audit for cycle {cycle}. "
                f"Redundancy findings: {redundancy_count}. "
                f"Consistency findings: {consistency_count}."
            )
            repairs.append("summary synthesized from finding counts")

        return data, repairs

    def _load_repaired_cross_chapter_audit(
        self,
        rel: str,
        cycle: int,
        chapter_ids: set[str],
        novel_file: str,
    ) -> dict[str, Any]:
        data = self._read_json(rel)
        repaired_data, repairs = self._repair_cross_chapter_audit_data(
            data,
            cycle,
            chapter_ids,
        )
        if repairs:
            preserved_rel = self._preserve_invalid_artifact(rel)
            self._write_json(rel, repaired_data)
            detail_blob = " | ".join(repairs[:8])
            if len(repairs) > 8:
                detail_blob += f" | ... (+{len(repairs) - 8} more)"
            preserve_note = f" preserved={preserved_rel}" if preserved_rel else ""
            self._log(
                f"cross_chapter_audit_repair artifact={rel}"
                f"{preserve_note} details={detail_blob}"
            )
            data = repaired_data
        self._validate_cross_chapter_audit_json(
            data,
            cycle,
            chapter_ids,
            rel,
            novel_file,
        )
        return data

    def _fallback_cross_chapter_audit_payload(self, cycle: int) -> dict[str, Any]:
        return {
            "cycle": cycle,
            "summary": "Cross-chapter audit could not be completed; fallback with no findings.",
            "redundancy_findings": [],
            "consistency_findings": [],
        }

    def _is_cross_chapter_audit_fallback_payload(
        self, data: dict[str, Any], cycle: int
    ) -> bool:
        if not isinstance(data, dict):
            return False
        expected = self._fallback_cross_chapter_audit_payload(cycle)
        return (
            data.get("cycle") == expected["cycle"]
            and data.get("summary") == expected["summary"]
            and data.get("redundancy_findings") == expected["redundancy_findings"]
            and data.get("consistency_findings") == expected["consistency_findings"]
        )

    def _normalize_local_window_category(self, value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")
        return LOCAL_WINDOW_CATEGORY_ALIASES.get(normalized, normalized)

    def _default_local_window_pass_hint(self, category: str) -> str | None:
        return LOCAL_WINDOW_PASS_HINT_BY_CATEGORY.get(
            self._normalize_local_window_category(category)
        )

    def _local_window_category_requirements(self, category: str) -> set[str]:
        normalized = self._normalize_local_window_category(category)
        if normalized == "factual_coherence":
            return {"related_chapter_ids", "boundary_span", "counterpart_evidence"}
        if normalized == "boundary_local_voice_drift":
            return {"related_chapter_ids", "boundary_span"}
        if normalized == "redundant_scene_functions":
            return {"related_chapter_ids"}
        return set()

    def _validate_local_window_audit_json(
        self,
        data: dict[str, Any],
        cycle: int,
        chapter_ids: set[str],
        rel: str,
        novel_file: str,
    ) -> None:
        if not isinstance(data, dict):
            raise PipelineError(f"{rel} must be a JSON object")
        if data.get("cycle") != cycle:
            raise PipelineError(f"{rel} cycle mismatch (expected {cycle})")
        window_id = str(data.get("window_id", "")).strip()
        if not window_id:
            raise PipelineError(f"{rel} missing non-empty window_id")
        chapters_reviewed = data.get("chapters_reviewed")
        if not isinstance(chapters_reviewed, list) or len(chapters_reviewed) < 2:
            raise PipelineError(f"{rel} chapters_reviewed must contain at least 2 chapters")
        chapters_reviewed_set: set[str] = set()
        for idx, chapter_id in enumerate(chapters_reviewed, start=1):
            chapter_id = str(chapter_id).strip()
            if chapter_id not in chapter_ids:
                raise PipelineError(
                    f"{rel} chapters_reviewed[{idx}] must map to chapter_XX in this manuscript"
                )
            chapters_reviewed_set.add(chapter_id)
        summary = data.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise PipelineError(f"{rel} missing non-empty summary")
        findings = data.get("findings")
        if not isinstance(findings, list):
            raise PipelineError(f"{rel} findings must be an array")
        seen_ids: set[str] = set()
        for idx, finding in enumerate(findings, start=1):
            if not isinstance(finding, dict):
                raise PipelineError(f"{rel} findings[{idx}] must be object")
            required = [
                "finding_id",
                "category",
                "subcategory",
                "severity",
                "chapter_id",
                "evidence",
                "problem",
                "rewrite_direction",
                "acceptance_test",
                "fix_owner_reason",
                "pass_hint",
            ]
            for key in required:
                if key not in finding or not str(finding[key]).strip():
                    raise PipelineError(f"{rel} findings[{idx}] missing {key}")
            finding_id = str(finding["finding_id"]).strip()
            if finding_id in seen_ids:
                raise PipelineError(f"{rel} duplicate finding_id: {finding_id}")
            seen_ids.add(finding_id)
            category = self._normalize_local_window_category(finding["category"])
            if finding["severity"] not in SEVERITY_VALUES:
                raise PipelineError(f"{rel} findings[{idx}] invalid severity")
            chapter_id = str(finding["chapter_id"]).strip()
            if chapter_id not in chapter_ids:
                raise PipelineError(f"{rel} findings[{idx}] invalid chapter_id")
            if chapter_id not in chapters_reviewed_set:
                raise PipelineError(
                    f"{rel} findings[{idx}] chapter_id must be within chapters_reviewed"
                )
            pass_hint = str(finding["pass_hint"]).strip()
            if pass_hint not in REVISION_PASS_KEYS:
                raise PipelineError(f"{rel} findings[{idx}] invalid pass_hint")
            evidence = self._normalize_evidence_field(finding["evidence"])
            if not self._evidence_citations_valid(evidence, novel_file):
                raise PipelineError(
                    f"{rel} findings[{idx}] evidence must cite {novel_file}:<line>"
                )
            counterpart_evidence = str(finding.get("counterpart_evidence", "")).strip()
            if counterpart_evidence:
                normalized_counterpart = self._normalize_evidence_field(counterpart_evidence)
                if not self._evidence_citations_valid(normalized_counterpart, novel_file):
                    raise PipelineError(
                        f"{rel} findings[{idx}] counterpart_evidence must cite {novel_file}:<line>"
                    )
            self._validate_rewrite_direction(
                rewrite_direction=str(finding["rewrite_direction"]),
                target_file=novel_file,
                rel=rel,
                finding_index=idx,
            )
            self._validate_acceptance_test(
                acceptance_test=str(finding["acceptance_test"]),
                target_file=novel_file,
                rel=rel,
                finding_index=idx,
            )
            related_chapter_ids = finding.get("related_chapter_ids")
            if not isinstance(related_chapter_ids, list) or not related_chapter_ids:
                raise PipelineError(
                    f"{rel} findings[{idx}] related_chapter_ids must be a non-empty array"
                )
            for rel_idx, related_id in enumerate(related_chapter_ids, start=1):
                normalized_related = str(related_id).strip()
                if normalized_related not in chapter_ids:
                    raise PipelineError(
                        f"{rel} findings[{idx}] related_chapter_ids[{rel_idx}] invalid chapter_id"
                    )
            requirements = self._local_window_category_requirements(category)
            if "related_chapter_ids" in requirements and not finding.get("related_chapter_ids"):
                raise PipelineError(
                    f"{rel} findings[{idx}] category {category} requires related_chapter_ids"
                )
            if "boundary_span" in requirements and not str(
                finding.get("boundary_span", "")
            ).strip():
                raise PipelineError(
                    f"{rel} findings[{idx}] category {category} requires boundary_span"
                )
            if "counterpart_evidence" in requirements and not counterpart_evidence:
                raise PipelineError(
                    f"{rel} findings[{idx}] category {category} requires counterpart_evidence"
                )

    def _repair_local_window_audit_data(
        self,
        data: dict[str, Any],
        cycle: int,
        chapter_ids: set[str],
    ) -> tuple[dict[str, Any], list[str]]:
        if not isinstance(data, dict):
            return data, []

        repairs: list[str] = []
        raw_cycle = data.get("cycle")
        if isinstance(raw_cycle, str):
            stripped = raw_cycle.strip()
            if stripped.isdigit():
                data["cycle"] = int(stripped)
                repairs.append("cycle coerced to integer")

        chapters_reviewed = data.get("chapters_reviewed")
        if not isinstance(chapters_reviewed, list):
            legacy_chapters = data.get("chapters")
            if isinstance(legacy_chapters, list):
                data["chapters_reviewed"] = legacy_chapters
                chapters_reviewed = legacy_chapters
                repairs.append("chapters_reviewed mapped from chapters")
        if isinstance(chapters_reviewed, list):
            normalized_reviewed: list[str] = []
            for idx, chapter_id in enumerate(chapters_reviewed, start=1):
                normalized_id, changed = self._coerce_full_award_chapter_id(
                    chapter_id,
                    chapter_ids,
                )
                if changed:
                    repairs.append(f"chapters_reviewed[{idx}] normalized")
                normalized_reviewed.append(normalized_id)
            data["chapters_reviewed"] = normalized_reviewed

        window_id = str(data.get("window_id", "")).strip()
        if not window_id:
            window_suffix = re.search(r"(\d+)", str(data.get("window", "")).strip())
            if window_suffix:
                data["window_id"] = self._window_id_for_index(int(window_suffix.group(1)))
                repairs.append("window_id synthesized from window")
                window_id = str(data.get("window_id", "")).strip()

        findings = data.get("findings")
        if isinstance(findings, list):
            seen_ids: dict[str, int] = {}
            for idx, finding in enumerate(findings, start=1):
                if not isinstance(finding, dict):
                    continue
                finding_id = str(finding.get("finding_id", "")).strip()
                if not finding_id:
                    suffix = window_id or "window"
                    finding_id = f"{suffix}_{idx:03d}"
                    finding["finding_id"] = finding_id
                    repairs.append(f"findings[{idx}].finding_id synthesized")
                raw_category = str(finding.get("category", "")).strip()
                normalized_category = self._normalize_local_window_category(raw_category)
                if normalized_category and normalized_category != raw_category:
                    finding["category"] = normalized_category
                    repairs.append(f"findings[{idx}].category normalized")
                if not str(finding.get("subcategory", "")).strip():
                    finding["subcategory"] = "unspecified"
                    repairs.append(f"findings[{idx}].subcategory synthesized")
                severity = str(finding.get("severity", "")).strip()
                normalized_severity = severity.upper()
                if normalized_severity and normalized_severity != severity:
                    finding["severity"] = normalized_severity
                    repairs.append(f"findings[{idx}].severity normalized")
                normalized_chapter_id, changed = self._coerce_full_award_chapter_id(
                    finding.get("chapter_id", ""),
                    chapter_ids,
                )
                if changed:
                    finding["chapter_id"] = normalized_chapter_id
                    repairs.append(f"findings[{idx}].chapter_id normalized")
                if not str(finding.get("problem", "")).strip():
                    description = str(finding.get("description", "")).strip()
                    if description:
                        finding["problem"] = description
                        repairs.append(f"findings[{idx}].problem mapped from description")
                evidence = self._normalize_evidence_field(finding.get("evidence", ""))
                if evidence and evidence != finding.get("evidence"):
                    finding["evidence"] = evidence
                    repairs.append(f"findings[{idx}].evidence flattened")
                counterpart_evidence = self._normalize_evidence_field(
                    finding.get("counterpart_evidence", "")
                )
                if counterpart_evidence and counterpart_evidence != finding.get(
                    "counterpart_evidence"
                ):
                    finding["counterpart_evidence"] = counterpart_evidence
                    repairs.append(f"findings[{idx}].counterpart_evidence flattened")
                if not str(finding.get("rewrite_direction", "")).strip():
                    revision_directive = str(
                        finding.get("revision_directive", "")
                    ).strip()
                    if revision_directive:
                        finding["rewrite_direction"] = revision_directive
                        repairs.append(
                            f"findings[{idx}].rewrite_direction mapped from revision_directive"
                        )
                if not str(finding.get("pass_hint", "")).strip() or str(
                    finding.get("pass_hint", "")
                ).strip() not in REVISION_PASS_KEYS:
                    pass_hint = self._default_local_window_pass_hint(
                        str(finding.get("category", ""))
                    )
                    if pass_hint:
                        finding["pass_hint"] = pass_hint
                        repairs.append(f"findings[{idx}].pass_hint synthesized from category")
                related_chapter_ids = finding.get("related_chapter_ids")
                if isinstance(related_chapter_ids, list):
                    normalized_related: list[str] = []
                    changed_related = False
                    for rel_idx, chapter_id in enumerate(related_chapter_ids, start=1):
                        normalized_related_id, related_changed = self._coerce_full_award_chapter_id(
                            chapter_id,
                            chapter_ids,
                        )
                        normalized_related.append(normalized_related_id)
                        if related_changed:
                            repairs.append(
                                f"findings[{idx}].related_chapter_ids[{rel_idx}] normalized"
                            )
                            changed_related = True
                    if changed_related:
                        finding["related_chapter_ids"] = normalized_related
                elif not related_chapter_ids:
                    boundary_span = str(finding.get("boundary_span", "")).strip()
                    if "/" in boundary_span:
                        parsed = [part.strip() for part in boundary_span.split("/") if part.strip()]
                        if parsed:
                            finding["related_chapter_ids"] = parsed
                            repairs.append(
                                f"findings[{idx}].related_chapter_ids synthesized from boundary_span"
                            )
                requirements = self._local_window_category_requirements(
                    normalized_category or str(finding.get("category", ""))
                )
                if (
                    "boundary_span" in requirements
                    and not str(finding.get("boundary_span", "")).strip()
                ):
                    related = finding.get("related_chapter_ids")
                    chapter_id = str(finding.get("chapter_id", "")).strip()
                    if isinstance(related, list) and related:
                        lead = str(related[0]).strip()
                        if lead and lead != chapter_id:
                            finding["boundary_span"] = f"{lead}/{chapter_id}"
                            repairs.append(
                                f"findings[{idx}].boundary_span synthesized from related_chapter_ids"
                            )
                if not str(finding.get("fix_owner_reason", "")).strip():
                    finding["fix_owner_reason"] = "Repair synthesized during validation salvage."
                    repairs.append(f"findings[{idx}].fix_owner_reason synthesized")
                base_id = str(finding.get("finding_id", "")).strip()
                if base_id:
                    dup_count = seen_ids.get(base_id, 0)
                    if dup_count:
                        finding["finding_id"] = f"{base_id}_{dup_count + 1}"
                        repairs.append(f"findings[{idx}].finding_id deduplicated")
                    seen_ids[base_id] = dup_count + 1

        summary = data.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            finding_count = len(data.get("findings", [])) if isinstance(
                data.get("findings"), list
            ) else 0
            data["summary"] = (
                f"Local-window audit for cycle {cycle}. Findings: {finding_count}."
            )
            repairs.append("summary synthesized from finding count")
        return data, repairs

    def _load_repaired_local_window_audit(
        self,
        rel: str,
        cycle: int,
        chapter_ids: set[str],
        novel_file: str,
    ) -> dict[str, Any]:
        data = self._read_json(rel)
        repaired_data, repairs = self._repair_local_window_audit_data(
            data,
            cycle,
            chapter_ids,
        )
        if repairs:
            preserved_rel = self._preserve_invalid_artifact(rel)
            self._write_json(rel, repaired_data)
            detail_blob = " | ".join(repairs[:8])
            if len(repairs) > 8:
                detail_blob += f" | ... (+{len(repairs) - 8} more)"
            preserve_note = f" preserved={preserved_rel}" if preserved_rel else ""
            self._log(
                f"local_window_audit_repair artifact={rel}"
                f"{preserve_note} details={detail_blob}"
            )
            data = repaired_data
        self._validate_local_window_audit_json(
            data,
            cycle,
            chapter_ids,
            rel,
            novel_file,
        )
        return data

    def _repair_aggregation_decisions(
        self,
        data: dict[str, Any],
        input_finding_ids: set[str],
    ) -> tuple[dict[str, Any], list[str]]:
        if not isinstance(data, dict):
            return data, []

        repairs: list[str] = []
        valid_ids = {
            str(finding_id).strip()
            for finding_id in input_finding_ids
            if str(finding_id).strip()
        }
        valid_chapters = {spec.chapter_id for spec in self.chapter_specs}

        def normalize_id_list(raw: Any, label: str) -> list[str]:
            out: list[str] = []
            seen: set[str] = set()
            if not isinstance(raw, list):
                return out
            for idx, item in enumerate(raw, start=1):
                finding_id = str(item).strip()
                if not finding_id:
                    continue
                if finding_id not in valid_ids:
                    repairs.append(f"{label}[{idx}] dropped unknown finding_id")
                    continue
                if finding_id in seen:
                    repairs.append(f"{label}[{idx}] deduplicated")
                    continue
                seen.add(finding_id)
                out.append(finding_id)
            return out

        def normalize_chapter_list(raw: Any, label: str) -> list[str]:
            out: list[str] = []
            seen: set[str] = set()
            if not isinstance(raw, list):
                return out
            for idx, item in enumerate(raw, start=1):
                chapter_id = str(item).strip()
                if not chapter_id:
                    continue
                if chapter_id not in valid_chapters:
                    repairs.append(f"{label}[{idx}] dropped unknown chapter_id")
                    continue
                if chapter_id in seen:
                    repairs.append(f"{label}[{idx}] deduplicated")
                    continue
                seen.add(chapter_id)
                out.append(chapter_id)
            return out

        for key in AGGREGATION_DECISION_KEYS:
            raw_value = data.get(key)
            if raw_value is None:
                data[key] = []
                repairs.append(f"{key} synthesized as empty array")
            elif not isinstance(raw_value, list):
                data[key] = []
                repairs.append(f"{key} coerced to empty array")

        data["unchanged"] = normalize_id_list(data.get("unchanged", []), "unchanged")

        normalized_merges: list[dict[str, Any]] = []
        for idx, row in enumerate(data.get("merges", []), start=1):
            if not isinstance(row, dict):
                repairs.append(f"merges[{idx}] dropped non-object entry")
                continue
            target_finding = str(row.get("target_finding", "")).strip()
            if target_finding not in valid_ids:
                repairs.append(f"merges[{idx}] dropped unknown target_finding")
                continue
            absorbed_findings = normalize_id_list(
                row.get("absorbed_findings", []),
                f"merges[{idx}].absorbed_findings",
            )
            absorbed_findings = [
                finding_id
                for finding_id in absorbed_findings
                if finding_id != target_finding
            ]
            merged_rewrite_direction = str(
                row.get("merged_rewrite_direction", "")
            ).strip()
            reason = str(row.get("reason", "")).strip()
            if not absorbed_findings or not merged_rewrite_direction or not reason:
                repairs.append(f"merges[{idx}] dropped incomplete merge entry")
                continue
            normalized_merges.append(
                {
                    "target_finding": target_finding,
                    "absorbed_findings": absorbed_findings,
                    "merged_rewrite_direction": merged_rewrite_direction,
                    "reason": reason,
                }
            )
        data["merges"] = normalized_merges

        normalized_canonical_choices: list[dict[str, Any]] = []
        for idx, row in enumerate(data.get("canonical_choices", []), start=1):
            if not isinstance(row, dict):
                repairs.append(f"canonical_choices[{idx}] dropped non-object entry")
                continue
            choice_id = str(row.get("choice_id", "")).strip()
            value = str(row.get("value", "")).strip()
            grounding = str(row.get("grounding", "")).strip()
            affected_findings = normalize_id_list(
                row.get("affected_findings", []),
                f"canonical_choices[{idx}].affected_findings",
            )
            affected_chapters = normalize_chapter_list(
                row.get("affected_chapters", []),
                f"canonical_choices[{idx}].affected_chapters",
            )
            if not (
                choice_id
                and value
                and grounding
                and affected_findings
                and affected_chapters
            ):
                repairs.append(
                    f"canonical_choices[{idx}] dropped incomplete canonical choice"
                )
                continue
            normalized_canonical_choices.append(
                {
                    "choice_id": choice_id,
                    "value": value,
                    "grounding": grounding,
                    "affected_findings": affected_findings,
                    "affected_chapters": affected_chapters,
                }
            )
        data["canonical_choices"] = normalized_canonical_choices

        normalized_consistency_directives: list[dict[str, Any]] = []
        for idx, row in enumerate(data.get("consistency_directives", []), start=1):
            if not isinstance(row, dict):
                repairs.append(
                    f"consistency_directives[{idx}] dropped non-object entry"
                )
                continue
            directive_id = str(row.get("directive_id", "")).strip()
            rule = str(row.get("rule", "")).strip()
            reason = str(row.get("reason", "")).strip()
            source_findings = normalize_id_list(
                row.get("source_findings", []),
                f"consistency_directives[{idx}].source_findings",
            )
            if not (directive_id and rule and reason and source_findings):
                repairs.append(
                    f"consistency_directives[{idx}] dropped incomplete directive"
                )
                continue
            normalized_consistency_directives.append(
                {
                    "directive_id": directive_id,
                    "rule": rule,
                    "source_findings": source_findings,
                    "reason": reason,
                }
            )
        data["consistency_directives"] = normalized_consistency_directives

        normalized_context_injections: list[dict[str, Any]] = []
        for idx, row in enumerate(data.get("context_injections", []), start=1):
            if not isinstance(row, dict):
                repairs.append(f"context_injections[{idx}] dropped non-object entry")
                continue
            target_finding = str(row.get("target_finding", "")).strip()
            cross_chapter_context = str(
                row.get("cross_chapter_context", "")
            ).strip()
            if target_finding not in valid_ids or not cross_chapter_context:
                repairs.append(
                    f"context_injections[{idx}] dropped incomplete context injection"
                )
                continue
            normalized_context_injections.append(
                {
                    "target_finding": target_finding,
                    "cross_chapter_context": cross_chapter_context,
                }
            )
        data["context_injections"] = normalized_context_injections

        for bucket_key in ("suppressions", "unfixable"):
            normalized_bucket: list[dict[str, Any]] = []
            for idx, row in enumerate(data.get(bucket_key, []), start=1):
                if not isinstance(row, dict):
                    repairs.append(f"{bucket_key}[{idx}] dropped non-object entry")
                    continue
                finding_id = str(row.get("finding_id", "")).strip()
                reason = str(row.get("reason", "")).strip()
                attempted_partial_fix = str(
                    row.get("attempted_partial_fix", "")
                ).strip()
                if bucket_key == "unfixable":
                    if finding_id not in valid_ids or not reason or not attempted_partial_fix:
                        repairs.append(f"{bucket_key}[{idx}] dropped incomplete entry")
                        continue
                    normalized_bucket.append(
                        {
                            "finding_id": finding_id,
                            "attempted_partial_fix": attempted_partial_fix,
                            "reason": reason,
                        }
                    )
                    continue
                if finding_id not in valid_ids or not reason:
                    repairs.append(f"{bucket_key}[{idx}] dropped incomplete entry")
                    continue
                normalized_bucket.append(
                    {
                        "finding_id": finding_id,
                        "reason": reason,
                    }
                )
            data[bucket_key] = normalized_bucket

        normalized_reassignments: list[dict[str, Any]] = []
        for idx, row in enumerate(data.get("pass_reassignments", []), start=1):
            if not isinstance(row, dict):
                repairs.append(f"pass_reassignments[{idx}] dropped non-object entry")
                continue
            finding_id = str(row.get("finding_id", "")).strip()
            from_pass = str(row.get("from_pass", "")).strip()
            to_pass = str(row.get("to_pass", "")).strip()
            reason = str(row.get("reason", "")).strip()
            if (
                finding_id not in valid_ids
                or from_pass not in REVISION_PASS_KEYS
                or to_pass not in REVISION_PASS_KEYS
                or from_pass == to_pass
                or not reason
            ):
                repairs.append(
                    f"pass_reassignments[{idx}] dropped incomplete pass reassignment"
                )
                continue
            normalized_reassignments.append(
                {
                    "finding_id": finding_id,
                    "from_pass": from_pass,
                    "to_pass": to_pass,
                    "reason": reason,
                }
            )
        data["pass_reassignments"] = normalized_reassignments

        return data, repairs

    def _validate_aggregation_decisions(
        self,
        data: dict[str, Any],
        input_finding_ids: set[str],
        rel: str,
    ) -> None:
        if not isinstance(data, dict):
            raise PipelineError(f"{rel} must be a JSON object")
        for key in AGGREGATION_DECISION_KEYS:
            if not isinstance(data.get(key), list):
                raise PipelineError(f"{rel} {key} must be an array")

        valid_ids = {
            str(finding_id).strip()
            for finding_id in input_finding_ids
            if str(finding_id).strip()
        }
        valid_chapters = {spec.chapter_id for spec in self.chapter_specs}
        accounted_for: dict[str, str] = {}

        def account(finding_id: str, bucket: str) -> None:
            if finding_id not in valid_ids:
                raise PipelineError(f"{rel} references unknown finding_id {finding_id}")
            prior_bucket = accounted_for.get(finding_id)
            if prior_bucket is not None:
                raise PipelineError(
                    f"{rel} finding_id {finding_id} appears in both {prior_bucket} and {bucket}"
                )
            accounted_for[finding_id] = bucket

        for idx, finding_id in enumerate(data.get("unchanged", []), start=1):
            if not isinstance(finding_id, str) or not finding_id.strip():
                raise PipelineError(f"{rel} unchanged[{idx}] must be a finding_id string")
            account(finding_id.strip(), "unchanged")

        for idx, row in enumerate(data.get("merges", []), start=1):
            if not isinstance(row, dict):
                raise PipelineError(f"{rel} merges[{idx}] must be object")
            target_finding = str(row.get("target_finding", "")).strip()
            absorbed_findings = row.get("absorbed_findings")
            merged_rewrite_direction = str(
                row.get("merged_rewrite_direction", "")
            ).strip()
            reason = str(row.get("reason", "")).strip()
            if not target_finding or not merged_rewrite_direction or not reason:
                raise PipelineError(f"{rel} merges[{idx}] missing required fields")
            if not isinstance(absorbed_findings, list) or not absorbed_findings:
                raise PipelineError(
                    f"{rel} merges[{idx}].absorbed_findings must be non-empty array"
                )
            account(target_finding, "merges")
            seen_absorbed: set[str] = set()
            for absorb_idx, absorbed_id in enumerate(absorbed_findings, start=1):
                if not isinstance(absorbed_id, str) or not absorbed_id.strip():
                    raise PipelineError(
                        f"{rel} merges[{idx}].absorbed_findings[{absorb_idx}] must be finding_id string"
                    )
                normalized_absorbed = absorbed_id.strip()
                if normalized_absorbed == target_finding:
                    raise PipelineError(
                        f"{rel} merges[{idx}] target_finding cannot also appear in absorbed_findings"
                    )
                if normalized_absorbed in seen_absorbed:
                    raise PipelineError(
                        f"{rel} merges[{idx}] absorbed_findings contains duplicate {normalized_absorbed}"
                    )
                seen_absorbed.add(normalized_absorbed)
                account(normalized_absorbed, "merges")

        for idx, row in enumerate(data.get("canonical_choices", []), start=1):
            if not isinstance(row, dict):
                raise PipelineError(f"{rel} canonical_choices[{idx}] must be object")
            choice_id = str(row.get("choice_id", "")).strip()
            value = str(row.get("value", "")).strip()
            grounding = str(row.get("grounding", "")).strip()
            affected_findings = row.get("affected_findings")
            affected_chapters = row.get("affected_chapters")
            if not choice_id or not value or not grounding:
                raise PipelineError(
                    f"{rel} canonical_choices[{idx}] missing choice_id, value, or grounding"
                )
            if not isinstance(affected_findings, list) or not affected_findings:
                raise PipelineError(
                    f"{rel} canonical_choices[{idx}].affected_findings must be non-empty array"
                )
            if not isinstance(affected_chapters, list) or not affected_chapters:
                raise PipelineError(
                    f"{rel} canonical_choices[{idx}].affected_chapters must be non-empty array"
                )
            for finding_idx, finding_id in enumerate(affected_findings, start=1):
                if not isinstance(finding_id, str) or finding_id.strip() not in valid_ids:
                    raise PipelineError(
                        f"{rel} canonical_choices[{idx}].affected_findings[{finding_idx}] must reference an input finding_id"
                    )
            for chapter_idx, chapter_id in enumerate(affected_chapters, start=1):
                if not isinstance(chapter_id, str) or chapter_id.strip() not in valid_chapters:
                    raise PipelineError(
                        f"{rel} canonical_choices[{idx}].affected_chapters[{chapter_idx}] must reference a valid chapter_id"
                    )

        for idx, row in enumerate(data.get("consistency_directives", []), start=1):
            if not isinstance(row, dict):
                raise PipelineError(
                    f"{rel} consistency_directives[{idx}] must be object"
                )
            directive_id = str(row.get("directive_id", "")).strip()
            rule = str(row.get("rule", "")).strip()
            reason = str(row.get("reason", "")).strip()
            source_findings = row.get("source_findings")
            if not directive_id or not rule or not reason:
                raise PipelineError(
                    f"{rel} consistency_directives[{idx}] missing directive_id, rule, or reason"
                )
            if not isinstance(source_findings, list) or not source_findings:
                raise PipelineError(
                    f"{rel} consistency_directives[{idx}].source_findings must be non-empty array"
                )
            for finding_idx, finding_id in enumerate(source_findings, start=1):
                if not isinstance(finding_id, str) or finding_id.strip() not in valid_ids:
                    raise PipelineError(
                        f"{rel} consistency_directives[{idx}].source_findings[{finding_idx}] must reference an input finding_id"
                    )

        for idx, row in enumerate(data.get("context_injections", []), start=1):
            if not isinstance(row, dict):
                raise PipelineError(f"{rel} context_injections[{idx}] must be object")
            target_finding = str(row.get("target_finding", "")).strip()
            cross_chapter_context = str(
                row.get("cross_chapter_context", "")
            ).strip()
            if target_finding not in valid_ids or not cross_chapter_context:
                raise PipelineError(
                    f"{rel} context_injections[{idx}] missing target_finding or cross_chapter_context"
                )

        for bucket_key in ("suppressions", "unfixable"):
            for idx, row in enumerate(data.get(bucket_key, []), start=1):
                if not isinstance(row, dict):
                    raise PipelineError(f"{rel} {bucket_key}[{idx}] must be object")
                finding_id = str(row.get("finding_id", "")).strip()
                reason = str(row.get("reason", "")).strip()
                attempted_partial_fix = str(
                    row.get("attempted_partial_fix", "")
                ).strip()
                if bucket_key == "unfixable":
                    if finding_id not in valid_ids or not reason or not attempted_partial_fix:
                        raise PipelineError(
                            f"{rel} {bucket_key}[{idx}] missing finding_id, attempted_partial_fix, or reason"
                        )
                    account(finding_id, bucket_key)
                    continue
                if finding_id not in valid_ids or not reason:
                    raise PipelineError(
                        f"{rel} {bucket_key}[{idx}] missing finding_id or reason"
                    )
                account(finding_id, bucket_key)

        for idx, row in enumerate(data.get("pass_reassignments", []), start=1):
            if not isinstance(row, dict):
                raise PipelineError(
                    f"{rel} pass_reassignments[{idx}] must be object"
                )
            finding_id = str(row.get("finding_id", "")).strip()
            from_pass = str(row.get("from_pass", "")).strip()
            to_pass = str(row.get("to_pass", "")).strip()
            reason = str(row.get("reason", "")).strip()
            if finding_id not in valid_ids or not reason:
                raise PipelineError(
                    f"{rel} pass_reassignments[{idx}] missing finding_id or reason"
                )
            if from_pass not in REVISION_PASS_KEYS or to_pass not in REVISION_PASS_KEYS:
                raise PipelineError(
                    f"{rel} pass_reassignments[{idx}] must use valid revision pass keys"
                )
            if from_pass == to_pass:
                raise PipelineError(
                    f"{rel} pass_reassignments[{idx}] from_pass must differ from to_pass"
                )
            account(finding_id, "pass_reassignments")

        if set(accounted_for.keys()) != valid_ids:
            missing = sorted(valid_ids - set(accounted_for.keys()))
            extra = sorted(set(accounted_for.keys()) - valid_ids)
            details: list[str] = []
            if missing:
                details.append(f"missing={', '.join(missing[:8])}")
            if extra:
                details.append(f"extra={', '.join(extra[:8])}")
            raise PipelineError(
                f"{rel} accounting rule violated ({'; '.join(details)})"
            )

    def _load_repaired_aggregation_decisions(
        self, rel: str, input_finding_ids: set[str]
    ) -> dict[str, Any]:
        self._materialize_output_alias(
            base_dir=self.run_dir,
            required_rel=rel,
            stage="llm_aggregator",
            cycle=None,
            chapter_id=None,
        )
        data = self._read_json(rel)
        repaired_data, repairs = self._repair_aggregation_decisions(
            data,
            input_finding_ids,
        )
        if repairs:
            preserved_rel = self._preserve_invalid_artifact(rel)
            self._write_json(rel, repaired_data)
            detail_blob = " | ".join(repairs[:8])
            if len(repairs) > 8:
                detail_blob += f" | ... (+{len(repairs) - 8} more)"
            preserve_note = f" preserved={preserved_rel}" if preserved_rel else ""
            self._log(
                f"aggregation_decisions_repair artifact={rel}"
                f"{preserve_note} details={detail_blob}"
            )
            data = repaired_data
        self._validate_aggregation_decisions(
            data,
            input_finding_ids,
            rel,
        )
        return data

    def _local_window_audit_input_paths(
        self,
        cycle: int,
        chapters_reviewed: list[str],
    ) -> list[Path]:
        cpad = self._cpad(cycle)
        continuity_snapshot_rel = self._cycle_continuity_snapshot_rel(cycle)
        input_paths = [
            self.run_dir / f"snapshots/cycle_{cpad}/FINAL_NOVEL.md",
            self.run_dir / self._chapter_line_index_rel(cycle),
            self.run_dir / continuity_snapshot_rel,
            self.run_dir / "outline" / "style_bible.json",
            self.run_dir / "config" / "constitution.md",
            self.run_dir / "config" / "prompts" / "local_window_audit_prompt.md",
        ]
        input_paths.extend(
            self.run_dir / "outline" / "chapter_specs" / f"{chapter_id}.json"
            for chapter_id in chapters_reviewed
        )
        return input_paths

    def _local_window_audit_unit_state(
        self,
        cycle: int,
        window_id: str,
        chapters_reviewed: list[str],
    ) -> dict[str, Any]:
        rel = self._local_window_audit_rel(cycle, window_id)
        self._materialize_output_alias(
            base_dir=self.run_dir,
            required_rel=rel,
            stage="local_window_audit",
            cycle=cycle,
            chapter_id=None,
        )
        path = self.run_dir / rel
        if not path.is_file():
            return {
                "status": "missing",
                "validated": False,
                "fresh": False,
                "reason": "missing_output",
            }
        cpad = self._cpad(cycle)
        novel_file = f"snapshots/cycle_{cpad}/FINAL_NOVEL.md"
        try:
            data = self._load_repaired_local_window_audit(
                rel,
                cycle,
                {spec.chapter_id for spec in self.chapter_specs},
                novel_file,
            )
            self._validate_local_window_window_output(
                data,
                rel=rel,
                window_id=window_id,
                chapters_reviewed=chapters_reviewed,
            )
        except PipelineError as exc:
            return {
                "status": "failed",
                "validated": False,
                "fresh": False,
                "reason": str(exc),
            }
        input_paths = self._local_window_audit_input_paths(cycle, chapters_reviewed)
        if not self._artifact_fresh_against_inputs(path, input_paths):
            return {
                "status": "stale",
                "validated": True,
                "fresh": False,
                "reason": "inputs_newer_than_output",
            }
        return {
            "status": "reused",
            "validated": True,
            "fresh": True,
            "artifact": rel,
            "chapter_count": len(chapters_reviewed),
        }

    def _validate_revision_report_json(
        self,
        data: dict[str, Any],
        chapter_id: str,
        rel: str,
        expected_finding_ids: set[str],
        chapter_file: str,
    ) -> None:
        if not isinstance(data, dict):
            raise PipelineError(f"{rel} must be a JSON object")
        if data.get("chapter_id") != chapter_id:
            raise PipelineError(f"{rel} chapter_id mismatch (expected {chapter_id})")

        finding_results = data.get("finding_results")
        if not isinstance(finding_results, list):
            raise PipelineError(f"{rel} finding_results must be an array")

        seen_ids: set[str] = set()
        allowed_status = {"FIXED", "PARTIAL", "UNRESOLVED"}
        for idx, row in enumerate(finding_results, start=1):
            if not isinstance(row, dict):
                raise PipelineError(f"{rel} finding_results #{idx} must be object")
            for key in ("finding_id", "status_after_revision", "evidence", "notes"):
                if key not in row:
                    raise PipelineError(f"{rel} finding_results #{idx} missing {key}")
            finding_id = str(row.get("finding_id", "")).strip()
            if not finding_id:
                raise PipelineError(f"{rel} finding_results #{idx} finding_id must be non-empty")
            status = str(row.get("status_after_revision", "")).strip()
            if status not in allowed_status:
                raise PipelineError(
                    f"{rel} finding_results #{idx} invalid status_after_revision: {status}"
                )
            evidence = self._normalize_evidence_field(row.get("evidence", ""))
            if not self._evidence_citations_valid(evidence, chapter_file):
                raise PipelineError(
                    f"{rel} finding_results #{idx} evidence must cite {chapter_file}:<line>"
                )
            notes = row.get("notes")
            if not isinstance(notes, str):
                raise PipelineError(f"{rel} finding_results #{idx} notes must be string")
            revision_note = row.get("revision_note")
            if revision_note is not None and not isinstance(revision_note, str):
                raise PipelineError(
                    f"{rel} finding_results #{idx} revision_note must be string when present"
                )
            if status in {"PARTIAL", "UNRESOLVED"}:
                if not isinstance(revision_note, str) or not revision_note.strip():
                    raise PipelineError(
                        f"{rel} finding_results #{idx} missing revision_note for {status}"
                    )
            seen_ids.add(finding_id)

        # Log coverage gaps but do NOT reject the whole report over them.
        # The model may skip low-priority findings or discover new issues
        # during revision — both are acceptable.
        missing = sorted(fid for fid in expected_finding_ids if fid not in seen_ids)
        if missing:
            preview = ", ".join(missing[:10])
            self._log(
                f"revision_report_coverage_gap {rel}: missing finding_results for: {preview}"
            )
        unexpected = sorted(fid for fid in seen_ids if fid not in expected_finding_ids)
        if unexpected:
            preview = ", ".join(unexpected[:10])
            self._log(
                f"revision_report_extra_findings {rel}: not in packet: {preview}"
            )

        summary = data.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise PipelineError(f"{rel} missing non-empty summary")

    def _repair_revision_report_data(
        self, data: dict[str, Any]
    ) -> tuple[dict[str, Any], list[str]]:
        if not isinstance(data, dict):
            return data, []

        repairs: list[str] = []
        finding_results = data.get("finding_results")
        if isinstance(finding_results, list):
            for idx, row in enumerate(finding_results, start=1):
                if not isinstance(row, dict):
                    continue
                status = str(row.get("status_after_revision", "")).strip().upper()
                revision_note = str(row.get("revision_note", "")).strip()
                notes = str(row.get("notes", "")).strip()
                if status in {"PARTIAL", "UNRESOLVED"} and not revision_note and notes:
                    row["revision_note"] = notes
                    repairs.append(
                        f"finding_results[{idx}].revision_note synthesized from notes"
                    )

        summary = data.get("summary")
        if isinstance(summary, str) and summary.strip():
            return data, repairs

        if not isinstance(finding_results, list):
            return data, repairs

        for idx, row in enumerate(finding_results, start=1):
            if not isinstance(row, dict):
                continue
            nested_summary = row.get("summary")
            if isinstance(nested_summary, str) and nested_summary.strip():
                data["summary"] = nested_summary.strip()
                repairs.append(
                    f"summary promoted from finding_results[{idx}].summary"
                )
                break
        return data, repairs

    def _load_repaired_revision_report(
        self,
        rel: str,
        chapter_id: str,
        expected_finding_ids: set[str],
        chapter_file: str,
    ) -> dict[str, Any]:
        data = self._read_json(rel)
        repaired_data, repairs = self._repair_revision_report_data(data)
        if repairs:
            preserved_rel = self._preserve_invalid_artifact(rel)
            self._write_json(rel, repaired_data)
            detail_blob = " | ".join(repairs)
            preserve_note = f" preserved={preserved_rel}" if preserved_rel else ""
            self._log(
                f"revision_report_repair chapter={chapter_id} artifact={rel}"
                f"{preserve_note} details={detail_blob}"
            )
            data = repaired_data
        self._validate_revision_report_json(
            data,
            chapter_id,
            rel,
            expected_finding_ids,
            chapter_file=chapter_file,
        )
        return data

    def _severity_allowed_for_source(self, severity: str, source: str) -> bool:
        if severity in SEVERITY_VALUES:
            return True
        return severity == "LOW" and source == PRIMARY_GLOBAL_FINDING_SOURCE

    def _count_medium_plus_findings(self, findings: list[dict[str, Any]]) -> int:
        return sum(
            1
            for finding in findings
            if str(finding.get("severity", "")).strip().upper() in SEVERITY_VALUES
        )

    def _normalize_finding(
        self, raw: dict[str, Any], cycle: int, force_source: str | None = None
    ) -> dict[str, Any]:
        source = str(force_source or raw.get("source", "")).strip()
        if not source:
            source = "unknown"
        source = self._canonical_finding_source_name(source)
        finding = {
            "finding_id": str(raw.get("finding_id", "")).strip(),
            "source": source,
            "severity": str(raw.get("severity", "")).strip().upper(),
            "chapter_id": str(raw.get("chapter_id", "")).strip(),
            "evidence": str(raw.get("evidence", "")).strip(),
            "problem": str(raw.get("problem", "")).strip(),
            "rewrite_direction": str(raw.get("rewrite_direction", "")).strip(),
            "acceptance_test": str(raw.get("acceptance_test", "")).strip(),
            "status": "UNRESOLVED",
            "cycle": cycle,
        }
        if source == "elevation":
            _, normalized_severity = self._normalize_full_award_finding_source_and_severity(
                source,
                finding["severity"],
            )
            finding["severity"] = normalized_severity
        pass_hint = str(raw.get("pass_hint", "")).strip()
        if pass_hint:
            finding["pass_hint"] = pass_hint
        if not self._severity_allowed_for_source(finding["severity"], source):
            raise PipelineError(f"invalid finding severity: {finding}")
        if finding["chapter_id"] not in {spec.chapter_id for spec in self.chapter_specs}:
            raise PipelineError(f"finding chapter_id not in outline: {finding}")
        if not finding["finding_id"]:
            token = "|".join(
                [
                    finding["source"],
                    finding["chapter_id"],
                    finding["severity"],
                    finding["problem"],
                    finding["rewrite_direction"],
                ]
            )
            digest = hashlib.sha1(token.encode("utf-8")).hexdigest()[:10]
            finding["finding_id"] = f"{finding['source']}_{finding['chapter_id']}_{digest}"
        return finding

    def _dedupe_findings(self, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_semantic_key: dict[tuple[str, str, str, str, str], int] = {}
        collapsed: list[dict[str, Any]] = []
        for finding in findings:
            key = (
                finding["chapter_id"],
                finding["severity"],
                self._normalize_text_for_key(finding["problem"]),
                self._normalize_text_for_key(finding["rewrite_direction"]),
                self._normalize_text_for_key(finding["acceptance_test"]),
            )
            if key in by_semantic_key:
                idx = by_semantic_key[key]
                merged = collapsed[idx]
                merged["evidence"] = self._merge_evidence_citations(
                    merged.get("evidence", ""), finding.get("evidence", "")
                )
                existing_source = self._canonical_finding_source_name(
                    merged.get("source", "")
                )
                incoming_source = self._canonical_finding_source_name(
                    finding.get("source", "")
                )
                if (
                    existing_source != PRIMARY_GLOBAL_FINDING_SOURCE
                    and incoming_source == PRIMARY_GLOBAL_FINDING_SOURCE
                ):
                    merged["source"] = incoming_source
                    incoming_id = str(finding.get("finding_id", "")).strip()
                    if incoming_id:
                        merged["finding_id"] = incoming_id
                elif existing_source != PRIMARY_GLOBAL_FINDING_SOURCE:
                    existing_pass = self._assign_revision_pass_key(merged)
                    incoming_pass = self._assign_revision_pass_key(finding)
                    pass_rank = {
                        "p1_structural_craft": 3,
                        "p2_dialogue_idiolect_cadence": 2,
                        "p3_prose_copyedit": 1,
                    }
                    if pass_rank.get(incoming_pass, 0) > pass_rank.get(existing_pass, 0):
                        merged["source"] = incoming_source
                        incoming_id = str(finding.get("finding_id", "")).strip()
                        if incoming_id:
                            merged["finding_id"] = incoming_id
                        incoming_pass_hint = str(finding.get("pass_hint", "")).strip()
                        if incoming_pass_hint:
                            merged["pass_hint"] = incoming_pass_hint
                if not str(merged.get("pass_hint", "")).strip():
                    incoming_pass_hint = str(finding.get("pass_hint", "")).strip()
                    if incoming_pass_hint:
                        merged["pass_hint"] = incoming_pass_hint
                continue
            by_semantic_key[key] = len(collapsed)
            collapsed.append(dict(finding))

        used_ids: dict[str, int] = {}
        out: list[dict[str, Any]] = []
        for finding in collapsed:
            base_id = str(finding.get("finding_id", "")).strip()
            if not base_id:
                token = "|".join(
                    [
                        finding["source"],
                        finding["chapter_id"],
                        finding["severity"],
                        self._normalize_text_for_key(finding["problem"]),
                        self._normalize_text_for_key(finding["rewrite_direction"]),
                        self._normalize_text_for_key(finding["acceptance_test"]),
                    ]
                )
                digest = hashlib.sha1(token.encode("utf-8")).hexdigest()[:10]
                base_id = f"{finding['source']}_{finding['chapter_id']}_{digest}"
            count = used_ids.get(base_id, 0)
            if count == 0:
                row_id = base_id
            else:
                row_id = f"{base_id}_{count + 1}"
            used_ids[base_id] = count + 1
            row = dict(finding)
            row["finding_id"] = row_id
            out.append(row)
        return out

    def _soft_validation_enabled(self) -> bool:
        return self.cfg.validation_mode in {"balanced", "lenient"}

    def _record_validation_warning(
        self,
        *,
        stage: str,
        cycle: int | None,
        chapter_id: str | None,
        artifact: str,
        reason: str,
        action: str,
    ) -> None:
        row = {
            "timestamp_utc": self._utc_now(),
            "validation_mode": self.cfg.validation_mode,
            "stage": stage,
            "cycle": cycle,
            "chapter_id": chapter_id,
            "artifact": artifact,
            "reason": str(reason),
            "action": action,
        }
        with self._warning_lock:
            self.validation_warnings.append(row)
            self._write_json(
                "reports/validation_warnings.json",
                {
                    "validation_mode": self.cfg.validation_mode,
                    "warning_count": len(self.validation_warnings),
                    "warnings": self.validation_warnings,
                },
            )
        cycle_tag = self._cpad(cycle) if cycle is not None else "--"
        chapter_tag = chapter_id or "-"
        self._log(
            f"validation_warning cycle={cycle_tag} stage={stage} chapter={chapter_tag} "
            f"action={action} reason={reason}"
        )

    def _output_alias_candidates(self, required_rel: str) -> list[str]:
        if required_rel.endswith(".review.json") and "/chapter_" in required_rel:
            name = Path(required_rel).name
            return [
                "out/review.json",
                "out/chapter_review.json",
                f"out/{name}",
            ]
        if required_rel.startswith("outline/outline_review_cycle_") and required_rel.endswith(".json"):
            name = Path(required_rel).name
            return [
                "out/outline_review.json",
                "out/review.json",
                f"out/{name}",
            ]
        if required_rel.endswith("full_award.review.json"):
            return [
                "out/full_award_review.json",
                "out/review.json",
            ]
        if required_rel.endswith("cross_chapter_audit.json"):
            return [
                "out/cross_chapter_audit.json",
                "out/review.json",
            ]
        if "/local_window_" in required_rel and required_rel.endswith(".json"):
            name = Path(required_rel).name
            return [
                "out/local_window_audit.json",
                "out/local_window_review.json",
                "out/review.json",
                f"out/{name}",
            ]
        if required_rel.endswith("aggregation_decisions.json"):
            return [
                "out/aggregation_decisions.json",
                "out/review.json",
            ]
        if required_rel.endswith(".revision_report.json"):
            name = Path(required_rel).name
            return [
                "out/revision_report.json",
                f"out/{name}",
            ]
        if required_rel.endswith("outline/spatial_layout.json"):
            return [
                "out/spatial_layout.json",
            ]
        return []

    def _materialize_output_alias(
        self,
        *,
        base_dir: Path,
        required_rel: str,
        stage: str,
        cycle: int | None,
        chapter_id: str | None,
    ) -> bool:
        if not self._soft_validation_enabled():
            return False
        required_path = base_dir / required_rel
        if required_path.is_file():
            return True
        for alias in self._output_alias_candidates(required_rel):
            alias_path = base_dir / alias
            if not alias_path.is_file():
                continue
            required_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(alias_path, required_path)
            self._record_validation_warning(
                stage=stage,
                cycle=cycle,
                chapter_id=chapter_id,
                artifact=required_rel,
                reason=f"required output missing; recovered from alias {alias}",
                action="copied_output_alias",
            )
            return True
        return False

    def _fallback_chapter_review_payload(
        self, cycle: int, chapter_id: str, chapter_file: str, reason: str
    ) -> dict[str, Any]:
        fallback_reason = " ".join(str(reason).split())
        return {
            "chapter_id": chapter_id,
            "verdicts": {
                "award": "FAIL",
                "craft": "FAIL",
                "dialogue": "FAIL",
                "prose": "FAIL",
            },
            "findings": [
                {
                    "finding_id": f"fallback_{chapter_id}_contract",
                    "source": "craft",
                    "severity": "HIGH",
                    "chapter_id": chapter_id,
                    "evidence": f"{chapter_file}:1",
                    "problem": (
                        "Review output contract could not be validated; chapter requires manual "
                        f"quality pass. Root validator reason: {fallback_reason}"
                    ),
                    "rewrite_direction": (
                        f"Audit and revise {chapter_file}:1-220 for constitution compliance and "
                        "complete actionable findings coverage."
                    ),
                    "acceptance_test": (
                        f"At least 1 grounded fix is applied in {chapter_file}:1-220 and a valid "
                        "review JSON is regenerated with anchored evidence lines."
                    ),
                }
            ],
            "summary": (
                "Fallback chapter review generated after repeated validation failure."
            ),
        }

    def _fallback_full_award_review_payload(
        self, cycle: int, novel_file: str, reason: str
    ) -> dict[str, Any]:
        chapter_id = self.chapter_specs[0].chapter_id if self.chapter_specs else "chapter_01"
        fallback_reason = " ".join(str(reason).split())
        return {
            "cycle": cycle,
            "verdict": "FAIL",
            "summary": "Fallback full-book review generated after repeated validation failure.",
            "findings": [
                {
                    "finding_id": "fallback_full_award_contract",
                    "severity": "HIGH",
                    "chapter_id": chapter_id,
                    "evidence": f"{novel_file}:1",
                    "problem": (
                        "Full-book review contract could not be validated; shortlist assessment "
                        f"is incomplete. Root validator reason: {fallback_reason}"
                    ),
                    "rewrite_direction": (
                        f"Regenerate full-book findings with anchored references in {novel_file}:1-400."
                    ),
                    "acceptance_test": (
                        f"At least 1 full-book actionable finding cites {novel_file}:1 and "
                        "includes measurable acceptance criteria."
                    ),
                }
            ],
        }

    def _fallback_revision_report_payload(
        self,
        chapter_id: str,
        chapter_file: str,
        expected_ids: set[str],
        reason: str,
    ) -> dict[str, Any]:
        rows = []
        sorted_ids = sorted(expected_ids)
        for fid in sorted_ids:
            rows.append(
                {
                    "finding_id": fid,
                    "status_after_revision": "UNRESOLVED",
                    "evidence": f"{chapter_file}:1",
                    "notes": f"Fallback revision report due to validator failure: {reason}",
                    "revision_note": (
                        f"Could not validate revision output automatically; manual follow-up "
                        f"needed. Root validator reason: {reason}"
                    ),
                }
            )
        return {
            "chapter_id": chapter_id,
            "finding_results": rows,
            "summary": "Fallback revision report generated after validation failure.",
        }

    def _write_final_report(
        self, success_cycle: int | None, gate_records: list[dict[str, Any]]
    ) -> None:
        completed_at_utc = self._utc_now()
        status = "PASS" if success_cycle is not None else "FAIL"
        warning_count = len(self.validation_warnings)
        gate_history = self._merged_gate_history(gate_records)
        terminal_reason = (
            "max_cycles_reached"
            if success_cycle is not None
            else "no_cycles_completed"
        )
        final_cycle = success_cycle if success_cycle is not None else (
            gate_history[-1]["cycle"] if gate_history else None
        )
        final_novel_snapshot_file = (
            f"snapshots/cycle_{self._cpad(final_cycle)}/FINAL_NOVEL.post_revision.md"
            if final_cycle is not None
            else None
        )
        final_novel_file = "FINAL_NOVEL.md" if final_cycle is not None else None
        cycle_status_files = sorted(
            str(path.relative_to(self.run_dir))
            for path in (self.run_dir / "status").glob("cycle_*/cycle_status.json")
        )
        quality_summary_files = sorted(
            str(path.relative_to(self.run_dir))
            for path in (self.run_dir / "status").glob("cycle_*/quality_summary.json")
        )
        final_report = {
            "completed_at_utc": completed_at_utc,
            "status": status,
            "success_cycle": success_cycle,
            "max_cycles": self.cfg.max_cycles,
            "min_cycles": self.cfg.min_cycles,
            "fixed_concurrency": {
                "draft": self.cfg.max_parallel_drafts,
                "review": self.cfg.max_parallel_reviews,
                "revision": self.cfg.max_parallel_revisions,
            },
            "gate_history": gate_history,
            "cycle_status_files": cycle_status_files,
            "quality_summary_files": quality_summary_files,
            "chapter_count": len(self.chapter_specs),
            "final_novel_file": final_novel_file,
            "final_novel_snapshot_file": final_novel_snapshot_file,
            "validation_mode": self.cfg.validation_mode,
            "validation_warning_count": warning_count,
            "validation_warnings_file": "reports/validation_warnings.json",
            "run_dir": str(self.run_dir),
            "add_cycles": self.cfg.add_cycles,
            "base_completed_cycles": self.cfg.base_completed_cycles,
            "final_cycle_global_only": self.cfg.final_cycle_global_only,
        }
        final_status = {
            "completed_at_utc": completed_at_utc,
            "status": status,
            "terminal_reason": terminal_reason,
            "success_cycle": success_cycle,
            "max_cycles": self.cfg.max_cycles,
            "min_cycles": self.cfg.min_cycles,
            "chapter_count": len(self.chapter_specs),
            "final_novel_file": final_novel_file,
            "final_novel_snapshot_file": final_novel_snapshot_file,
            "validation_mode": self.cfg.validation_mode,
            "validation_warning_count": warning_count,
            "completed_with_warnings": warning_count > 0,
            "last_gate": gate_history[-1] if gate_history else None,
            "last_cycle_status_file": cycle_status_files[-1] if cycle_status_files else None,
            "last_quality_summary_file": (
                quality_summary_files[-1] if quality_summary_files else None
            ),
            "run_dir": str(self.run_dir),
            "add_cycles": self.cfg.add_cycles,
            "base_completed_cycles": self.cfg.base_completed_cycles,
            "final_cycle_global_only": self.cfg.final_cycle_global_only,
        }
        self._write_json(
            "reports/validation_warnings.json",
            {
                "validation_mode": self.cfg.validation_mode,
                "warning_count": warning_count,
                "warnings": self.validation_warnings,
            },
        )
        self._write_json("reports/final_report.json", final_report)
        self._write_json("reports/final_status.json", final_status)

    def _load_existing_gate_history(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for path in sorted((self.run_dir / "gate").glob("cycle_*/gate.json")):
            rel = str(path.relative_to(self.run_dir))
            try:
                payload = self._read_json(rel)
            except PipelineError:
                continue
            cycle = payload.get("cycle")
            if isinstance(cycle, int) and cycle >= 1:
                rows.append(payload)
        return rows

    def _merged_gate_history(self, gate_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_cycle: dict[int, dict[str, Any]] = {}
        for row in self._load_existing_gate_history():
            cycle = row.get("cycle")
            if isinstance(cycle, int) and cycle >= 1:
                by_cycle[cycle] = row
        for row in gate_records:
            cycle = row.get("cycle")
            if isinstance(cycle, int) and cycle >= 1:
                by_cycle[cycle] = row
        return [by_cycle[cycle] for cycle in sorted(by_cycle)]

    _COST_RATES: dict[str, dict[str, Any]] = {
        "gpt-5.4": {
            "input": 2.50, "cached": 0.25, "output": 15.00,
            "long_ctx_threshold": 272_000,
            "long_ctx_input": 5.00, "long_ctx_cached": 0.50, "long_ctx_output": 22.50,
        },
        "gpt-5.3-codex": {
            "input": 1.75, "cached": 0.175, "output": 14.00,
            "long_ctx_threshold": None,
        },
    }

    def _print_cost_summary(self) -> None:
        logs_dir = self.run_dir / "logs" / "jobs"
        if not logs_dir.is_dir():
            return
        codex_totals = {
            "input": 0,
            "cached": 0,
            "output": 0,
            "cost": 0.0,
            "jobs": 0,
            "models": set(),
        }
        claude_totals = {
            "input": 0,
            "cache_create": 0,
            "cached": 0,
            "output": 0,
            "cost": 0.0,
            "jobs": 0,
            "models": set(),
        }
        for jsonl_path in sorted(logs_dir.glob("*.jsonl")):
            manifest = self._load_job_manifest(jsonl_path.stem)
            provider = str(manifest.get("provider", "")).strip().lower() or self.cfg.provider
            model = str(manifest.get("model", "")).strip() or DEFAULT_MODEL_BY_PROVIDER.get(
                provider, self.cfg.model or "unknown"
            )
            if provider == "claude":
                if self._accumulate_claude_cost(jsonl_path, model, claude_totals):
                    continue
            elif provider == "codex":
                self._accumulate_codex_cost(jsonl_path, model, codex_totals)
        if codex_totals["jobs"]:
            model_label = ",".join(sorted(codex_totals["models"]))
            self._log(
                f"cost_summary provider=codex model={model_label} jobs={codex_totals['jobs']} "
                f"input_tokens={codex_totals['input']} cached_tokens={codex_totals['cached']} "
                f"output_tokens={codex_totals['output']} estimated_cost=${codex_totals['cost']:.2f}"
            )
        if claude_totals["jobs"]:
            model_label = ",".join(sorted(claude_totals["models"]))
            self._log(
                f"cost_summary provider=claude model={model_label} jobs={claude_totals['jobs']} "
                f"input_tokens={claude_totals['input']} cache_create_tokens={claude_totals['cache_create']} "
                f"cached_tokens={claude_totals['cached']} output_tokens={claude_totals['output']} "
                f"estimated_cost=${claude_totals['cost']:.2f}"
            )

    def _load_job_manifest(self, job_id: str) -> dict[str, Any]:
        manifest_path = self.run_dir / "manifests" / f"{job_id}.json"
        if not manifest_path.is_file():
            return {}
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return loaded if isinstance(loaded, dict) else {}

    def _accumulate_codex_cost(
        self, jsonl_path: Path, model: str, totals: dict[str, Any]
    ) -> None:
        rates = self._COST_RATES.get(model, self._COST_RATES["gpt-5.3-codex"])
        total_input = total_cached = total_output = 0
        for raw_line in jsonl_path.read_text(encoding="utf-8").splitlines():
            try:
                evt = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if evt.get("type") == "turn.completed":
                usage = evt.get("usage", {})
                total_input = int(usage.get("input_tokens", 0) or 0)
                total_cached = int(usage.get("cached_input_tokens", 0) or 0)
                total_output = int(usage.get("output_tokens", 0) or 0)
        if total_input == 0 and total_output == 0:
            return
        threshold = rates.get("long_ctx_threshold")
        if threshold and total_input > threshold:
            ir, cr, orr = (
                rates["long_ctx_input"],
                rates["long_ctx_cached"],
                rates["long_ctx_output"],
            )
        else:
            ir, cr, orr = rates["input"], rates["cached"], rates["output"]
        cost = ((total_input - total_cached) * ir + total_cached * cr + total_output * orr) / 1_000_000
        totals["input"] += total_input
        totals["cached"] += total_cached
        totals["output"] += total_output
        totals["cost"] += cost
        totals["jobs"] += 1
        totals["models"].add(model)

    def _accumulate_claude_cost(
        self, jsonl_path: Path, model: str, totals: dict[str, Any]
    ) -> bool:
        events = self._load_provider_events(jsonl_path)
        if not events:
            return False
        try:
            result_event = self._extract_claude_result_event(events)
        except PipelineError:
            return False
        usage = result_event.get("usage")
        if not isinstance(usage, dict):
            usage = {}
        inp = int(usage.get("input_tokens", 0) or 0)
        cache_create = int(usage.get("cache_creation_input_tokens", 0) or 0)
        cached = int(usage.get("cache_read_input_tokens", 0) or 0)
        out = int(usage.get("output_tokens", 0) or 0)
        cost = float(result_event.get("total_cost_usd", 0.0) or 0.0)
        if inp == 0 and cache_create == 0 and cached == 0 and out == 0 and cost == 0.0:
            return False
        totals["input"] += inp
        totals["cache_create"] += cache_create
        totals["cached"] += cached
        totals["output"] += out
        totals["cost"] += cost
        totals["jobs"] += 1
        totals["models"].add(model)
        return True

    def _render_prompt(self, template_name: str, replacements: dict[str, str]) -> str:
        template_path = self.run_dir / "config" / "prompts" / template_name
        text = template_path.read_text(encoding="utf-8")
        for key, value in replacements.items():
            text = text.replace(f"{{{{{key}}}}}", str(value))
        unreplaced = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", text)))
        if unreplaced:
            raise PipelineError(
                f"{template_name} has unreplaced placeholders: {', '.join(unreplaced)}"
            )
        return text

    def _read_json(self, rel: str) -> dict[str, Any]:
        path = self.run_dir / rel
        if not path.is_file():
            raise PipelineError(f"missing JSON file: {rel}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise PipelineError(f"invalid JSON: {rel}") from exc
        if not isinstance(data, dict):
            raise PipelineError(f"expected JSON object in {rel}")
        return data

    def _load_jsonl_from_path(
        self, path: Path, *, label: str
    ) -> list[dict[str, Any]]:
        if not path.is_file():
            raise PipelineError(f"missing JSONL file: {label}")
        rows: list[dict[str, Any]] = []
        for line_number, raw_line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise PipelineError(
                    f"invalid JSONL row in {label} at line {line_number}"
                ) from exc
            if not isinstance(row, dict):
                raise PipelineError(
                    f"expected JSON object rows in {label} at line {line_number}"
                )
            rows.append(row)
        return rows

    def _read_jsonl(self, rel: str) -> list[dict[str, Any]]:
        return self._load_jsonl_from_path(self.run_dir / rel, label=rel)

    def _write_json(self, rel: str, payload: dict[str, Any]) -> None:
        path = self.run_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        rendered = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
        if path.is_file() and path.read_text(encoding="utf-8") == rendered:
            return
        path.write_text(rendered, encoding="utf-8")

    def _write_jsonl(self, rel: str | Path, rows: list[dict[str, Any]]) -> None:
        path = rel if isinstance(rel, Path) else self.run_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        rendered_rows = [json.dumps(row, ensure_ascii=True, sort_keys=True) for row in rows]
        rendered = ("\n".join(rendered_rows) + "\n") if rendered_rows else ""
        if path.is_file() and path.read_text(encoding="utf-8") == rendered:
            return
        path.write_text(rendered, encoding="utf-8")

    def _write_text(self, rel: str, text: str) -> None:
        path = self.run_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file() and path.read_text(encoding="utf-8") == text:
            return
        path.write_text(text, encoding="utf-8")

    def _write_workspace_json(self, workspace: Path, rel: str, payload: dict[str, Any]) -> None:
        path = workspace / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _write_workspace_text(self, workspace: Path, rel: str, text: str) -> None:
        path = workspace / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file() and path.read_text(encoding="utf-8") == text:
            return
        path.write_text(text, encoding="utf-8")

    def _read_workspace_jsonl(self, path: Path) -> list[dict[str, Any]]:
        return self._load_jsonl_from_path(path, label=str(path))

    def _artifact_fresh_against_inputs(
        self, output_path: Path, input_paths: list[Path]
    ) -> bool:
        if not output_path.is_file():
            return False
        try:
            output_mtime = output_path.stat().st_mtime
        except OSError:
            return False
        for path in input_paths:
            if not path.exists():
                return False
            try:
                if output_mtime < path.stat().st_mtime:
                    return False
            except OSError:
                return False
        return True

    def _artifacts_fresh_against_inputs(
        self, output_paths: list[Path], input_paths: list[Path]
    ) -> bool:
        return all(
            self._artifact_fresh_against_inputs(output_path, input_paths)
            for output_path in output_paths
        )

    def _cpad(self, cycle: int) -> str:
        return f"{cycle:02d}"

    def _chapter_number(self, chapter_id: str) -> int:
        m = CHAPTER_ID_RE.match(chapter_id)
        if not m:
            raise PipelineError(f"invalid chapter_id: {chapter_id}")
        return int(m.group(1))

    def _normalize_text_for_key(self, text: str) -> str:
        return re.sub(r"\s+", " ", str(text).strip().lower())

    def _normalize_evidence_field(self, raw: Any) -> str:
        if isinstance(raw, list):
            tokens = [str(item).strip() for item in raw if str(item).strip()]
            return "; ".join(tokens)
        return str(raw).strip()

    def _evidence_citations_valid(self, evidence: str, file_rel: str) -> bool:
        """Return True if *evidence* is non-empty.

        Previously this required strict ``file:line`` format, but models
        routinely produce perfectly usable prose-style evidence.  We now
        accept any non-empty string so that a single format mismatch
        doesn't cause the whole review/report to be replaced with a
        useless fallback stub.
        """
        text = str(evidence).strip()
        return bool(text)

    def _validate_rewrite_direction(
        self, rewrite_direction: str, target_file: str, rel: str, finding_index: int
    ) -> None:
        """Require only a non-empty rewrite direction.

        Previous strict checks (local line anchors, percentage-must-name-scene)
        caused entire reviews to be discarded when the model wrote
        perfectly usable prose-style directions.
        """
        text = str(rewrite_direction).strip()
        if not text:
            raise PipelineError(f"{rel} finding #{finding_index} rewrite_direction is empty")

    def _validate_acceptance_test(
        self, acceptance_test: str, target_file: str, rel: str, finding_index: int
    ) -> None:
        """Require only a non-empty acceptance test.

        Previous strict checks (local line anchors, measurability tokens)
        caused entire reviews to be discarded when the model wrote
        qualitative but perfectly actionable tests like "PASS if
        character voices are distinct throughout the scene."
        """
        text = str(acceptance_test).strip()
        if not text:
            raise PipelineError(f"{rel} finding #{finding_index} acceptance_test is empty")


    def _merge_evidence_citations(self, a: str, b: str) -> str:
        pieces = []
        for raw in (a, b):
            for item in re.split(r"[;,]\s*", str(raw).strip()):
                token = item.strip()
                if token:
                    pieces.append(token)
        deduped: list[str] = []
        seen: set[str] = set()
        for item in pieces:
            if item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return "; ".join(deduped)

    def _enrich_finding_for_revision_packet(
        self, cycle: int, finding: dict[str, Any]
    ) -> dict[str, Any]:
        enriched = dict(finding)
        locator_excerpts: dict[str, list[dict[str, str]]] = {}
        for field_name in ("evidence", "problem", "rewrite_direction", "acceptance_test"):
            field_value = str(enriched.get(field_name, "")).strip()
            if not field_value:
                continue
            excerpts = self._compiled_novel_locator_excerpts_from_text(field_value)
            if excerpts:
                locator_excerpts[field_name] = excerpts
        if locator_excerpts:
            enriched["locator_excerpts"] = locator_excerpts
        return enriched

    def _compiled_novel_locator_excerpts_from_text(
        self, text: str
    ) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for span in self._extract_line_citation_spans(text):
            file_rel = span["file_rel"]
            if not self._is_compiled_novel_path(file_rel):
                continue
            excerpt = self._line_span_excerpt(
                self.run_dir / file_rel,
                start_line=span["start_line"],
                end_line=span["end_line"],
                max_lines=12,
                max_chars=1200,
            )
            if not excerpt:
                continue
            out.append(
                {
                    "citation": span["citation"],
                    "source_file": file_rel,
                    "excerpt": excerpt,
                }
            )
        return out

    def _extract_line_citation_spans(self, text: str) -> list[dict[str, Any]]:
        range_re = re.compile(
            r"`?(?P<file>[A-Za-z0-9_./-]+\.md):(?P<start>\d+)`?\s*[-–]\s*`?"
            r"(?:(?P<file2>[A-Za-z0-9_./-]+\.md):)?(?P<end>\d+)`?"
        )
        single_re = re.compile(r"`?(?P<file>[A-Za-z0-9_./-]+\.md):(?P<line>\d+)`?")

        spans: list[tuple[int, dict[str, Any]]] = []
        occupied: list[tuple[int, int]] = []

        for match in range_re.finditer(text):
            file_rel = match.group("file")
            file_rel_2 = match.group("file2")
            if file_rel_2 and file_rel_2 != file_rel:
                continue
            start_line = int(match.group("start"))
            end_line = int(match.group("end"))
            if end_line < start_line:
                start_line, end_line = end_line, start_line
            spans.append(
                (
                    match.start(),
                    {
                        "file_rel": file_rel,
                        "start_line": start_line,
                        "end_line": end_line,
                        "citation": f"{file_rel}:{start_line}-{end_line}",
                    },
                )
            )
            occupied.append((match.start(), match.end()))

        def overlaps_existing(start: int, end: int) -> bool:
            return any(
                start < existing_end and end > existing_start
                for existing_start, existing_end in occupied
            )

        for match in single_re.finditer(text):
            if overlaps_existing(match.start(), match.end()):
                continue
            file_rel = match.group("file")
            line_no = int(match.group("line"))
            spans.append(
                (
                    match.start(),
                    {
                        "file_rel": file_rel,
                        "start_line": line_no,
                        "end_line": line_no,
                        "citation": f"{file_rel}:{line_no}",
                    },
                )
            )

        deduped: list[dict[str, Any]] = []
        seen: set[tuple[str, int, int]] = set()
        for _pos, span in sorted(spans, key=lambda row: row[0]):
            key = (span["file_rel"], span["start_line"], span["end_line"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(span)
        return deduped

    def _is_compiled_novel_path(self, file_rel: str) -> bool:
        return Path(file_rel).name.startswith("FINAL_NOVEL")

    def _line_span_excerpt(
        self, path: Path, start_line: int, end_line: int, max_lines: int, max_chars: int
    ) -> str:
        if not path.is_file():
            return ""
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines:
            return ""
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), end_line)
        if start_idx >= len(lines) or start_idx >= end_idx:
            return ""

        selected: list[str] = []
        for line_no in range(start_idx + 1, end_idx + 1):
            selected.append(f"{line_no}: {lines[line_no - 1]}")

        if len(selected) > max_lines:
            head_count = max_lines // 2
            tail_count = max_lines - head_count
            selected = selected[:head_count] + ["[...]"] + selected[-tail_count:]

        excerpt = "\n".join(selected).strip()
        if len(excerpt) > max_chars:
            excerpt = excerpt[:max_chars].rstrip() + "..."
        return excerpt

    def _head_excerpt(self, path: Path, max_lines: int, max_chars: int) -> str:
        if not path.is_file():
            return ""
        lines = path.read_text(encoding="utf-8").splitlines()
        excerpt = "\n".join(lines[:max_lines]).strip()
        if len(excerpt) > max_chars:
            excerpt = excerpt[:max_chars].rstrip() + "..."
        return excerpt

    def _tail_excerpt(self, path: Path, max_lines: int, max_chars: int) -> str:
        if not path.is_file():
            return ""
        lines = path.read_text(encoding="utf-8").splitlines()
        excerpt = "\n".join(lines[-max_lines:]).strip()
        if len(excerpt) > max_chars:
            excerpt = "..." + excerpt[-max_chars:].lstrip()
        return excerpt

    def _sha256_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _list_workspace_files(self, workspace: Path) -> set[str]:
        out: set[str] = set()
        for p in workspace.rglob("*"):
            if p.is_file():
                out.add(p.relative_to(workspace).as_posix())
        return out

    def _is_allowed_aux_workspace_file(self, rel: str) -> bool:
        if rel == ".DS_Store":
            return True
        if rel == ".claude.json" or rel.startswith(".claude/"):
            return True
        if rel.startswith("out/") and rel.endswith(".json") and self._soft_validation_enabled():
            return True
        if rel.endswith(".tmp") or rel.endswith(".log"):
            return True
        aux_prefixes = (".codex/", ".cache/", ".tmp/", "tmp/")
        return rel.startswith(aux_prefixes)

    def _assert_rel_path(self, rel: str) -> None:
        if os.path.isabs(rel):
            raise PipelineError(f"path must be relative: {rel}")
        if ".." in Path(rel).parts:
            raise PipelineError(f"path must not include '..': {rel}")

    def _count_by_key(self, rows: list[dict[str, Any]], key: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in rows:
            k = str(row.get(key, ""))
            counts[k] = counts.get(k, 0) + 1
        return counts

    def _tail_file(self, path: Path, max_lines: int = 20) -> str:
        if not path.is_file():
            return ""
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = lines[-max_lines:]
        return " | ".join(tail)

    def _is_retryable_job_error(self, exc: PipelineError) -> bool:
        text = str(exc).lower()
        retryable_tokens = (
            "codex exec failed rc=",
            "codex exec stalled",
            "claude exec failed rc=",
            "claude exec stalled",
            "job timed out after",
            "job did not produce required output",
            "required output missing in workspace",
        )
        return any(token in text for token in retryable_tokens)

    def _retry_backoff_seconds(self, attempt: int) -> int:
        base = max(0, JOB_EXEC_RETRY_BASE_SLEEP_SECONDS)
        cap = JOB_EXEC_RETRY_MAX_SLEEP_SECONDS
        if base <= 0:
            return 0
        wait = base * (2 ** max(0, attempt - 1))
        if cap > 0:
            return min(wait, cap)
        return wait

    def _retry_guidance_for_validation_error(self, validation_error: str, target_file: str) -> str:
        lower = str(validation_error).lower()
        guidance: list[str] = []
        if "evidence must cite" in lower:
            guidance.append(
                f"`evidence` must be bare citations only, e.g. `{target_file}:41; {target_file}:67`."
            )
            guidance.append("Do not include quotes, labels, or prose in `evidence`.")
        if "acceptance_test must cite concrete local lines/spans" in lower:
            guidance.append(
                "`acceptance_test` must include explicit anchors (file:line or lines X-Y) and measurable criteria."
            )
            guidance.append(
                f"Example shape: `At least 2 lines in {target_file}:120-150 retain contractions; no more than 1 clipped determiner.`"
            )
        if "rewrite_direction must include local line/span targets" in lower:
            guidance.append(
                f"`rewrite_direction` must include local targets in `{target_file}:<line>` or `lines X-Y` form."
            )
        if "percentage without named scenes" in lower:
            guidance.append(
                "Never use percentage-only rewrite directives unless the exact scene ids/names are explicitly listed."
            )
        if not guidance:
            return ""
        lines = "\n".join(f"- {item}" for item in guidance)
        return f"\nContract repair reminders:\n{lines}\n"

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _log(self, message: str) -> None:
        print(f"[novel-pipeline] {message}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Novel pipeline with premise generation, outlining, drafting, review, revision, and resume support."
    )
    parser.set_defaults(final_cycle_global_only=True)
    premise_group = parser.add_mutually_exclusive_group(required=True)
    premise_group.add_argument("--premise", type=str, help="Premise text")
    premise_group.add_argument(
        "--premise-file", type=str, help="Path to file containing premise text"
    )
    premise_group.add_argument(
        "--generate-premise",
        action="store_true",
        help="Generate a premise internally before the outline stage",
    )
    brief_group = parser.add_mutually_exclusive_group(required=False)
    brief_group.add_argument(
        "--premise-brief",
        type=str,
        help="Optional steering brief for premise generation",
    )
    brief_group.add_argument(
        "--premise-brief-file",
        type=str,
        help="Path to file containing the optional steering brief for premise generation",
    )
    parser.add_argument(
        "--award-profile",
        type=str,
        default="major-award",
        help="Compatibility metadata only; premise search is award-agnostic (default: major-award)",
    )
    parser.add_argument(
        "--premise-seed",
        type=str,
        default="",
        help="Optional seed for deterministic premise-search replay",
    )
    parser.add_argument(
        "--premise-reroll-max",
        type=int,
        default=4,
        help="Maximum rerolls after insufficient unique premise clusters (default: 4)",
    )
    parser.add_argument(
        "--premise-candidate-count",
        type=int,
        default=30,
        help="Number of premise candidates to generate before deduplication (default: 30)",
    )
    parser.add_argument(
        "--premise-generation-batch-size",
        type=int,
        default=6,
        help="How many premise candidates to generate per model batch (default: 6)",
    )
    parser.add_argument(
        "--premise-min-unique-clusters",
        type=int,
        default=8,
        help="Minimum number of unique premise clusters required before selection (default: 8)",
    )
    parser.add_argument(
        "--premise-shortlist-size",
        type=int,
        default=6,
        help="How many unique representatives to keep before the final random draw (default: 6)",
    )

    parser.add_argument(
        "--run-dir",
        type=str,
        default="",
        help="Run directory (default: ./runs/<timestamp>_<slug>)",
    )
    parser.add_argument("--max-cycles", type=int, default=2)
    parser.add_argument("--min-cycles", type=int, default=2)
    parser.add_argument(
        "--add-cycles",
        type=int,
        default=0,
        help="Append this many new cycles after the last completed successful cycle in an existing run-dir.",
    )
    parser.add_argument("--max-parallel-drafts", type=int, default=6)
    parser.add_argument("--max-parallel-reviews", type=int, default=6)
    parser.add_argument("--max-parallel-revisions", type=int, default=6)
    parser.add_argument(
        "--provider",
        type=str,
        default=os.environ.get("AGENT_PROVIDER", "codex"),
        help="Execution provider: codex | claude (default: codex)",
    )
    parser.add_argument(
        "--premise-provider",
        type=str,
        default="",
        help="Optional provider override for premise-search jobs.",
    )
    parser.add_argument(
        "--outline-provider",
        type=str,
        default="",
        help="Optional provider override for outline jobs.",
    )
    parser.add_argument(
        "--draft-provider",
        type=str,
        default="",
        help="Optional provider override for draft and expand jobs.",
    )
    parser.add_argument(
        "--review-provider",
        type=str,
        default="",
        help="Optional provider override for chapter-review jobs.",
    )
    parser.add_argument(
        "--full-review-provider",
        type=str,
        default="",
        help="Optional provider override for full-book review jobs.",
    )
    parser.add_argument(
        "--cross-chapter-audit-provider",
        type=str,
        default="",
        help="Optional provider override for cross-chapter audit jobs.",
    )
    parser.add_argument(
        "--local-window-audit-provider",
        type=str,
        default="",
        help="Optional provider override for local-window audit jobs only.",
    )
    parser.add_argument(
        "--revision-provider",
        type=str,
        default="",
        help="Optional provider override for revision and continuity jobs.",
    )
    parser.add_argument(
        "--aggregation-provider",
        type=str,
        default="",
        help="Optional provider override for LLM aggregation jobs only.",
    )
    parser.add_argument(
        "--revision-dialogue-provider",
        type=str,
        default="",
        help="Optional provider override for the dialogue/idiolect revision pass only.",
    )
    parser.add_argument("--model", type=str, default=os.environ.get("MODEL", ""))
    parser.add_argument(
        "--reasoning-effort",
        type=str,
        default=os.environ.get("REASONING_EFFORT", ""),
        help="Shared effort knob. Codex receives model_reasoning_effort; Claude maps xhigh->max.",
    )
    parser.add_argument(
        "--validation-mode",
        type=str,
        default=os.environ.get("VALIDATION_MODE", "lenient"),
        help="Validation strictness: strict | balanced | lenient (default: lenient)",
    )
    parser.add_argument(
        "--outline-review-cycles",
        type=int,
        default=1,
        help="How many outline review/revision passes to run before drafting (default: 1, max: 2).",
    )
    parser.add_argument(
        "--final-cycle-global-only",
        dest="final_cycle_global_only",
        action="store_true",
        help="On multi-cycle runs, skip chapter review on the final cycle and rely on full-book, cross-chapter, and local-window review only.",
    )
    parser.add_argument(
        "--no-final-cycle-global-only",
        dest="final_cycle_global_only",
        action="store_false",
        help="Disable global-only final-cycle mode and continue running chapter review on the last cycle.",
    )
    parser.add_argument(
        "--skip-outline-review",
        action="store_true",
        help="Skip the outline review/revision loop and draft directly from the base outline.",
    )
    parser.add_argument(
        "--outline-revision-provider",
        type=str,
        default="",
        help="Optional provider override for outline revision jobs only.",
    )
    parser.add_argument(
        "--skip-cross-chapter-audit",
        action="store_true",
        help="Skip the cross-chapter audit stage during review/aggregation.",
    )
    parser.add_argument(
        "--skip-local-window-audit",
        action="store_true",
        help="Skip the local-window audit stage when it is enabled.",
    )
    parser.add_argument(
        "--require-local-window-for-revision",
        action="store_true",
        help="Require local-window audit artifacts before revision once the stage is enabled.",
    )
    parser.add_argument(
        "--local-window-size",
        type=int,
        default=LOCAL_WINDOW_SIZE,
        help=f"How many consecutive chapters each local-window audit reviews (default: {LOCAL_WINDOW_SIZE}).",
    )
    parser.add_argument(
        "--local-window-overlap",
        type=int,
        default=LOCAL_WINDOW_OVERLAP,
        help=f"How many chapters consecutive local-window audits overlap by (default: {LOCAL_WINDOW_OVERLAP}).",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--dry-run-chapter-count",
        type=int,
        default=18,
        help="Only used with --dry-run; clamped to 16..20",
    )
    parser.add_argument(
        "--agent-bin",
        type=str,
        default=os.environ.get("AGENT_BIN", ""),
        help="Path to the provider CLI binary. Falls back to CODEX_BIN/CLAUDE_BIN/provider defaults.",
    )
    parser.add_argument("--job-timeout-seconds", type=int, default=3600)
    parser.add_argument(
        "--job-idle-timeout-seconds",
        type=int,
        default=1800,
        help="Kill a provider job if its JSONL output stops growing for this many seconds (0 to disable). Default: 1800",
    )
    return parser.parse_args()


def _load_optional_text_arg(value: str | None, file_path: str | None, label: str) -> str | None:
    if value:
        text = value.strip()
    elif file_path:
        path = Path(file_path)
        if not path.is_file():
            raise PipelineError(f"{label} file not found: {path}")
        text = path.read_text(encoding="utf-8").strip()
    else:
        return None
    if not text:
        raise PipelineError(f"{label} cannot be empty")
    return text


def load_premise_inputs(args: argparse.Namespace) -> tuple[str | None, str, str | None]:
    if args.generate_premise:
        premise_mode = "generate"
        premise = None
    else:
        premise_mode = "user"
        premise = _load_optional_text_arg(args.premise, args.premise_file, "premise")
    premise_brief = _load_optional_text_arg(
        args.premise_brief, args.premise_brief_file, "premise brief"
    )
    if premise_mode != "generate" and premise_brief is not None:
        raise PipelineError(
            "--premise-brief and --premise-brief-file require --generate-premise"
        )
    return premise, premise_mode, premise_brief


def slugify(text: str) -> str:
    lowered = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    if not slug:
        slug = "novel"
    return slug[:40]


def resolve_run_dir(repo_root: Path, run_dir_arg: str, slug_source: str) -> Path:
    if run_dir_arg:
        run_dir = Path(run_dir_arg).expanduser()
        if not run_dir.is_absolute():
            run_dir = (repo_root / run_dir).resolve()
        return run_dir
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return (repo_root / "runs" / f"{ts}_{slugify(slug_source)}").resolve()


def _load_existing_success_cycle(run_dir: Path) -> int:
    for path in (
        run_dir / "reports" / "final_status.json",
        run_dir / "reports" / "final_report.json",
    ):
        if not path.is_file():
            continue
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(loaded, dict):
            continue
        status = str(loaded.get("status", "")).strip().upper()
        success_cycle = loaded.get("success_cycle")
        if status == "PASS" and isinstance(success_cycle, int) and success_cycle >= 1:
            return success_cycle
    return 0


def _resolve_provider(value: str) -> str:
    provider = str(value).strip().lower() or "codex"
    if provider not in PROVIDER_VALUES:
        allowed = ", ".join(sorted(PROVIDER_VALUES))
        raise PipelineError(f"--provider must be one of: {allowed}")
    return provider


def _resolve_default_model(provider: str, model_value: str) -> str:
    model = str(model_value).strip()
    return model or DEFAULT_MODEL_BY_PROVIDER[provider]


def _resolve_reasoning_effort(provider: str, effort_value: str) -> str:
    effort = str(effort_value).strip().lower()
    if not effort:
        return DEFAULT_REASONING_EFFORT_BY_PROVIDER[provider]
    if provider == "claude":
        mapped = CLAUDE_EFFORT_MAP.get(effort)
        if not mapped:
            allowed = ", ".join(sorted(CLAUDE_EFFORT_MAP))
            raise PipelineError(
                f"--reasoning-effort must map cleanly for Claude; use one of: {allowed}"
            )
        return mapped
    return effort


def _resolve_agent_bin(
    provider: str, agent_bin_value: str, *, allow_shared_overrides: bool = True
) -> str:
    def resolve_candidate(candidate: str) -> str | None:
        raw = str(candidate).strip()
        if not raw:
            return None
        expanded = os.path.expanduser(raw)
        if os.path.isfile(expanded):
            return expanded
        resolved = shutil.which(raw)
        if resolved:
            return resolved
        return None

    explicit = str(agent_bin_value).strip()
    if allow_shared_overrides and explicit:
        return resolve_candidate(explicit) or explicit
    env_override = os.environ.get("AGENT_BIN", "").strip() if allow_shared_overrides else ""
    if env_override:
        return resolve_candidate(env_override) or env_override
    if provider == "codex":
        for candidate in (
            os.environ.get("CODEX_BIN", "").strip(),
            "codex",
            "/Applications/Codex.app/Contents/Resources/codex",
        ):
            resolved = resolve_candidate(candidate)
            if resolved:
                return resolved
        return "codex"
    for candidate in (
        os.environ.get("CLAUDE_BIN", "").strip(),
        "claude",
        str(Path.home() / ".local" / "bin" / "claude"),
    ):
        resolved = resolve_candidate(candidate)
        if resolved:
            return resolved
    return "claude"


def _resolve_stage_profiles(
    *,
    global_provider: str,
    global_model: str,
    global_reasoning_effort: str,
    global_agent_bin: str,
    args: argparse.Namespace,
) -> dict[str, ExecutionProfile]:
    profiles: dict[str, ExecutionProfile] = {
        stage_group: ExecutionProfile(
            provider=global_provider,
            agent_bin=global_agent_bin,
            model=global_model,
            reasoning_effort=global_reasoning_effort,
        )
        for stage_group in STAGE_GROUP_VALUES
    }
    for stage_group in STAGE_GROUP_VALUES:
        raw = str(getattr(args, f"{stage_group}_provider", "")).strip()
        if not raw:
            continue
        provider = _resolve_provider(raw)
        if provider == global_provider:
            continue
        profiles[stage_group] = ExecutionProfile(
            provider=provider,
            agent_bin=_resolve_agent_bin(
                provider, "", allow_shared_overrides=False
            ),
            model=_resolve_default_model(provider, ""),
            reasoning_effort=_resolve_reasoning_effort(provider, ""),
        )
    for stage_name, (stage_group, arg_name) in STAGE_PROVIDER_OVERRIDE_SPECS.items():
        raw = str(getattr(args, arg_name, "")).strip()
        if not raw:
            continue
        provider = _resolve_provider(raw)
        base_profile = profiles[stage_group]
        if provider == base_profile.provider:
            continue
        profiles[stage_name] = ExecutionProfile(
            provider=provider,
            agent_bin=_resolve_agent_bin(
                provider, "", allow_shared_overrides=False
            ),
            model=_resolve_default_model(provider, ""),
            reasoning_effort=_resolve_reasoning_effort(provider, ""),
        )
    return profiles


def _resolve_revision_pass_profiles(
    *,
    stage_profiles: dict[str, ExecutionProfile],
    args: argparse.Namespace,
) -> dict[str, ExecutionProfile]:
    profiles: dict[str, ExecutionProfile] = {}
    revision_base = stage_profiles["revision"]
    raw = str(getattr(args, "revision_dialogue_provider", "")).strip()
    if raw:
        provider = _resolve_provider(raw)
        if provider == revision_base.provider:
            profiles[REVISION_DIALOGUE_PASS_KEY] = revision_base
        else:
            profiles[REVISION_DIALOGUE_PASS_KEY] = ExecutionProfile(
                provider=provider,
                agent_bin=_resolve_agent_bin(provider, "", allow_shared_overrides=False),
                model=_resolve_default_model(provider, ""),
                reasoning_effort=_resolve_reasoning_effort(provider, ""),
            )
    return profiles


def build_config(repo_root: Path, args: argparse.Namespace) -> RunnerConfig:
    premise, premise_mode, premise_brief = load_premise_inputs(args)
    if args.add_cycles < 0:
        raise PipelineError("--add-cycles must be >= 0")
    if args.max_cycles < 1:
        raise PipelineError("--max-cycles must be >= 1")
    if args.min_cycles < 1:
        raise PipelineError("--min-cycles must be >= 1")
    if args.max_cycles < args.min_cycles:
        raise PipelineError("--max-cycles must be >= --min-cycles")
    for name in (
        "max_parallel_drafts",
        "max_parallel_reviews",
        "max_parallel_revisions",
    ):
        if getattr(args, name) < 1:
            raise PipelineError(f"--{name.replace('_', '-')} must be >= 1")
    if args.job_timeout_seconds < 60:
        raise PipelineError("--job-timeout-seconds must be >= 60")
    if args.job_idle_timeout_seconds < 0:
        raise PipelineError("--job-idle-timeout-seconds must be >= 0")
    if args.outline_review_cycles < 1 or args.outline_review_cycles > 2:
        raise PipelineError("--outline-review-cycles must be between 1 and 2")
    if args.local_window_size < 2:
        raise PipelineError("--local-window-size must be >= 2")
    if args.local_window_overlap < 0:
        raise PipelineError("--local-window-overlap must be >= 0")
    if args.local_window_overlap >= args.local_window_size:
        raise PipelineError(
            "--local-window-overlap must be smaller than --local-window-size"
        )
    if args.premise_reroll_max < 0:
        raise PipelineError("--premise-reroll-max must be >= 0")
    if args.premise_candidate_count < 1:
        raise PipelineError("--premise-candidate-count must be >= 1")
    if args.premise_generation_batch_size < 1:
        raise PipelineError("--premise-generation-batch-size must be >= 1")
    if args.premise_min_unique_clusters < 1:
        raise PipelineError("--premise-min-unique-clusters must be >= 1")
    if args.premise_shortlist_size < 1:
        raise PipelineError("--premise-shortlist-size must be >= 1")
    if args.premise_shortlist_size > args.premise_candidate_count:
        raise PipelineError("--premise-shortlist-size cannot exceed --premise-candidate-count")
    if args.premise_min_unique_clusters > args.premise_candidate_count:
        raise PipelineError(
            "--premise-min-unique-clusters cannot exceed --premise-candidate-count"
        )
    validation_mode = str(args.validation_mode).strip().lower()
    if validation_mode not in VALIDATION_MODES:
        allowed = ", ".join(sorted(VALIDATION_MODES))
        raise PipelineError(f"--validation-mode must be one of: {allowed}")
    provider = _resolve_provider(args.provider)
    award_profile = str(args.award_profile).strip()
    if not award_profile:
        award_profile = "major-award"
    premise_seed = str(args.premise_seed).strip() or None
    model = _resolve_default_model(provider, args.model)
    reasoning_effort = _resolve_reasoning_effort(provider, args.reasoning_effort)
    agent_bin = _resolve_agent_bin(provider, args.agent_bin)
    stage_profiles = _resolve_stage_profiles(
        global_provider=provider,
        global_model=model,
        global_reasoning_effort=reasoning_effort,
        global_agent_bin=agent_bin,
        args=args,
    )
    revision_pass_profiles = _resolve_revision_pass_profiles(
        stage_profiles=stage_profiles,
        args=args,
    )

    slug_source = premise or premise_brief or "auto-premise"
    run_dir = resolve_run_dir(repo_root, args.run_dir, slug_source)
    add_cycles = int(args.add_cycles or 0)
    base_completed_cycles = 0
    max_cycles = args.max_cycles
    if add_cycles:
        if not run_dir.is_dir():
            raise PipelineError(
                "--add-cycles requires --run-dir to point to an existing completed run"
            )
        base_completed_cycles = _load_existing_success_cycle(run_dir)
        if base_completed_cycles < 1:
            raise PipelineError(
                "--add-cycles requires reports/final_status.json (or final_report.json) with status=PASS and success_cycle >= 1"
            )
        max_cycles = base_completed_cycles + add_cycles
        if max_cycles < args.min_cycles:
            raise PipelineError(
                "--add-cycles results in total --max-cycles smaller than --min-cycles; "
                "lower --min-cycles or add more cycles"
            )
    return RunnerConfig(
        premise=premise,
        premise_mode=premise_mode,
        premise_brief=premise_brief,
        award_profile=award_profile,
        premise_seed=premise_seed,
        premise_reroll_max=args.premise_reroll_max,
        premise_candidate_count=args.premise_candidate_count,
        premise_generation_batch_size=args.premise_generation_batch_size,
        premise_min_unique_clusters=args.premise_min_unique_clusters,
        premise_shortlist_size=args.premise_shortlist_size,
        run_dir=run_dir,
        max_cycles=max_cycles,
        min_cycles=args.min_cycles,
        max_parallel_drafts=args.max_parallel_drafts,
        max_parallel_reviews=args.max_parallel_reviews,
        max_parallel_revisions=args.max_parallel_revisions,
        provider=provider,
        agent_bin=agent_bin,
        model=model,
        reasoning_effort=reasoning_effort,
        stage_profiles=stage_profiles,
        revision_pass_profiles=revision_pass_profiles,
        dry_run=bool(args.dry_run),
        dry_run_chapter_count=args.dry_run_chapter_count,
        job_timeout_seconds=args.job_timeout_seconds,
        job_idle_timeout_seconds=args.job_idle_timeout_seconds,
        validation_mode=validation_mode,
        outline_review_cycles=args.outline_review_cycles,
        final_cycle_global_only=bool(args.final_cycle_global_only),
        skip_outline_review=bool(args.skip_outline_review),
        skip_cross_chapter_audit=bool(args.skip_cross_chapter_audit),
        skip_local_window_audit=bool(args.skip_local_window_audit),
        require_local_window_for_revision=bool(args.require_local_window_for_revision),
        local_window_size=args.local_window_size,
        local_window_overlap=args.local_window_overlap,
        add_cycles=add_cycles,
        base_completed_cycles=base_completed_cycles,
    )


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    try:
        args = parse_args()
        cfg = build_config(repo_root, args)
        runner = NovelPipelineRunner(repo_root=repo_root, cfg=cfg)
        return runner.run()
    except PipelineError as exc:
        print(f"[novel-pipeline][error] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


V5Runner = NovelPipelineRunner
