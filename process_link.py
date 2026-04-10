import os
import re
import shutil
import subprocess
import sys
import json
import time
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import requests
from dotenv import load_dotenv
from faster_whisper import WhisperModel


load_dotenv()


INSTAGRAM_URL_RE = re.compile(r"https?://(?:www\.)?instagram\.com/[^\s>]+", re.IGNORECASE)
DEFAULT_TOP_LEVEL_CATEGORIES = [
    "design",
    "productivity",
    "ai",
    "marketing",
    "business",
    "coding",
    "education",
    "health",
    "mindset",
    "general",
]
DEFAULT_TAG_PREFIXES = ["topic", "domain", "tool", "format"]


@dataclass(frozen=True)
class PipelineConfig:
    vault_path: Path
    ollama_model: str
    openrouter_model: str
    openrouter_api_key: Optional[str]
    temp_dir: Path
    processed_db_path: Path
    keep_temp: bool
    keep_temp_on_failure: bool
    cookies_from_browser: Optional[str]
    cookies_file: Optional[Path]
    pipeline_mode: str
    graph_min_entity_confidence: float
    max_topics_per_video: int
    taxonomy_path: Path
    taxonomy_mode: str
    taxonomy_auto_max_categories: int
    taxonomy_auto_min_slug_len: int
    taxonomy_auto_max_slug_len: int
    visual_context_enabled: bool
    max_keyframes_analyzed: int
    max_images_per_note: int
    frame_sampling_mode: str
    frame_interval_seconds: int
    ocr_tesseract_cmd: str
    consistency_check_enabled: bool
    min_alignment_score_for_strict_mode: float
    rewrite_contradicted_claims: bool
    title_style: str
    allow_filename_date_prefix: bool
    note_filename_style: str
    migrate_existing_note_filenames: bool
    rewrite_vault_links_on_migration: bool
    transcript_gate_enabled: bool
    transcript_min_words: int
    transcript_min_unique_words: int
    transcript_min_alpha_ratio: float
    transcript_gate_allow_force: bool
    caption_context_enabled: bool
    caption_mismatch_gate_enabled: bool
    caption_min_words: int
    transcript_caption_min_overlap: float
    caption_primary_when_transcript_weak: bool
    subprocess_verbose_logs: bool
    emoji_logs_enabled: bool
    eta_base_seconds: float
    eta_per_video_second: float
    eta_llm_overhead_seconds: float
    eta_history_path: Path
    eta_history_window: int
    eta_min_samples: int
    eta_quantile: float


@dataclass(frozen=True)
class TaxonomyConfig:
    categories: list[str]
    tag_prefixes: list[str]
    synonyms: dict[str, str]


@dataclass(frozen=True)
class Entity:
    name: str
    kind: str
    confidence: float


@dataclass(frozen=True)
class GraphPayload:
    title: str
    category: str
    subtopics: list[str]
    tags: list[str]
    entities: list[Entity]
    summary_markdown: str
    visual_context: str
    alignment_score: float
    alignment_context: str
    title_generated_by: str
    verification: dict[str, Any]
    transcript_useful: bool
    transcript_quality_reasons: list[str]
    caption_available: bool
    caption_primary_context: bool
    transcript_caption_mismatch: bool
    transcript_caption_mismatch_reasons: list[str]


class LowTranscriptSignalError(Exception):
    def __init__(self, *, url: str, reasons: list[str], metrics: dict[str, Any]):
        super().__init__("No transcript detected")
        self.url = url
        self.reasons = reasons
        self.metrics = metrics


@dataclass(frozen=True)
class ProcessRunResult:
    note_path: Path
    elapsed_seconds: float
    video_duration_seconds: float
    estimated_total_seconds: float
    estimated_remaining_seconds: float = 0.0


_llm_stage_stats: dict[str, Any] = {"total_calls": 0, "total_elapsed_s": 0.0, "stages": defaultdict(int)}
_eta_history_lock = threading.Lock()
_eta_runtime_lock = threading.Lock()


def _new_history_state() -> dict[str, Any]:
    return {"version": 1, "stages": {}}


def _load_eta_history(cfg: PipelineConfig) -> dict[str, Any]:
    path = cfg.eta_history_path
    if not path.exists():
        return _new_history_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _new_history_state()
        stages = data.get("stages")
        if not isinstance(stages, dict):
            return _new_history_state()
        return {"version": int(data.get("version", 1)), "stages": stages}
    except Exception:
        return _new_history_state()


def _save_eta_history(cfg: PipelineConfig, history: dict[str, Any]) -> None:
    cfg.eta_history_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.eta_history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    xs = sorted(float(v) for v in values)
    if len(xs) == 1:
        return xs[0]
    pos = max(0.0, min(1.0, q)) * (len(xs) - 1)
    low = int(pos)
    high = min(len(xs) - 1, low + 1)
    frac = pos - low
    return (xs[low] * (1.0 - frac)) + (xs[high] * frac)


def _history_stage_values(history: dict[str, Any], key: str, stage: str) -> list[float]:
    stages = history.get("stages", {})
    by_key = stages.get(key, {}) if isinstance(stages, dict) else {}
    values = by_key.get(stage, []) if isinstance(by_key, dict) else []
    out: list[float] = []
    for v in values if isinstance(values, list) else []:
        try:
            out.append(max(0.0, float(v)))
        except Exception:
            pass
    return out


def _append_history_stage(cfg: PipelineConfig, *, key: str, stage: str, elapsed_seconds: float) -> None:
    with _eta_history_lock:
        history = _load_eta_history(cfg)
        stages = history.setdefault("stages", {})
        by_key = stages.setdefault(key, {})
        series = by_key.setdefault(stage, [])
        if not isinstance(series, list):
            series = []
            by_key[stage] = series
        series.append(max(0.0, float(elapsed_seconds)))
        if len(series) > cfg.eta_history_window:
            del series[:-cfg.eta_history_window]
        _save_eta_history(cfg, history)


def _default_stage_estimates(video_duration_seconds: float, *, cfg: PipelineConfig) -> dict[str, float]:
    total = _estimate_total_runtime_seconds(video_duration_seconds, cfg=cfg)
    # Conservative split tuned for OpenRouter-heavy workloads.
    fractions = {
        "download_video": 0.04,
        "extract_keyframes": 0.05,
        "extract_audio": 0.01,
        "llm_classify": 0.10,
        "llm_entities": 0.35,
        "llm_summary": 0.10,
        "llm_verify": 0.20,
        "llm_title": 0.15,
    }
    return {k: max(0.2, total * v) for k, v in fractions.items()}


def _estimate_stage_seconds(
    *,
    cfg: PipelineConfig,
    history: dict[str, Any],
    stage: str,
    provider_key: str,
    default_seconds: float,
) -> tuple[float, int]:
    llm_key = provider_key
    pipeline_key = "pipeline/default"
    target_key = llm_key if stage.startswith("llm_") else pipeline_key
    values = _history_stage_values(history, target_key, stage)
    if len(values) >= cfg.eta_min_samples:
        return max(0.2, _quantile(values, cfg.eta_quantile)), len(values)
    return max(0.2, float(default_seconds)), len(values)


_active_run_snapshots: dict[str, dict[str, Any]] = {}
_thread_run_url = threading.local()


def _set_active_run_url(url: Optional[str]) -> None:
    setattr(_thread_run_url, "url", url)


def _get_active_run_url() -> Optional[str]:
    return getattr(_thread_run_url, "url", None)


def get_run_eta_snapshot(url: str) -> Optional[dict[str, Any]]:
    key = (url or "").strip()
    if not key:
        return None
    with _eta_runtime_lock:
        snap = _active_run_snapshots.get(key)
        return dict(snap) if isinstance(snap, dict) else None


def _update_run_snapshot(url: str, updates: dict[str, Any]) -> None:
    if not url:
        return
    with _eta_runtime_lock:
        current = dict(_active_run_snapshots.get(url, {}))
        current.update(updates)
        _active_run_snapshots[url] = current


def _remove_run_snapshot(url: str) -> None:
    if not url:
        return
    with _eta_runtime_lock:
        _active_run_snapshots.pop(url, None)


def _reset_llm_stage_stats() -> None:
    _llm_stage_stats["total_calls"] = 0
    _llm_stage_stats["total_elapsed_s"] = 0.0
    _llm_stage_stats["stages"] = defaultdict(int)


def _record_llm_stage_call(*, stage: str, elapsed_s: float) -> None:
    label = (stage or "unspecified").strip() or "unspecified"
    _llm_stage_stats["total_calls"] = int(_llm_stage_stats.get("total_calls", 0)) + 1
    _llm_stage_stats["total_elapsed_s"] = float(_llm_stage_stats.get("total_elapsed_s", 0.0)) + max(0.0, elapsed_s)
    stages = _llm_stage_stats.get("stages")
    if not isinstance(stages, dict):
        stages = defaultdict(int)
        _llm_stage_stats["stages"] = stages
    stages[label] = int(stages.get(label, 0)) + 1


def _llm_stage_summary() -> str:
    total_calls = int(_llm_stage_stats.get("total_calls", 0))
    total_elapsed = float(_llm_stage_stats.get("total_elapsed_s", 0.0))
    stages = _llm_stage_stats.get("stages", {})
    if not total_calls:
        return "[LLM] SUMMARY calls=0 elapsed=0.00s stages=(none)"
    stage_pairs = sorted(((str(k), int(v)) for k, v in dict(stages).items()), key=lambda kv: (-kv[1], kv[0]))
    stage_text = ", ".join(f"{name}:{count}" for name, count in stage_pairs) or "(none)"
    return f"[LLM] SUMMARY calls={total_calls} elapsed={total_elapsed:.2f}s stages={stage_text}"


def _parse_title_style(raw: Optional[str]) -> str:
    """Normalize TITLE_STYLE env to clean | heuristic | summary_heading | category."""
    s = (raw or "").strip().lower() or "clean"
    aliases = {
        "fallback": "heuristic",
        "keywords": "heuristic",
        "messy": "heuristic",
        "summary": "summary_heading",
    }
    s = aliases.get(s, s)
    valid = frozenset({"clean", "heuristic", "summary_heading", "category"})
    if s in valid:
        return s
    print(
        "[CONFIG] TITLE_STYLE="
        f"{raw!r} is not recognized; valid: clean, heuristic, summary_heading, category "
        "(aliases: fallback, keywords, messy → heuristic; summary → summary_heading). Using heuristic."
    )
    return "heuristic"


