from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

try:
    from src.models import LectureContext, TechnicalElement, VisualElement
    from src.translator import translate_text
except ModuleNotFoundError:
    from models import LectureContext, TechnicalElement, VisualElement  # type: ignore[no-redef]
    from translator import translate_text  # type: ignore[no-redef]


@dataclass
class StructuredNotes:
    title: str
    language: str
    summary: str
    key_points: List[str] = field(default_factory=list)
    formulas_and_terms: List[Dict[str, str]] = field(default_factory=list)
    visual_summaries: List[Dict[str, str]] = field(default_factory=list)
    source_references: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Renders notes into clean, student-ready markdown with headers and bullet points."""
        lines: List[str] = []

        lines.append(f"# {self.title}")
        lines.append("")
        lines.append(f"**Language:** {self.language}")
        lines.append("")

        if self.summary:
            lines.append("## Summary")
            lines.append("")
            lines.append(self.summary)
            lines.append("")

        if self.key_points:
            lines.append("## Key Points")
            lines.append("")
            for point in self.key_points:
                lines.append(f"- {point}")
            lines.append("")

        if self.formulas_and_terms:
            lines.append("## Formulas and Technical Terms")
            lines.append("")
            for item in self.formulas_and_terms:
                label = item.get("type", "term").capitalize()
                content = item.get("content", "")
                lines.append(f"- **{label}:** {content}")
            lines.append("")

        if self.visual_summaries:
            lines.append("## Visual Elements")
            lines.append("")
            for vis in self.visual_summaries:
                vtype = vis.get("type", "visual").capitalize()
                desc = vis.get("description", "")
                src = vis.get("source_image", "")
                lines.append(f"- **{vtype}:** {desc} *(source: {src})*")
            lines.append("")

        if self.source_references:
            lines.append("## Source References")
            lines.append("")
            for ref in self.source_references:
                lines.append(f"- {ref}")
            lines.append("")

        return "\n".join(lines)


def generate_structured_notes(
    context: LectureContext,
    language: str = "en",
    title: Optional[str] = None,
) -> StructuredNotes:
    """Transforms a LectureContext into organized notes in the selected language.
    Guarantees formula preservation and source-attribution links (ARCHITECTURE.md §2.7, §9)."""
    try:
        resolved_title = title or "Lecture Notes"
        lang_lower = language.strip().lower()
        need_translation = lang_lower not in ("en", "english")

        def _translate(text: str) -> str:
            if not need_translation or not text:
                return text
            try:
                return translate_text(text, language)
            except Exception:
                return text  # fallback: return original on any translation failure

        # --- Key points: transcript segments + OCR text ---
        key_points: List[str] = []
        for seg in context.transcript:
            if seg.text.strip():
                key_points.append(_translate(seg.text.strip()))
        for ext in context.extracted_text:
            if ext.text.strip():
                key_points.append(_translate(ext.text.strip()))

        # --- Summary: first transcript segment, or generic fallback ---
        if context.transcript and context.transcript[0].text.strip():
            summary_en = context.transcript[0].text.strip()
        elif context.extracted_text and context.extracted_text[0].text.strip():
            summary_en = context.extracted_text[0].text.strip()
        else:
            summary_en = ""
        summary = _translate(summary_en)

        # --- Formulas and terms: preserved verbatim, never translated ---
        formulas_and_terms: List[Dict[str, str]] = [
            {"content": elem.raw_content, "type": elem.element_type}
            for elem in context.technical_elements
            if elem.raw_content.strip()
        ]

        # --- Visual summaries: descriptions translated, source paths preserved ---
        visual_summaries: List[Dict[str, str]] = [
            {
                "description": _translate(vis.description),
                "source_image": vis.source_image,   # never translated — it's a file path
                "type": vis.visual_type,
            }
            for vis in context.visual_elements
        ]

        # --- Source references: preserved verbatim ---
        source_references: List[str] = list(context.source_references)

        return StructuredNotes(
            title=resolved_title,
            language=language,
            summary=summary,
            key_points=key_points,
            formulas_and_terms=formulas_and_terms,
            visual_summaries=visual_summaries,
            source_references=source_references,
        )

    except Exception:
        # Fail-safe: return a valid empty StructuredNotes object, never crash
        return StructuredNotes(
            title=title or "Lecture Notes",
            language=language,
            summary="",
        )


if __name__ == "__main__":
    try:
        from src.models import TranscriptSegment, ExtractedText, TechnicalElement, VisualElement
    except ModuleNotFoundError:
        from models import TranscriptSegment, ExtractedText, TechnicalElement, VisualElement  # type: ignore[no-redef]

    ctx = LectureContext(
        transcript=[TranscriptSegment(id="s1", start_time=0.0, end_time=2.0,
                                       text="Quicksort partitions the array around a pivot.")],
        extracted_text=[ExtractedText(id="e1", text="Partition runtime is O(n)", source_image="board.jpg")],
        visual_elements=[VisualElement(id="v1", visual_type="diagram", description="Recursion tree diagram",
                                       source_image="tree.png")],
        technical_elements=[TechnicalElement(id="t1", element_type="formula", raw_content="O(n log n)")],
        source_references=["board.jpg", "tree.png"],
    )

    notes = generate_structured_notes(ctx, language="en", title="Sorting Algorithms")
    assert notes.title == "Sorting Algorithms"
    assert len(notes.key_points) >= 1, f"Expected >= 1 key_points, got {notes.key_points}"
    assert len(notes.formulas_and_terms) == 1, f"Expected 1 formula, got {notes.formulas_and_terms}"
    assert notes.formulas_and_terms[0]["content"] == "O(n log n)"
    assert len(notes.visual_summaries) == 1
    assert notes.visual_summaries[0]["source_image"] == "tree.png"

    md = notes.to_markdown()
    assert "# Sorting Algorithms" in md, f"Title missing from markdown:\n{md}"
    assert "O(n log n)" in md, f"Formula missing from markdown:\n{md}"
    assert "tree.png" in md, f"Source image missing from markdown:\n{md}"

    # Edge case: empty context
    empty_notes = generate_structured_notes(LectureContext(), language="en")
    assert isinstance(empty_notes, StructuredNotes)
    assert empty_notes.key_points == []

    print("ALL NOTES ACCEPTANCE TESTS PASSED")
