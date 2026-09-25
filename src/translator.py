import dataclasses
from typing import Optional, List, Dict

try:
    from src.models import LectureContext, TranscriptSegment, ExtractedText
    from src.formula_handler import (
        extract_technical_elements,
        mask_technical_elements,
        unmask_technical_elements,
    )
except ModuleNotFoundError:
    from models import LectureContext, TranscriptSegment, ExtractedText  # type: ignore[no-redef]
    from formula_handler import (  # type: ignore[no-redef]
        extract_technical_elements,
        mask_technical_elements,
        unmask_technical_elements,
    )


SUPPORTED_LANGUAGES: Dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "bn": "Bangla",
    "ar": "Arabic",
}


def _normalize_language(lang: str) -> Optional[str]:
    """Returns canonical BCP-47 code or None if unsupported."""
    lang = lang.strip().lower()
    if lang in SUPPORTED_LANGUAGES:
        return lang
    # Accept full names: "hindi" -> "hi", etc.
    for code, name in SUPPORTED_LANGUAGES.items():
        if lang == name.lower():
            return code
    return None


def _do_translate(text: str, target_code: str, source_code: str) -> str:
    """Attempt translation via available library. Returns original text on any failure."""
    # --- Attempt deep_translator (GoogleTranslator) ---
    try:
        from deep_translator import GoogleTranslator  # type: ignore
        return GoogleTranslator(source=source_code, target=target_code).translate(text)
    except ImportError:
        pass
    except Exception:
        return text  # network / API failure → original text

    # --- Attempt googletrans ---
    try:
        from googletrans import Translator  # type: ignore
        translator = Translator()
        result = translator.translate(text, src=source_code, dest=target_code)
        return result.text if result and result.text else text
    except ImportError:
        pass
    except Exception:
        return text  # failure → original text

    # No translation engine available — return original (architecture §9 fallback)
    return text


def translate_text(
    text: str,
    target_language: str,
    source_language: str = "en",
) -> str:
    """Translates text while strictly preserving formulas and technical terms.
    If target == source or translation fails, returns original text safely."""
    if not text:
        return text

    target_code = _normalize_language(target_language)
    source_code = _normalize_language(source_language) or "en"

    # Unsupported or identical language → return as-is
    if target_code is None or target_code == source_code:
        return text

    # 1. Extract and mask technical elements so the translator never sees them
    elements = extract_technical_elements(text)
    masked, placeholder_map = mask_technical_elements(text, elements)

    # 2. Translate the masked text (placeholders are opaque ASCII tokens)
    try:
        translated_masked = _do_translate(masked, target_code, source_code)
    except Exception:
        return text  # last-resort safety net

    # 3. Restore technical elements byte-for-byte
    restored = unmask_technical_elements(translated_masked, placeholder_map)

    return restored


def translate_lecture_context(
    context: LectureContext,
    target_language: str,
) -> LectureContext:
    """Returns a new LectureContext with translated transcript and extracted_text,
    leaving formulas, technical elements, and source_references preserved."""
    translated_transcript = [
        dataclasses.replace(seg, text=translate_text(seg.text, target_language))
        for seg in context.transcript
    ]

    translated_extracted = [
        dataclasses.replace(ext, text=translate_text(ext.text, target_language))
        for ext in context.extracted_text
    ]

    return LectureContext(
        transcript=translated_transcript,
        extracted_text=translated_extracted,
        # visual_elements, technical_elements, source_references are preserved unchanged
        visual_elements=list(context.visual_elements),
        technical_elements=list(context.technical_elements),
        source_references=list(context.source_references),
    )


if __name__ == "__main__":
    # 1. Identity translation (en -> en)
    text = "The algorithm runs in O(n log n) time and follows $E=mc^2$."
    assert translate_text(text, "en") == text

    # 2. Formula preservation: math tokens must never be mangled even when translating
    translated = translate_text(text, "hi")
    assert "$E=mc^2$" in translated, f"$E=mc^2$ missing from: {translated}"
    assert "O(n log n)" in translated, f"O(n log n) missing from: {translated}"

    # 3. Fallback on invalid/empty text
    assert translate_text("", "hi") == ""

    # 4. Context translation non-destructive test
    ctx = LectureContext(
        transcript=[TranscriptSegment(id="s1", start_time=0.0, end_time=2.0, text=text)],
        extracted_text=[ExtractedText(id="e1", text="Whiteboard $x=1$", source_image="board.jpg")],
    )
    translated_ctx = translate_lecture_context(ctx, "hi")
    assert len(translated_ctx.transcript) == 1
    assert "$E=mc^2$" in translated_ctx.transcript[0].text, (
        f"$E=mc^2$ missing from translated ctx: {translated_ctx.transcript[0].text}"
    )
    assert "$x=1$" in translated_ctx.extracted_text[0].text, (
        f"$x=1$ missing from translated ctx: {translated_ctx.extracted_text[0].text}"
    )
    # Ensure original context was not mutated
    assert ctx.transcript[0].text == text

    print("ALL TRANSLATION ACCEPTANCE TESTS PASSED")