def _cfg() -> PipelineConfig:
    vault = Path(os.environ["OBSIDIAN_VAULT_PATH"])
    model = os.getenv("OLLAMA_MODEL", "llama3.1")
    # Ollama commonly exposes models as `name:latest`; accept `name` and normalize.
    if ":" not in model:
        model = f"{model}:latest"
    return PipelineConfig(
        vault_path=vault,
        ollama_model=model,
        openrouter_model=os.getenv("OPENROUTER_MODEL", "openrouter/free"),
        openrouter_api_key=(os.getenv("OPENROUTER_API_KEY") or "").strip() or None,
        temp_dir=Path("temp"),
        processed_db_path=Path("processed.json"),
        keep_temp=os.getenv("KEEP_TEMP", "false").strip().lower() in {"1", "true", "yes", "y"},
        keep_temp_on_failure=os.getenv("KEEP_TEMP_ON_FAILURE", "true").strip().lower() in {"1", "true", "yes", "y"},
        cookies_from_browser=os.getenv("YTDLP_COOKIES_FROM_BROWSER") or None,
        cookies_file=Path(os.environ["YTDLP_COOKIES_FILE"]) if os.getenv("YTDLP_COOKIES_FILE") else None,
        pipeline_mode=(os.getenv("PIPELINE_MODE", "graph").strip().lower() or "graph"),
        graph_min_entity_confidence=float(os.getenv("GRAPH_MIN_ENTITY_CONFIDENCE", "0.55")),
        max_topics_per_video=max(1, int(os.getenv("MAX_TOPICS_PER_VIDEO", "6"))),
        taxonomy_path=Path(os.getenv("TAXONOMY_PATH", "taxonomy.json")),
        taxonomy_mode=(
            "auto"
            if (os.getenv("TAXONOMY_MODE", "static").strip().lower() or "static") == "auto"
            else "static"
        ),
        taxonomy_auto_max_categories=max(
            len(DEFAULT_TOP_LEVEL_CATEGORIES) + 1,
            int(os.getenv("TAXONOMY_AUTO_MAX_CATEGORIES", "48")),
        ),
        taxonomy_auto_min_slug_len=max(1, int(os.getenv("TAXONOMY_AUTO_MIN_SLUG_LEN", "2"))),
        taxonomy_auto_max_slug_len=max(2, min(80, int(os.getenv("TAXONOMY_AUTO_MAX_SLUG_LEN", "40")))),
        visual_context_enabled=os.getenv("VISUAL_CONTEXT_ENABLED", "true").strip().lower() in {"1", "true", "yes", "y"},
        max_keyframes_analyzed=max(1, int(os.getenv("MAX_KEYFRAMES_ANALYZED", "12"))),
        max_images_per_note=max(1, min(3, int(os.getenv("MAX_IMAGES_PER_NOTE", "3")))),
        frame_sampling_mode=(os.getenv("FRAME_SAMPLING_MODE", "interval").strip().lower() or "interval"),
        frame_interval_seconds=max(1, int(os.getenv("FRAME_INTERVAL_SECONDS", "2"))),
        ocr_tesseract_cmd=(os.getenv("OCR_TESSERACT_CMD", "tesseract").strip() or "tesseract"),
        consistency_check_enabled=os.getenv("CONSISTENCY_CHECK_ENABLED", "true").strip().lower() in {"1", "true", "yes", "y"},
        min_alignment_score_for_strict_mode=max(0.0, min(1.0, float(os.getenv("MIN_ALIGNMENT_SCORE_FOR_STRICT_MODE", "0.25")))),
        rewrite_contradicted_claims=os.getenv("REWRITE_CONTRADICTED_CLAIMS", "false").strip().lower() in {"1", "true", "yes", "y"},
        title_style=_parse_title_style(os.getenv("TITLE_STYLE", "clean")),
        allow_filename_date_prefix=os.getenv("ALLOW_FILENAME_DATE_PREFIX", "false").strip().lower() in {"1", "true", "yes", "y"},
        note_filename_style=(os.getenv("NOTE_FILENAME_STYLE", "human").strip().lower() or "human"),
        migrate_existing_note_filenames=os.getenv("MIGRATE_EXISTING_NOTE_FILENAMES", "true").strip().lower() in {"1", "true", "yes", "y"},
        rewrite_vault_links_on_migration=os.getenv("REWRITE_VAULT_LINKS_ON_MIGRATION", "true").strip().lower() in {"1", "true", "yes", "y"},
        transcript_gate_enabled=os.getenv("TRANSCRIPT_GATE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "y"},
        transcript_min_words=max(1, int(os.getenv("TRANSCRIPT_MIN_WORDS", "20"))),
        transcript_min_unique_words=max(1, int(os.getenv("TRANSCRIPT_MIN_UNIQUE_WORDS", "12"))),
        transcript_min_alpha_ratio=max(0.0, min(1.0, float(os.getenv("TRANSCRIPT_MIN_ALPHA_RATIO", "0.55")))),
        transcript_gate_allow_force=os.getenv("TRANSCRIPT_GATE_ALLOW_FORCE", "true").strip().lower() in {"1", "true", "yes", "y"},
        caption_context_enabled=os.getenv("CAPTION_CONTEXT_ENABLED", "true").strip().lower() in {"1", "true", "yes", "y"},
        caption_mismatch_gate_enabled=os.getenv("CAPTION_MISMATCH_GATE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "y"},
        caption_min_words=max(1, int(os.getenv("CAPTION_MIN_WORDS", "6"))),
        transcript_caption_min_overlap=max(0.0, min(1.0, float(os.getenv("TRANSCRIPT_CAPTION_MIN_OVERLAP", "0.08")))),
        caption_primary_when_transcript_weak=os.getenv("CAPTION_PRIMARY_WHEN_TRANSCRIPT_WEAK", "true").strip().lower() in {"1", "true", "yes", "y"},
        subprocess_verbose_logs=os.getenv("SUBPROCESS_VERBOSE_LOGS", "false").strip().lower() in {"1", "true", "yes", "y"},
        emoji_logs_enabled=os.getenv("EMOJI_LOGS_ENABLED", "true").strip().lower() in {"1", "true", "yes", "y"},
        eta_base_seconds=max(1.0, float(os.getenv("ETA_BASE_SECONDS", "8.0"))),
        eta_per_video_second=max(0.0, float(os.getenv("ETA_PER_VIDEO_SECOND", "0.75"))),
        eta_llm_overhead_seconds=max(0.0, float(os.getenv("ETA_LLM_OVERHEAD_SECONDS", "10.0"))),
        eta_history_path=Path(os.getenv("ETA_HISTORY_PATH", "eta-history.json")),
        eta_history_window=max(20, int(os.getenv("ETA_HISTORY_WINDOW", "200"))),
        eta_min_samples=max(1, int(os.getenv("ETA_MIN_SAMPLES", "3"))),
        eta_quantile=max(0.5, min(0.99, float(os.getenv("ETA_QUANTILE", "0.75")))),
    )


def _slugify_filename(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^a-z0-9\-]+", "", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "note"


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = (raw or "").strip()
        if not value:
            continue
        low = value.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(value)
    return out


def _load_taxonomy(cfg: PipelineConfig) -> TaxonomyConfig:
    if cfg.taxonomy_path.exists():
        try:
            data = json.loads(cfg.taxonomy_path.read_text(encoding="utf-8"))
            categories = [str(v).strip().lower() for v in data.get("categories", []) if str(v).strip()]
            tag_prefixes = [str(v).strip().lower() for v in data.get("tag_prefixes", []) if str(v).strip()]
            synonyms_obj = data.get("synonyms", {})
            synonyms = {str(k).strip().lower(): str(v).strip().lower() for k, v in synonyms_obj.items() if str(k).strip() and str(v).strip()}
            if categories and tag_prefixes:
                if "general" not in categories:
                    categories.append("general")
                return TaxonomyConfig(
                    categories=_dedupe_preserve_order(categories),
                    tag_prefixes=_dedupe_preserve_order(tag_prefixes),
                    synonyms=synonyms,
                )
        except Exception:
            pass
    return TaxonomyConfig(
        categories=DEFAULT_TOP_LEVEL_CATEGORIES[:],
        tag_prefixes=DEFAULT_TAG_PREFIXES[:],
        synonyms={},
    )


def _default_taxonomy_dict() -> dict[str, Any]:
    return {
        "categories": DEFAULT_TOP_LEVEL_CATEGORIES[:],
        "tag_prefixes": DEFAULT_TAG_PREFIXES[:],
        "synonyms": {},
    }


def _sanitize_taxonomy_category_slug(
    raw: str,
    *,
    min_len: int,
    max_len: int,
) -> Optional[str]:
    t = (raw or "").strip()
    if not t:
        return None
    s = t.lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\-]+", "", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    if not s or len(s) < min_len or len(s) > max_len:
        return None
    if s in {"unknown", "none", "n-a", "na"}:
        return None
    return s


def _merge_category_into_taxonomy_json(path: Path, new_category: str, *, max_categories: int) -> bool:
    """Append new_category to taxonomy JSON if under max_categories. Atomic replace on success."""
    new_category = (new_category or "").strip().lower()
    if not new_category or new_category == "general":
        return True
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = _default_taxonomy_dict()
        else:
            data = _default_taxonomy_dict()
        categories = [str(v).strip().lower() for v in data.get("categories", []) if str(v).strip()]
        tag_prefixes = [str(v).strip().lower() for v in data.get("tag_prefixes", []) if str(v).strip()]
        synonyms_obj = data.get("synonyms", {})
        if not isinstance(synonyms_obj, dict):
            synonyms_obj = {}
        synonyms = {
            str(k).strip().lower(): str(v).strip().lower()
            for k, v in synonyms_obj.items()
            if str(k).strip() and str(v).strip()
        }
        if not tag_prefixes:
            tag_prefixes = DEFAULT_TAG_PREFIXES[:]
        categories = _dedupe_preserve_order(categories)
        if "general" not in categories:
            categories.append("general")
        if new_category in categories:
            return True
        if len(categories) >= max_categories:
            print(
                f"[TAXONOMY] auto-merge skipped: at max categories ({max_categories}); "
                f"cannot add {new_category!r}"
            )
            return False
        categories.append(new_category)
        categories = _dedupe_preserve_order(categories)
        out = {
            "categories": categories,
            "tag_prefixes": _dedupe_preserve_order(tag_prefixes),
            "synonyms": synonyms,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.parent / f".{path.name}.{os.getpid()}.tmp"
        tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(str(tmp), str(path))
        print(f"[TAXONOMY] auto-merged new category: {new_category}")
        return True
    except Exception as e:
        print(f"[TAXONOMY] auto-merge failed: {e}")
        return False


def _apply_taxonomy_auto_merge(
    class_raw: Any,
    taxonomy: TaxonomyConfig,
    cfg: PipelineConfig,
) -> tuple[TaxonomyConfig, str]:
    if not isinstance(class_raw, dict):
        return taxonomy, "general"
    raw = str(class_raw.get("category", "general")).strip().lower() or "general"
    cats_lower = {c.lower() for c in taxonomy.categories}
    if raw in cats_lower:
        return taxonomy, raw
    slug = _sanitize_taxonomy_category_slug(
        str(class_raw.get("category", "")),
        min_len=cfg.taxonomy_auto_min_slug_len,
        max_len=cfg.taxonomy_auto_max_slug_len,
    )
    if slug and slug in cats_lower:
        return taxonomy, slug
    if cfg.taxonomy_mode != "auto" or not slug or slug == "general":
        return taxonomy, raw
    if _merge_category_into_taxonomy_json(cfg.taxonomy_path, slug, max_categories=cfg.taxonomy_auto_max_categories):
        taxonomy = _load_taxonomy(cfg)
        if slug in {c.lower() for c in taxonomy.categories}:
            return taxonomy, slug
    return taxonomy, raw


def _normalize_topic(value: str) -> str:
    normalized = re.sub(r"\s+", " ", (value or "").strip())
    return normalized[:80]


def _normalize_tag(raw: str, *, taxonomy: TaxonomyConfig, default_prefix: str = "topic") -> Optional[str]:
    value = (raw or "").strip().lower()
    if not value:
        return None
    prefix = default_prefix
    tag_body = value
    if "/" in value:
        maybe_prefix, maybe_body = value.split("/", 1)
        maybe_prefix = maybe_prefix.strip()
        if maybe_prefix in taxonomy.tag_prefixes:
            prefix = maybe_prefix
            tag_body = maybe_body.strip()
    if tag_body in taxonomy.synonyms:
        tag_body = taxonomy.synonyms[tag_body]
    slug = _slugify_filename(tag_body)
    if not slug:
        return None
    return f"{prefix}/{slug}"


def _extract_json_block(text: str) -> str:
    text = (text or "").strip()
    if not text:
        raise ValueError("Model response was empty.")
    fenced = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    start_obj = text.find("{")
    start_arr = text.find("[")
    starts = [s for s in [start_obj, start_arr] if s >= 0]
    if not starts:
        raise ValueError("No JSON block found.")
    return text[min(starts):].strip()


def _tail_lines(text: str, *, max_lines: int = 12, max_chars: int = 1500) -> str:
    body = (text or "").strip()
    if not body:
        return ""
    lines = body.splitlines()
    tail = "\n".join(lines[-max_lines:]).strip()
    if len(tail) > max_chars:
        return "...\n" + tail[-max_chars:]
    return tail


def _estimate_total_runtime_seconds(video_duration_seconds: float, *, cfg: PipelineConfig) -> float:
    duration = max(0.0, float(video_duration_seconds))
    return max(1.0, cfg.eta_base_seconds + (cfg.eta_per_video_second * duration) + cfg.eta_llm_overhead_seconds)


def estimate_processing_for_url(url: str) -> dict[str, Any]:
    cfg = _cfg()
    metadata = fetch_video_metadata((url or "").strip())
    raw_duration = metadata.get("duration_seconds")
    try:
        duration_s = float(raw_duration) if raw_duration is not None else 0.0
    except Exception:
        duration_s = 0.0
    duration_s = max(0.0, duration_s)
    provider = "openrouter" if cfg.openrouter_api_key else "ollama"
    model = cfg.openrouter_model if cfg.openrouter_api_key else cfg.ollama_model
    provider_key = f"llm/{provider}:{model}"
    defaults = _default_stage_estimates(duration_s, cfg=cfg)
    with _eta_history_lock:
        history = _load_eta_history(cfg)
    stage_order = [
        "download_video",
        "extract_keyframes",
        "extract_audio",
        "llm_classify",
        "llm_entities",
        "llm_summary",
        "llm_verify",
        "llm_title",
    ]
    stage_estimates: dict[str, float] = {}
    sample_counts: dict[str, int] = {}
    for stage in stage_order:
        est, count = _estimate_stage_seconds(
            cfg=cfg,
            history=history,
            stage=stage,
            provider_key=provider_key,
            default_seconds=float(defaults.get(stage, 1.0)),
        )
        stage_estimates[stage] = est
        sample_counts[stage] = count

    eta_s = sum(stage_estimates.values())
    return {
        "video_duration_seconds": duration_s,
        "estimated_total_seconds": eta_s,
        "provider": provider,
        "model": model,
        "confidence": "conservative",
        "stage_estimates": stage_estimates,
        "sample_counts": sample_counts,
    }


def _run(cmd: list[str], *, step: str, verbose: bool = False) -> subprocess.CompletedProcess[str]:
    cfg = _cfg()
    started = time.monotonic()
    start_icon = "▶️" if cfg.emoji_logs_enabled else ""
    done_icon = "✅" if cfg.emoji_logs_enabled else ""
    fail_icon = "❌" if cfg.emoji_logs_enabled else ""
    print(f"[PIPELINE] {start_icon} START {step}".strip())
    if verbose:
        completed = subprocess.run(cmd, check=True, text=True)
        elapsed = time.monotonic() - started
        print(f"[PIPELINE] {done_icon} DONE {step} ({elapsed:.2f}s)".strip())
        return completed

    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    elapsed = time.monotonic() - started
    if completed.returncode != 0:
        print(f"[PIPELINE] {fail_icon} FAIL {step} (exit={completed.returncode}, {elapsed:.2f}s)".strip())
        stderr_tail = _tail_lines(completed.stderr or "")
        stdout_tail = _tail_lines(completed.stdout or "")
        if stderr_tail:
            print(f"[PIPELINE] stderr tail:\n{stderr_tail}")
        if stdout_tail:
            print(f"[PIPELINE] stdout tail:\n{stdout_tail}")
        raise subprocess.CalledProcessError(
            completed.returncode,
            cmd,
            output=completed.stdout,
            stderr=completed.stderr,
        )

    print(f"[PIPELINE] {done_icon} DONE {step} ({elapsed:.2f}s)".strip())
    stage_map = {
        "download video": "download_video",
        "extract keyframes": "extract_keyframes",
        "extract audio": "extract_audio",
    }
    stage_name = stage_map.get((step or "").strip().lower())
    active_url = _get_active_run_url()
    if stage_name and active_url:
        snap = get_run_eta_snapshot(active_url) or {}
        provider = str(snap.get("provider") or "openrouter")
        model = str(snap.get("model") or "unknown")
        provider_key = f"llm/{provider}:{model}"
        cfg_local = _cfg()
        _append_history_stage(cfg_local, key="pipeline/default", stage=stage_name, elapsed_seconds=elapsed)
        completed_stage_seconds = dict(snap.get("completed_stage_seconds", {}))
        completed_stage_seconds[stage_name] = elapsed
        stage_estimates = dict(snap.get("stage_estimates", {}))
        remaining = 0.0
        for key, est in stage_estimates.items():
            if key not in completed_stage_seconds:
                remaining += max(0.0, float(est))
        _update_run_snapshot(
            active_url,
            {
                "completed_stage_seconds": completed_stage_seconds,
                "estimated_remaining_seconds": remaining,
                "elapsed_seconds": max(0.0, time.monotonic() - float(snap.get("run_started_monotonic", time.monotonic()))),
                "provider_key": provider_key,
            },
        )
    return completed


def _load_processed(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
        return {}
    except Exception:
        return {}


def _save_processed(path: Path, data: dict[str, str]) -> None:
    import json

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def is_processed_url(url: str) -> bool:
    cfg = _cfg()
    processed = _load_processed(cfg.processed_db_path)
    return url.strip() in processed


def get_processed_urls() -> set[str]:
    cfg = _cfg()
    processed = _load_processed(cfg.processed_db_path)
    return set(processed.keys())


def download_instagram_video(url: str, job_dir: Path, *, cookies_from_browser: Optional[str], cookies_file: Optional[Path]) -> Path:
    cfg = _cfg()
    output_template = str(job_dir / "video.%(ext)s")
    # Use the current interpreter so this works even if the yt-dlp launcher
    # points to an old venv path after moving the project.
    cmd = [sys.executable, "-m", "yt_dlp", url, "-o", output_template]
    if not cfg.subprocess_verbose_logs:
        cmd += ["--no-progress", "--no-warnings"]
    if cookies_from_browser:
        cmd += ["--cookies-from-browser", cookies_from_browser]
    if cookies_file:
        cmd += ["--cookies", str(cookies_file)]
    _run(cmd, step="download video", verbose=cfg.subprocess_verbose_logs)

    candidates = sorted(job_dir.glob("video.*"))
    if not candidates:
        raise FileNotFoundError("yt-dlp finished but no video file was found.")
    return candidates[0]


def extract_audio(video_path: Path, job_dir: Path) -> Path:
    cfg = _cfg()
    audio_path = job_dir / "audio.wav"
    _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(audio_path),
        ],
        step="extract audio",
        verbose=cfg.subprocess_verbose_logs,
    )
    return audio_path


_WHISPER_MODEL: Optional[WhisperModel] = None


def _whisper_model() -> WhisperModel:
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        _WHISPER_MODEL = WhisperModel("base", device="cpu", compute_type="int8")
    return _WHISPER_MODEL


def transcribe_audio(audio_path: Path) -> str:
    segments, _info = _whisper_model().transcribe(str(audio_path), beam_size=5)
    transcript = " ".join(segment.text.strip() for segment in segments).strip()
    if not transcript:
        raise ValueError("Transcript was empty.")
    return transcript


def _video_duration_seconds(video_path: Path) -> float:
    try:
        completed = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return max(0.0, float((completed.stdout or "").strip() or "0"))
    except Exception:
        return 0.0


def extract_keyframes(video_path: Path, job_dir: Path, *, cfg: PipelineConfig) -> list[Path]:
    frames_dir = job_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = str(frames_dir / "frame-%05d.jpg")
    if cfg.frame_sampling_mode == "scene":
        vf = "select='gt(scene,0.35)',fps=1/2"
    else:
        vf = f"fps=1/{cfg.frame_interval_seconds}"
    _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            vf,
            "-vsync",
            "vfr",
            output_pattern,
        ],
        step="extract keyframes",
        verbose=cfg.subprocess_verbose_logs,
    )
    frames = sorted(frames_dir.glob("frame-*.jpg"))
    return frames[: cfg.max_keyframes_analyzed]


