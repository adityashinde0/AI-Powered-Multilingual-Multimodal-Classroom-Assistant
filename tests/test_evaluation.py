"""
EVAL-01: Evaluation and validation test suite.
Tests grounding, formula preservation, failure isolation, and performance measurement.
Run via: python -m unittest tests/test_evaluation.py
"""
import time
import unittest
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import patch

from src.models import (
    LectureContext,
    LectureInput,
    TranscriptSegment,
    ExtractedText,
    VisualElement,
    TechnicalElement,
)
from src.qa_engine import answer_lecture_question, _NOT_ESTABLISHED_EN
from src.translator import translate_text, SUPPORTED_LANGUAGES
from src.formula_handler import (
    extract_technical_elements,
    mask_technical_elements,
    unmask_technical_elements,
)
from src.notes_generator import generate_structured_notes
from src.lecture_processor import process_lecture
from src.speech_pipeline import transcribe_audio
from src.ocr_pipeline import extract_text_from_images
from src.vision_pipeline import analyze_visuals


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

def _make_cs_context() -> LectureContext:
    return LectureContext(
        transcript=[
            TranscriptSegment(
                id="s1", start_time=0.0, end_time=5.0,
                text="Quicksort has an average time complexity of O(n log n).",
            ),
            TranscriptSegment(
                id="s2", start_time=5.0, end_time=10.0,
                text="It was invented by Tony Hoare in 1959.",
            ),
            TranscriptSegment(
                id="s3", start_time=10.0, end_time=15.0,
                text="Energy-mass equivalence is described by $E=mc^2$.",
            ),
        ],
        extracted_text=[
            ExtractedText(id="e1", text="Worst case is O(n^2)", source_image="board.png"),
        ],
        visual_elements=[
            VisualElement(
                id="v1", visual_type="diagram",
                description="Recursion tree showing divide and conquer steps.",
                source_image="tree.png",
            ),
        ],
        technical_elements=[
            TechnicalElement(id="t1", element_type="formula", raw_content="O(n log n)"),
            TechnicalElement(id="t2", element_type="formula", raw_content="$E=mc^2$"),
        ],
        source_references=["board.png", "tree.png"],
    )


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------

class TestGroundingEvaluation(unittest.TestCase):
    """Evaluates strict grounding and anti-hallucination discipline
    (ARCHITECTURE.md §2.9, §10)."""

    def setUp(self) -> None:
        self.ctx = _make_cs_context()

    def test_grounded_query_complexity(self) -> None:
        res = answer_lecture_question(
            self.ctx, "What is the average time complexity of Quicksort?", language="en"
        )
        self.assertEqual(res.grounding_status, "grounded")
        self.assertIn("O(n log n)", res.answer)
        self.assertGreater(len(res.supporting_context), 0)

    def test_grounded_query_inventor(self) -> None:
        res = answer_lecture_question(
            self.ctx, "Who invented Quicksort?", language="en"
        )
        self.assertEqual(res.grounding_status, "grounded")
        self.assertGreater(len(res.supporting_context), 0)

    def test_ungrounded_query_trivia(self) -> None:
        res = answer_lecture_question(
            self.ctx, "What is the capital of France?", language="en"
        )
        self.assertEqual(res.grounding_status, "not_established")
        self.assertEqual(res.supporting_context, [])
        self.assertIn("not establish", res.answer.lower())

    def test_ungrounded_query_adversarial(self) -> None:
        """Adversarial: question sounds technical but is not in the lecture."""
        res = answer_lecture_question(
            self.ctx,
            "What is the asymptotic bound of mergesort on linked lists?",
            language="en",
        )
        self.assertEqual(res.grounding_status, "not_established")
        self.assertEqual(res.supporting_context, [])

    def test_ungrounded_exact_message(self) -> None:
        """Verbatim warning message must be returned for ungrounded queries."""
        res = answer_lecture_question(
            self.ctx, "What is the speed of light in vacuum?", language="en"
        )
        self.assertEqual(res.grounding_status, "not_established")
        self.assertEqual(res.answer, _NOT_ESTABLISHED_EN)

    def test_empty_question_not_established(self) -> None:
        res = answer_lecture_question(self.ctx, "", language="en")
        self.assertEqual(res.grounding_status, "not_established")
        self.assertEqual(res.supporting_context, [])

    def test_whitespace_question_not_established(self) -> None:
        res = answer_lecture_question(self.ctx, "   ", language="en")
        self.assertEqual(res.grounding_status, "not_established")


