#!/usr/bin/env python3
"""
Local registry for coding knowledge gaps, study priorities, and lesson plans.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
REGISTRY_PATH = DATA_DIR / "knowledge_registry.json"
LESSON_DIR = DATA_DIR / "lesson-plans"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", lowered)
    lowered = re.sub(r"-{2,}", "-", lowered)
    return lowered.strip("-") or "concept"


def normalize_label(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value.strip().lower())


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LESSON_DIR.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_PATH.exists():
        save_registry({"concepts": [], "updated_at": utc_now()})


def load_registry() -> dict[str, Any]:
    ensure_storage()
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def save_registry(data: dict[str, Any]) -> None:
    data["updated_at"] = utc_now()
    REGISTRY_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def score_concept(concept: dict[str, Any]) -> tuple[float, str]:
    encounter_count = int(concept.get("encounter_count", 0))
    confusion_count = int(concept.get("confusion_count", 0))
    importance_level = int(concept.get("importance_level", 3))
    blocker_level = int(concept.get("blocker_level", 3))
    prerequisite_count = len(concept.get("prerequisites", []))
    unresolved_bonus = 4 if concept.get("status") != "mastered" else 0
    lesson_bonus = 2 if concept.get("lesson_status") != "complete" else 0

    score = (
        importance_level * 3
        + blocker_level * 3
        + confusion_count * 2.5
        + encounter_count * 1.5
        + prerequisite_count * 0.5
        + unresolved_bonus
        + lesson_bonus
    )

    if score >= 32:
        rating = "S"
    elif score >= 24:
        rating = "A"
    elif score >= 16:
        rating = "B"
    else:
        rating = "C"
    return round(score, 1), rating


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_label(left), normalize_label(right)).ratio()


def find_match(
    incoming: dict[str, Any], concepts: list[dict[str, Any]]
) -> dict[str, Any] | None:
    incoming_title = incoming["title"].strip()
    incoming_slug = slugify(incoming_title)
    incoming_aliases = {normalize_label(item) for item in incoming.get("aliases", [])}
    incoming_aliases.add(normalize_label(incoming_title))

    best_match: dict[str, Any] | None = None
    best_score = 0.0

    for concept in concepts:
        if concept.get("slug") == incoming_slug:
            return concept

        haystack = [concept.get("title", "")]
        haystack.extend(concept.get("aliases", []))
        normalized_existing = {normalize_label(item) for item in haystack}
        if incoming_aliases & normalized_existing:
            return concept

        for candidate in haystack:
            candidate_score = similarity(incoming_title, candidate)
            if candidate_score > best_score:
                best_score = candidate_score
                best_match = concept

    if best_score >= 0.9:
        return best_match
    return None


def merge_concept(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    existing["title"] = existing.get("title") or incoming["title"].strip()
    existing["slug"] = existing.get("slug") or slugify(existing["title"])
    existing["summary"] = incoming.get("summary") or existing.get("summary", "")
    existing["why_now"] = incoming.get("why_now") or existing.get("why_now", "")
    existing["status"] = incoming.get("status") or existing.get("status", "unfamiliar")
    existing["lesson_status"] = incoming.get("lesson_status") or existing.get(
        "lesson_status", "missing"
    )
    existing["encounter_count"] = int(existing.get("encounter_count", 0)) + int(
        incoming.get("encounter_delta", 1)
    )

    confusion_level = int(incoming.get("confusion_level", 3))
    confusion_delta = int(incoming.get("confusion_delta", 1 if confusion_level >= 3 else 0))
    existing["confusion_count"] = int(existing.get("confusion_count", 0)) + confusion_delta
    existing["importance_level"] = max(
        int(existing.get("importance_level", 3)),
        int(incoming.get("importance_level", 3)),
    )
    existing["blocker_level"] = max(
        int(existing.get("blocker_level", 3)),
        int(incoming.get("blocker_level", 3)),
    )
    existing["aliases"] = unique_strings(existing.get("aliases", []) + incoming.get("aliases", []))
    existing["prerequisites"] = unique_strings(
        existing.get("prerequisites", []) + incoming.get("prerequisites", [])
    )
    existing["evidence"] = unique_strings(existing.get("evidence", []) + incoming.get("evidence", []))
    existing["sources"] = unique_strings(existing.get("sources", []) + incoming.get("sources", []))
    if incoming.get("lesson_plan_path"):
        existing["lesson_plan_path"] = incoming["lesson_plan_path"]
    existing["last_seen_at"] = utc_now()
    existing["created_at"] = existing.get("created_at") or utc_now()
    score, rating = score_concept(existing)
    existing["priority_score"] = score
    existing["priority_rating"] = rating
    return existing


def read_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def concept_summary(concept: dict[str, Any]) -> dict[str, Any]:
    return {
        "slug": concept["slug"],
        "title": concept["title"],
        "priority_score": concept["priority_score"],
        "priority_rating": concept["priority_rating"],
        "status": concept["status"],
        "lesson_status": concept.get("lesson_status", "missing"),
        "encounter_count": concept["encounter_count"],
        "confusion_count": concept["confusion_count"],
        "importance_level": concept["importance_level"],
        "blocker_level": concept["blocker_level"],
        "lesson_plan_path": concept.get("lesson_plan_path"),
    }


def sort_key(concept: dict[str, Any]) -> tuple[Any, ...]:
    return (
        -float(concept.get("priority_score", 0)),
        -int(concept.get("importance_level", 0)),
        -int(concept.get("blocker_level", 0)),
        concept.get("title", "").lower(),
    )


def cmd_upsert(args: argparse.Namespace) -> int:
    payload = read_json(args.input)
    incoming_concepts = payload.get("concepts", [])
    if not incoming_concepts:
        print(json.dumps({"updated": 0, "created": 0, "matched": 0}, ensure_ascii=False))
        return 0

    registry = load_registry()
    concepts = registry.setdefault("concepts", [])
    created = 0
    matched = 0
    updated_items: list[dict[str, Any]] = []

    for incoming in incoming_concepts:
        if "title" not in incoming or not str(incoming["title"]).strip():
            raise SystemExit("Each concept must include a non-empty 'title'.")

        matched_concept = find_match(incoming, concepts)
        if matched_concept is None:
            matched_concept = {}
            concepts.append(matched_concept)
            created += 1
        else:
            matched += 1

        updated = merge_concept(matched_concept, incoming)
        updated_items.append(concept_summary(updated))

    concepts.sort(key=sort_key)
    save_registry(registry)
    print(
        json.dumps(
            {
                "updated": len(incoming_concepts),
                "created": created,
                "matched": matched,
                "concepts": updated_items,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def format_text_list(concepts: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for index, concept in enumerate(concepts, start=1):
        lines.append(
            (
                f"{index}. {concept['title']} | rating={concept['priority_rating']} "
                f"| score={concept['priority_score']} | status={concept['status']} "
                f"| lesson={concept.get('lesson_status', 'missing')} "
                f"| seen={concept['encounter_count']} | confusion={concept['confusion_count']}"
            )
        )
    return "\n".join(lines) if lines else "No concepts found."


def filter_concepts(
    concepts: list[dict[str, Any]],
    status: str | None = None,
    unresolved_only: bool = False,
) -> list[dict[str, Any]]:
    items = concepts
    if status:
        items = [item for item in items if item.get("status") == status]
    if unresolved_only:
        items = [item for item in items if item.get("status") != "mastered"]
    return sorted(items, key=sort_key)


def cmd_list(args: argparse.Namespace) -> int:
    registry = load_registry()
    concepts = filter_concepts(
        registry.get("concepts", []),
        status=args.status,
        unresolved_only=args.unresolved_only,
    )
    if args.top:
        concepts = concepts[: args.top]

    if args.format == "json":
        print(json.dumps([concept_summary(item) for item in concepts], ensure_ascii=False, indent=2))
    else:
        print(format_text_list(concepts))
    return 0


def cmd_today(args: argparse.Namespace) -> int:
    registry = load_registry()
    concepts = filter_concepts(registry.get("concepts", []), unresolved_only=True)
    concepts = concepts[: args.top]
    if args.format == "json":
        print(json.dumps([concept_summary(item) for item in concepts], ensure_ascii=False, indent=2))
    else:
        if not concepts:
            print("No unresolved concepts found.")
            return 0
        top = concepts[0]
        print(
            "\n".join(
                [
                    f"Today focus: {top['title']}",
                    f"rating={top['priority_rating']} score={top['priority_score']}",
                    f"status={top['status']} lesson={top.get('lesson_status', 'missing')}",
                    f"seen={top['encounter_count']} confusion={top['confusion_count']}",
                    f"why_now={top.get('why_now', '')}",
                ]
            )
        )
        if args.top > 1:
            remainder = concepts[1:]
            if remainder:
                print("")
                print("Next up:")
                print(format_text_list(remainder))
    return 0


def render_lesson_markdown(concept: dict[str, Any], lesson: dict[str, Any]) -> str:
    sources = lesson.get("sources", [])
    source_lines = []
    for item in sources:
        if isinstance(item, dict):
            title = item.get("title", item.get("url", "source")).strip()
            url = item.get("url", "").strip()
            if url:
                source_lines.append(f"- [{title}]({url})")
            elif title:
                source_lines.append(f"- {title}")
        else:
            source_lines.append(f"- {str(item).strip()}")

    def bullet_lines(items: list[str]) -> str:
        cleaned = [f"- {str(item).strip()}" for item in items if str(item).strip()]
        return "\n".join(cleaned) if cleaned else "- None yet"

    return f"""# {lesson.get('title', concept['title'])}

