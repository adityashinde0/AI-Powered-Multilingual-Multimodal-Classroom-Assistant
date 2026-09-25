from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    from src.models import LectureInput, LectureContext
    from src.lecture_processor import process_lecture
    from src.notes_generator import generate_structured_notes, StructuredNotes
    from src.qa_engine import answer_lecture_question, QuestionResponse
    from src.translator import SUPPORTED_LANGUAGES
except ModuleNotFoundError:
    from models import LectureInput, LectureContext  # type: ignore[no-redef]
    from lecture_processor import process_lecture  # type: ignore[no-redef]
    from notes_generator import generate_structured_notes, StructuredNotes  # type: ignore[no-redef]
    from qa_engine import answer_lecture_question, QuestionResponse  # type: ignore[no-redef]
    from translator import SUPPORTED_LANGUAGES  # type: ignore[no-redef]


class SmartClassroomApp:
    """Student and Instructor session interface for The Smart Classroom."""

    def __init__(self, context: Optional[LectureContext] = None) -> None:
        self.context: Optional[LectureContext] = context

    def _safe_context(self) -> LectureContext:
        """Returns current context or an empty LectureContext if none is loaded."""
        return self.context if self.context is not None else LectureContext()

    def load_lecture(self, lecture_input: LectureInput) -> LectureContext:
        """Processes and loads lecture session into memory."""
        self.context = process_lecture(lecture_input)
        return self.context

    def get_notes(
        self,
        language: str = "en",
        title: Optional[str] = None,
    ) -> StructuredNotes:
        """Generates structured notes in the selected language."""
        return generate_structured_notes(
            self._safe_context(),
            language=language,
            title=title,
        )

    def ask(self, question: str, language: str = "en") -> QuestionResponse:
        """Queries lecture context strictly grounded with citations."""
        return answer_lecture_question(
            self._safe_context(),
            question=question,
            language=language,
        )

    def export_notes_markdown(
        self,
        output_path: str,
        language: str = "en",
        title: Optional[str] = None,
    ) -> str:
        """Exports structured notes to markdown file on disk, returning written path."""
        notes = self.get_notes(language=language, title=title)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(notes.to_markdown(), encoding="utf-8")
        return str(path)


if __name__ == "__main__":
    import sys
    import tempfile

    try:
        from src.models import TranscriptSegment, TechnicalElement
    except ModuleNotFoundError:
        from models import TranscriptSegment, TechnicalElement  # type: ignore[no-redef]

    # -----------------------------------------------------------------------
    # Acceptance tests
    # -----------------------------------------------------------------------
    app = SmartClassroomApp()

    # 1. Unloaded state safety test: must not crash
    empty_notes = app.get_notes(language="en")
    assert isinstance(empty_notes, StructuredNotes)
    empty_qa = app.ask("What is Quicksort?")
    assert empty_qa.grounding_status == "not_established"

    # 2. Mock lecture context load
    test_ctx = LectureContext(
        transcript=[TranscriptSegment(
            id="s1", start_time=0.0, end_time=2.0,
            text="Dijkstra algorithm computes shortest paths in graphs.",
        )],
        technical_elements=[TechnicalElement(
            id="t1", element_type="term", raw_content="Dijkstra",
        )],
    )
    app.context = test_ctx

    # 3. Notes generation
    notes = app.get_notes(language="en", title="Graph Algorithms")
    assert notes.title == "Graph Algorithms"
    assert len(notes.key_points) >= 1

    # 4. Grounded Q&A
    qa_res = app.ask("What does Dijkstra algorithm compute?")
    assert qa_res.grounding_status == "grounded", (
        f"Expected grounded, got: {qa_res.grounding_status}"
    )
    assert "shortest paths" in qa_res.answer, (
        f"Expected 'shortest paths' in answer: {qa_res.answer}"
    )

    # 5. Export notes markdown to disk
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = Path(tmpdir) / "test_notes.md"
        saved_path = app.export_notes_markdown(
            str(out_file), language="en", title="Graph Algorithms"
        )
        assert Path(saved_path).exists()
        content = Path(saved_path).read_text(encoding="utf-8")
        assert "# Graph Algorithms" in content

    print("ALL SMART CLASSROOM APP ACCEPTANCE TESTS PASSED")

    # -----------------------------------------------------------------------
    # Optional interactive CLI (only entered when --interactive flag passed)
    # -----------------------------------------------------------------------
    if "--interactive" in sys.argv:
        print("\n=== Smart Classroom Interactive Mode ===")
        print(f"Supported languages: {', '.join(f'{k} ({v})' for k, v in SUPPORTED_LANGUAGES.items())}")
        print("No lecture loaded. Set app.context or call app.load_lecture() to begin.")
        while True:
            try:
                user_input = input("\nAsk a question (or 'quit' to exit): ").strip()
                if user_input.lower() in ("quit", "exit", "q"):
                    break
                if not user_input:
                    continue
                lang = input("Language code [en]: ").strip() or "en"
                response = app.ask(user_input, language=lang)
                print(f"\nAnswer: {response.answer}")
                print(f"Status: {response.grounding_status}")
                if response.supporting_context:
                    print("Evidence:")
                    for snippet in response.supporting_context:
                        print(f"  - {snippet}")
            except (KeyboardInterrupt, EOFError):
                break
        print("Session ended.")