def _ocr_image_text(image_path: Path, *, cfg: PipelineConfig) -> str:
    try:
        completed = subprocess.run(
            [cfg.ocr_tesseract_cmd, str(image_path), "stdout", "-l", "eng"],
            check=True,
            capture_output=True,
            text=True,
        )
        return (completed.stdout or "").strip()
    except Exception:
        return ""


def _word_richness(text: str) -> int:
    words = re.findall(r"[a-zA-Z0-9]{3,}", (text or "").lower())
    return len(set(words))


def analyze_frames_with_ocr(frame_paths: list[Path], *, cfg: PipelineConfig, duration_seconds: float) -> list[dict[str, Any]]:
    if not frame_paths:
        return []
    analyzed: list[dict[str, Any]] = []
    count = len(frame_paths)
    for idx, frame in enumerate(frame_paths):
        ocr_text = _ocr_image_text(frame, cfg=cfg) if cfg.visual_context_enabled else ""
        timestamp = (duration_seconds * (idx + 1) / (count + 1)) if duration_seconds > 0 else float(idx * cfg.frame_interval_seconds)
        analyzed.append(
            {
                "path": frame,
                "timestamp": round(timestamp, 2),
                "ocr_text": ocr_text,
                "score": _word_richness(ocr_text),
                "index": idx,
            }
        )
    return analyzed


