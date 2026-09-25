import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict

try:
    from src.models import LectureContext
    from src.translator import translate_text
except ModuleNotFoundError:
    from models import LectureContext  # type: ignore[no-redef]
    from translator import translate_text  # type: ignore[no-redef]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_NOT_ESTABLISHED_EN = (
    "The processed lecture does not establish an answer to this question."
)

# Minimum keyword-overlap count to consider a snippet relevant
_RELEVANCE_THRESHOLD = 1

_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "on", "at", "by", "for", "with", "about",
    "against", "between", "into", "through", "during", "before", "after",
    "above", "below", "from", "up", "down", "out", "off", "over", "under",
    "again", "further", "then", "once", "and", "but", "or", "nor", "so",
    "yet", "both", "either", "neither", "not", "only", "own", "same",
    "than", "too", "very", "just", "what", "which", "who", "whom", "this",
    "that", "these", "those", "i", "me", "my", "myself", "we", "our",
    "you", "your", "he", "him", "his", "she", "her", "it", "its", "they",
    "them", "their", "how", "when", "where", "why", "all", "each", "every",
    "few", "more", "most", "other", "some", "such", "no", "any", "if",
})


# ---------------------------------------------------------------------------
# Contract dataclass
# ---------------------------------------------------------------------------

@dataclass
class QuestionResponse:
    answer: str
    supporting_context: List[str] = field(default_factory=list)
    grounding_status: str = "grounded"  # "grounded" | "not_established"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Common suffix normalisations for improved recall — these are applied as
# simple suffix rewrites, not full stemming, to keep the implementation
# stdlib-only and deterministic.
_SUFFIX_RULES: List[Tuple[str, str]] = [
    ("ities", "ity"),
    ("ity",   ""),
    ("ies",   "y"),
    ("ness",  ""),
    ("tion",  ""),
    ("sion",  ""),
    ("ing",   ""),
    ("ings",  ""),
    ("ment",  ""),
    ("ments", ""),
    ("ers",   "er"),
    ("ors",   "or"),
    ("sts",   "st"),
    ("ical",  "ic"),
    ("ally",  ""),
    ("able",  ""),
    ("ible",  ""),
    ("ful",   ""),
    ("less",  ""),
    ("ed",    ""),
    ("es",    ""),
    ("s",     ""),
]
_MIN_STEM_LEN = 4   # don't stem tokens shorter than this


def _stem(token: str) -> str:
    """Apply the first matching suffix rule; return unchanged if none match."""
    if len(token) < _MIN_STEM_LEN:
        return token
    for suffix, replacement in _SUFFIX_RULES:
        if token.endswith(suffix) and len(token) - len(suffix) >= _MIN_STEM_LEN:
            return token[: len(token) - len(suffix)] + replacement
    return token


def _tokenize(text: str) -> List[str]:
    """Lowercase alphanumeric tokens, stopwords removed, with light suffix normalisation."""
    raw = re.findall(r'[a-zA-Z0-9]+', text.lower())
    result: List[str] = []
    for t in raw:
        if t in _STOPWORDS:
            continue
        result.append(t)
        stemmed = _stem(t)
        if stemmed != t and stemmed and stemmed not in _STOPWORDS:
            result.append(stemmed)
    return result


def _relevance(query_tokens: List[str], snippet: str) -> int:
    """Count of query keywords present in snippet tokens (case-insensitive)."""
    snippet_tokens = set(re.findall(r'[a-zA-Z0-9]+', snippet.lower()))
    # Also add stemmed forms of snippet tokens for symmetric matching
    stemmed_snippet = {_stem(t) for t in snippet_tokens if len(t) >= _MIN_STEM_LEN}
    all_snippet = snippet_tokens | stemmed_snippet
    return sum(1 for t in query_tokens if t in all_snippet)


# AttributedSnippet: (raw_text_for_scoring, attributed_citation_string, score_placeholder)
_AttributedSnippet = Tuple[str, str]  # (raw_text, cited_text)


def _collect_snippets(context: LectureContext) -> List[_AttributedSnippet]:
    """Flatten all text-bearing context fields into (raw, cited) pairs."""
    snippets: List[_AttributedSnippet] = []
    for seg in context.transcript:
        raw = seg.text.strip()
        if raw:
            cited = f"[{seg.start_time:.1f}s - {seg.end_time:.1f}s] {raw}"
            snippets.append((raw, cited))
    for ext in context.extracted_text:
        raw = ext.text.strip()
        if raw:
            cited = f"[Image: {ext.source_image}] {raw}"
            snippets.append((raw, cited))
    for vis in context.visual_elements:
        raw = vis.description.strip()
        if raw:
            cited = f"[Visual: {vis.source_image}] {raw}"
            snippets.append((raw, cited))
        for entity in vis.key_entities:
            e = entity.strip()
            if e:
                snippets.append((e, f"[Visual entity: {vis.source_image}] {e}"))
    for tech in context.technical_elements:
        raw = tech.raw_content.strip()
        if raw:
            snippets.append((raw, f"[Formula/Term] {raw}"))
    return snippets


