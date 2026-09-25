"""
DEMO-01: End-to-End Smart Classroom Demo Workflow
Topic: Quicksort & Divide-and-Conquer Algorithm Analysis

Demonstrates:
  - Multimodal lecture ingestion (speech, OCR, vision, formulas)
  - Four-language note generation (en, hi, bn, ar) with formula preservation
  - Grounded Q&A (answered from lecture)
  - Ungrounded Q&A (explicit not_established response, zero hallucination)

Run: python demo/run_demo.py
"""
import sys
from pathlib import Path
from typing import Dict

# Ensure project root is on path when run directly
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.models import (
    LectureContext,
    TranscriptSegment,
    ExtractedText,
    VisualElement,
    TechnicalElement,
)
from src.app import SmartClassroomApp
from src.translator import SUPPORTED_LANGUAGES


# ---------------------------------------------------------------------------
# Lecture fixture — realistic CS lecture scenario (PRD.md §10)
# ---------------------------------------------------------------------------

def _build_lecture_context() -> LectureContext:
    return LectureContext(
        transcript=[
            TranscriptSegment(
                id="s1", start_time=0.0, end_time=6.0,
                text=(
                    "Quicksort partitions the array around a pivot element, "
                    "placing smaller elements to the left and larger ones to the right."
                ),
            ),
            TranscriptSegment(
                id="s2", start_time=6.0, end_time=12.0,
                text=(
                    "The average-case time complexity of Quicksort is O(n log n), "
                    "making it one of the most efficient comparison-based sorting algorithms."
                ),
            ),
            TranscriptSegment(
                id="s3", start_time=12.0, end_time=18.0,
                text=(
                    "This follows from the divide-and-conquer recurrence: "
                    "T(n) = 2T(n/2) + O(n), which resolves to O(n log n) by the Master Theorem."
                ),
            ),
            TranscriptSegment(
                id="s4", start_time=18.0, end_time=24.0,
                text=(
                    "Quicksort was invented by Tony Hoare in 1959 and remains widely used "
                    "in practice due to its excellent cache performance."
                ),
            ),
        ],
        extracted_text=[
            ExtractedText(
                id="e1",
                text="Worst-case: O(n^2) — occurs when pivot is always min or max",
                source_image="whiteboard.png",
                confidence=0.95,
            ),
            ExtractedText(
                id="e2",
                text="Best-case: O(n log n) — balanced partitions",
                source_image="whiteboard.png",
                confidence=0.93,
            ),
        ],
        visual_elements=[
            VisualElement(
                id="v1",
                visual_type="diagram",
                description=(
                    "Recursion tree diagram showing Quicksort divide-and-conquer steps: "
                    "each level performs O(n) work across all partitions."
                ),
                source_image="tree.png",
                key_entities=["recursion tree", "partition", "pivot", "subarray"],
            ),
            VisualElement(
                id="v2",
                visual_type="graph",
                description=(
                    "Bar chart comparing average-case runtime of Quicksort O(n log n) "
                    "versus Bubble Sort O(n^2) for n = 1000."
                ),
                source_image="comparison_chart.png",
                key_entities=["Quicksort", "Bubble Sort", "runtime comparison"],
            ),
        ],
        technical_elements=[
            TechnicalElement(
                id="t1", element_type="formula",
                raw_content="O(n log n)",
                description="Average-case and best-case time complexity of Quicksort",
            ),
            TechnicalElement(
                id="t2", element_type="formula",
                raw_content="O(n^2)",
                description="Worst-case time complexity of Quicksort",
            ),
            TechnicalElement(
                id="t3", element_type="formula",
                raw_content="$E=mc^2$",
                description="Einstein mass-energy equivalence (formula preservation demo)",
            ),
            TechnicalElement(
                id="t4", element_type="technical_term",
                raw_content="divide-and-conquer",
                description="Algorithmic paradigm used by Quicksort",
            ),
        ],
        source_references=["whiteboard.png", "tree.png", "comparison_chart.png"],
    )


# ---------------------------------------------------------------------------
# Demo runner
# ---------------------------------------------------------------------------

NOTES_DIR = Path(__file__).parent / "notes"

FORMULAS_TO_CHECK = ["O(n log n)", "O(n^2)", "$E=mc^2$"]

IN_LECTURE_QUESTION = "What is the average time complexity of Quicksort?"
OUT_OF_LECTURE_QUESTION = "Who was the first president of the United States?"