def select_best_frames(frame_insights: list[dict[str, Any]], *, max_images: int) -> list[dict[str, Any]]:
    if not frame_insights:
        return []
    ranked = sorted(frame_insights, key=lambda x: (int(x.get("score", 0)), -int(x.get("index", 0))), reverse=True)
    selected: list[dict[str, Any]] = []
    min_gap = max(1, len(frame_insights) // max(1, max_images))
    for item in ranked:
        idx = int(item.get("index", 0))
        if any(abs(idx - int(s.get("index", 0))) < min_gap for s in selected):
            continue
        selected.append(item)
        if len(selected) >= max_images:
            break
    if not selected:
        selected = [frame_insights[0]]
    return sorted(selected, key=lambda x: float(x.get("timestamp", 0.0)))


def build_visual_context(frame_insights: list[dict[str, Any]]) -> str:
    if not frame_insights:
        return ""
    lines: list[str] = []
    for item in frame_insights[:12]:
        ts = float(item.get("timestamp", 0.0))
        text = str(item.get("ocr_text", "")).strip()
        if text:
            compact = re.sub(r"\s+", " ", text)[:240]
            lines.append(f"- t={ts:.1f}s OCR: {compact}")
    return "\n".join(lines)


def _extract_keywords(text: str) -> set[str]:
    stop = {
        "this",
        "that",
        "with",
        "from",
        "your",
        "have",
        "there",
        "about",
        "into",
        "just",
        "like",
        "make",
        "then",
        "they",
        "them",
        "their",
        "here",
        "will",
    }
    words = re.findall(r"[a-z0-9]{3,}", (text or "").lower())
    return {w for w in words if w not in stop}


def assess_transcript_quality(transcript: str, *, cfg: PipelineConfig) -> dict[str, Any]:
    text = (transcript or "").strip()
    words = re.findall(r"[a-zA-Z0-9']+", text.lower())
    alpha_chars = sum(ch.isalpha() for ch in text)
    total_chars = max(1, len(text))
    alpha_ratio = alpha_chars / total_chars
    unique_words = len(set(words))
    repeated_ratio = 0.0
    if words:
        repeated_ratio = 1.0 - (unique_words / max(1, len(words)))

    low_info_hits = 0
    low_info_patterns = [
        r"\bmusic\b",
        r"\bbeats?\b",
        r"\bla la\b",
        r"\bmm+\b",
        r"\buh+\b",
        r"\bah+\b",
        r"\bheart and follow\b",
    ]
    for pat in low_info_patterns:
        if re.search(pat, text, flags=re.IGNORECASE):
            low_info_hits += 1

    reasons: list[str] = []
    if len(words) < cfg.transcript_min_words:
        reasons.append(f"low word count ({len(words)}<{cfg.transcript_min_words})")
    if unique_words < cfg.transcript_min_unique_words:
        reasons.append(f"low lexical diversity ({unique_words}<{cfg.transcript_min_unique_words})")
    if alpha_ratio < cfg.transcript_min_alpha_ratio:
        reasons.append(f"low alphabetic ratio ({alpha_ratio:.2f}<{cfg.transcript_min_alpha_ratio:.2f})")
    if repeated_ratio > 0.65:
        reasons.append(f"high repetition ({repeated_ratio:.2f})")
    if low_info_hits >= 2:
        reasons.append("transcript appears low-information/noise-heavy")

    is_useful = not reasons
    return {
        "is_useful": is_useful,
        "reasons": reasons,
        "metrics": {
            "word_count": len(words),
            "unique_word_count": unique_words,
            "alpha_ratio": round(alpha_ratio, 3),
            "repeated_ratio": round(repeated_ratio, 3),
            "low_info_hits": low_info_hits,
        },
    }


def fetch_video_metadata(url: str) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "yt_dlp",
                "--dump-single-json",
                "--skip-download",
                url,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads((completed.stdout or "").strip() or "{}")
        caption = str(data.get("description") or "").strip()
        post_title = str(data.get("title") or "").strip()
        uploader = str(data.get("uploader") or "").strip()
        duration_raw = data.get("duration")
        try:
            duration_seconds = max(0.0, float(duration_raw)) if duration_raw is not None else 0.0
        except Exception:
            duration_seconds = 0.0
        return {
            "caption": caption,
            "post_title": post_title,
            "uploader": uploader,
            "duration_seconds": duration_seconds,
        }
    except Exception:
        return {"caption": "", "post_title": "", "uploader": "", "duration_seconds": 0.0}


def assess_transcript_caption_alignment(transcript: str, caption: str, *, cfg: PipelineConfig) -> dict[str, Any]:
    transcript_terms = _extract_keywords(transcript)
    caption_terms = _extract_keywords(caption)
    overlap = sorted(transcript_terms & caption_terms)
    transcript_only = sorted(transcript_terms - caption_terms)
    caption_only = sorted(caption_terms - transcript_terms)
    overlap_ratio = (len(overlap) / max(1, len(caption_terms))) if caption_terms else 0.0
    mismatch = bool(caption_terms) and overlap_ratio < cfg.transcript_caption_min_overlap
    reasons: list[str] = []
    if mismatch:
        reasons.append(
            f"transcript does not match caption topics ({overlap_ratio:.2f}<{cfg.transcript_caption_min_overlap:.2f})"
        )
    return {
        "is_mismatch": mismatch,
        "mismatch_reasons": reasons,
        "score": overlap_ratio,
        "metrics": {
            "overlap_count": len(overlap),
            "transcript_term_count": len(transcript_terms),
            "caption_term_count": len(caption_terms),
            "overlap_ratio": round(overlap_ratio, 3),
        },
        "context": (
            f"Transcript-caption overlap: {overlap_ratio:.2f}\n"
            f"Overlap terms: {', '.join(overlap[:24]) or '(none)'}\n"
            f"Caption-only terms: {', '.join(caption_only[:16]) or '(none)'}\n"
            f"Transcript-only terms: {', '.join(transcript_only[:16]) or '(none)'}"
        ),
    }


def align_ocr_transcript(transcript: str, frame_insights: list[dict[str, Any]]) -> dict[str, Any]:
    transcript_terms = _extract_keywords(transcript)
    ocr_text = " ".join(str(item.get("ocr_text", "")) for item in frame_insights)
    ocr_terms = _extract_keywords(ocr_text)
    overlap = sorted(transcript_terms & ocr_terms)
    transcript_only = sorted(transcript_terms - ocr_terms)
    ocr_only = sorted(ocr_terms - transcript_terms)
    denom = max(1, len(ocr_terms))
    score = min(1.0, len(overlap) / denom)
    context = (
        f"Alignment score: {score:.2f}\n"
        f"Overlap terms: {', '.join(overlap[:24]) or '(none)'}\n"
        f"OCR-only terms: {', '.join(ocr_only[:16]) or '(none)'}\n"
        f"Transcript-only terms: {', '.join(transcript_only[:16]) or '(none)'}"
    )
    return {
        "score": score,
        "overlap_terms": overlap,
        "transcript_only_terms": transcript_only,
        "ocr_only_terms": ocr_only,
        "context": context,
    }


def _extract_key_idea_claims(summary_markdown: str) -> list[str]:
    lines = [ln.strip() for ln in (summary_markdown or "").splitlines()]
    claims: list[str] = []
    in_key_ideas = False
    for line in lines:
        if line.lower().startswith("## "):
            in_key_ideas = line.strip().lower() == "## key ideas"
            continue
        if in_key_ideas and line.startswith("-"):
            claims.append(re.sub(r"^\-\s*", "", line).strip())
    return claims[:12]


def _repair_verification(raw_text: str, *, cfg: PipelineConfig) -> dict[str, Any]:
    prompt = f"""Repair this into strict JSON object only.
Shape:
{{
  "claims":[{{"claim":"...", "status":"supported|uncertain|contradicted", "confidence":0.0, "transcript_evidence":"...", "visual_evidence":"..."}}],
  "supported_count":0,
  "uncertain_count":0,
  "contradicted_count":0
}}

Original:
{raw_text}
""".strip()
    repaired = _llm_chat_completion(
        prompt=prompt,
        system="Repair malformed verification output into valid JSON only.",
        cfg=cfg,
        temperature=0.0,
        stage="repair:verification",
    )
    data = json.loads(_extract_json_block(repaired))
    if not isinstance(data, dict):
        raise ValueError("Verification repair output was not object.")
    return data


def verify_note_consistency(
    *,
    summary_markdown: str,
    transcript: str,
    visual_context: str,
    alignment_context: str,
    cfg: PipelineConfig,
) -> dict[str, Any]:
    claims = _extract_key_idea_claims(summary_markdown)
    if not claims:
        return {"claims": [], "supported_count": 0, "uncertain_count": 0, "contradicted_count": 0}
    claim_text = "\n".join(f"- {c}" for c in claims)
    prompt = f"""Evaluate whether each claim is supported by transcript and visual context.
Return strict JSON object only with shape:
{{
  "claims":[{{"claim":"...", "status":"supported|uncertain|contradicted", "confidence":0.0, "transcript_evidence":"...", "visual_evidence":"..."}}],
  "supported_count":0,
  "uncertain_count":0,
  "contradicted_count":0
}}

Claims:
{claim_text}

Alignment context:
{alignment_context}

Visual context:
{visual_context or "(none)"}

Transcript:
{_bounded_transcript(transcript)}
""".strip()
    try:
        raw = _llm_chat_completion(
            prompt=prompt,
            system="You are a strict factual verifier. Output JSON only.",
            cfg=cfg,
            temperature=0.0,
            stage="verify",
        )
        data = json.loads(_extract_json_block(raw))
        if not isinstance(data, dict):
            raise ValueError("Invalid verification shape.")
        return data
    except Exception:
        try:
            return _repair_verification(raw if "raw" in locals() else prompt, cfg=cfg)
        except Exception:
            return {"claims": [], "supported_count": 0, "uncertain_count": len(claims), "contradicted_count": 0}


def rewrite_summary_from_verification(
    *,
    summary_markdown: str,
    verification: dict[str, Any],
    transcript: str,
    visual_context: str,
    alignment_context: str,
    cfg: PipelineConfig,
) -> str:
    contradicted = [
        str(c.get("claim", "")).strip()
        for c in verification.get("claims", [])
        if str(c.get("status", "")).strip().lower() == "contradicted" and str(c.get("claim", "")).strip()
    ]
    if not contradicted:
        return summary_markdown
    uncertain = [
        str(c.get("claim", "")).strip()
        for c in verification.get("claims", [])
        if str(c.get("status", "")).strip().lower() == "uncertain" and str(c.get("claim", "")).strip()
    ]
    prompt = f"""Rewrite this Obsidian summary to remove/fix contradicted claims.

Rules:
- Preserve markdown format and required sections:
  - ## TL;DR
  - ## Key Ideas
  - ## Actionable Takeaways
- Keep concise and specific.
- Remove or correct contradicted claims using transcript evidence.
- Keep uncertain claims only if clearly labeled as uncertain.
- Return markdown only.

Contradicted claims:
{chr(10).join(f"- {c}" for c in contradicted)}

Uncertain claims:
{chr(10).join(f"- {c}" for c in uncertain) or "- (none)"}

Alignment context:
{alignment_context}

Visual context:
{visual_context or "(none)"}

Original summary:
{summary_markdown}

Transcript:
{_bounded_transcript(transcript)}
""".strip()
    try:
        rewritten = _llm_chat_completion(
            prompt=prompt,
            system="You are a factual technical editor. Return markdown only.",
            cfg=cfg,
            temperature=0.1,
            stage="rewrite:contradictions",
        ).strip()
        if rewritten:
            return rewritten
    except Exception:
        pass
    return summary_markdown


def _clean_title_text(title: str) -> str:
    t = re.sub(r"https?://\S+", "", title or "")
    t = re.sub(r"\binstagram\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\d{4}-\d{2}-\d{2}", "", t)
    t = re.sub(r"\b20\d{2}\b", "", t)
    t = re.sub(r"\s+", " ", t).strip(" -_")
    if not t:
        return "Untitled Note"
    t = t.title()
    t = re.sub(r"\b(How To)\b", "How to", t)
    words = t.split()
    if len(words) > 8:
        t = " ".join(words[:8])
    if len(words) < 2:
        t = f"{t} Guide"
    generic = {"Tutorial", "Tips", "How", "Guide"}
    if all(w in generic for w in t.split()):
        t = "Workflow Tutorial"
    return t


def _extract_transcript_keywords(transcript: str, limit: int = 4) -> list[str]:
    words = re.findall(r"[a-zA-Z]{4,}", transcript.lower())
    ban = {"this", "that", "with", "from", "have", "there", "make", "your", "into", "just", "like"}
    freq: dict[str, int] = {}
    for w in words:
        if w in ban:
            continue
        freq[w] = freq.get(w, 0) + 1
    ranked = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)
    return [w for w, _ in ranked[:limit]]


