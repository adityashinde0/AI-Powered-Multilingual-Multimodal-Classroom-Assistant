# The Smart Classroom
### AI-Powered Multilingual Multimodal Classroom Assistant

**Hackathon:** IBM Hackathon · Execution: Google Antigravity
**Status:** ![Tests](https://img.shields.io/badge/tests-30%2F30%20passing-brightgreen) ![Invariants](https://img.shields.io/badge/invariants-59%2F59%20verified-brightgreen) ![Languages](https://img.shields.io/badge/languages-en%20hi%20bn%20ar-blue)

---

## Problem

University lectures are multimodal and multilingual by nature. A professor speaks in English while students may prefer Hindi, Bangla, or Arabic. Critical information appears in speech, whiteboard text, diagrams, graphs, and formulas simultaneously. Students miss content, struggle to translate, and finish lectures with scattered notes and unresolved questions.

## Solution

An AI pipeline that understands a complete classroom lecture across all modalities and transforms it into a personalized, multilingual learning resource — structured notes, visual explanations, formula preservation, and lecture-grounded Q&A — in the student's preferred language.

---

## Core Capabilities

| Capability | Modality | PRD Req |
|---|---|---|
| Lecture speech transcription | Audio / Speech Recognition | FR-01 |
| Classroom text extraction | Images / OCR | FR-04 |
| Diagram & chart understanding | Images / Computer Vision | FR-05, FR-06 |
| Formula & technical term preservation | All modalities | FR-07 |
| Multilingual translation (en/hi/bn/ar) | LLM / Machine Translation | FR-02 |
| Structured note generation | LectureContext | FR-03 |
| Lecture-grounded Q&A | LectureContext / LLM | FR-08 |
| Student learning interface | Web UI | FR-10 |

---

## Architecture

### Data Flow

```
Lecture Input (audio + images)
        |
        v
  [Input Orchestrator]  ← LectureInput.validate()
   /       |       \
  v        v        v
Speech    OCR     Vision       ← Additive: one failure never aborts others
  \        |        /
   v       v       v
     [Formula Handler]         ← Extracts & preserves formulas/technical terms
            |
            v
    [LectureContext]            ← Unified in-memory representation
   /         |        \
  v          v         v
Notes    Translator   Q&A      ← translate_text() masks formulas before translation
  \          |         /
   v         v        v
       [Student UI]            ← Notes view + language selector + Q&A chat
            |
            v
     [Evaluation Layer]        ← 59 traceability checks, 30 unit tests
```

### Component Map

| Module | Responsibility |
|---|---|
| `src/models.py` | Core data contracts: `LectureInput`, `LectureContext`, all element types |
| `src/speech_pipeline.py` | `faster-whisper` → `whisper` → safe `[]` fallback |
| `src/ocr_pipeline.py` | `pytesseract` → PIL heuristic → safe `[]` fallback |
| `src/vision_pipeline.py` | PIL dimension classification → safe `[]` fallback |
| `src/formula_handler.py` | LaTeX / Big-O / equation detection, mask/unmask for translation |
| `src/translator.py` | `deep_translator` → `googletrans` → original-text fallback |
| `src/qa_engine.py` | Keyword-overlap retrieval, strict grounding, anti-hallucination gate |
| `src/notes_generator.py` | `LectureContext` → `StructuredNotes` → Markdown |
| `src/lecture_processor.py` | Orchestrates all modalities → `LectureContext` |
| `src/app.py` | `SmartClassroomApp` session API |
| `src/web_ui.py` | Zero-dependency HTTP server + Single-Page App |

---

## Engineering Invariants (ARCHITECTURE.md §10)

All 10 invariants verified by `tests/traceability_review.py` (59/59 checks):

1. **Never fabricate lecture information** — Q&A engine has no generative component; answers cite verbatim lecture snippets only.
2. **Never silently alter formulas** — `mask_technical_elements()` shields formulas from translation; `unmask_technical_elements()` restores byte-for-byte.
3. **Preserve technical terminology** — `TechnicalElement` records are never passed through translation.
4. **Additive failure isolation** — each modality (speech / OCR / vision) is wrapped in independent `try/except`; failure returns `[]`.
5. **Grounded Q&A** — answers only from `LectureContext`; `"The processed lecture does not establish an answer to this question."` returned when evidence is absent.
6. **No hallucinated answers** — same as invariant 5; `grounding_status` is always explicit.
7. **Secrets never reach client** — no credentials in `src/`; verified by static scan.
8. **Invalid inputs fail safely** — `LectureInput.validate()` raises `ValueError`; empty questions and empty contexts return `not_established`.
9. **No invented performance claims** — `Baseline → Proposed Solution → Measured Result` discipline enforced.
10. **Explicit testable interfaces** — all 24 public symbols verified importable by `tests/traceability_review.py`.

---

## Measured Latencies (No claims made before measurement)

| Metric | Measured Result |
|---|---|
| formula_extraction | ~0.10 ms |
| mask_unmask_roundtrip | ~0.02 ms |
| notes_generation_en | ~0.01 ms |
| qa_grounded_query | ~0.05 ms |
| qa_ungrounded_query | ~0.02 ms |
| translate_text_en_to_hi | ~2.0 ms (no engine = passthrough) |
| lecture_processor_offline | ~0.40 ms |

_All values measured locally; results will vary with real AI engine initialization._

---

## Quickstart

### Prerequisites

```bash
python --version   # Python 3.10+
```

Optional AI engine dependencies (graceful fallback if absent):

```bash
pip install faster-whisper        # Speech recognition
pip install pytesseract pillow    # OCR
pip install deep_translator       # Translation
```

### Run Unit Tests

```bash
python -m unittest tests/test_evaluation.py -v
```

### Run Traceability Audit (59-check quality gate)

```bash
python tests/traceability_review.py
```

### Run End-to-End Demo

```bash
python demo/run_demo.py
```

_Exports notes to `demo/notes/notes_{en,hi,bn,ar}.md`_

### Launch Student Web UI

```bash
python src/web_ui.py
# Open: http://localhost:8000
```

With auto-open browser:

```bash
python src/web_ui.py --open
```

### Self-Test Web UI

```bash
python src/web_ui.py --test
```

### Interactive Q&A (CLI)

```bash
python -m src.app --interactive
```

---

## Requirement Traceability (PRD.md §11)

| PRD Requirement | Implementation | Test |
|---|---|---|
| FR-01 Speech Understanding | `src/speech_pipeline.py` | `TestFailureFallbackIsolation` |
| FR-02 Multilingual Translation | `src/translator.py` | `TestFormulaPreservationEvaluation` |
| FR-03 Structured Notes | `src/notes_generator.py` | `TestPerformanceMeasurement` |
| FR-04 OCR / Whiteboard | `src/ocr_pipeline.py` | `TestFailureFallbackIsolation` |
| FR-05 Diagram Understanding | `src/vision_pipeline.py` | `TestFailureFallbackIsolation` |
| FR-06 Graph/Chart Understanding | `src/vision_pipeline.py` | `TestFailureFallbackIsolation` |
| FR-07 Formula Preservation | `src/formula_handler.py` | `TestFormulaPreservationEvaluation` |
| FR-08 Lecture Q&A | `src/qa_engine.py` | `TestGroundingEvaluation` |
| FR-09 Multimodal Pipeline | `src/lecture_processor.py` | `TestFailureFallbackIsolation` |
| FR-10 Student Interface | `src/app.py`, `src/web_ui.py` | `demo/run_demo.py` |

---

## Failure & Fallback Strategy

| Failure | Detection | Fallback |
|---|---|---|
| Speech recognition unavailable | `ImportError` / `Exception` | Returns `[]`; other modalities continue |
| OCR engine missing | `ImportError` / `Exception` | Returns `[]`; source image reference preserved |
| Vision model absent | PIL `ImportError` / `Exception` | Returns `[]`; source image reference preserved |
| Translation engine absent | `ImportError` / `Exception` | Returns original-language content |
| Formula detection failure | `Exception` | Returns original text unmasked |
| Q&A lacks lecture evidence | Score below threshold | Returns verbatim `not_established` message |
| Invalid lecture input | `LectureInput.validate()` | Raises `ValueError` — explicit, not silent |

---

## Project Files

```
IBM-01-PS/
├── src/
│   ├── models.py              # Core data contracts
│   ├── speech_pipeline.py     # Speech → TranscriptSegment[]
│   ├── ocr_pipeline.py        # Images → ExtractedText[]
│   ├── vision_pipeline.py     # Images → VisualElement[]
│   ├── formula_handler.py     # Formula detection, mask/unmask
│   ├── translator.py          # Multilingual translation
│   ├── qa_engine.py           # Grounded Q&A engine
│   ├── notes_generator.py     # LectureContext → StructuredNotes
│   ├── lecture_processor.py   # Orchestration pipeline
│   ├── app.py                 # Session API
│   └── web_ui.py              # Zero-dependency web server
├── tests/
│   ├── test_evaluation.py     # 30 unit tests (4 test classes)
│   └── traceability_review.py # 59-check quality gate
├── demo/
│   ├── run_demo.py            # End-to-end demo workflow
│   └── notes/                 # Generated notes (en/hi/bn/ar)
├── PRD.md                     # Requirements baseline
├── ARCHITECTURE.md            # Architecture baseline
├── PROGRESS.md                # Execution state
└── README.md                  # This file
```

---

## Source and Decision Discipline

Technology, model, and infrastructure choices are tracked with:
`Decision → Evidence/Source → Reason → Confidence`

No performance or accuracy claim is made before measurement.
See `ARCHITECTURE.md §12` for accepted technical debt.
