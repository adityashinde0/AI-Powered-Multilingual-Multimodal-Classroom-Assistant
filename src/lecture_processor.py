from typing import Optional, List

try:
    from src.models import LectureInput, LectureContext, TechnicalElement
    from src.speech_pipeline import transcribe_audio
    from src.ocr_pipeline import extract_text_from_images
    from src.vision_pipeline import analyze_visuals
    from src.formula_handler import extract_technical_elements
except ModuleNotFoundError:
    from models import LectureInput, LectureContext, TechnicalElement  # type: ignore[no-redef]
    from speech_pipeline import transcribe_audio  # type: ignore[no-redef]
    from ocr_pipeline import extract_text_from_images  # type: ignore[no-redef]
    from vision_pipeline import analyze_visuals  # type: ignore[no-redef]
    from formula_handler import extract_technical_elements  # type: ignore[no-redef]


def process_lecture(lecture_input: LectureInput) -> LectureContext:
    """Orchestrates all lecture input modalities into a unified LectureContext.
    Enforces additive failure isolation: one failed modality does not erase successful ones
    (ARCHITECTURE.md §1, §2.6, §3, §9, §10)."""
    # Raises ValueError on empty input — intentionally not caught here
    lecture_input.validate()

    # --- Modality 1: Speech recognition ---
    transcript = []
    try:
        transcript = transcribe_audio(lecture_input.audio_path)
    except Exception:
        pass  # failure → continue with other modalities

    # --- Modality 2: OCR ---
    extracted_text = []
    try:
        extracted_text = extract_text_from_images(lecture_input.image_paths)
    except Exception:
        pass

    # --- Modality 3: Vision ---
    visual_elements = []
    try:
        visual_elements = analyze_visuals(lecture_input.image_paths)
    except Exception:
        pass

    # --- Technical element aggregation across all text-bearing modalities ---
    seen_raw: set = set()
    technical_elements: List[TechnicalElement] = []

    text_sources = (
        [seg.text for seg in transcript]
        + [ext.text for ext in extracted_text]
    )
    for text in text_sources:
        for elem in extract_technical_elements(text):
            if elem.raw_content not in seen_raw:
                seen_raw.add(elem.raw_content)
                technical_elements.append(elem)

    # --- Source references: audio + all images ---
    source_references: List[str] = []
    if lecture_input.audio_path:
        source_references.append(lecture_input.audio_path)
    source_references.extend(lecture_input.image_paths)

    return LectureContext(
        transcript=transcript,
        extracted_text=extracted_text,
        visual_elements=visual_elements,
        technical_elements=technical_elements,
        source_references=source_references,
    )


if __name__ == "__main__":
    from pathlib import Path

    # 1. Validation test: empty input fails safely
    try:
        process_lecture(LectureInput())
        assert False, "Should raise ValueError on empty input"
    except ValueError:
        pass

    # 2. Additive isolation test with non-existent files (pipelines return empty lists safely)
    inp = LectureInput(image_paths=["dummy_board.png"])
    _orig = Path.exists
    Path.exists = lambda self: True  # type: ignore[method-assign]
    try:
        ctx = process_lecture(inp)
        assert isinstance(ctx, LectureContext)
        assert "dummy_board.png" in ctx.source_references
    finally:
        Path.exists = _orig  # type: ignore[method-assign]

    print("ALL LECTURE PROCESSOR ACCEPTANCE TESTS PASSED")
