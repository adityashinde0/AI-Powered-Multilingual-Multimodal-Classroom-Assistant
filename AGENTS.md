# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project State

**Implementation has NOT started.** The repo is in Phase 0 — planning complete, no source code yet.
The three authoritative documents are:
- `PRD.md` — requirements baseline (source of truth for what must be built)
- `ARCHITECTURE.md` — architecture baseline (source of truth for how to build it)
- `PROGRESS.md` — execution state, task ownership, decisions log, blockers

## Context

- **Project:** The Smart Classroom — AI-powered multimodal multilingual classroom assistant
- **Hackathon:** IBM Hackathon, execution environment: **Google Antigravity**
- **Available MCPs:** Sequential Thinking, Stitch UI
- **Team roles:** Programmer 1 (lead/critical path), Programmer 2 (OCR/vision), Programmer 3 (UI/QA/eval)
- **Time box:** 24-hour implementation window

## Non-Obvious Constraints From the Docs

- **No stack is decided yet.** Technology, models, and vendors must be validated before selection. Do not assume Python, Node, or any specific model.
- **No database, vector DB, or microservices** unless a concrete need is demonstrated — this is an explicit architectural constraint, not a default.
- **Paid external APIs must be avoided** unless explicitly required or strongly justified (hackathon constraint).
- **Formulas and technical terms are a separate preservation concern** — they must not be passed through translation/rewriting as ordinary prose.
- **Q&A must be grounded in the processed lecture context only.** Unsupported answers must never be presented as lecture facts; the system must explicitly state when the lecture does not establish an answer.
- **One failed modality must not erase successful modalities** — fallback is additive, not destructive (e.g., OCR failure retains the source image).
- **Performance and quality claims require measurement first.** Use `Baseline → Proposed Solution → Measured Result`. Do not invent percentages.
- Languages in scope for MVP: **English, Hindi, Bangla, Arabic** (explicitly stated in problem statement).

## Decision Discipline

For every major external decision, record: `Decision → Evidence/source → Reason → Confidence`  
Confidence levels: High (problem-statement fact), Medium (credible evidence), Low (engineering judgment).

## Before Writing Any Code

1. Read `PRD.md` first.
2. Read `ARCHITECTURE.md` second.
3. Read `PROGRESS.md` third.
4. Identify which Programmer role (1, 2, or 3) the work falls under and stay within that ownership boundary.
5. Update `PROGRESS.md` after meaningful milestones.