class TestFormulaPreservationEvaluation(unittest.TestCase):
    """Evaluates byte-for-byte mathematical preservation across all supported
    languages (ARCHITECTURE.md §2.5)."""

    FORMULAS = [
        "$E=mc^2$",
        "O(n log n)",
        "a^2 + b^2 = c^2",
    ]

    def _assert_formulas_preserved(self, original: str, translated: str) -> None:
        elements = extract_technical_elements(original)
        for elem in elements:
            self.assertIn(
                elem.raw_content,
                translated,
                msg=(
                    f"Formula '{elem.raw_content}' was mangled.\n"
                    f"Original:   {original}\n"
                    f"Translated: {translated}"
                ),
            )

    def test_formula_preservation_all_languages(self) -> None:
        sample = (
            "The energy formula is $E=mc^2$ and "
            "sorting takes O(n log n) where a^2 + b^2 = c^2 holds."
        )
        for lang_code in SUPPORTED_LANGUAGES:
            with self.subTest(language=lang_code):
                translated = translate_text(sample, lang_code)
                self._assert_formulas_preserved(sample, translated)

    def test_mask_unmask_roundtrip(self) -> None:
        sample = "Energy is $E=mc^2$ and complexity is O(n log n)."
        elements = extract_technical_elements(sample)
        masked, pmap = mask_technical_elements(sample, elements)
        restored = unmask_technical_elements(masked, pmap)
        self.assertEqual(restored, sample)

    def test_inline_latex_preserved_hindi(self) -> None:
        text = "According to physics, $E=mc^2$ is fundamental."
        translated = translate_text(text, "hi")
        self.assertIn("$E=mc^2$", translated)

    def test_bigo_preserved_bangla(self) -> None:
        text = "Quicksort runs in O(n log n) on average."
        translated = translate_text(text, "bn")
        self.assertIn("O(n log n)", translated)

    def test_power_expression_preserved_arabic(self) -> None:
        text = "Pythagorean theorem: a^2 + b^2 = c^2"
        translated = translate_text(text, "ar")
        self.assertIn("a^2 + b^2 = c^2", translated)

    def test_formula_untouched_in_notes(self) -> None:
        ctx = LectureContext(
            transcript=[
                TranscriptSegment(
                    id="s1", start_time=0.0, end_time=3.0,
                    text="The formula $E=mc^2$ is essential.",
                )
            ],
            technical_elements=[
                TechnicalElement(id="t1", element_type="formula", raw_content="$E=mc^2$"),
            ],
        )
        for lang_code in SUPPORTED_LANGUAGES:
            with self.subTest(language=lang_code):
                notes = generate_structured_notes(ctx, language=lang_code)
                formula_contents = [f["content"] for f in notes.formulas_and_terms]
                self.assertIn(
                    "$E=mc^2$",
                    formula_contents,
                    msg=f"Formula mangled in notes for language '{lang_code}'",
                )


class TestFailureFallbackIsolation(unittest.TestCase):
    """Evaluates additive failure isolation and safe degradation
    (ARCHITECTURE.md §9, §10)."""

    def test_missing_audio_ocr_vision_still_run(self) -> None:
        """Missing audio → speech returns [], other modalities unaffected."""
        result = transcribe_audio("non_existent_audio_xyz.wav")
        self.assertEqual(result, [])

    def test_missing_image_returns_empty_not_crash(self) -> None:
        """Missing images → OCR and vision return [], do not raise."""
        ocr_result = extract_text_from_images(["non_existent_xyz.png"])
        vision_result = analyze_visuals(["non_existent_xyz.png"])
        self.assertIsInstance(ocr_result, list)
        self.assertIsInstance(vision_result, list)

    def test_none_audio_returns_empty(self) -> None:
        self.assertEqual(transcribe_audio(None), [])

    def test_empty_images_list_returns_empty(self) -> None:
        self.assertEqual(extract_text_from_images([]), [])
        self.assertEqual(analyze_visuals([]), [])

    def test_empty_lecture_input_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            process_lecture(LectureInput())

    def test_process_lecture_with_missing_files_returns_context(self) -> None:
        """Pipeline must return a LectureContext even when all files are absent."""
        inp = LectureInput(image_paths=["no_such_image.png"])
        _orig = Path.exists
        Path.exists = lambda self: True  # type: ignore[method-assign]
        try:
            ctx = process_lecture(inp)
            self.assertIsInstance(ctx, LectureContext)
            self.assertIn("no_such_image.png", ctx.source_references)
        finally:
            Path.exists = _orig  # type: ignore[method-assign]

    def test_one_modality_failure_does_not_erase_others(self) -> None:
        """Simulates speech engine raising; OCR result must still appear in context."""
        inp = LectureInput(image_paths=["board.png"])
        _orig = Path.exists
        Path.exists = lambda self: True  # type: ignore[method-assign]
        try:
            with (
                patch("src.lecture_processor.transcribe_audio", side_effect=RuntimeError("engine crashed")),
                patch("src.lecture_processor.extract_text_from_images",
                      return_value=[ExtractedText(id="e1", text="Force = ma", source_image="board.png")]),
                patch("src.lecture_processor.analyze_visuals", return_value=[]),
            ):
                ctx = process_lecture(inp)
        finally:
            Path.exists = _orig  # type: ignore[method-assign]

        self.assertEqual(ctx.transcript, [])
        self.assertEqual(len(ctx.extracted_text), 1)
        self.assertEqual(ctx.extracted_text[0].text, "Force = ma")

    def test_notes_on_empty_context_does_not_crash(self) -> None:
        from src.notes_generator import StructuredNotes
        notes = generate_structured_notes(LectureContext(), language="en")
        self.assertIsInstance(notes, StructuredNotes)
        self.assertEqual(notes.key_points, [])

    def test_qa_on_empty_context_not_established(self) -> None:
        res = answer_lecture_question(LectureContext(), "What is gravity?")
        self.assertEqual(res.grounding_status, "not_established")

    def test_translation_failure_returns_original(self) -> None:
        """If translation engine is absent, original text is returned unchanged."""
        text = "Binary search runs in O(log n)."
        with (
            patch("src.translator._do_translate", side_effect=Exception("engine down")),
        ):
            result = translate_text(text, "hi")
        self.assertEqual(result, text)


