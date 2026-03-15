# Web Learning Coach

`web-learning-coach` is a Codex skill for turning web-coding confusion into a reusable study system.

It helps with four things:

- detect computer-science and software-engineering concepts the user likely does not understand yet
- expand those concepts into prerequisite topics
- store and score a local learning backlog based on recurrence and blocker impact
- generate lesson plans with standard definitions, finance-style analogies, and exercises

## Repository Layout

- `SKILL.md`: skill instructions and workflow
- `agents/openai.yaml`: UI metadata
- `scripts/knowledge_registry.py`: local registry, scoring, and lesson rendering
- `data/knowledge_registry.json`: saved concept backlog
- `data/lesson-plans/`: generated lesson plans
- `data/analysis/`: optional session notes

## Quick Start

List unresolved topics:

```bash
python3 scripts/knowledge_registry.py list --unresolved-only
```

Import newly discovered concepts:

```bash
python3 scripts/knowledge_registry.py upsert --input /tmp/concepts.json
```

See today's highest-priority study topic:

```bash
python3 scripts/knowledge_registry.py today --top 5
```

Render a lesson plan:

```bash
python3 scripts/knowledge_registry.py render-lesson --slug <concept-slug> --input /tmp/lesson.json
```