def _render_note_filename(title: str, *, cfg: PipelineConfig, existing_dir: Optional[Path] = None) -> str:
    clean = _clean_title_text(title)
    if cfg.note_filename_style == "slug":
        stem = _slugify_filename(clean)
    else:
        stem = re.sub(r'[<>:"/\\|?*]', "", clean)
        stem = re.sub(r"\s+", " ", stem).strip(" .")
        if not stem:
            stem = "Untitled Note"
    if cfg.allow_filename_date_prefix:
        stem = f"{datetime.now().strftime('%Y-%m-%d')} - {stem}"
    filename = f"{stem}.md"
    if existing_dir is None:
        return filename
    candidate = existing_dir / filename
    idx = 2
    while candidate.exists():
        filename = f"{stem} ({idx}).md"
        candidate = existing_dir / filename
        idx += 1
    return filename


def generate_clean_title(
    *,
    transcript: str,
    summary_md: str,
    category: str,
    subtopics: list[str],
    alignment_context: str,
    cfg: PipelineConfig,
) -> tuple[str, str]:
    keywords = _extract_transcript_keywords(transcript, limit=3)
    if subtopics:
        fallback_seed = subtopics[0]
    elif keywords:
        fallback_seed = f"{' '.join(k.title() for k in keywords[:2])} Guide"
    else:
        fallback_seed = category or "Untitled Note"
    fallback = _clean_title_text(fallback_seed)
    style = cfg.title_style
    if style == "category":
        seed = (category or "").strip() or fallback_seed
        return _clean_title_text(seed), "category"
    if style == "summary_heading":
        m = re.search(r"^\s*#\s+(.+?)\s*$", summary_md or "", flags=re.MULTILINE)
        if m:
            raw_h1 = m.group(1).strip().strip('"')
            t = _clean_title_text(raw_h1)
            if t.lower() not in {"untitled note", "instagram", "tutorial", "guide", "workflow tutorial"}:
                return t, "summary_heading"
        return fallback, "fallback"
    if style == "heuristic":
        return fallback, "heuristic"
    if style != "clean":
        return fallback, "fallback"
    prompt = f"""Generate a concise note title for an instructional social video.
Rules:
- 2-8 words
- Title Case
- No date
- No word 'Instagram'
- Must be specific to content
- Prefer actionable style when suitable (e.g., "Color Swatching Guide")
- Avoid generic-only outputs like "Tutorial", "Tips", "Guide"

Category: {category}
Subtopics: {", ".join(subtopics) or "(none)"}
Alignment context: {alignment_context}
Summary:
{summary_md[:1800]}
""".strip()
    try:
        title = _llm_chat_completion(
            prompt=prompt,
            system="Generate only the title text, no markdown.",
            cfg=cfg,
            temperature=0.1,
            stage="title",
        ).strip()
        cleaned = _clean_title_text(title)
        if cleaned.lower() in {"instagram", "tutorial", "guide", "workflow tutorial"}:
            return fallback, "fallback"
        return cleaned, "llm"
    except Exception:
        return fallback, "fallback"


def persist_selected_frames(*, selected_frames: list[dict[str, Any]], cfg: PipelineConfig, note_slug: str) -> list[dict[str, Any]]:
    if not selected_frames:
        return []
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    assets_dir = cfg.vault_path / "Assets" / "Instagram" / f"{date_prefix}-{note_slug}"
    assets_dir.mkdir(parents=True, exist_ok=True)
    persisted: list[dict[str, Any]] = []
    for idx, item in enumerate(selected_frames, start=1):
        src = Path(item["path"])
        if not src.exists():
            continue
        target = assets_dir / f"frame-{idx:02d}.jpg"
        shutil.copy2(src, target)
        rel = target.relative_to(cfg.vault_path).as_posix()
        persisted.append(
            {
                "relative_path": rel,
                "timestamp": float(item.get("timestamp", 0.0)),
                "ocr_text": str(item.get("ocr_text", "")).strip(),
            }
        )
    return persisted


def cleanup_temp_paths(*, cfg: PipelineConfig, job_dir: Path, success: bool) -> None:
    keep_dir = cfg.keep_temp or (not success and cfg.keep_temp_on_failure)
    if keep_dir:
        if not success:
            print(f"Kept temp job dir due to failure: {job_dir}")
        return

    shutil.rmtree(job_dir, ignore_errors=True)
    print(f"Cleaned temp job dir: {job_dir}")
    # Remove temp root itself when it becomes empty after successful runs.
    if success and cfg.temp_dir.exists():
        try:
            next(cfg.temp_dir.iterdir())
        except StopIteration:
            cfg.temp_dir.rmdir()
            print(f"Removed empty temp root dir: {cfg.temp_dir}")
        except Exception:
            pass


def _llm_chat_completion(
    *, prompt: str, system: str, cfg: PipelineConfig, temperature: float = 0.2, stage: str = "unspecified"
) -> str:
    stage_name = (stage or "unspecified").strip() or "unspecified"
    provider = "openrouter" if cfg.openrouter_api_key else "ollama"
    model = cfg.openrouter_model if cfg.openrouter_api_key else cfg.ollama_model
    start_icon = "🧠" if cfg.emoji_logs_enabled else ""
    done_icon = "✅" if cfg.emoji_logs_enabled else ""
    fail_icon = "❌" if cfg.emoji_logs_enabled else ""
    started = time.monotonic()
    print(f"[LLM] {start_icon} START stage={stage_name} provider={provider} model={model}".strip())
    try:
        if cfg.openrouter_api_key:
            r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {cfg.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": cfg.openrouter_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
            },
            timeout=120,
        )
            if not r.ok:
                raise RuntimeError(f"OpenRouter error {r.status_code}: {r.text[:500]}")
            data = r.json()
            try:
                content = (data["choices"][0]["message"]["content"] or "").strip()
            except Exception:
                raise RuntimeError(f"OpenRouter response parse error: {str(data)[:500]}")
        else:
            fallback_prompt = f"{system}\n\n{prompt}".strip()
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": cfg.ollama_model, "prompt": fallback_prompt, "stream": False},
                timeout=600,
            )
            if not response.ok:
                raise RuntimeError(f"Ollama error {response.status_code}: {response.text[:500]}")
            content = str(response.json().get("response") or "").strip()
        elapsed = time.monotonic() - started
        _record_llm_stage_call(stage=stage_name, elapsed_s=elapsed)
        history_stage = f"llm_{stage_name}"
        provider_key = f"llm/{provider}:{model}"
        cfg_local = _cfg()
        _append_history_stage(cfg_local, key=provider_key, stage=history_stage, elapsed_seconds=elapsed)
        active_url = _get_active_run_url()
        if active_url:
            snap = get_run_eta_snapshot(active_url) or {}
            completed_stage_seconds = dict(snap.get("completed_stage_seconds", {}))
            completed_stage_seconds[history_stage] = elapsed
            stage_estimates = dict(snap.get("stage_estimates", {}))
            remaining = 0.0
            for key, est in stage_estimates.items():
                if key not in completed_stage_seconds:
                    remaining += max(0.0, float(est))
            _update_run_snapshot(
                active_url,
                {
                    "completed_stage_seconds": completed_stage_seconds,
                    "estimated_remaining_seconds": remaining,
                    "elapsed_seconds": max(
                        0.0, time.monotonic() - float(snap.get("run_started_monotonic", time.monotonic()))
                    ),
                },
            )
        print(f"[LLM] {done_icon} DONE stage={stage_name} provider={provider} model={model} ({elapsed:.2f}s)".strip())
        return content
    except Exception as e:
        elapsed = time.monotonic() - started
        print(f"[LLM] {fail_icon} FAIL stage={stage_name} provider={provider} model={model} ({elapsed:.2f}s): {e}".strip())
        raise


def _bounded_transcript(transcript: str) -> str:
    if len(transcript) <= 18000:
        return transcript
    return (
        transcript[:15000].rstrip()
        + "\n\n[... transcript truncated for summarization ...]\n\n"
        + transcript[-2500:].lstrip()
    )


def classify_video(
    transcript: str,
    *,
    cfg: PipelineConfig,
    taxonomy: TaxonomyConfig,
    visual_context: str = "",
    alignment_context: str = "",
    caption_context: str = "",
) -> dict[str, Any]:
    categories = ", ".join(taxonomy.categories)
    prompt = f"""Classify this transcript into a fixed taxonomy.

Return JSON only with this exact shape:
{{
  "category": "<one of: {categories}>",
  "subtopics": ["short phrase"],
  "tags": ["topic/example", "tool/example"]
}}

Keep subtopics concise and practical.
Visual context extracted from frames/OCR:
{visual_context or "(none)"}
Alignment context:
{alignment_context or "(none)"}
Caption context:
{caption_context or "(none)"}

Transcript:
{_bounded_transcript(transcript)}
""".strip()
    raw = _llm_chat_completion(
        prompt=prompt,
        system="You classify transcripts into a fixed taxonomy and output strict JSON only.",
        cfg=cfg,
        temperature=0.1,
        stage="classify",
    )
    data = json.loads(_extract_json_block(raw))
    if not isinstance(data, dict):
        raise ValueError("Classification output must be a JSON object.")
    return data


def extract_entities(
    transcript: str,
    *,
    cfg: PipelineConfig,
    visual_context: str = "",
    alignment_context: str = "",
    caption_context: str = "",
) -> list[dict[str, Any]]:
    prompt = f"""Extract entities from this transcript.

Return JSON only as an array of objects with shape:
[
  {{"name":"...", "kind":"concept|person|tool|brand|resource", "confidence":0.0}}
]

Visual context extracted from frames/OCR:
{visual_context or "(none)"}
Alignment context:
{alignment_context or "(none)"}
Caption context:
{caption_context or "(none)"}

Transcript:
{_bounded_transcript(transcript)}
""".strip()
    raw = _llm_chat_completion(
        prompt=prompt,
        system="You extract entities from transcripts and output strict JSON only.",
        cfg=cfg,
        temperature=0.1,
        stage="entities",
    )
    data = json.loads(_extract_json_block(raw))
    if not isinstance(data, list):
        raise ValueError("Entity output must be a JSON array.")
    return data


def generate_video_summary(
    transcript: str,
    *,
    cfg: PipelineConfig,
    category: str,
    subtopics: list[str],
    entities: list[Entity],
    visual_context: str = "",
    alignment_context: str = "",
    caption_context: str = "",
    caption_primary: bool = False,
) -> str:
    entity_names = ", ".join(e.name for e in entities[:12]) or "None identified"
    subtopics_text = ", ".join(subtopics) or "None"
    alignment_score_match = re.search(r"Alignment score:\s*([0-9.]+)", alignment_context or "")
    alignment_score = float(alignment_score_match.group(1)) if alignment_score_match else 0.0
    strict_guidance = (
        "- Alignment is weak. Prefer transcript-grounded claims and explicitly mark uncertainty.\n"
        if alignment_score < cfg.min_alignment_score_for_strict_mode
        else ""
    )
    prompt = f"""Create a high-quality Obsidian markdown summary.

Requirements:
- Start with a level-1 title.
- Include sections exactly: ## TL;DR, ## Key Ideas, ## Actionable Takeaways.
- Keep it specific and concise.
- Prioritize claims supported by transcript and overlap terms.
- Mark uncertain visual-only inferences with cautious wording.
{strict_guidance}
- If transcript conflicts with caption context, explicitly mark uncertainty.
- {"Caption is primary context for this note." if caption_primary else "Transcript remains primary context."}

Context:
- Category: {category}
- Subtopics: {subtopics_text}
- Entities: {entity_names}
- Visual context:
{visual_context or "(none)"}
- Alignment context:
{alignment_context or "(none)"}
- Caption context:
{caption_context or "(none)"}

Transcript:
{_bounded_transcript(transcript)}
""".strip()
    return _llm_chat_completion(
        prompt=prompt,
        system="You write clean, accurate Obsidian Markdown summaries.",
        cfg=cfg,
        temperature=0.2,
        stage="summary",
    )