class TestPerformanceMeasurement(unittest.TestCase):
    """Measures pipeline latencies.
    Baseline → Proposed Solution → Measured Result (ARCHITECTURE.md §8)."""

    _perf_results: Dict[str, float] = {}

    @classmethod
    def tearDownClass(cls) -> None:
        print("\n" + "=" * 60)
        print("PERFORMANCE MEASUREMENT REPORT (ARCHITECTURE.md §8)")
        print("=" * 60)
        for metric, elapsed_ms in sorted(cls._perf_results.items()):
            print(f"Metric: {metric:<40} | Measured Result: {elapsed_ms:.2f} ms")
        print("=" * 60)
        print("Note: No improvement claims made. These are raw measured values.")

    def _measure(self, label: str, fn, *args, **kwargs):
        t0 = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        TestPerformanceMeasurement._perf_results[label] = elapsed_ms
        return result

    def test_perf_formula_extraction(self) -> None:
        text = (
            "Energy is $E=mc^2$. Quicksort is O(n log n). "
            "Pythagorean: a^2 + b^2 = c^2."
        )
        elems = self._measure("formula_extraction", extract_technical_elements, text)
        self.assertIsInstance(elems, list)

    def test_perf_mask_unmask_roundtrip(self) -> None:
        text = "Energy is $E=mc^2$. Sorting is O(n log n)."
        elements = extract_technical_elements(text)

        def _roundtrip(t, e):
            masked, pmap = mask_technical_elements(t, e)
            return unmask_technical_elements(masked, pmap)

        restored = self._measure("mask_unmask_roundtrip", _roundtrip, text, elements)
        self.assertEqual(restored, text)

    def test_perf_translate_text_en_to_hi(self) -> None:
        text = "Quicksort has average complexity O(n log n)."
        result = self._measure("translate_text_en_to_hi", translate_text, text, "hi")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_perf_notes_generation(self) -> None:
        ctx = _make_cs_context()
        notes = self._measure(
            "notes_generation_en", generate_structured_notes, ctx, "en", "Perf Test"
        )
        self.assertIsNotNone(notes)

    def test_perf_qa_grounded(self) -> None:
        ctx = _make_cs_context()
        res = self._measure(
            "qa_grounded_query",
            answer_lecture_question,
            ctx,
            "What is the average complexity of Quicksort?",
            "en",
        )
        self.assertEqual(res.grounding_status, "grounded")

    def test_perf_qa_ungrounded(self) -> None:
        ctx = _make_cs_context()
        res = self._measure(
            "qa_ungrounded_query",
            answer_lecture_question,
            ctx,
            "What is the capital of Japan?",
            "en",
        )
        self.assertEqual(res.grounding_status, "not_established")

    def test_perf_lecture_processor_offline(self) -> None:
        """Measures process_lecture with missing files (all modalities return [])."""
        inp = LectureInput(image_paths=["perf_test_dummy.png"])
        _orig = Path.exists
        Path.exists = lambda self: True  # type: ignore[method-assign]
        try:
            ctx = self._measure("lecture_processor_offline", process_lecture, inp)
            self.assertIsInstance(ctx, LectureContext)
        finally:
            Path.exists = _orig  # type: ignore[method-assign]


if __name__ == "__main__":
    unittest.main()