## Learning Goal

{lesson.get('tagline', '')}

## Standard Definition

{lesson.get('definition', '')}

## Why It Matters In Current Coding Work

{lesson.get('why_it_matters', concept.get('why_now', ''))}

## Prerequisites

{bullet_lines(lesson.get('prerequisites', concept.get('prerequisites', [])))}

## Finance Analogy

{lesson.get('finance_analogy', '')}

## Concrete Examples

{bullet_lines(lesson.get('examples', []))}

## Common Mistakes

{bullet_lines(lesson.get('common_mistakes', []))}

## Exercises

{bullet_lines(lesson.get('exercises', []))}

## Next Steps

{bullet_lines(lesson.get('next_steps', []))}

## Sources

{chr(10).join(source_lines) if source_lines else "- Add official docs or primary references"}
"""


def cmd_render_lesson(args: argparse.Namespace) -> int:
    lesson = read_json(args.input)
    registry = load_registry()
    concepts = registry.get("concepts", [])

    concept = None
    if args.slug:
        for item in concepts:
            if item.get("slug") == args.slug:
                concept = item
                break
    elif lesson.get("title"):
        concept = find_match({"title": lesson["title"]}, concepts)

    if concept is None:
        raise SystemExit("Concept not found in registry. Upsert it before rendering a lesson.")

    lesson_filename = f"{concept['slug']}.md"
    output_path = LESSON_DIR / lesson_filename
    markdown = render_lesson_markdown(concept, lesson)
    write_text(output_path, markdown)

    concept["lesson_plan_path"] = str(output_path.relative_to(ROOT))
    concept["lesson_status"] = lesson.get("lesson_status", "drafted")
    score, rating = score_concept(concept)
    concept["priority_score"] = score
    concept["priority_rating"] = rating
    save_registry(registry)

    print(
        json.dumps(
            {
                "title": concept["title"],
                "slug": concept["slug"],
                "lesson_plan_path": str(output_path),
                "lesson_status": concept["lesson_status"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    registry = load_registry()
    concepts = registry.get("concepts", [])
    target = None
    for concept in concepts:
        if concept.get("slug") == args.slug:
            target = concept
            break
    if target is None:
        raise SystemExit(f"Concept '{args.slug}' not found.")
    print(json.dumps(target, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Track knowledge gaps encountered during coding work."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    upsert = subparsers.add_parser("upsert", help="Create or merge concept records from JSON.")
    upsert.add_argument("--input", required=True, help="Path to a JSON payload.")
    upsert.set_defaults(func=cmd_upsert)

    list_cmd = subparsers.add_parser("list", help="List tracked concepts.")
    list_cmd.add_argument("--status", help="Filter by status.")
    list_cmd.add_argument("--unresolved-only", action="store_true")
    list_cmd.add_argument("--top", type=int, default=0)
    list_cmd.add_argument("--format", choices=["text", "json"], default="text")
    list_cmd.set_defaults(func=cmd_list)

    today = subparsers.add_parser("today", help="Show today's highest-priority study item.")
    today.add_argument("--top", type=int, default=3)
    today.add_argument("--format", choices=["text", "json"], default="text")
    today.set_defaults(func=cmd_today)

    render_lesson = subparsers.add_parser(
        "render-lesson",
        help="Render a lesson plan markdown file from JSON.",
    )
    render_lesson.add_argument("--input", required=True, help="Path to lesson JSON payload.")
    render_lesson.add_argument("--slug", help="Concept slug to attach the lesson to.")
    render_lesson.set_defaults(func=cmd_render_lesson)

    show = subparsers.add_parser("show", help="Show a concept as JSON.")
    show.add_argument("--slug", required=True)
    show.set_defaults(func=cmd_show)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    ensure_storage()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
