---
name: web-learning-coach
description: Use this skill during web coding work to detect likely computer-science or software-engineering knowledge gaps, expand them into prerequisite concepts, deduplicate against an existing local registry, score importance based on recurrence and blocker impact, save a study queue locally, collect authoritative learning resources, and generate lesson plans with standard definitions, finance analogies, and exercises.
---

# Web Learning Coach

## Overview

Use this skill whenever coding work surfaces concepts the author probably does not understand well enough yet: framework internals, browser APIs, HTTP/networking, async flow, type systems, architecture patterns, tooling, testing, performance, security, databases, deployment, and adjacent software-engineering fundamentals.

The skill has two main jobs:

1. Turn coding friction into a local, reusable learning backlog.
2. Tell the user what they most need to learn today, backed by saved evidence and lesson plans.

## When To Trigger It

Trigger this skill when any of the following happens during web coding:

- The user asks what a concept means, even after it already appeared once before.
- A bug or review comment suggests a missing underlying concept, not just a typo.
- A concept blocks progress across multiple files, sessions, or frameworks.
- The user asks what they should study next, what they repeatedly do not understand, or what knowledge is missing under the surface.
- The user wants a structured mini-course, lesson plan, or practice questions for a coding topic.

## Workflow

### 1. Extract the visible concepts

Read only the code, error messages, PR comments, docs excerpts, or user question needed for the current task. Extract the concepts that look unfamiliar, unstable, or repeatedly confusing.

For each concept, capture:

- `title`: canonical concept name
- `summary`: one-line plain-language meaning
- `why_now`: why it matters in the current coding task
- `aliases`: close variants or alternate names
- `prerequisites`: lower-level concepts the author may also be missing
- `importance_level`: `1-5`
- `blocker_level`: `1-5`
- `confusion_level`: `1-5`
- `evidence`: direct evidence from the current session
- `sources`: current code paths, docs, or URLs if useful

When in doubt, prefer fewer, higher-signal concepts over a long noisy list.

### 2. Expand to hidden prerequisites

Do not stop at the surface term. Ask what must be understood underneath it.

Examples:

- `React hydration` may imply `SSR`, `DOM reconciliation`, `event delegation`, `browser parsing`, `network waterfalls`
- `Promise` may imply `event loop`, `microtask queue`, `async error propagation`
- `CORS` may imply `origin`, `preflight`, `HTTP headers`, `credential modes`

Add only prerequisites that are genuinely likely missing for this user. Avoid exploding the graph unnecessarily.

### 3. Check the local registry before adding anything new

Before creating a new concept, inspect the registry:

```bash
python3 scripts/knowledge_registry.py list --unresolved-only --format json
```

Then merge new findings with:

```bash
python3 scripts/knowledge_registry.py upsert --input /tmp/concepts.json
```

Use the same concept when the title, alias, or very close wording already exists. If a near-duplicate exists, update the existing record instead of creating a new one.

## Scoring And Priority

The registry script computes a `priority_score` and `priority_rating`.

The score grows when:

- the concept appears repeatedly
- confusion repeats
- the concept is foundational
- the concept blocks real work
- prerequisite depth is larger
- no complete lesson exists yet

Ratings:

- `S`: most urgent and foundational
- `A`: important and repeatedly relevant
- `B`: worthwhile but less urgent
- `C`: lower priority for now

Use the rating to decide what to teach first, not just what is newest.

## Local Storage

Keep all outputs inside this skill folder:

- Registry: `data/knowledge_registry.json`
- Lesson plans: `data/lesson-plans/<slug>.md`
- Optional per-session analysis notes: `data/analysis/`

Never scatter this skill's memory across unrelated folders.

## Lesson Plan Generation

When the user asks for teaching material, browse authoritative sources first. Prefer primary or official documentation:

- MDN for browser/web platform topics
- official framework docs
- standards or vendor docs when relevant
- high-quality primary references for tooling/runtime behavior

Then create a lesson JSON payload and render it:

```bash
python3 scripts/knowledge_registry.py render-lesson --slug <concept-slug> --input /tmp/lesson.json
```

Each lesson should include:

- a standard, rigorous definition
- why it matters in the current coding context
- prerequisite checklist
- a finance analogy using investing, markets, funds, accounting, risk, or trading language
- concrete examples
- common mistakes
- short exercises or quiz questions
- next steps
- source links

Keep the tone precise but easy to picture. The finance analogy should clarify, not replace, the correct definition.

## Daily Recommendation Mode

When the user asks questions like:

- "今天我最需要学什么？"
- "我最不知道的知识是什么？"
- "给我今天的学习重点"

Run:

```bash
python3 scripts/knowledge_registry.py today --top 5
```

Use the top result as the main recommendation. Explain:

- why it ranks highest
- what it is blocking
- what prerequisite concepts are underneath it
- whether a lesson plan already exists
- the next best two fallback topics

## Suggested JSON Payloads

Concept payload:

```json
{
  "concepts": [
    {
      "title": "Promise",
      "summary": "Represents the eventual completion or failure of an async operation.",
      "why_now": "The current fetch flow chains async work and error handling incorrectly.",
      "aliases": ["JavaScript Promise", "promises"],
      "prerequisites": ["event loop", "microtask queue"],
      "importance_level": 5,
      "blocker_level": 4,
      "confusion_level": 4,
      "status": "unfamiliar",
      "evidence": ["The user asked what resolve and reject mean in fetch handling."],
      "sources": ["src/api/client.ts"]
    }
  ]
}
```

Lesson payload:

```json
{
  "title": "Promise",
  "tagline": "Understand how JavaScript represents async outcomes.",
  "definition": "A Promise is a JavaScript object representing the eventual result of an asynchronous operation.",
  "why_it_matters": "Without it, async control flow and error handling become guesswork.",
  "prerequisites": ["event loop", "microtask queue"],
  "finance_analogy": "A Promise is like a pending trade ticket: it has not settled yet, but the system already knows it will eventually settle successfully or fail.",
  "examples": ["Use `await fetch(...)` to pause until the Promise settles."],
  "common_mistakes": ["Assuming `await` blocks the whole thread."],
  "exercises": ["Explain the difference between a pending and fulfilled Promise."],
  "next_steps": ["Study the microtask queue after this lesson."],
  "sources": [
    {
      "title": "MDN Promise",
      "url": "https://developer.mozilla.org/"
    }
  ]
}
```

## Operating Rules

- Prefer updating the registry over re-teaching from scratch every time.
- If a concept already has a lesson plan, reuse it and only refresh when the gap is deeper or the sources are weak.
- Keep concept names canonical and stable.
- When doing web searches, cite the exact sources used.
- If the concept is transient or too trivial, explain it inline and do not pollute the registry.