def _build_answer(question: str, matched: List[Tuple[int, str]]) -> str:
    """Construct a grounded answer from the top-scoring matched raw snippets."""
    top = sorted(matched, key=lambda x: x[0], reverse=True)[:3]
    evidence = " | ".join(s for _, s in top)
    return f"Based on the lecture: {evidence}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def answer_lecture_question(
    context: LectureContext,
    question: str,
    language: str = "en",
) -> QuestionResponse:
    """Answers a question strictly grounded in the LectureContext.
    If the lecture does not contain the answer, explicitly states that
    the lecture does not establish the answer (ARCHITECTURE.md §2.9, §9, §10)."""
    try:
        if not question or not question.strip():
            return QuestionResponse(
                answer=_NOT_ESTABLISHED_EN,
                supporting_context=[],
                grounding_status="not_established",
            )

        query_tokens = _tokenize(question)
        if not query_tokens:
            return QuestionResponse(
                answer=_NOT_ESTABLISHED_EN,
                supporting_context=[],
                grounding_status="not_established",
            )

        snippets = _collect_snippets(context)
        if not snippets:
            return QuestionResponse(
                answer=_NOT_ESTABLISHED_EN,
                supporting_context=[],
                grounding_status="not_established",
            )

        # Score every snippet against query keywords
        # scored entries: (score, raw_text, cited_text)
        scored: List[Tuple[int, str, str]] = []
        for raw, cited in snippets:
            score = _relevance(query_tokens, raw)
            if score >= _RELEVANCE_THRESHOLD:
                scored.append((score, raw, cited))

        if not scored:
            return QuestionResponse(
                answer=_NOT_ESTABLISHED_EN,
                supporting_context=[],
                grounding_status="not_established",
            )

        # Build answer from raw snippets; expose cited snippets as supporting_context
        top_scored = sorted(scored, key=lambda x: x[0], reverse=True)[:3]
        answer_en = _build_answer(question, [(sc, raw) for sc, raw, _ in top_scored])
        supporting = [cited for _, _, cited in top_scored]

        # Translate answer if requested language differs from English
        answer_final = (
            translate_text(answer_en, language)
            if language.strip().lower() not in ("en", "english")
            else answer_en
        )

        return QuestionResponse(
            answer=answer_final,
            supporting_context=supporting,
            grounding_status="grounded",
        )

    except Exception:
        return QuestionResponse(
            answer=_NOT_ESTABLISHED_EN,
            supporting_context=[],
            grounding_status="not_established",
        )


if __name__ == "__main__":
    try:
        from src.models import TranscriptSegment, ExtractedText, TechnicalElement
    except ModuleNotFoundError:
        from models import TranscriptSegment, ExtractedText, TechnicalElement

    ctx = LectureContext(
        transcript=[
            TranscriptSegment(id="s1", start_time=0.0, end_time=5.0,
                              text="Quicksort has an average time complexity of O(n log n)."),
            TranscriptSegment(id="s2", start_time=5.0, end_time=10.0,
                              text="It was developed by Tony Hoare in 1959."),
        ],
        extracted_text=[ExtractedText(id="e1", text="Worst case is O(n^2)", source_image="board.png")],
        technical_elements=[TechnicalElement(id="t1", element_type="formula", raw_content="O(n log n)")],
    )

    # 1. Grounded query: Answerable from lecture
    res1 = answer_lecture_question(ctx, "What is the average time complexity of Quicksort?", language="en")
    assert res1.grounding_status == "grounded", f"Expected grounded, got: {res1.grounding_status}"
    assert "O(n log n)" in res1.answer, f"O(n log n) missing from: {res1.answer}"
    assert len(res1.supporting_context) > 0, "Expected non-empty supporting_context"

    # 2. Ungrounded query: Not in lecture -> MUST return "not_established"
    res2 = answer_lecture_question(ctx, "What is the capital of France?", language="en")
    assert res2.grounding_status == "not_established", f"Expected not_established, got: {res2.grounding_status}"
    assert "not establish" in res2.answer.lower(), f"Expected 'not establish' in: {res2.answer}"
    assert res2.supporting_context == [], f"Expected empty supporting_context, got: {res2.supporting_context}"

    # 3. Empty question edge case
    res3 = answer_lecture_question(ctx, "", language="en")
    assert res3.grounding_status == "not_established", f"Expected not_established, got: {res3.grounding_status}"

    print("ALL QA ACCEPTANCE TESTS PASSED")