def _validate_graph_payload(
    *,
    classification_raw: dict[str, Any],
    entities_raw: list[dict[str, Any]],
    summary_markdown: str,
    visual_context: str,
    alignment_score: float,
    alignment_context: str,
    title_generated_by: str,
    verification: Optional[dict[str, Any]],
    transcript_useful: bool,
    transcript_quality_reasons: list[str],
    caption_available: bool,
    caption_primary_context: bool,
    transcript_caption_mismatch: bool,
    transcript_caption_mismatch_reasons: list[str],
    taxonomy: TaxonomyConfig,
    cfg: PipelineConfig,
) -> GraphPayload:
    category = str(classification_raw.get("category", "")).strip().lower()
    if category not in taxonomy.categories:
        category = "general"

    subtopics_raw = classification_raw.get("subtopics", [])
    if not isinstance(subtopics_raw, list):
        subtopics_raw = []
    subtopics = _dedupe_preserve_order([_normalize_topic(str(v)) for v in subtopics_raw if str(v).strip()])[: cfg.max_topics_per_video]
    if not subtopics:
        subtopics = ["general"]

    tags_raw = classification_raw.get("tags", [])
    if not isinstance(tags_raw, list):
        tags_raw = []
    tags: list[str] = []
    for raw in tags_raw:
        normalized = _normalize_tag(str(raw), taxonomy=taxonomy, default_prefix="topic")
        if normalized:
            tags.append(normalized)
    tags.append(f"domain/{_slugify_filename(category)}")
    tags = _dedupe_preserve_order(tags)

    entities: list[Entity] = []
    for raw in entities_raw:
        if not isinstance(raw, dict):
            continue
        name = _normalize_topic(str(raw.get("name", "")))
        if not name:
            continue
        kind = _slugify_filename(str(raw.get("kind", "concept"))) or "concept"
        try:
            confidence = float(raw.get("confidence", 0.0))
        except Exception:
            confidence = 0.0
        if confidence < cfg.graph_min_entity_confidence:
            continue
        entities.append(Entity(name=name, kind=kind, confidence=max(0.0, min(1.0, confidence))))
    entities = entities[:20]

    title = "instagram"
    m = re.search(r"^\s*#\s+(.+?)\s*$", summary_markdown or "", flags=re.MULTILINE)
    if m:
        title = m.group(1).strip().strip('"')
    summary = (summary_markdown or "").strip()
    if not summary:
        summary = "# Instagram Note\n\n## TL;DR\n- Summary unavailable.\n"
    return GraphPayload(
        title=title,
        category=category,
        subtopics=subtopics,
        tags=tags,
        entities=entities,
        summary_markdown=summary,
        visual_context=(visual_context or "").strip(),
        alignment_score=max(0.0, min(1.0, float(alignment_score))),
        alignment_context=(alignment_context or "").strip(),
        title_generated_by=(title_generated_by or "fallback"),
        verification=verification or {"claims": [], "supported_count": 0, "uncertain_count": 0, "contradicted_count": 0},
        transcript_useful=bool(transcript_useful),
        transcript_quality_reasons=[str(r) for r in (transcript_quality_reasons or []) if str(r).strip()],
        caption_available=bool(caption_available),
        caption_primary_context=bool(caption_primary_context),
        transcript_caption_mismatch=bool(transcript_caption_mismatch),
        transcript_caption_mismatch_reasons=[str(r) for r in (transcript_caption_mismatch_reasons or []) if str(r).strip()],
    )


def _repair_classification(raw_text: str, *, cfg: PipelineConfig, taxonomy: TaxonomyConfig) -> dict[str, Any]:
    categories = ", ".join(taxonomy.categories)
    prompt = f"""Repair this output into strict JSON only.
Allowed categories: {categories}
Output shape:
{{"category":"...", "subtopics":["..."], "tags":["topic/example"]}}

Original text:
{raw_text}
""".strip()
    repaired = _llm_chat_completion(
        prompt=prompt,
        system="You repair malformed model output into valid JSON only.",
        cfg=cfg,
        temperature=0.0,
        stage="repair:classification",
    )
    parsed = json.loads(_extract_json_block(repaired))
    if not isinstance(parsed, dict):
        raise ValueError("Repair classification output was not an object.")
    return parsed


def _repair_entities(raw_text: str, *, cfg: PipelineConfig) -> list[dict[str, Any]]:
    prompt = f"""Repair this output into strict JSON array only.
Output shape:
[{{"name":"...", "kind":"concept", "confidence":0.0}}]

Original text:
{raw_text}
""".strip()
    repaired = _llm_chat_completion(
        prompt=prompt,
        system="You repair malformed model output into valid JSON only.",
        cfg=cfg,
        temperature=0.0,
        stage="repair:entities",
    )
    parsed = json.loads(_extract_json_block(repaired))
    if not isinstance(parsed, list):
        raise ValueError("Repair entities output was not an array.")
    return parsed


def build_obsidian_payload(
    transcript: str,
    *,
    cfg: PipelineConfig,
    taxonomy: TaxonomyConfig,
    visual_context: str = "",
    alignment_result: Optional[dict[str, Any]] = None,
    transcript_quality: Optional[dict[str, Any]] = None,
    caption_context: str = "",
    caption_primary_context: bool = False,
    caption_alignment: Optional[dict[str, Any]] = None,
) -> GraphPayload:
    alignment_result = alignment_result or {"score": 0.0, "context": "(none)"}
    transcript_quality = transcript_quality or {"is_useful": True, "reasons": []}
    caption_alignment = caption_alignment or {"is_mismatch": False, "mismatch_reasons": []}
    alignment_context = str(alignment_result.get("context", "(none)"))
    alignment_score = float(alignment_result.get("score", 0.0) or 0.0)
    class_raw_text = ""
    entities_raw_text = ""
    try:
        class_raw = classify_video(
            transcript,
            cfg=cfg,
            taxonomy=taxonomy,
            visual_context=visual_context,
            alignment_context=alignment_context,
            caption_context=caption_context,
        )
    except Exception:
        class_raw_text = _llm_chat_completion(
            prompt=(
                "Classify transcript + visual context into JSON with category/subtopics/tags.\n\n"
                f"Alignment context:\n{alignment_context}\n\n"
                f"Visual context:\n{visual_context or '(none)'}\n\n"
                f"Caption context:\n{caption_context or '(none)'}\n\n"
                f"{_bounded_transcript(transcript)}"
            ),
            system="Output JSON only.",
            cfg=cfg,
            temperature=0.1,
            stage="classify:fallback",
        )
        try:
            class_raw = _repair_classification(class_raw_text, cfg=cfg, taxonomy=taxonomy)
        except Exception:
            class_raw = {"category": "general", "subtopics": ["general"], "tags": ["topic/general"]}

    taxonomy, category_candidate = _apply_taxonomy_auto_merge(class_raw, taxonomy, cfg)

    try:
        entities_raw = extract_entities(
            transcript,
            cfg=cfg,
            visual_context=visual_context,
            alignment_context=alignment_context,
            caption_context=caption_context,
        )
    except Exception:
        entities_raw_text = _llm_chat_completion(
            prompt=(
                "Extract entities into JSON array with name/kind/confidence from transcript + visual context.\n\n"
                f"Alignment context:\n{alignment_context}\n\n"
                f"Visual context:\n{visual_context or '(none)'}\n\n"
                f"Caption context:\n{caption_context or '(none)'}\n\n"
                f"{_bounded_transcript(transcript)}"
            ),
            system="Output JSON only.",
            cfg=cfg,
            temperature=0.1,
            stage="entities:fallback",
        )
        try:
            entities_raw = _repair_entities(entities_raw_text, cfg=cfg)
        except Exception:
            entities_raw = []

    subtopics_candidate = class_raw.get("subtopics", []) if isinstance(class_raw, dict) else []
    validated_entities = _validate_graph_payload(
        classification_raw={"category": category_candidate, "subtopics": subtopics_candidate, "tags": class_raw.get("tags", []) if isinstance(class_raw, dict) else []},
        entities_raw=entities_raw if isinstance(entities_raw, list) else [],
        summary_markdown="",
        visual_context=visual_context,
        alignment_score=alignment_score,
        alignment_context=alignment_context,
        title_generated_by="fallback",
        verification=None,
        transcript_useful=bool(transcript_quality.get("is_useful", True)),
        transcript_quality_reasons=list(transcript_quality.get("reasons", [])),
        caption_available=bool((caption_context or "").strip()),
        caption_primary_context=bool(caption_primary_context),
        transcript_caption_mismatch=bool(caption_alignment.get("is_mismatch", False)),
        transcript_caption_mismatch_reasons=list(caption_alignment.get("mismatch_reasons", [])),
        taxonomy=taxonomy,
        cfg=cfg,
    ).entities
    summary_md = generate_video_summary(
        transcript,
        cfg=cfg,
        category=category_candidate,
        subtopics=[str(v) for v in subtopics_candidate if str(v).strip()] if isinstance(subtopics_candidate, list) else [],
        entities=validated_entities,
        visual_context=visual_context,
        alignment_context=alignment_context,
        caption_context=caption_context,
        caption_primary=caption_primary_context,
    )
    if cfg.consistency_check_enabled:
        verification = verify_note_consistency(
            summary_markdown=summary_md,
            transcript=transcript,
            visual_context=visual_context,
            alignment_context=alignment_context,
            cfg=cfg,
        )
        if cfg.rewrite_contradicted_claims and int(verification.get("contradicted_count", 0)) > 0:
            summary_md = rewrite_summary_from_verification(
                summary_markdown=summary_md,
                verification=verification,
                transcript=transcript,
                visual_context=visual_context,
                alignment_context=alignment_context,
                cfg=cfg,
            )
            verification = verify_note_consistency(
                summary_markdown=summary_md,
                transcript=transcript,
                visual_context=visual_context,
                alignment_context=alignment_context,
                cfg=cfg,
            )
    else:
        verification = {"claims": [], "supported_count": 0, "uncertain_count": 0, "contradicted_count": 0}

    payload = _validate_graph_payload(
        classification_raw=class_raw if isinstance(class_raw, dict) else {},
        entities_raw=entities_raw if isinstance(entities_raw, list) else [],
        summary_markdown=summary_md,
        visual_context=visual_context,
        alignment_score=alignment_score,
        alignment_context=alignment_context,
        title_generated_by="fallback",
        verification=verification,
        transcript_useful=bool(transcript_quality.get("is_useful", True)),
        transcript_quality_reasons=list(transcript_quality.get("reasons", [])),
        caption_available=bool((caption_context or "").strip()),
        caption_primary_context=bool(caption_primary_context),
        transcript_caption_mismatch=bool(caption_alignment.get("is_mismatch", False)),
        transcript_caption_mismatch_reasons=list(caption_alignment.get("mismatch_reasons", [])),
        taxonomy=taxonomy,
        cfg=cfg,
    )
    clean_title, title_source = generate_clean_title(
        transcript=transcript,
        summary_md=payload.summary_markdown,
        category=payload.category,
        subtopics=payload.subtopics,
        alignment_context=alignment_context,
        cfg=cfg,
    )
    return GraphPayload(
        title=clean_title,
        category=payload.category,
        subtopics=payload.subtopics,
        tags=payload.tags,
        entities=payload.entities,
        summary_markdown=payload.summary_markdown,
        visual_context=payload.visual_context,
        alignment_score=payload.alignment_score,
        alignment_context=payload.alignment_context,
        title_generated_by=title_source,
        verification=payload.verification,
        transcript_useful=payload.transcript_useful,
        transcript_quality_reasons=payload.transcript_quality_reasons,
        caption_available=payload.caption_available,
        caption_primary_context=payload.caption_primary_context,
        transcript_caption_mismatch=payload.transcript_caption_mismatch,
        transcript_caption_mismatch_reasons=payload.transcript_caption_mismatch_reasons,
    )