def run_full_classroom_demo() -> bool:
    """Executes the complete end-to-end Smart Classroom workflow.
    Loads multimodal lecture, generates notes in 4 languages, tests grounded & ungrounded Q&A,
    exports notes to disk, and returns True on complete success."""
    passed = True
    results: Dict[str, str] = {}

    print("\n" + "=" * 65)
    print("  THE SMART CLASSROOM — END-TO-END DEMO")
    print("  Topic: Quicksort & Divide-and-Conquer Algorithm Analysis")
    print("=" * 65)

    # 1. Load lecture context into app
    print("\n[1/5] Loading multimodal lecture context...")
    app = SmartClassroomApp(context=_build_lecture_context())
    ctx = app.context
    assert ctx is not None
    print(f"      Transcript segments : {len(ctx.transcript)}")
    print(f"      OCR text blocks     : {len(ctx.extracted_text)}")
    print(f"      Visual elements     : {len(ctx.visual_elements)}")
    print(f"      Technical elements  : {len(ctx.technical_elements)}")
    print(f"      Source references   : {ctx.source_references}")
    results["Lecture load"] = "PASS"

    # 2. Four-language note generation + export
    print("\n[2/5] Generating and exporting notes in all 4 languages...")
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    for lang_code, lang_name in SUPPORTED_LANGUAGES.items():
        out_path = str(NOTES_DIR / f"notes_{lang_code}.md")
        saved = app.export_notes_markdown(out_path, language=lang_code, title="Quicksort & Divide-and-Conquer")
        content = Path(saved).read_text(encoding="utf-8")

        # Assert formulas exist byte-for-byte in every exported file
        for formula in FORMULAS_TO_CHECK:
            if formula not in content:
                print(f"      FAIL [{lang_code}] Formula '{formula}' missing from notes!")
                passed = False
                results[f"Notes {lang_code} formula preservation"] = "FAIL"
            else:
                results[f"Notes {lang_code} formula preservation"] = "PASS"

        title_ok = "# Quicksort" in content
        results[f"Notes {lang_code} title"] = "PASS" if title_ok else "FAIL"
        if not title_ok:
            passed = False
        print(f"      [{lang_code}] {lang_name:8s} -> {out_path}  {'OK' if title_ok else 'FAIL'}")

    # 3. Grounded Q&A
    print(f"\n[3/5] Grounded Q&A test...")
    print(f"      Question : {IN_LECTURE_QUESTION}")
    res_grounded = app.ask(IN_LECTURE_QUESTION, language="en")
    grounded_ok = (
        res_grounded.grounding_status == "grounded"
        and "O(n log n)" in res_grounded.answer
        and len(res_grounded.supporting_context) > 0
    )
    print(f"      Status   : {res_grounded.grounding_status}")
    print(f"      Answer   : {res_grounded.answer}")
    print(f"      Evidence : {res_grounded.supporting_context[:1]}")
    results["Grounded Q&A"] = "PASS" if grounded_ok else "FAIL"
    if not grounded_ok:
        passed = False
        print("      FAIL: grounded Q&A did not meet requirements")

    # 4. Ungrounded Q&A — zero hallucination gate
    print(f"\n[4/5] Ungrounded Q&A (hallucination gate)...")
    print(f"      Question : {OUT_OF_LECTURE_QUESTION}")
    res_ungrounded = app.ask(OUT_OF_LECTURE_QUESTION, language="en")
    ungrounded_ok = (
        res_ungrounded.grounding_status == "not_established"
        and res_ungrounded.supporting_context == []
        and "not establish" in res_ungrounded.answer.lower()
    )
    print(f"      Status   : {res_ungrounded.grounding_status}")
    print(f"      Answer   : {res_ungrounded.answer}")
    results["Ungrounded Q&A (no hallucination)"] = "PASS" if ungrounded_ok else "FAIL"
    if not ungrounded_ok:
        passed = False
        print("      FAIL: ungrounded Q&A did not meet requirements")

    # 5. Executive summary
    print("\n[5/5] Executive Summary")
    print("-" * 65)
    print(f"  {'Check':<45} {'Result':>6}")
    print("-" * 65)
    for check, status in results.items():
        marker = "OK" if status == "PASS" else "--"
        print(f"  {marker} {check:<43} {status:>6}")
    print("-" * 65)
    total = len(results)
    passing = sum(1 for s in results.values() if s == "PASS")
    print(f"  {passing}/{total} checks passed")
    print("=" * 65)
    print(f"  DEMO RESULT: {'ALL CHECKS PASSED' if passed else 'SOME CHECKS FAILED'}")
    print("=" * 65 + "\n")

    return passed


if __name__ == "__main__":
    import sys
    success = run_full_classroom_demo()
    sys.exit(0 if success else 1)