def summarize_transcript(transcript: str, *, cfg: PipelineConfig, visual_context: str = "") -> str:
    prompt = f"""You organize transcripts into Obsidian notes.

Return valid Markdown only.

Visual context extracted from frames/OCR:
{visual_context or "(none)"}

Transcript:
{_bounded_transcript(transcript)}
""".strip()
    return _llm_chat_completion(
        prompt=prompt,
        system="You organize transcripts into Obsidian notes. Return valid Markdown only.",
        cfg=cfg,
        temperature=0.2,
        stage="summary:basic",
    )


def write_note(markdown: str, *, vault_path: Path, filename: str) -> Path:
    notes_dir = vault_path / "Instagram Notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    note_path = notes_dir / filename
    note_path.write_text(markdown, encoding="utf-8")
    return note_path


def _format_frontmatter(data: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list):
            if value:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f'  - "{str(item).replace(chr(34), "")}"')
            else:
                lines.append(f"{key}: []")
        elif isinstance(value, str):
            lines.append(f'{key}: "{value.replace(chr(34), "")}"')
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def _append_unique_line(path: Path, line: str) -> None:
    line = line.rstrip()
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if line in existing:
            return
        path.write_text(existing.rstrip() + "\n" + line + "\n", encoding="utf-8")
    else:
        path.write_text(line + "\n", encoding="utf-8")


def _extract_note_heading_title(markdown: str) -> Optional[str]:
    m = re.search(r"^\s*#\s*(.+?)\s*$", markdown or "", flags=re.MULTILINE)
    if not m:
        return None
    title = m.group(1).strip().strip('"')
    return title or None


def _extract_primary_subtopic(markdown: str) -> Optional[str]:
    m = re.search(r"^\s*subtopics:\s*(?:\r?\n|\r)\s*-\s*\"?(.+?)\"?\s*$", markdown or "", flags=re.MULTILINE)
    if not m:
        return None
    topic = m.group(1).strip().strip('"')
    return topic or None


def migrate_existing_instagram_note_filenames(*, cfg: PipelineConfig) -> dict[str, str]:
    instagram_dir = cfg.vault_path / "Instagram Notes"
    if not instagram_dir.exists():
        return {}
    marker = cfg.vault_path / ".filename_migration_done"
    if marker.exists():
        return {}

    rename_map: dict[str, str] = {}
    files = sorted(instagram_dir.glob("*.md"))
    for note_path in files:
        try:
            content = note_path.read_text(encoding="utf-8")
        except Exception:
            continue
        heading = _extract_note_heading_title(content) or _extract_primary_subtopic(content) or note_path.stem
        clean_title = _clean_title_text(heading)
        target_name = _render_note_filename(clean_title, cfg=cfg, existing_dir=instagram_dir)
        target_path = instagram_dir / target_name
        if target_path == note_path:
            continue
        # keep same file if render chose occupied name with same source URL content
        if target_path.exists():
            try:
                existing = target_path.read_text(encoding="utf-8")
                src_old = re.search(r'^source_url:\s*"(.*?)"\s*$', content, flags=re.MULTILINE)
                if src_old and f'source_url: "{src_old.group(1)}"' in existing:
                    rename_map[note_path.name] = target_path.name
                    continue
            except Exception:
                pass
        note_path.rename(target_path)
        rename_map[note_path.name] = target_path.name

    if rename_map and cfg.rewrite_vault_links_on_migration:
        rewrite_vault_links_from_map(cfg=cfg, rename_map=rename_map)
    if rename_map:
        update_processed_mapping_from_rename_map(cfg=cfg, rename_map=rename_map)
        snapshot = cfg.vault_path / f"filename-migration-map-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        try:
            snapshot.write_text(json.dumps(rename_map, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    marker.write_text(datetime.now().isoformat(timespec="seconds"), encoding="utf-8")
    return rename_map


def rewrite_vault_links_from_map(*, cfg: PipelineConfig, rename_map: dict[str, str]) -> None:
    if not rename_map:
        return
    md_files = list(cfg.vault_path.rglob("*.md"))
    for path in md_files:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        updated = text
        for old_name, new_name in rename_map.items():
            old_stem = Path(old_name).stem
            new_stem = Path(new_name).stem
            updated = updated.replace(f"[[Instagram Notes/{old_stem}|", f"[[Instagram Notes/{new_stem}|")
            updated = updated.replace(f"[[Instagram Notes/{old_name}|", f"[[Instagram Notes/{new_name}|")
            updated = updated.replace(f"[[Instagram Notes/{old_stem}]]", f"[[Instagram Notes/{new_stem}]]")
            updated = updated.replace(f"[[{old_stem}]]", f"[[{new_stem}]]")
        if updated != text:
            path.write_text(updated, encoding="utf-8")


def update_processed_mapping_from_rename_map(*, cfg: PipelineConfig, rename_map: dict[str, str]) -> None:
    if not rename_map:
        return
    processed = _load_processed(cfg.processed_db_path)
    changed = False
    for url, old_path_str in list(processed.items()):
        old_path = Path(old_path_str)
        old_name = old_path.name
        if old_name in rename_map:
            new_path = cfg.vault_path / "Instagram Notes" / rename_map[old_name]
            processed[url] = str(new_path)
            changed = True
    if changed:
        _save_processed(cfg.processed_db_path, processed)


def _write_graph_notes(
    *,
    payload: GraphPayload,
    transcript: str,
    url: str,
    cfg: PipelineConfig,
    visual_highlights: Optional[list[dict[str, Any]]] = None,
) -> Path:
    instagram_dir = cfg.vault_path / "Instagram Notes"
    topics_dir = cfg.vault_path / "Topics"
    entities_dir = cfg.vault_path / "Entities"
    indexes_dir = cfg.vault_path / "Indexes"
    for d in [instagram_dir, topics_dir, entities_dir, indexes_dir]:
        d.mkdir(parents=True, exist_ok=True)

    filename = _render_note_filename(payload.title, cfg=cfg)
    note_path = instagram_dir / filename
    suffix = 2
    while note_path.exists():
        existing = note_path.read_text(encoding="utf-8")
        if f'source_url: "{url.strip()}"' in existing:
            break
        stem = Path(filename).stem
        # normalize to base stem if already suffixed
        stem = re.sub(r"\s\(\d+\)$", "", stem)
        filename = f"{stem} ({suffix}).md"
        note_path = instagram_dir / filename
        suffix += 1

    topic_links = [f"[[Topics/{_slugify_filename(t)}|{t}]]" for t in payload.subtopics]
    entity_links = [f"[[Entities/{_slugify_filename(e.name)}|{e.name}]]" for e in payload.entities]
    frontmatter = _format_frontmatter(
        {
            "type": "video-note",
            "source_url": url.strip(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "title_generated_by": payload.title_generated_by,
            "alignment_score": f"{payload.alignment_score:.2f}",
            "verification_supported_count": int(payload.verification.get("supported_count", 0)),
            "verification_uncertain_count": int(payload.verification.get("uncertain_count", 0)),
            "verification_contradicted_count": int(payload.verification.get("contradicted_count", 0)),
            "transcript_useful": payload.transcript_useful,
            "transcript_quality_reasons": payload.transcript_quality_reasons,
            "caption_available": payload.caption_available,
            "caption_primary_context": payload.caption_primary_context,
            "transcript_caption_mismatch": payload.transcript_caption_mismatch,
            "transcript_caption_mismatch_reasons": payload.transcript_caption_mismatch_reasons,
            "category": payload.category,
            "subtopics": payload.subtopics,
            "entities": [e.name for e in payload.entities],
            "tags": payload.tags,
            "status": "processed",
        }
    )
    visual_section = ""
    if visual_highlights:
        lines = ["## Visual Highlights"]
        for item in visual_highlights:
            rel = str(item.get("relative_path", "")).strip()
            if not rel:
                continue
            ts = float(item.get("timestamp", 0.0))
            ocr_text = re.sub(r"\s+", " ", str(item.get("ocr_text", "")).strip())[:180]
            lines.append(f"- t={ts:.1f}s")
            lines.append(f"  - ![[{rel}]]")
            if ocr_text:
                lines.append(f"  - OCR: {ocr_text}")
        if len(lines) > 1:
            visual_section = "\n".join(lines) + "\n\n"

    final_md = (
        f"{frontmatter}\n"
        f"{payload.summary_markdown.rstrip()}\n\n"
        f"## Category\n- [[Indexes/Category - {payload.category.title()}|{payload.category.title()}]]\n\n"
        f"## Topics\n"
        + ("\n".join(f"- {link}" for link in topic_links) if topic_links else "- None")
        + "\n\n## Entities\n"
        + ("\n".join(f"- {link}" for link in entity_links) if entity_links else "- None")
        + "\n\n"
        + visual_section
        + (
            "## Transcript Quality Warning\n"
            + "\n".join(f"- {r}" for r in payload.transcript_quality_reasons)
            + "\n\n"
            if (not payload.transcript_useful and payload.transcript_quality_reasons)
            else ""
        )
        + (
            "## Context Source\n"
            + (
                "- Caption used as primary context due to weak or mismatched transcript.\n"
                if payload.caption_primary_context
                else "- Transcript remained primary context.\n"
            )
            + (
                "\n".join(f"- {r}" for r in payload.transcript_caption_mismatch_reasons) + "\n"
                if payload.transcript_caption_mismatch_reasons
                else ""
            )
            + "\n"
        )
        + "## Verification\n"
        + f"- Supported claims: {int(payload.verification.get('supported_count', 0))}\n"
        + f"- Uncertain claims: {int(payload.verification.get('uncertain_count', 0))}\n"
        + f"- Contradicted claims: {int(payload.verification.get('contradicted_count', 0))}\n"
        + (
            "\n".join(
                f"- Uncertain: {str(c.get('claim', '')).strip()}"
                for c in payload.verification.get("claims", [])
                if str(c.get("status", "")).strip().lower() == "uncertain"
            )
            + "\n\n"
            if payload.verification.get("claims")
            else "\n"
        )
        + f"## Source\n- Instagram link: {url.strip()}\n\n## Transcript\n\n{transcript.strip()}\n"
    )
    note_path.write_text(final_md, encoding="utf-8")

    video_rel = f"Instagram Notes/{filename}"
    for topic in payload.subtopics:
        slug = _slugify_filename(topic)
        path = topics_dir / f"{slug}.md"
        if not path.exists():
            path.write_text(
                _format_frontmatter(
                    {
                        "type": "topic-note",
                        "topic": topic,
                        "category": payload.category,
                        "tags": [f"topic/{slug}", f"domain/{_slugify_filename(payload.category)}"],
                    }
                )
                + f"\n# {topic}\n\n## Related Videos\n",
                encoding="utf-8",
            )
        _append_unique_line(path, f"- [[{video_rel}|{payload.title}]]")

    for entity in payload.entities:
        slug = _slugify_filename(entity.name)
        path = entities_dir / f"{slug}.md"
        if not path.exists():
            path.write_text(
                _format_frontmatter(
                    {
                        "type": "entity-note",
                        "entity": entity.name,
                        "entity_kind": entity.kind,
                        "tags": [f"topic/{slug}", f"domain/{_slugify_filename(payload.category)}"],
                    }
                )
                + f"\n# {entity.name}\n\n## Related Videos\n",
                encoding="utf-8",
            )
        _append_unique_line(path, f"- [[{video_rel}|{payload.title}]]")

    category_title = payload.category.title()
    category_index = indexes_dir / f"Category - {category_title}.md"
    if not category_index.exists():
        category_index.write_text(
            _format_frontmatter(
                {
                    "type": "category-index",
                    "category": payload.category,
                    "tags": [f"domain/{_slugify_filename(payload.category)}"],
                }
            )
            + f"\n# Category - {category_title}\n\n## Videos\n",
            encoding="utf-8",
        )
    _append_unique_line(category_index, f"- [[{video_rel}|{payload.title}]]")
    return note_path


def process_instagram_link_detailed(url: str, *, force_process: bool = False) -> ProcessRunResult:
    """Download → transcribe → summarize → write note; return note path."""
    url = url.strip()
    if not INSTAGRAM_URL_RE.search(url):
        raise ValueError("URL does not look like an Instagram link.")

    cfg = _cfg()
    run_started = time.monotonic()
    _reset_llm_stage_stats()
    cfg.temp_dir.mkdir(parents=True, exist_ok=True)
    if cfg.migrate_existing_note_filenames:
        try:
            migrate_existing_instagram_note_filenames(cfg=cfg)
        except Exception:
            pass

    processed = _load_processed(cfg.processed_db_path)
    if url in processed:
        cached_path = Path(processed[url])
        if cached_path.exists():
            return ProcessRunResult(
                note_path=cached_path,
                elapsed_seconds=0.0,
                video_duration_seconds=0.0,
                estimated_total_seconds=0.0,
                estimated_remaining_seconds=0.0,
            )

        # Repair stale cached paths (for example after moving the vault).
        repaired_path = cfg.vault_path / "Instagram Notes" / cached_path.name
        if repaired_path.exists():
            processed[url] = str(repaired_path)
            _save_processed(cfg.processed_db_path, processed)
            return ProcessRunResult(
                note_path=repaired_path,
                elapsed_seconds=0.0,
                video_duration_seconds=0.0,
                estimated_total_seconds=0.0,
                estimated_remaining_seconds=0.0,
            )

    job_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    job_dir = cfg.temp_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    success = False
    video_duration_seconds = 0.0
    estimated_total_seconds = 0.0
    try:
        metadata = fetch_video_metadata(url.strip())
        estimate_data = estimate_processing_for_url(url)
        try:
            video_duration_seconds = max(0.0, float(metadata.get("duration_seconds") or 0.0))
        except Exception:
            video_duration_seconds = 0.0
        estimated_total_seconds = float(estimate_data.get("estimated_total_seconds", 0.0) or 0.0)
        stage_estimates = dict(estimate_data.get("stage_estimates", {}))
        sample_counts = dict(estimate_data.get("sample_counts", {}))
        provider = str(estimate_data.get("provider") or ("openrouter" if cfg.openrouter_api_key else "ollama"))
        model = str(estimate_data.get("model") or (cfg.openrouter_model if cfg.openrouter_api_key else cfg.ollama_model))
        _set_active_run_url(url)
        _update_run_snapshot(
            url,
            {
                "url": url,
                "provider": provider,
                "model": model,
                "confidence": "conservative",
                "video_duration_seconds": video_duration_seconds,
                "estimated_total_seconds": estimated_total_seconds,
                "estimated_remaining_seconds": estimated_total_seconds,
                "stage_estimates": stage_estimates,
                "sample_counts": sample_counts,
                "completed_stage_seconds": {},
                "run_started_monotonic": run_started,
                "elapsed_seconds": 0.0,
                "status": "running",
            },
        )
        run_icon = "⏱️" if cfg.emoji_logs_enabled else ""
        print(
            f"[PIPELINE] {run_icon} RUN start video_duration={video_duration_seconds:.1f}s eta={estimated_total_seconds:.1f}s".strip()
        )

        video_path = download_instagram_video(
            url,
            job_dir,
            cookies_from_browser=cfg.cookies_from_browser,
            cookies_file=cfg.cookies_file,
        )
        if video_duration_seconds <= 0:
            video_duration_seconds = _video_duration_seconds(video_path)
            if estimated_total_seconds <= 0:
                estimated_total_seconds = _estimate_total_runtime_seconds(video_duration_seconds, cfg=cfg)
        metadata = metadata if cfg.caption_context_enabled else {"caption": "", "post_title": "", "uploader": "", "duration_seconds": video_duration_seconds}
        caption_context = (metadata.get("caption") or metadata.get("post_title") or "").strip()
        frame_insights: list[dict[str, Any]] = []
        selected_frames: list[dict[str, Any]] = []
        visual_context = ""
        alignment_result: dict[str, Any] = {"score": 0.0, "context": "(none)"}
        if cfg.visual_context_enabled:
            try:
                frame_paths = extract_keyframes(video_path, job_dir, cfg=cfg)
                duration_seconds = _video_duration_seconds(video_path)
                frame_insights = analyze_frames_with_ocr(frame_paths, cfg=cfg, duration_seconds=duration_seconds)
                selected_frames = select_best_frames(frame_insights, max_images=cfg.max_images_per_note)
                visual_context = build_visual_context(frame_insights)
                alignment_result = align_ocr_transcript("", frame_insights)
            except Exception:
                frame_insights = []
                selected_frames = []
                visual_context = ""
                alignment_result = {"score": 0.0, "context": "(none)"}

        audio_path = extract_audio(video_path, job_dir)
        transcript = transcribe_audio(audio_path)
        transcript_quality = assess_transcript_quality(transcript, cfg=cfg)
        caption_alignment = assess_transcript_caption_alignment(transcript, caption_context, cfg=cfg)
        caption_word_count = len(re.findall(r"[a-zA-Z0-9']+", caption_context))
        caption_strong = caption_word_count >= cfg.caption_min_words
        caption_primary_context = (
            cfg.caption_primary_when_transcript_weak
            and (not bool(transcript_quality.get("is_useful", True)))
            and caption_strong
        )
        if (
            cfg.transcript_gate_enabled
            and (
                ((not bool(transcript_quality.get("is_useful", True))) and not caption_primary_context)
                or (cfg.caption_mismatch_gate_enabled and bool(caption_alignment.get("is_mismatch", False)) and not caption_primary_context)
            )
            and (not force_process or not cfg.transcript_gate_allow_force)
        ):
            reasons = list(transcript_quality.get("reasons", []))
            reasons.extend(list(caption_alignment.get("mismatch_reasons", [])))
            raise LowTranscriptSignalError(
                url=url.strip(),
                reasons=reasons,
                metrics={
                    "transcript": dict(transcript_quality.get("metrics", {})),
                    "caption": dict(caption_alignment.get("metrics", {})),
                    "caption_word_count": caption_word_count,
                },
            )
        if frame_insights:
            alignment_result = align_ocr_transcript(transcript, frame_insights)
        if caption_context:
            alignment_result["context"] = (
                str(alignment_result.get("context", ""))
                + "\n"
                + str(caption_alignment.get("context", ""))
            ).strip()
        if cfg.pipeline_mode == "graph":
            taxonomy = _load_taxonomy(cfg)
            payload = build_obsidian_payload(
                transcript,
                cfg=cfg,
                taxonomy=taxonomy,
                visual_context=visual_context,
                alignment_result=alignment_result,
                transcript_quality=transcript_quality,
                caption_context=caption_context,
                caption_primary_context=caption_primary_context,
                caption_alignment=caption_alignment,
            )
            note_slug = _slugify_filename(payload.title)
            visual_assets = persist_selected_frames(selected_frames=selected_frames, cfg=cfg, note_slug=note_slug)
            note_path = _write_graph_notes(
                payload=payload,
                transcript=transcript,
                url=url,
                cfg=cfg,
                visual_highlights=visual_assets,
            )
        else:
            summary_md = summarize_transcript(
                transcript,
                cfg=cfg,
                visual_context=(visual_context + "\n\n" + str(alignment_result.get("context", "") + "\nCaption: " + caption_context)).strip(),
            )
            title = "instagram"
            m = re.search(r"^\s*#\s+(.+?)\s*$", summary_md, flags=re.MULTILINE)
            if m:
                title = m.group(1).strip().strip('"')
            filename = _render_note_filename(title, cfg=cfg, existing_dir=cfg.vault_path / "Instagram Notes")
            final_md = summary_md.rstrip() + "\n\n## Source\n- Instagram link: " + url.strip() + "\n\n## Transcript\n\n" + transcript + "\n"
            note_path = write_note(final_md, vault_path=cfg.vault_path, filename=filename)

        processed[url] = str(note_path)
        _save_processed(cfg.processed_db_path, processed)
        success = True
        elapsed = time.monotonic() - run_started
        done_icon = "✅" if cfg.emoji_logs_enabled else ""
        print(f"[PIPELINE] {done_icon} RUN done total={elapsed:.2f}s status=success".strip())
        return ProcessRunResult(
            note_path=note_path,
            elapsed_seconds=elapsed,
            video_duration_seconds=video_duration_seconds,
            estimated_total_seconds=estimated_total_seconds,
            estimated_remaining_seconds=0.0,
        )
    finally:
        print(_llm_stage_summary())
        if not success:
            elapsed = time.monotonic() - run_started
            fail_icon = "❌" if cfg.emoji_logs_enabled else ""
            print(f"[PIPELINE] {fail_icon} RUN done total={elapsed:.2f}s status=failed".strip())
            _update_run_snapshot(
                url,
                {
                    "status": "failed",
                    "elapsed_seconds": elapsed,
                    "estimated_remaining_seconds": 0.0,
                },
            )
        else:
            _update_run_snapshot(
                url,
                {
                    "status": "success",
                    "elapsed_seconds": max(0.0, time.monotonic() - run_started),
                    "estimated_remaining_seconds": 0.0,
                },
            )
        cleanup_temp_paths(cfg=cfg, job_dir=job_dir, success=success)
        _set_active_run_url(None)
        _remove_run_snapshot(url)


def process_instagram_link(url: str, *, force_process: bool = False) -> Path:
    return process_instagram_link_detailed(url, force_process=force_process).note_path
